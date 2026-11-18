# Groww Weekly Review Pulse — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an on-demand weekly review-pulse pipeline for the Groww Play app that imports ~8–12 weeks of public reviews, clusters ≤5 themes, writes a ≤250-word note (top 3 themes, 3 verbatim quotes, 3 actions), then delivers via Google Docs + Gmail draft using MCP.

**Architecture:** Separate `pulse/` Python package beside the FAQ stack. Public Play fetch → PII strip → LangChain (Groq) theme + pulse chains → deterministic auditor → `pulse/out/` artifacts. Operator/agent publishes with Docs/Gmail MCP (no custom Google OAuth/REST; no LangChain Google toolkits; no scheduler in v1). FAQ `frontend/` + `backend/` and Vercel/Railway stay untouched until a later combined-demo merge.

**Tech Stack:** Python 3.11+, `google-play-scraper`, pydantic, python-dotenv, LangChain + `langchain-groq`, pytest, Groq chat model; MCP Docs + Gmail (environment tools)

**Spec:** `Docs-MCP-&-RAG/Architecture.md` (primary), `Docs-MCP-&-RAG/ProblemStatement.md` (requirements)

## Global Constraints

- Play app only for v1: `com.nextbillion.groww` — https://play.google.com/store/apps/details?id=com.nextbillion.groww&hl=en_IN
- Public review exports / public listing helpers only — no store-login scraping
- Lookback window 8–12 weeks (default **10**)
- Theme cluster hard-cap **5**; written pulse highlights **top 3**
- Exactly **3** verbatim quotes (grounded in cleaned review text) and **3** action ideas
- Pulse body ≤ **250** words
- No PII in any artifact (no usernames, emails, device IDs, phones)
- Docs + Gmail via **MCP only** as primary delivery path
- LangChain for theme/pulse only — not for Google delivery
- Do not modify FAQ corpus, Chroma index, or Railway/Vercel FAQ deploys in this plan
- No scheduler in v1 — on-demand CLI
- Never commit `.env` or Google OAuth secrets

## Review Focus

- Quote inventing: pulse must fail audit if a quote is not a substring of a cleaned review body
- PII leakage: emails/phones in raw reviews must not appear in `clean/`, `themes.json`, or `pulse-*.md`
- Theme overflow: model returning 6+ themes must be truncated/rejected to ≤5 before write
- Empty window: zero reviews in lookback must stop with a clear error (no empty Doc publish)
- MCP boundary: no `google-api-python-client` / LangChain Gmail-Drive toolkit added as primary path

## Target File Map

```text
RAG-1/
├── Docs-MCP-&-RAG/
│   ├── ProblemStatement.md
│   ├── Architecture.md
│   ├── implementation-plan.md
│   ├── mcp-runbook.md                 # Task 7
│   └── superpowers/plans/
│       └── 2026-11-17-groww-weekly-pulse.md
├── frontend/ + backend/               # FAQ — do not change in this plan
└── pulse/
    ├── README.md
    ├── requirements.txt
    ├── .env.example
    ├── prompts/
    │   ├── theme_system.txt
    │   └── pulse_system.txt
    ├── data/
    │   ├── raw/.gitkeep
    │   ├── clean/.gitkeep
    │   └── samples/reviews_sample.jsonl   # anonymized fixture
    ├── src/
    │   ├── __init__.py
    │   ├── config.py
    │   ├── models.py
    │   ├── fetch_play.py
    │   ├── clean.py
    │   ├── theme.py
    │   ├── write_pulse.py
    │   ├── audit.py
    │   ├── chains.py
    │   └── run_pulse.py
    ├── tests/
    │   ├── test_clean.py
    │   ├── test_fetch_window.py
    │   ├── test_theme.py
    │   ├── test_write_pulse.py
    │   ├── test_audit.py
    │   └── fixtures/
    └── out/.gitkeep
```

---

## Phase 0 — Scaffolding

### Task 0: `pulse/` skeleton, deps, config, models

**Files:**
- Create: `pulse/requirements.txt`, `pulse/.env.example`, `pulse/src/__init__.py`, `pulse/src/config.py`, `pulse/src/models.py`, `pulse/data/raw/.gitkeep`, `pulse/data/clean/.gitkeep`, `pulse/out/.gitkeep`, `pulse/prompts/theme_system.txt`, `pulse/prompts/pulse_system.txt`
- Modify: root `.gitignore` (ensure `pulse/.env`, optionally ignore large `pulse/data/raw/*` except samples)

**Interfaces:**
- Produces: `Settings` from `get_settings()`; Pydantic models `Review`, `Theme`, `ThemeResult`, `PulseDoc`

- [ ] **Step 1: Create `pulse/requirements.txt`**

```text
google-play-scraper>=1.2.7
pydantic>=2.7.0
pydantic-settings>=2.3.0
python-dotenv>=1.0.0
langchain>=0.3.0
langchain-core>=0.3.0
langchain-groq>=0.2.0
pytest>=8.0.0
```

- [ ] **Step 2: Create `pulse/.env.example`**

```text
GROQ_API_KEY=gsk_your_key_here
GROQ_CHAT_MODEL=llama-3.3-70b-versatile
PULSE_LOOKBACK_WEEKS=10
PULSE_APP_ID=com.nextbillion.groww
PULSE_LANG=en
PULSE_COUNTRY=in
PULSE_DRAFT_TO=you@example.com
PULSE_MAX_REVIEWS=500
```

- [ ] **Step 3: Create `pulse/src/config.py`**

