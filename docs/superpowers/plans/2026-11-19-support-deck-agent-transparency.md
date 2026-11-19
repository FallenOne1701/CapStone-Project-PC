# Support Deck Queue Agent Transparency Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Persist a structured `agent_package` on each queue item and show Retrieve / Pattern / Policy / Reviewer / agents-fired panels on the Queue detail pane—without rebuilding Support Deck.

**Architecture:** Extend the existing desk pipeline to build a JSON agent package after review + `record_question`, store it on `queue_items.agent_package_json`, expose it on existing queue API responses, and render it in the Queue detail UI. Flat draft/citation/routing fields and approval gates stay unchanged.

**Tech Stack:** Python 3.11+, SQLite, FastAPI, pytest; Next.js (existing `frontend/`)

**Spec:** [`docs/superpowers/specs/2026-11-19-support-deck-agent-transparency-design.md`](../specs/2026-11-19-support-deck-agent-transparency-design.md)

## Global Constraints

- Multi-tab Support Deck stays; reference Vercel app is inspiration only
- Architecture agent names: Retrieve / Draft / Policy / Orchestrator / Reviewer; Pattern = frequency connector
- Flat queue fields remain source of truth for Approvals / PATCH draft / existing tests
- `PATCH /queue/{id}` edits draft only; does **not** update `agent_package` in v1
- No refine rounds, no `/sessions`, no Facts/Pattern/Compliance renames
- No Docs/Gmail / Pulse runner / explainer-generation changes
- Do not brand UI as “operator console”; shell copy: dual loops + human gate
- Never commit `.env` or secrets

## Review Focus

- Legacy DB without `agent_package_json` column still boots (`ensure_column` / `init_db`)
- Explainer-reuse path omits `"draft"` from `agents_fired` but still has draft text in package
- `PATCH` draft leaves `agent_package_json` byte-identical
- Empty/missing package does not crash Queue UI (legacy banner)
- Policy refuse path still returns a full package with `policy.refuse=true`

## File map

| File | Role |
|------|------|
| `support-deck/src/db.py` | Add column + idempotent ensure |
| `support-deck/src/models.py` | `QueueItem.agent_package` |
| `support-deck/src/desk/agent_package.py` | **New** pure `build_agent_package` |
| `support-deck/src/desk/pipeline.py` | Wire package; reorder persist after `record_question` |
| `support-deck/src/api/deps.py` | Read/write column in row mapping + persist paths if any |
| `support-deck/tests/test_agent_package.py` | **New** unit tests |
| `support-deck/tests/test_desk_pipeline.py` | Assert package on process |
| `support-deck/tests/test_api.py` | API + PATCH isolation |
| `support-deck/tests/test_db_init.py` | Column present |
| `frontend/lib/support-deck-api.ts` | Types |
| `frontend/app/support-deck/queue/page.tsx` | Detail panels |
| `frontend/components/support-deck/AgentPackagePanels.tsx` | **New** optional presentational split |

---

### Task 1: Schema + model field

**Files:**
- Modify: `support-deck/src/db.py`
- Modify: `support-deck/src/models.py`
- Modify: `support-deck/tests/test_db_init.py`

**Interfaces:**
- Consumes: existing `SCHEMA_SQL`, `init_db`, `QueueItem`
- Produces: `queue_items.agent_package_json`; `QueueItem.agent_package: dict[str, Any]`

- [ ] **Step 1: Write the failing test**

Add to `support-deck/tests/test_db_init.py`:

