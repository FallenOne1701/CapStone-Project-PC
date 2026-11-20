from __future__ import annotations

from datetime import datetime, timezone

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field, field_validator

from src.chains import build_chat_model, load_prompt, structured_invoke
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
    payload: LLMPulse = structured_invoke(
        llm,
        prompt,
        LLMPulse,
        {
            "themes": ", ".join(top_labels),
            "quotes": "\n".join(f"- {q}" for q in candidates),
        },
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