```python
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PULSE_ROOT = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(PULSE_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    groq_api_key: str = ""
    groq_chat_model: str = "llama-3.3-70b-versatile"
    pulse_lookback_weeks: int = 10
    pulse_app_id: str = "com.nextbillion.groww"
    pulse_lang: str = "en"
    pulse_country: str = "in"
    pulse_draft_to: str = ""
    pulse_max_reviews: int = 500

    @property
    def data_raw(self) -> Path:
        return PULSE_ROOT / "data" / "raw"

    @property
    def data_clean(self) -> Path:
        return PULSE_ROOT / "data" / "clean"

    @property
    def out_dir(self) -> Path:
        return PULSE_ROOT / "out"

    @property
    def prompts_dir(self) -> Path:
        return PULSE_ROOT / "prompts"


@lru_cache
def get_settings() -> Settings:
    return Settings()
```

- [ ] **Step 4: Create `pulse/src/models.py`**

```python
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class Review(BaseModel):
    review_id: str
    store: Literal["play"] = "play"
    app_id: str = "com.nextbillion.groww"
    rating: int = Field(ge=1, le=5)
    title: str | None = None
    text: str
    created_at: date
    lang: str | None = None
    theme_id: str | None = None

    @field_validator("text")
    @classmethod
    def non_empty_text(cls, v: str) -> str:
        v = (v or "").strip()
        if not v:
            raise ValueError("review text must be non-empty")
        return v


class Theme(BaseModel):
    theme_id: str
    label: str
    review_ids: list[str] = Field(default_factory=list)
    count: int = 0


class ThemeResult(BaseModel):
    themes: list[Theme] = Field(max_length=5)
    top_theme_ids: list[str] = Field(max_length=3)


class PulseDoc(BaseModel):
    title: str
    window_start: date
    window_end: date
    review_count: int
    themes: list[str]  # top 3 labels
    quotes: list[str]  # exactly 3
    actions: list[str]  # exactly 3
    body_markdown: str
    created_at: datetime
```

- [ ] **Step 5: Stub prompt files**

`pulse/prompts/theme_system.txt`:

```text
You label Groww mobile-app store reviews into at most 5 product themes.
Return JSON only matching the schema. Use short labels (e.g. KYC, Payments, App Stability).
Do not invent reviews. Do not include usernames or emails.
```

`pulse/prompts/pulse_system.txt`:

```text
You write a scannable Groww weekly review pulse.
Rules: body ≤250 words; exactly 3 themes (given); exactly 3 quotes chosen ONLY from the provided candidate quotes (copy verbatim); exactly 3 concrete action ideas grounded in those themes.
No PII. No invented quotes. No investment advice.
```

- [ ] **Step 6: Update root `.gitignore` if needed**

Ensure these lines exist:

```text
.env
pulse/.env
pulse/data/raw/*
!pulse/data/raw/.gitkeep
!pulse/data/samples/
```

- [ ] **Step 7: Commit**

```bash
git add pulse Docs-MCP-&-RAG .gitignore
git commit -m "chore(pulse): scaffold package, config, and models"
```

---

## Phase 1 — Ingest & Clean

### Task 1: Window helpers + Play fetch

**Files:**
- Create: `pulse/src/fetch_play.py`, `pulse/tests/test_fetch_window.py`, `pulse/data/samples/reviews_sample.jsonl`
- Test: `pulse/tests/test_fetch_window.py`

**Interfaces:**
- Consumes: `Settings`, `Review`
- Produces: `window_bounds(weeks: int, today: date | None) -> tuple[date, date]`; `fetch_play_reviews(settings: Settings) -> list[Review]`; `load_reviews_jsonl(path: Path) -> list[Review]`; `filter_by_window(reviews, start, end) -> list[Review]`

- [ ] **Step 1: Write failing tests for window filter**

```python
# pulse/tests/test_fetch_window.py
from datetime import date

from src.fetch_play import filter_by_window, window_bounds
from src.models import Review


def test_window_bounds_ten_weeks():
    start, end = window_bounds(10, today=date(2026, 11, 17))
    assert end == date(2026, 11, 17)
    assert (end - start).days == 70


def test_filter_by_window_drops_old():
    reviews = [
        Review(
            review_id="1",
            rating=5,
            text="new enough",
            created_at=date(2026, 10, 1),
        ),
        Review(
            review_id="2",
            rating=1,
            text="too old",
            created_at=date(2026, 1, 1),
        ),
    ]
    start, end = window_bounds(10, today=date(2026, 11, 17))
    kept = filter_by_window(reviews, start, end)
    assert [r.review_id for r in kept] == ["1"]
```

- [ ] **Step 2: Run tests — expect FAIL**

```bash
cd pulse
pytest tests/test_fetch_window.py -v
```

Expected: import/module errors or missing functions.

- [ ] **Step 3: Implement `pulse/src/fetch_play.py`**