```python
def test_queue_items_has_agent_package_json(tmp_path):
    from src.db import init_db, connect

    db = tmp_path / "t.db"
    init_db(db)
    con = connect(db)
    cols = {r[1] for r in con.execute("PRAGMA table_info(queue_items)")}
    con.close()
    assert "agent_package_json" in cols


def test_ensure_agent_package_column_on_legacy_db(tmp_path):
    """Existing DB created without the column still gains it on init_db."""
    import sqlite3
    from src.db import init_db, connect

    db = tmp_path / "legacy.db"
    con = sqlite3.connect(str(db))
    con.execute(
        """
        CREATE TABLE queue_items (
            question_id TEXT PRIMARY KEY,
            question_text TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'pending',
            draft TEXT,
            citation_url TEXT,
            routing_note TEXT,
            searched_json TEXT NOT NULL DEFAULT '[]',
            reviewer_flags_json TEXT NOT NULL DEFAULT '[]',
            explainer_id TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )
    con.commit()
    con.close()
    init_db(db)
    con = connect(db)
    cols = {r[1] for r in con.execute("PRAGMA table_info(queue_items)")}
    con.close()
    assert "agent_package_json" in cols
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd support-deck && python -m pytest tests/test_db_init.py::test_queue_items_has_agent_package_json tests/test_db_init.py::test_ensure_agent_package_column_on_legacy_db -v`

Expected: FAIL (column missing)

- [ ] **Step 3: Implement schema + model**

In `db.py` `SCHEMA_SQL` for `queue_items`, add:

```sql
agent_package_json TEXT NOT NULL DEFAULT '{}'
```

Add helper and call from `init_db` after `executescript`:

```python
def ensure_agent_package_column(con: sqlite3.Connection) -> None:
    cols = {r[1] for r in con.execute("PRAGMA table_info(queue_items)")}
    if "agent_package_json" not in cols:
        con.execute(
            "ALTER TABLE queue_items ADD COLUMN agent_package_json TEXT NOT NULL DEFAULT '{}'"
        )
```

In `models.py` `QueueItem`, add:

```python
agent_package: dict[str, Any] = Field(default_factory=dict)
```