```python
from __future__ import annotations

import json
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from google_play_scraper import Sort, reviews as play_reviews

from src.config import Settings
from src.models import Review


def window_bounds(weeks: int, today: date | None = None) -> tuple[date, date]:
    if weeks < 8 or weeks > 12:
        raise ValueError("lookback weeks must be between 8 and 12")
    end = today or date.today()
    start = end - timedelta(days=weeks * 7)
    return start, end


def filter_by_window(
    reviews: list[Review], start: date, end: date
) -> list[Review]:
    return [r for r in reviews if start <= r.created_at <= end]


def _to_review(raw: dict, app_id: str) -> Review | None:
    text = (raw.get("content") or "").strip()
    if not text:
        return None
    # Never copy userName into Review
    at = raw.get("at")
    if isinstance(at, datetime):
        created = at.date()
    else:
        created = date.today()
    return Review(
        review_id=str(raw.get("reviewId") or raw.get("review_id")),
        app_id=app_id,
        rating=int(raw.get("score") or raw.get("rating") or 0),
        title=(raw.get("title") or None),
        text=text,
        created_at=created,
        lang=None,
    )


def fetch_play_reviews(settings: Settings) -> list[Review]:
    """Fetch public Play reviews; stop early when older than window."""
    start, end = window_bounds(settings.pulse_lookback_weeks)
    collected: list[Review] = []
    token = None
    while len(collected) < settings.pulse_max_reviews:
        batch, token = play_reviews(
            settings.pulse_app_id,
            lang=settings.pulse_lang,
            country=settings.pulse_country,
            sort=Sort.NEWEST,
            count=100,
            continuation_token=token,
        )
        if not batch:
            break
        oldest_in_batch = end
        for raw in batch:
            rev = _to_review(raw, settings.pulse_app_id)
            if rev is None:
                continue
            oldest_in_batch = min(oldest_in_batch, rev.created_at)
            if start <= rev.created_at <= end:
                collected.append(rev)
        if oldest_in_batch < start or token is None:
            break
        time.sleep(0.5)
    return collected[: settings.pulse_max_reviews]


def save_raw_jsonl(reviews: list[Review], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for r in reviews:
            f.write(r.model_dump_json() + "\n")


def load_reviews_jsonl(path: Path) -> list[Review]:
    out: list[Review] = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(Review.model_validate_json(line))
    return out
```

- [ ] **Step 4: Add anonymized sample fixture** (`pulse/data/samples/reviews_sample.jsonl`) with ≥6 fake reviews spanning ratings/themes (no real usernames). Example lines:

```json
{"review_id":"s1","store":"play","app_id":"com.nextbillion.groww","rating":2,"title":null,"text":"KYC keeps failing after uploading documents","created_at":"2026-10-20","lang":"en","theme_id":null}
{"review_id":"s2","store":"play","app_id":"com.nextbillion.groww","rating":1,"title":null,"text":"Payment deducted but order not reflected","created_at":"2026-10-18","lang":"en","theme_id":null}
{"review_id":"s3","store":"play","app_id":"com.nextbillion.groww","rating":3,"title":null,"text":"App crashes on IPO apply screen","created_at":"2026-09-30","lang":"en","theme_id":null}
{"review_id":"s4","store":"play","app_id":"com.nextbillion.groww","rating":2,"title":null,"text":"Withdrawal pending for many days","created_at":"2026-10-05","lang":"en","theme_id":null}
{"review_id":"s5","store":"play","app_id":"com.nextbillion.groww","rating":4,"title":null,"text":"Mutual fund SIP setup was smooth","created_at":"2026-10-12","lang":"en","theme_id":null}
{"review_id":"s6","store":"play","app_id":"com.nextbillion.groww","rating":1,"title":null,"text":"Customer support not resolving bank linking","created_at":"2026-10-01","lang":"en","theme_id":null}
```

- [ ] **Step 5: Re-run window tests**

```bash
cd pulse
pytest tests/test_fetch_window.py -v
```

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add pulse/src/fetch_play.py pulse/tests pulse/data/samples
git commit -m "feat(pulse): Play fetch helpers and lookback window filter"
```

---

### Task 2: PII strip + clean persistence

**Files:**
- Create: `pulse/src/clean.py`, `pulse/tests/test_clean.py`
- Test: `pulse/tests/test_clean.py`

**Interfaces:**
- Consumes: `list[Review]`
- Produces: `strip_pii_text(text: str) -> str`; `clean_reviews(reviews: list[Review]) -> list[Review]`; `EMAIL_RE`, `PHONE_RE`

- [ ] **Step 1: Write failing tests**

```python
# pulse/tests/test_clean.py
from datetime import date

from src.clean import clean_reviews, strip_pii_text
from src.models import Review


def test_strip_email_and_phone():
    raw = "Contact me at user@example.com or +91 98765 43210 about KYC"
    cleaned = strip_pii_text(raw)
    assert "user@example.com" not in cleaned
    assert "98765" not in cleaned
    assert "KYC" in cleaned


def test_clean_reviews_redacts_body():
    reviews = [
        Review(
            review_id="1",
            rating=2,
            text="Help email me at a@b.com",
            created_at=date(2026, 10, 1),
        )
    ]
    out = clean_reviews(reviews)
    assert "a@b.com" not in out[0].text
```

- [ ] **Step 2: Run — expect FAIL**

```bash
cd pulse
pytest tests/test_clean.py -v
```

- [ ] **Step 3: Implement `pulse/src/clean.py`**

```python
from __future__ import annotations

import re

from src.models import Review

EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
PHONE_RE = re.compile(
    r"(?:\+?\d{1,3}[\s-]?)?(?:\(?\d{2,4}\)?[\s-]?)?\d{3,5}[\s-]?\d{4,6}"
)
HANDLE_RE = re.compile(r"@\w{2,}")


def strip_pii_text(text: str) -> str:
    text = EMAIL_RE.sub("[redacted-email]", text)
    text = HANDLE_RE.sub("[redacted-handle]", text)
    text = PHONE_RE.sub("[redacted-phone]", text)
    return text.strip()


def clean_reviews(reviews: list[Review]) -> list[Review]:
    cleaned: list[Review] = []
    for r in reviews:
        text = strip_pii_text(r.text)
        title = strip_pii_text(r.title) if r.title else None
        if not text:
            continue
        cleaned.append(r.model_copy(update={"text": text, "title": title}))
    return cleaned
```

- [ ] **Step 4: Run tests — expect PASS**

```bash
cd pulse
pytest tests/test_clean.py -v
```

- [ ] **Step 5: Commit**

```bash
git add pulse/src/clean.py pulse/tests/test_clean.py
git commit -m "feat(pulse): strip PII from review text before theming"
```

---

## Phase 2 — LangChain Theme & Pulse

### Task 3: Shared LangChain / Groq wiring

**Files:**
- Create: `pulse/src/chains.py`
- Modify: none required beyond imports in later tasks

**Interfaces:**
- Produces: `build_chat_model(settings: Settings)`; `load_prompt(name: str) -> str`

- [ ] **Step 1: Implement `pulse/src/chains.py`**

```python
from __future__ import annotations

from langchain_groq import ChatGroq

from src.config import Settings, get_settings


def load_prompt(name: str, settings: Settings | None = None) -> str:
    settings = settings or get_settings()
    path = settings.prompts_dir / name
    return path.read_text(encoding="utf-8")


def build_chat_model(settings: Settings | None = None) -> ChatGroq:
    settings = settings or get_settings()
    if not settings.groq_api_key:
        raise RuntimeError("GROQ_API_KEY is required for theme/pulse chains")
    return ChatGroq(
        api_key=settings.groq_api_key,
        model=settings.groq_chat_model,
        temperature=0.2,
    )
```

- [ ] **Step 2: Smoke import (no API call)**

```bash
cd pulse
python -c "from src.chains import load_prompt; print(load_prompt('theme_system.txt')[:40])"
```

Expected: prints prompt prefix.

- [ ] **Step 3: Commit**

```bash
git add pulse/src/chains.py
git commit -m "feat(pulse): LangChain ChatGroq helper and prompt loader"
```

---

### Task 4: Theme clustering (≤5) via LangChain structured output

**Files:**
- Create: `pulse/src/theme.py`, `pulse/tests/test_theme.py`
- Test: `pulse/tests/test_theme.py`

**Interfaces:**
- Consumes: `list[Review]`, `build_chat_model`, prompts
- Produces: `cluster_themes(reviews: list[Review], settings: Settings | None = None) -> ThemeResult`; `rank_top_themes(result: ThemeResult, n: int = 3) -> ThemeResult`

- [ ] **Step 1: Write tests that do not need live Groq (pure helpers + schema)**

```python
# pulse/tests/test_theme.py
from src.models import Theme, ThemeResult
from src.theme import enforce_theme_cap, rank_top_themes


def test_enforce_theme_cap_keeps_five():
    themes = [
        Theme(theme_id=f"t{i}", label=f"L{i}", review_ids=[str(i)], count=i)
        for i in range(1, 8)
    ]
    capped = enforce_theme_cap(themes, max_themes=5)
    assert len(capped) == 5
    assert capped[0].count >= capped[-1].count


def test_rank_top_themes():
    result = ThemeResult(
        themes=[
            Theme(theme_id="a", label="KYC", review_ids=["1", "2"], count=2),
            Theme(theme_id="b", label="Pay", review_ids=["3"], count=1),
            Theme(theme_id="c", label="Crash", review_ids=["4", "5", "6"], count=3),
        ],
        top_theme_ids=[],
    )
    ranked = rank_top_themes(result, n=3)
    assert ranked.top_theme_ids[0] == "c"
    assert len(ranked.top_theme_ids) == 3
```

- [ ] **Step 2: Run — expect FAIL**

```bash
cd pulse
pytest tests/test_theme.py -v
```

- [ ] **Step 3: Implement `pulse/src/theme.py`**

```python
from __future__ import annotations

import json
from typing import Literal

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from src.chains import build_chat_model, load_prompt
from src.config import Settings, get_settings
from src.models import Review, Theme, ThemeResult


class LLMTheme(BaseModel):
    theme_id: str
    label: str
    review_ids: list[str] = Field(default_factory=list)


class LLMThemePayload(BaseModel):
    themes: list[LLMTheme] = Field(default_factory=list, max_length=5)


def enforce_theme_cap(themes: list[Theme], max_themes: int = 5) -> list[Theme]:
    ordered = sorted(themes, key=lambda t: t.count, reverse=True)
    return ordered[:max_themes]


def rank_top_themes(result: ThemeResult, n: int = 3) -> ThemeResult:
    ordered = sorted(result.themes, key=lambda t: t.count, reverse=True)
    top = [t.theme_id for t in ordered[:n]]
    return ThemeResult(themes=enforce_theme_cap(result.themes), top_theme_ids=top)


def _reviews_for_prompt(reviews: list[Review], limit: int = 80) -> str:
    lines = []
    for r in reviews[:limit]:
        lines.append(f"- id={r.review_id} rating={r.rating}: {r.text[:240]}")
    return "\n".join(lines)