(`Any` already imported in `models.py`.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd support-deck && python -m pytest tests/test_db_init.py -v`

Expected: PASS

- [ ] **Step 5: Commit** (only if the user asked to commit)

```bash
git add support-deck/src/db.py support-deck/src/models.py support-deck/tests/test_db_init.py
git commit -m "feat(support-deck): add agent_package_json column on queue_items"
```

---

### Task 2: Pure `build_agent_package`

**Files:**
- Create: `support-deck/src/desk/agent_package.py`
- Create: `support-deck/tests/test_agent_package.py`

**Interfaces:**
- Consumes: `RetrieveResult`, `PolicyResult`, `CandidateReply`, `ReviewResult`, `FrequencyBucket` (from `record_question`)
- Produces: `build_agent_package(...) -> dict[str, Any]` matching spec §4.1

- [ ] **Step 1: Write the failing tests**

Create `support-deck/tests/test_agent_package.py`:

```python
from datetime import datetime

from src.desk.faq_client import RetrieveResult
from src.desk.orchestrator import CandidateReply
from src.desk.policy_agent import PolicyResult
from src.desk.reviewer import ReviewResult
from src.models import FrequencyBucket, QueueStatus


def _retrieve():
    return RetrieveResult(
        chunks=[{"text": "Exit load 1%", "source_url": "https://groww.in/p/exit-load"}],
        source_urls=["https://groww.in/p/exit-load"],
        searched=["FAQ corpus", "https://groww.in/p/exit-load"],
    )


def test_build_faq_path_package():
    from src.desk.agent_package import build_agent_package

    policy = PolicyResult(allow=True, refuse=False, reasons=["ok"], category="factual")
    candidate = CandidateReply(
        status=QueueStatus.drafted,
        draft="Exit load is 1%. https://groww.in/p/exit-load",
        citation_url="https://groww.in/p/exit-load",
        routing_note="answer",
        searched=["FAQ corpus"],
    )
    reviewed = ReviewResult(candidate=candidate, flags=[], passed=True)
    bucket = FrequencyBucket(
        bucket_id="fb-x",
        normalized_text="exit load",
        count=1,
        window_start=datetime(2026, 1, 1),
        window_end=datetime(2026, 1, 2),
    )
    pkg = build_agent_package(
        retrieve=_retrieve(),
        policy=policy,
        reviewed=reviewed,
        bucket=bucket,
        retrieve_path="faq",
        agents_fired_base=["retrieve", "draft", "policy", "orchestrator", "reviewer"],
        frequency_threshold=5,
        window_days=7,
    )
    assert pkg["retrieve"]["path"] == "faq"
    assert pkg["retrieve"]["chunk_count"] == 1
    assert pkg["policy"]["refuse"] is False
    assert pkg["pattern"]["count"] == 1
    assert pkg["pattern"]["recurring"] is False
    assert pkg["reviewer"]["passed"] is True
    assert pkg["reviewer"]["round"] == 1
    assert pkg["agents_fired"][-1] == "pattern"
    assert "draft" in pkg["agents_fired"]


def test_build_explainer_reuse_omits_draft_agent():
    from src.desk.agent_package import build_agent_package

    policy = PolicyResult(allow=True, refuse=False, reasons=[], category="factual")
    candidate = CandidateReply(
        status=QueueStatus.drafted,
        draft="Fees explained.",
        citation_url="https://a.example/1",
        routing_note="reuse_explainer",
        searched=["fee_explainer"],
    )
    reviewed = ReviewResult(candidate=candidate, flags=[], passed=True)
    bucket = FrequencyBucket(
        bucket_id="fb-y", normalized_text="fees", count=6
    )
    pkg = build_agent_package(
        retrieve=RetrieveResult(chunks=[], source_urls=[], searched=["fee_explainer"]),
        policy=policy,
        reviewed=reviewed,
        bucket=bucket,
        retrieve_path="reuse_explainer",
        agents_fired_base=["policy", "retrieve", "orchestrator", "reviewer"],
        frequency_threshold=5,
        window_days=7,
    )
    assert "draft" not in pkg["agents_fired"]
    assert pkg["pattern"]["recurring"] is True
    assert pkg["retrieve"]["path"] == "reuse_explainer"


def test_build_policy_refuse_package():
    from src.desk.agent_package import build_agent_package

    policy = PolicyResult(allow=False, refuse=True, reasons=["pii"], category="pii")
    candidate = CandidateReply(
        status=QueueStatus.not_covered,
        draft="not_covered: personal data.",
        citation_url=None,
        routing_note="escalate_human",
        searched=["FAQ corpus"],
    )
    reviewed = ReviewResult(candidate=candidate, flags=["pii"], passed=False)
    bucket = FrequencyBucket(bucket_id="fb-z", normalized_text="pan", count=1)
    pkg = build_agent_package(
        retrieve=_retrieve(),
        policy=policy,
        reviewed=reviewed,
        bucket=bucket,
        retrieve_path="faq",
        agents_fired_base=["retrieve", "draft", "policy", "orchestrator", "reviewer"],
        frequency_threshold=5,
        window_days=7,
    )
    assert pkg["policy"]["refuse"] is True
    assert pkg["policy"]["category"] == "pii"
    assert pkg["orchestrator"]["routing_note"] == "escalate_human"
    assert pkg["reviewer"]["passed"] is False
```

Fix import: use `from src.models import FrequencyBucket` only (not frequency module).

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd support-deck && python -m pytest tests/test_agent_package.py -v`

Expected: FAIL (`ModuleNotFoundError` or import error)

- [ ] **Step 3: Implement `build_agent_package`**

Create `support-deck/src/desk/agent_package.py`:

```python
from __future__ import annotations

from typing import Any, Literal

from src.desk.faq_client import RetrieveResult
from src.desk.policy_agent import PolicyResult
from src.desk.reviewer import ReviewResult
from src.models import FrequencyBucket


def _word_count(text: str | None) -> int:
    t = (text or "").strip()
    return len(t.split()) if t else 0


def build_agent_package(
    *,
    retrieve: RetrieveResult,
    policy: PolicyResult,
    reviewed: ReviewResult,
    bucket: FrequencyBucket,
    retrieve_path: Literal["faq", "reuse_explainer"],
    agents_fired_base: list[str],
    frequency_threshold: int,
    window_days: int = 7,
) -> dict[str, Any]:
    final = reviewed.candidate
    draft_text = final.draft or ""
    count = int(bucket.count)
    fired = list(agents_fired_base)
    if "pattern" not in fired:
        fired.append("pattern")
    return {
        "retrieve": {
            "path": retrieve_path,
            "chunk_count": len(retrieve.chunks),
            "source_urls": list(retrieve.source_urls),
            "searched": list(retrieve.searched),
        },
        "draft": {"text": draft_text, "word_count": _word_count(draft_text)},
        "policy": {
            "refuse": bool(policy.refuse),
            "allow": bool(policy.allow),
            "category": policy.category,
            "reasons": list(policy.reasons),
        },
        "pattern": {
            "normalized_text": bucket.normalized_text,
            "count": count,
            "window_days": window_days,
            "threshold": frequency_threshold,
            "recurring": count >= frequency_threshold,
            "window_start": bucket.window_start.isoformat(sep=" ")
            if bucket.window_start
            else None,
            "window_end": bucket.window_end.isoformat(sep=" ")
            if bucket.window_end
            else None,
        },
        "orchestrator": {
            "routing_note": final.routing_note,
            "status": final.status.value
            if hasattr(final.status, "value")
            else str(final.status),
            "citation_url": final.citation_url,
        },
        "reviewer": {
            "passed": bool(reviewed.passed),
            "flags": list(reviewed.flags),
            "round": 1,
        },
        "agents_fired": fired,
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd support-deck && python -m pytest tests/test_agent_package.py -v`

Expected: PASS

- [ ] **Step 5: Commit** (only if the user asked to commit)

```bash
git add support-deck/src/desk/agent_package.py support-deck/tests/test_agent_package.py
git commit -m "feat(support-deck): add build_agent_package helper"
```

---

### Task 3: Wire pipeline + persist package

**Files:**
- Modify: `support-deck/src/desk/pipeline.py`
- Modify: `support-deck/tests/test_desk_pipeline.py`

**Interfaces:**
- Consumes: `build_agent_package`, `record_question` → `FrequencyBucket`, settings `frequency_threshold`
- Produces: `process_question` returns `QueueItem` with non-empty `agent_package` when agents ran

**Order (spec):** review → `record_question` → build package → persist → reply_finalize.  
Today persist runs before `record_question`; **move persist after** so Pattern uses the returned bucket.

- [ ] **Step 1: Extend failing assertion in pipeline test**

In `test_factual_in_corpus_drafted_with_citation`, after existing asserts:

```python
    assert item.agent_package
    assert item.agent_package["retrieve"]["path"] == "faq"
    assert "pattern" in item.agent_package["agents_fired"]
    assert item.agent_package["orchestrator"]["citation_url"] == item.citation_url

    con = connect(db)
    row = con.execute(
        "SELECT agent_package_json FROM queue_items WHERE question_id = ?",
        (item.question_id,),
    ).fetchone()
    con.close()
    stored = json.loads(row["agent_package_json"])
    assert stored["reviewer"]["passed"] is True
```

Also fix reuse-path variable: keep `policy` (not `_policy`) so package can use it.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd support-deck && python -m pytest tests/test_desk_pipeline.py::test_factual_in_corpus_drafted_with_citation -v`

Expected: FAIL (`agent_package` empty or column missing in INSERT)

- [ ] **Step 3: Update `_persist_queue_item` and `process_question`**

`_persist_queue_item` INSERT/UPDATE include `agent_package_json` with `json.dumps(item.agent_package or {})`.

In `process_question`:

```python
    if matched is not None:
        policy, retrieve, candidate = _reuse_explainer_path(safe_text, matched)
        reused_id = matched.explainer_id
        retrieve_path = "reuse_explainer"
        agents_fired_base = ["policy", "retrieve", "orchestrator", "reviewer"]
    else:
        policy, retrieve, draft = agents.run_agents_parallel(...)
        candidate = orchestrate(policy, retrieve, draft)
        reused_id = None
        retrieve_path = "faq"
        agents_fired_base = ["retrieve", "draft", "policy", "orchestrator", "reviewer"]

    reviewed = review(candidate, retrieve)
    final = reviewed.candidate
    now = _utcnow()

    bucket = record_question(safe_text, at=now, db_path=path)
    package = build_agent_package(
        retrieve=retrieve,
        policy=policy,
        reviewed=reviewed,
        bucket=bucket,
        retrieve_path=retrieve_path,
        agents_fired_base=agents_fired_base,
        frequency_threshold=int(settings.frequency_threshold),
        window_days=7,
    )

    item = QueueItem(..., agent_package=package, ...)
    _persist_queue_item(path, item)
    # then reply_finalize as today
```

Import `build_agent_package` from `src.desk.agent_package`.

- [ ] **Step 4: Run pipeline tests**

Run: `cd support-deck && python -m pytest tests/test_desk_pipeline.py -v`

Expected: PASS

- [ ] **Step 5: Commit** (only if the user asked to commit)

```bash
git add support-deck/src/desk/pipeline.py support-deck/tests/test_desk_pipeline.py
git commit -m "feat(support-deck): persist agent_package on process_question"
```

---

### Task 4: API mapping + PATCH isolation

**Files:**
- Modify: `support-deck/src/api/deps.py`
- Modify: `support-deck/tests/test_api.py` (or add cases there)

**Interfaces:**
- Consumes: `agent_package_json` column
- Produces: `row_to_queue_item` sets `agent_package`; `update_queue_draft` does not touch package JSON

- [ ] **Step 1: Write failing API tests**

```python
def test_enqueue_returns_agent_package(client):  # use existing fixture pattern from test_api.py
    ...
    # POST /api/support-deck/queue with a fixture-mode question
    # assert response.json()["agent_package"]["agents_fired"]

def test_patch_draft_does_not_wipe_agent_package(client, tmp_path, ...):
    # enqueue → capture agent_package
    # PATCH draft to "edited"
    # GET queue item → agent_package equals original; draft is "edited"
```

Mirror whatever fixture/`TestClient` setup `test_api.py` already uses (`app.state.db_path`, fixture mode env, etc.).

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd support-deck && python -m pytest tests/test_api.py -k agent_package -v`

Expected: FAIL until deps parse the column

- [ ] **Step 3: Update `row_to_queue_item`**

```python
def row_to_queue_item(row) -> QueueItem:
    keys = row.keys() if hasattr(row, "keys") else []
    raw_pkg = row["agent_package_json"] if "agent_package_json" in keys else "{}"
    try:
        package = json.loads(raw_pkg or "{}")
    except json.JSONDecodeError:
        package = {}
    if not isinstance(package, dict):
        package = {}
    return QueueItem(
        ...,
        agent_package=package,
    )
```

Confirm `update_queue_draft` only `SET draft = ?` (already true)—add assertion in test that column unchanged.

- [ ] **Step 4: Run API tests**

Run: `cd support-deck && python -m pytest tests/test_api.py -v`

Expected: PASS

- [ ] **Step 5: Commit** (only if the user asked to commit)

```bash
git add support-deck/src/api/deps.py support-deck/tests/test_api.py
git commit -m "feat(support-deck): expose agent_package on queue API"
```

---

### Task 5: Frontend types + Queue transparency UI

**Files:**
- Modify: `frontend/lib/support-deck-api.ts`
- Create: `frontend/components/support-deck/AgentPackagePanels.tsx`
- Modify: `frontend/app/support-deck/queue/page.tsx`

**Interfaces:**
- Consumes: `QueueItem.agent_package` from API
- Produces: badges + Retrieve/Pattern/Policy columns + Reviewer + Agents fired; legacy empty-state

- [ ] **Step 1: Extend TypeScript types**

In `support-deck-api.ts`:

```typescript
export interface AgentPackage {
  retrieve?: {
    path?: string;
    chunk_count?: number;
    source_urls?: string[];
    searched?: string[];
  };
  draft?: { text?: string; word_count?: number };
  policy?: {
    refuse?: boolean;
    allow?: boolean;
    category?: string;
    reasons?: string[];
  };
  pattern?: {
    normalized_text?: string;
    count?: number;
    window_days?: number;
    threshold?: number;
    recurring?: boolean;
    window_start?: string | null;
    window_end?: string | null;
  };
  orchestrator?: {
    routing_note?: string | null;
    status?: string;
    citation_url?: string | null;
  };
  reviewer?: { passed?: boolean; flags?: string[]; round?: number };
  agents_fired?: string[];
}

export interface QueueItem {
  // existing fields...
  agent_package?: AgentPackage | null;
}
```

- [ ] **Step 2: Add `AgentPackagePanels` component**

Create `frontend/components/support-deck/AgentPackagePanels.tsx` that accepts `pkg: AgentPackage` and renders:

1. Badge row: `REVIEWER PASS|FAIL`, `ROUTING: …`, `PATTERN: RECURRING|NEW`
2. Routing note card (policy category + recurring one-liner)
3. Three columns: Retrieve | Pattern | Policy
4. Reviewer + Agents fired blocks

Use existing Support Deck tokens (`bg-surface-container-lowest`, `font-label-sm`, etc.)—no new purple theme.

If `!pkg || Object.keys(pkg).length === 0`, render: `No agent package (legacy item)`.

- [ ] **Step 3: Wire into Queue detail**

In `queue/page.tsx`:

- While `busy` on enqueue: show `Running Retrieve · Draft · Policy…` in detail or near the form submit button
- Below customer query / above or below draft (prefer **below draft + citation**, above approve): render `<AgentPackagePanels pkg={selected.agent_package ?? {}} />`
- Keep Approve/Reject + PATCH draft behavior unchanged
- Optional list affordance: if `agent_package?.pattern?.recurring`, small “recurring” hint on list row

- [ ] **Step 4: Manual smoke**

1. Start Support Deck API + frontend as you usually do  
2. Enqueue “What is the exit load if I redeem within 7 days?”  
3. Confirm panels populate; Approve still works  
4. Open Pulse / Approvals — still load  

- [ ] **Step 5: Commit** (only if the user asked to commit)

```bash
git add frontend/lib/support-deck-api.ts frontend/components/support-deck/AgentPackagePanels.tsx frontend/app/support-deck/queue/page.tsx
git commit -m "feat(frontend): show agent_package panels on Support Deck Queue"
```

---

### Task 6: Regression sweep

**Files:** none new (run only)

- [ ] **Step 1: Run full support-deck pytest**

Run: `cd support-deck && python -m pytest -v`

Expected: PASS

- [ ] **Step 2: Confirm non-goals untouched**

Quick grep / open: weekly routes, mcp_bridge, explainer generation—no unintended edits in this branch.

- [ ] **Step 3: Commit** only if there are leftover fixes and the user asked

---

## Spec coverage checklist

| Spec section | Task |
|--------------|------|
| §4 agent_package shape | 2 |
| §4.2 Pattern from frequency / agents_fired paths | 2–3 |
| §4.3 PATCH does not mutate package | 4 |
| §5 pipeline order | 3 |
| §6 schema + API | 1, 4 |
| §7 Queue UI | 5 |
| §8 non-goals | 6 |
| §9 tests | 1–4, 6 |