def cluster_themes(
    reviews: list[Review], settings: Settings | None = None
) -> ThemeResult:
    if not reviews:
        raise ValueError("cannot cluster themes: no reviews in window")
    settings = settings or get_settings()
    llm = build_chat_model(settings)
    structured = llm.with_structured_output(LLMThemePayload)
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", load_prompt("theme_system.txt", settings)),
            (
                "human",
                "Assign each review to at most 5 themes.\nReviews:\n{reviews}",
            ),
        ]
    )
    chain = prompt | structured
    payload: LLMThemePayload = chain.invoke(
        {"reviews": _reviews_for_prompt(reviews)}
    )
    themes: list[Theme] = []
    for t in payload.themes:
        ids = [i for i in t.review_ids if i]
        themes.append(
            Theme(
                theme_id=t.theme_id,
                label=t.label.strip(),
                review_ids=ids,
                count=len(ids),
            )
        )
    themes = enforce_theme_cap(themes, 5)
    if not themes:
        raise ValueError("theme model returned no themes")
    return rank_top_themes(ThemeResult(themes=themes, top_theme_ids=[]), n=3)


def save_themes(result: ThemeResult, path) -> None:
    path.write_text(result.model_dump_json(indent=2), encoding="utf-8")
```

- [ ] **Step 4: Run unit tests — expect PASS**

```bash
cd pulse
pytest tests/test_theme.py -v
```

- [ ] **Step 5: Optional live smoke (manual, needs GROQ_API_KEY)**

```bash
cd pulse
python -c "from pathlib import Path; from src.fetch_play import load_reviews_jsonl; from src.clean import clean_reviews; from src.theme import cluster_themes; r=clean_reviews(load_reviews_jsonl(Path('data/samples/reviews_sample.jsonl'))); print(cluster_themes(r))"
```

- [ ] **Step 6: Commit**

```bash
git add pulse/src/theme.py pulse/tests/test_theme.py
git commit -m "feat(pulse): LangChain theme clustering capped at 5"
```

---

### Task 5: Pulse writer (≤250 words, 3 quotes, 3 actions)

**Files:**
- Create: `pulse/src/write_pulse.py`, `pulse/tests/test_write_pulse.py`
- Test: `pulse/tests/test_write_pulse.py`

**Interfaces:**
- Consumes: `list[Review]`, `ThemeResult`
- Produces: `select_quote_candidates(reviews, theme_result, per_theme: int = 3) -> list[str]`; `render_pulse_markdown(doc: PulseDoc) -> str`; `write_pulse(reviews, theme_result, settings=None) -> PulseDoc`; `count_words(text: str) -> int`

- [ ] **Step 1: Write failing tests**

```python
# pulse/tests/test_write_pulse.py
from datetime import date

from src.models import Review, Theme, ThemeResult
from src.write_pulse import count_words, render_pulse_markdown, select_quote_candidates
from src.models import PulseDoc
from datetime import datetime, timezone


def test_select_quote_candidates_are_verbatim():
    reviews = [
        Review(
            review_id="1",
            rating=1,
            text="KYC keeps failing after uploading documents",
            created_at=date(2026, 10, 1),
            theme_id="kyc",
        )
    ]
    themes = ThemeResult(
        themes=[Theme(theme_id="kyc", label="KYC", review_ids=["1"], count=1)],
        top_theme_ids=["kyc"],
    )
    quotes = select_quote_candidates(reviews, themes)
    assert quotes[0] in reviews[0].text


def test_render_contains_sections():
    doc = PulseDoc(
        title="Groww Weekly Review Pulse — 2026-11-17",
        window_start=date(2026, 9, 8),
        window_end=date(2026, 11, 17),
        review_count=6,
        themes=["KYC", "Payments", "Stability"],
        quotes=["q1", "q2", "q3"],
        actions=["a1", "a2", "a3"],
        body_markdown="",
        created_at=datetime.now(timezone.utc),
    )
    md = render_pulse_markdown(doc)
    assert "## Top themes" in md
    assert "## What users said" in md
    assert "## Action ideas" in md
    assert count_words("one two three") == 3
```

- [ ] **Step 2: Run — expect FAIL**

```bash
cd pulse
pytest tests/test_write_pulse.py -v
```

- [ ] **Step 3: Implement `pulse/src/write_pulse.py`**

```python
from __future__ import annotations

from datetime import datetime, timezone

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field, field_validator

from src.chains import build_chat_model, load_prompt
from src.config import Settings, get_settings
from src.fetch_play import window_bounds
from src.models import PulseDoc, Review, ThemeResult


class LLMPulse(BaseModel):
    themes: list[str] = Field(min_length=3, max_length=3)
    quotes: list[str] = Field(min_length=3, max_length=3)
    actions: list[str] = Field(min_length=3, max_length=3)
    summary_bullets: list[str] = Field(default_factory=list)

    @field_validator("quotes")
    @classmethod
    def quotes_nonempty(cls, v: list[str]) -> list[str]:
        if any(not q.strip() for q in v):
            raise ValueError("empty quote")
        return v


def count_words(text: str) -> int:
    return len([w for w in text.replace("#", " ").split() if w.strip()])


def select_quote_candidates(
    reviews: list[Review],
    theme_result: ThemeResult,
    per_theme: int = 3,
) -> list[str]:
    by_id = {r.review_id: r for r in reviews}
    candidates: list[str] = []
    for tid in theme_result.top_theme_ids:
        theme = next((t for t in theme_result.themes if t.theme_id == tid), None)
        if not theme:
            continue
        for rid in theme.review_ids[:per_theme]:
            r = by_id.get(rid)
            if r and r.text:
                # trim long reviews but keep contiguous verbatim prefix
                snippet = r.text.strip()
                words = snippet.split()
                if len(words) > 40:
                    snippet = " ".join(words[:40])
                candidates.append(snippet)
    # fallback: highest-signal low ratings
    if len(candidates) < 3:
        for r in sorted(reviews, key=lambda x: x.rating):
            if r.text not in candidates:
                candidates.append(r.text.strip())
            if len(candidates) >= 9:
                break
    return candidates


def render_pulse_markdown(doc: PulseDoc) -> str:
    theme_lines = "\n".join(f"{i}. {t}" for i, t in enumerate(doc.themes, 1))
    quote_lines = "\n".join(f'> "{q}"' for q in doc.quotes)
    action_lines = "\n".join(f"{i}. {a}" for i, a in enumerate(doc.actions, 1))
    return "\n".join(
        [
            f"# {doc.title}",
            f"Window: {doc.window_start.isoformat()} → {doc.window_end.isoformat()} · {doc.review_count} Play reviews",
            "",
            "## Top themes",
            theme_lines,
            "",
            "## What users said",
            quote_lines,
            "",
            "## Action ideas",
            action_lines,
            "",
        ]
    )


def write_pulse(
    reviews: list[Review],
    theme_result: ThemeResult,
    settings: Settings | None = None,
) -> PulseDoc:
    if not reviews:
        raise ValueError("cannot write pulse: no reviews")
    settings = settings or get_settings()
    start, end = window_bounds(settings.pulse_lookback_weeks)
    top_labels = []
    for tid in theme_result.top_theme_ids[:3]:
        t = next(t for t in theme_result.themes if t.theme_id == tid)
        top_labels.append(t.label)
    while len(top_labels) < 3 and len(theme_result.themes) >= 3:
        # should not happen if rank_top_themes worked
        break
    if len(top_labels) < 3:
        raise ValueError("need at least 3 themes for pulse")

    candidates = select_quote_candidates(reviews, theme_result)
    llm = build_chat_model(settings)
    structured = llm.with_structured_output(LLMPulse)
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", load_prompt("pulse_system.txt", settings)),
            (
                "human",
                "Top themes: {themes}\nCandidate quotes (copy 3 verbatim):\n{quotes}\n"
                "Write themes, quotes, actions. Quotes MUST be copied exactly from candidates.",
            ),
        ]
    )
    chain = prompt | structured
    payload: LLMPulse = chain.invoke(
        {
            "themes": ", ".join(top_labels),
            "quotes": "\n".join(f"- {q}" for q in candidates),
        }
    )
    title = f"Groww Weekly Review Pulse — {end.isoformat()}"
    doc = PulseDoc(
        title=title,
        window_start=start,
        window_end=end,
        review_count=len(reviews),
        themes=payload.themes,
        quotes=payload.quotes,
        actions=payload.actions,
        body_markdown="",
        created_at=datetime.now(timezone.utc),
    )
    doc.body_markdown = render_pulse_markdown(doc)
    return doc
```

- [ ] **Step 4: Run unit tests — expect PASS**

```bash
cd pulse
pytest tests/test_write_pulse.py -v
```

- [ ] **Step 5: Commit**

```bash
git add pulse/src/write_pulse.py pulse/tests/test_write_pulse.py
git commit -m "feat(pulse): LangChain pulse writer with verbatim quote candidates"
```

---

## Phase 3 — Audit & CLI

### Task 6: Privacy + structure auditor

**Files:**
- Create: `pulse/src/audit.py`, `pulse/tests/test_audit.py`
- Test: `pulse/tests/test_audit.py`

**Interfaces:**
- Consumes: `PulseDoc`, `list[Review]`
- Produces: `AuditResult(ok: bool, errors: list[str])`; `audit_pulse(doc: PulseDoc, reviews: list[Review]) -> AuditResult`

- [ ] **Step 1: Write failing tests**

```python
# pulse/tests/test_audit.py
from datetime import date, datetime, timezone

from src.audit import audit_pulse
from src.models import PulseDoc, Review


def _doc(**kwargs):
    base = dict(
        title="t",
        window_start=date(2026, 9, 8),
        window_end=date(2026, 11, 17),
        review_count=3,
        themes=["A", "B", "C"],
        quotes=["alpha beta", "gamma", "delta"],
        actions=["a1", "a2", "a3"],
        body_markdown="word " * 10,
        created_at=datetime.now(timezone.utc),
    )
    base.update(kwargs)
    return PulseDoc(**base)


def test_audit_passes_grounded_quotes():
    reviews = [
        Review(review_id="1", rating=1, text="alpha beta extra", created_at=date(2026, 10, 1)),
        Review(review_id="2", rating=1, text="gamma yes", created_at=date(2026, 10, 1)),
        Review(review_id="3", rating=1, text="delta ok", created_at=date(2026, 10, 1)),
    ]
    result = audit_pulse(_doc(), reviews)
    assert result.ok


def test_audit_rejects_invented_quote():
    reviews = [
        Review(review_id="1", rating=1, text="only this text", created_at=date(2026, 10, 1)),
    ]
    result = audit_pulse(
        _doc(quotes=["invented quote", "only this text", "only this text"]),
        reviews,
    )
    assert not result.ok
    assert any("quote" in e.lower() for e in result.errors)


def test_audit_rejects_pii_in_body():
    reviews = [
        Review(review_id="1", rating=1, text="hello world", created_at=date(2026, 10, 1)),
    ]
    result = audit_pulse(
        _doc(
            quotes=["hello world", "hello world", "hello world"],
            body_markdown="reach me at x@y.com " + ("word " * 20),
        ),
        reviews,
    )
    assert not result.ok
```

- [ ] **Step 2: Run — expect FAIL**

```bash
cd pulse
pytest tests/test_audit.py -v
```

- [ ] **Step 3: Implement `pulse/src/audit.py`**

```python
from __future__ import annotations

from dataclasses import dataclass, field

from src.clean import EMAIL_RE, PHONE_RE
from src.models import PulseDoc, Review
from src.write_pulse import count_words


@dataclass
class AuditResult:
    ok: bool
    errors: list[str] = field(default_factory=list)


def _quote_grounded(quote: str, reviews: list[Review]) -> bool:
    q = quote.strip().strip('"').strip("'")
    if not q:
        return False
    for r in reviews:
        if q in r.text:
            return True
    return False


def audit_pulse(doc: PulseDoc, reviews: list[Review], max_words: int = 250) -> AuditResult:
    errors: list[str] = []
    if len(doc.themes) != 3:
        errors.append(f"expected 3 themes, got {len(doc.themes)}")
    if len(doc.quotes) != 3:
        errors.append(f"expected 3 quotes, got {len(doc.quotes)}")
    if len(doc.actions) != 3:
        errors.append(f"expected 3 actions, got {len(doc.actions)}")
    for i, q in enumerate(doc.quotes):
        if not _quote_grounded(q, reviews):
            errors.append(f"quote[{i}] not grounded in cleaned reviews")
    blob = "\n".join([doc.body_markdown, *doc.quotes, *doc.actions, *doc.themes])
    if EMAIL_RE.search(blob) or PHONE_RE.search(blob):
        errors.append("PII pattern detected in pulse artifact")
    words = count_words(doc.body_markdown)
    if words > max_words:
        errors.append(f"body word count {words} exceeds {max_words}")
    if doc.review_count <= 0:
        errors.append("review_count must be > 0")
    return AuditResult(ok=not errors, errors=errors)
```

- [ ] **Step 4: Run tests — expect PASS**

```bash
cd pulse
pytest tests/test_audit.py -v
```

- [ ] **Step 5: Commit**

```bash
git add pulse/src/audit.py pulse/tests/test_audit.py
git commit -m "feat(pulse): audit pulse for grounding, PII, and structure"
```

---

### Task 7: CLI `run_pulse` end-to-end (offline sample path)

**Files:**
- Create: `pulse/src/run_pulse.py`, `pulse/README.md`
- Modify: `pulse/src/__init__.py` (empty OK)

**Interfaces:**
- Produces: CLI entry `python -m src.run_pulse [--sample] [--live]`; writes `data/clean/reviews.jsonl`, `out/themes.json`, `out/pulse-YYYY-MM-DD.md`

- [ ] **Step 1: Implement `pulse/src/run_pulse.py`**

```python
from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

from src.audit import audit_pulse
from src.clean import clean_reviews
from src.config import get_settings
from src.fetch_play import (
    fetch_play_reviews,
    filter_by_window,
    load_reviews_jsonl,
    save_raw_jsonl,
    window_bounds,
)
from src.theme import cluster_themes, save_themes
from src.write_pulse import write_pulse


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Groww weekly review pulse")
    parser.add_argument(
        "--sample",
        action="store_true",
        help="Use data/samples/reviews_sample.jsonl instead of live Play fetch",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="Fetch public Play reviews (default if --sample not set)",
    )
    args = parser.parse_args(argv)
    settings = get_settings()
    settings.out_dir.mkdir(parents=True, exist_ok=True)
    settings.data_clean.mkdir(parents=True, exist_ok=True)
    settings.data_raw.mkdir(parents=True, exist_ok=True)

    # Default = sample (safe). --live fetches public Play reviews.
    if args.live:
        reviews = fetch_play_reviews(settings)
        save_raw_jsonl(
            reviews, settings.data_raw / f"play-{date.today().isoformat()}.jsonl"
        )
    else:
        sample = (
            Path(__file__).resolve().parents[1]
            / "data"
            / "samples"
            / "reviews_sample.jsonl"
        )
        reviews = load_reviews_jsonl(sample)

    start, end = window_bounds(settings.pulse_lookback_weeks)
    reviews = filter_by_window(reviews, start, end)
    reviews = clean_reviews(reviews)
    if not reviews:
        print("ERROR: no reviews in lookback window after clean", file=sys.stderr)
        return 1

    save_raw_jsonl(reviews, settings.data_clean / "reviews.jsonl")
    themes = cluster_themes(reviews, settings)
    save_themes(themes, settings.out_dir / "themes.json")
    doc = write_pulse(reviews, themes, settings)
    audit = audit_pulse(doc, reviews)
    if not audit.ok:
        print("AUDIT FAILED:", *audit.errors, sep="\n - ", file=sys.stderr)
        return 2

    out_path = settings.out_dir / f"pulse-{end.isoformat()}.md"
    out_path.write_text(doc.body_markdown, encoding="utf-8")
    print(f"Wrote {out_path}")
    print(f"Themes: {settings.out_dir / 'themes.json'}")
    print("Next: follow Docs-MCP-&-RAG/mcp-runbook.md to publish Doc + Gmail draft")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

CLI behavior: default / `--sample` → fixture; `--live` → Play fetch.

- [ ] **Step 2: Write `pulse/README.md`** covering install, `.env`, `--sample` vs `--live`, and pointer to MCP runbook.

- [ ] **Step 3: Run sample pipeline (needs GROQ_API_KEY)**

```bash
cd pulse
copy .env.example .env   # set GROQ_API_KEY
pip install -r requirements.txt
python -m src.run_pulse --sample
```

Expected: exit 0; `out/pulse-*.md` and `out/themes.json` exist; audit passes.

- [ ] **Step 4: Run full unit suite**

```bash
cd pulse
pytest -v
```

Expected: PASS (live fetch not required).

- [ ] **Step 5: Commit**

```bash
git add pulse/src/run_pulse.py pulse/README.md
git commit -m "feat(pulse): CLI run_pulse sample and live paths"
```

---

## Phase 4 — MCP Delivery

### Task 8: MCP runbook (Docs + Gmail draft)

**Files:**
- Create: `Docs-MCP-&-RAG/mcp-runbook.md`

**Interfaces:**
- Consumes: `pulse/out/pulse-YYYY-MM-DD.md`, env `PULSE_DRAFT_TO`
- Produces: operator checklist that creates/updates a Google Doc and a Gmail draft via MCP tools available in the environment (tool names filled at runtime)

- [ ] **Step 1: Write `Docs-MCP-&-RAG/mcp-runbook.md`**

Must include:

1. Prerequisites: Google Docs + Gmail MCP connected/authenticated in Cursor (or course environment)  
2. Inputs: path to latest `pulse/out/pulse-*.md`, draft recipient from `PULSE_DRAFT_TO`  
3. Steps:
   - Read pulse markdown  
   - Call Docs MCP → create (or update) document titled like `Groww Weekly Review Pulse — YYYY-MM-DD` with the markdown/plain body  
   - Record Doc URL  
   - Call Gmail MCP → create **draft** to `PULSE_DRAFT_TO` with subject `Groww Weekly Review Pulse — YYYY-MM-DD` and body = pulse text **or** Doc link + short pointer  
4. Explicit: do **not** implement `google-api-python-client` for this path  
5. Verification checklist: Doc exists; draft exists; no PII; not sent automatically unless human sends  

Include a placeholder table:

| Capability | Example MCP tool name (fill when wiring) | Status |
|------------|------------------------------------------|--------|
| Create/update Doc | _depends on installed server_ | |
| Create Gmail draft | _depends on installed server_ | |

- [ ] **Step 2: Dry-run the runbook once in the agent environment** (human/agent): produce Doc + draft from the sample pulse file. Record actual tool names back into the runbook table.

- [ ] **Step 3: Commit**

```bash
git add Docs-MCP-&-RAG/mcp-runbook.md
git commit -m "docs(pulse): MCP runbook for Docs and Gmail draft delivery"
```

---

## Phase 5 — Docs & Safety Finish

### Task 9: Root README blurb + eval checklist + isolation check

**Files:**
- Modify: root `README.md` (add second-track section; do not remove FAQ instructions)
- Create: `Docs-MCP-&-RAG/eval.md`

- [ ] **Step 1: Create `Docs-MCP-&-RAG/eval.md`**

Checklist:

- [ ] Lookback weeks ∈ [8, 12]  
- [ ] `themes.json` has 1–5 themes  
- [ ] Pulse has top 3 themes, 3 quotes, 3 actions  
- [ ] Each quote substring-matches cleaned reviews  
- [ ] No email/phone patterns in `out/`  
- [ ] Word count ≤250  
- [ ] Google Doc created via MCP  
- [ ] Gmail draft created via MCP  
- [ ] FAQ `backend/corpus_index` untouched  

- [ ] **Step 2: Update root `README.md`** with a short “Tracks” table:

| Track | Docs | Code | Host |
|-------|------|------|------|
| FAQ | `Docs-FAQ/` | `frontend/`, `backend/` | Vercel + Railway |
| Weekly pulse | `Docs-MCP-&-RAG/` | `pulse/` | Local CLI + MCP Docs/Gmail |

- [ ] **Step 3: Confirm no FAQ breakage**

```bash
# from repo root — FAQ still importable / health if venv active
cd backend
python -c "import main; print('faq ok')"
```

- [ ] **Step 4: Commit**

```bash
git add README.md Docs-MCP-&-RAG/eval.md
git commit -m "docs: link pulse track and add eval checklist"
```

---

## Out of Scope (explicit — later plan)

- Combined demo hub / `/pulse` route on existing Vercel  
- Railway trigger endpoint  
- OS/GitHub Actions scheduler  
- App Store ingest  
- Merging pulse into FAQ RAG corpus  

---

## Execution Notes

- Work only under `pulse/` + `Docs-MCP-&-RAG/` (+ light root README/gitignore).  
- Prefer `--sample` until live Play fetch is verified.  
- Rate-limit live fetch (`time.sleep`); stop when past lookback.  
- If structured output fails on Groq model, fall back once with JSON-mode prompt + `json.loads`, still validating via Pydantic.  
- Commits are listed per task for agentic execution; only commit when the human asks if working interactively under user git rules — agents following this plan may commit as written when the user has approved plan execution.

---

## Self-Review (author)

| Spec requirement | Task |
|------------------|------|
| 8–12 week public Play reviews | Task 1 |
| PII strip | Task 2 |
| ≤5 themes / top 3 | Task 4 |
| LangChain + Groq | Tasks 3–5 |
| ≤250 words, 3 quotes, 3 actions | Tasks 5–6 |
| MCP Docs + Gmail | Task 8 |
| No scheduler | CLI only (Task 7) |
| FAQ isolation | Target map + Task 9 |
| Eval / README | Task 9 |
