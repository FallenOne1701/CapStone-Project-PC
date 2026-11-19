# Groww Support Deck (Integrated Support + Product Loop) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a deployed Support Deck that runs Groww’s weekly product loop (live Play reviews → pulse + fee explainer) and support response loop (multi-agent cited drafts) behind a coded human approval gate, with dual-loop connectors and assembled-system evals.

**Architecture:** New `support-deck/` Python package composes existing `pulse/` (live/sample ingest → themes → pulse) and `backend/` (retrieve + classify + refuse). Adds fee explainer, SQLite-backed queue/approvals, Retrieve/Draft/Policy agents + orchestrator + reviewer, frequency→pulse and fee→explainer connectors, FastAPI surface, and Next.js operator views. MCP Docs/Gmail (`google_docs_append_content`, `gmail_create_draft`) run **only after** approve. Do not index reviews into Chroma; do not make CSV the primary ingest path.

**Tech Stack:** Python 3.11+, FastAPI, SQLite (v1), LangChain + `langchain-groq`, pydantic, pytest; reuse `pulse/` + `backend/` RAG; Next.js (extend `frontend/`); MCP-Server-1 for Docs/Gmail

**Spec:** [`DOCS-AI-Agent-Support-Deck/Architecture.md`](./Architecture.md) (primary), [`DOCS-AI-Agent-Support-Deck/ProblemStatement.md`](./ProblemStatement.md) (requirements). Sibling: `Docs-FAQ/Architecture.md`, `Docs-MCP-&-RAG/Architecture.md`.

## Global Constraints

- Play app: `com.nextbillion.groww` — live public fetch primary (`pulse --live`); sample JSONL fallback; **no CSV-primary** design
- Lookback 8–12 weeks (default 10); themes ≤5; pulse top 3; pulse ≤250 words; 3 grounded quotes; 3 actions
- Fee explainer ≤6 bullets; exactly 2 official corpus links; `last_checked` date; facts-only
- Reply drafts ≤3 sentences; exactly one citation URL or explicit `not_covered` naming what was searched
- No PII in UI, artifacts, logs, or agent state (PAN, Aadhaar, accounts, OTPs, emails, phones, reviewer usernames, device IDs)
- No advice / buy-sell / return-performance figures; enforce in code validators + policy agent
- Nothing written/sent without human approve of **that** action (Docs, Gmail, reply are separate by default)
- Docs + Gmail via MCP-Server-1 only as primary Google path; no LangChain Google toolkits as primary
- Do not fold review text into FAQ Chroma; prefer compose / update-in-place over discarding Vercel/Railway FAQ hosts
- Never commit `.env` or Google OAuth secrets

## Review Focus

- Publish without approve: MCP or reply finalize must be unreachable unless `action.status == approved`
- Edit cascade: editing/approving/rejecting one queue item or action must not mutate siblings (diff store)
- Invented quotes/citations: pulse audit + reviewer must fail ungrounded quotes / non-allowlisted URLs
- Explainer reuse skip: fee-intent questions must hit canonical explainer when present (`routing_note=reuse_explainer`)
- PII in logs: advice/PII eval cases must leave no PAN/phone/account tokens in log sinks used by tests
- Live fetch failure: weekly API path must fall back to sample (or fail closed with clear error)—never hang mid-gate

## Target File Map

```text
RAG-1/
├── DOCS-AI-Agent-Support-Deck/
│   ├── ProblemStatement.md
│   ├── Architecture.md
│   ├── ImplementationPlan.md          # this file
│   ├── mcp-runbook.md                 # Task 12 (gated publish)
│   ├── eval.md                        # Task 14
│   └── README.md                      # Task 15
├── frontend/                          # extend with Support Deck routes (Phase 5)
├── backend/                           # thin adapters only if needed (Task 3)
├── pulse/                             # reuse; small hooks for signals (Task 5/10)
└── support-deck/
    ├── README.md
    ├── requirements.txt
    ├── .env.example
    ├── pyproject.toml                 # optional; or plain requirements
    ├── prompts/
    │   ├── retrieve_system.txt
    │   ├── draft_system.txt
    │   ├── policy_system.txt
    │   └── fee_explainer_system.txt
    ├── data/
    │   ├── seeds/questions.jsonl
    │   └── fixtures/
    ├── src/
    │   ├── __init__.py
    │   ├── config.py
    │   ├── models.py
    │   ├── db.py                      # SQLite schema + helpers
    │   ├── pii.py
    │   ├── weekly/
    │   │   ├── runner.py              # wrap pulse run → pending approvals
    │   │   ├── fee_detect.py
    │   │   └── fee_explainer.py
    │   ├── desk/
    │   │   ├── retrieve_agent.py
    │   │   ├── draft_agent.py
    │   │   ├── policy_agent.py
    │   │   ├── orchestrator.py
    │   │   ├── reviewer.py
    │   │   └── pipeline.py            # enqueue → draft
    │   ├── connectors/
    │   │   ├── frequency.py
    │   │   └── explainer_reuse.py
    │   ├── approval/
    │   │   ├── store.py
    │   │   └── service.py
    │   ├── mcp_bridge.py              # invoke only after approve (dry-run + real)
    │   ├── api/
    │   │   ├── app.py
    │   │   ├── queue_routes.py
    │   │   ├── weekly_routes.py
    │   │   ├── approval_routes.py
    │   │   └── sources_routes.py
    │   └── main.py
    └── tests/
        ├── test_pii.py
        ├── test_fee_explainer.py
        ├── test_approval_isolation.py
        ├── test_desk_pipeline.py
        ├── test_frequency.py
        ├── test_explainer_reuse.py
        ├── test_weekly_pending.py
        └── fixtures/
```

**UI files (Phase 5 — extend `frontend/`):**

```text
frontend/app/support-deck/
  page.tsx                 # hub
  queue/page.tsx
  pulse/page.tsx
  sources/page.tsx
  approvals/page.tsx
  explainers/page.tsx
frontend/lib/support-deck-api.ts
```

---

## Phase 0 — Scaffolding

### Task 0: `support-deck/` skeleton, config, models, SQLite

**Files:**
- Create: `support-deck/requirements.txt`, `support-deck/.env.example`, `support-deck/src/__init__.py`, `support-deck/src/config.py`, `support-deck/src/models.py`, `support-deck/src/db.py`, `support-deck/data/seeds/questions.jsonl`, `support-deck/prompts/*.txt` (stubs)
- Modify: root `.gitignore` (ensure `support-deck/.env`, `support-deck/data/*.db`)

**Interfaces:**
- Produces: `get_settings() -> Settings`; Pydantic models `QueueItem`, `ApprovalAction`, `FeeExplainer`, `FrequencySignal`; `init_db(path) -> None`

- [x] **Step 1: Create `support-deck/requirements.txt`**

```text
fastapi>=0.115.0
uvicorn>=0.30.0
pydantic>=2.7.0
pydantic-settings>=2.3.0
python-dotenv>=1.0.0
langchain>=0.3.0
langchain-core>=0.3.0
langchain-groq>=0.2.0
httpx>=0.27.0
pytest>=8.0.0
pytest-asyncio>=0.24.0
```

- [x] **Step 2: Create `support-deck/.env.example`**

```text
GROQ_API_KEY=gsk_your_key_here
GROQ_CHAT_MODEL=llama-3.3-70b-versatile
SUPPORT_DECK_DB=./data/support_deck.db
PULSE_ROOT=../pulse
BACKEND_ROOT=../backend
PULSE_LOOKBACK_WEEKS=10
PULSE_APP_ID=com.nextbillion.groww
PULSE_DOC_ID=
PULSE_DRAFT_TO=you@example.com
SUPPORT_DECK_API_PREFIX=/api/support-deck
FREQUENCY_THRESHOLD=5
```

- [x] **Step 3: Implement `Settings` + core Pydantic models** (`QueueItem` statuses: `pending|drafted|approved|rejected|not_covered`; `ApprovalAction` types: `docs_append|gmail_draft|reply_finalize`; statuses: `pending_approval|approved|rejected`)

- [x] **Step 4: Implement SQLite schema** — tables `queue_items`, `approval_actions`, `explainers`, `frequency_buckets`, `audit_events`

- [x] **Step 5: Write failing test for `init_db` creates tables**

```python
def test_init_db_creates_tables(tmp_path):
    from src.db import init_db, connect
    db = tmp_path / "t.db"
    init_db(db)
    con = connect(db)
    names = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"queue_items", "approval_actions", "explainers", "frequency_buckets"}.issubset(names)
```

- [x] **Step 6: Run test — fail then pass after implementation**

Run: `cd support-deck && pytest tests/test_db_init.py -v` (create this test file)

- [x] **Step 7: Commit** — `support-deck: scaffold package, settings, sqlite schema`

---

## Phase 1 — PII + Backend/Pulse adapters

### Task 1: Shared PII redact / detect

**Files:**
- Create: `support-deck/src/pii.py`, `support-deck/tests/test_pii.py`

**Interfaces:**
- Produces: `contains_pii(text: str) -> bool`; `redact_pii(text: str) -> str` (PAN/phone/email/account-like patterns)

- [x] **Step 1: Write failing tests** for PAN, phone, email, account-like strings → `contains_pii` True; redacted output has no raw match

- [x] **Step 2: Implement `pii.py` and pass tests**

- [x] **Step 3: Commit** — `support-deck: add PII detect/redact helpers`

### Task 2: FAQ retrieve/refuse adapter (no Chroma duplication)

**Files:**
- Create: `support-deck/src/desk/faq_client.py`
- Modify (only if required): `backend/src/api/...` to expose a small internal helper — **prefer** importing `answer_query` / `retrieve` / `classify` via `sys.path` to `BACKEND_ROOT` without changing FAQ HTTP contract
- Test: `support-deck/tests/test_faq_client.py` (may mock retrieve)

**Interfaces:**
- Produces: `faq_retrieve(question: str) -> RetrieveResult` with `chunks`, `source_urls`, `searched: list[str]`; `faq_classify(question: str) -> str` intent

- [x] **Step 1: Document import path strategy in `support-deck/README.md` stub** (PYTHONPATH=`backend` + `support-deck`)

- [x] **Step 2: Implement `faq_client` wrapping `backend.src.rag.retrieve.retrieve` and `classify`**

- [x] **Step 3: Test with mock or offline index — returns `searched` non-empty list even on empty hits**

- [x] **Step 4: Commit** — `support-deck: FAQ retrieve/classify adapter`

### Task 3: Pulse runner wrapper → artifacts only (no MCP)

**Files:**
- Create: `support-deck/src/weekly/runner.py`, `support-deck/tests/test_weekly_pending.py`

**Interfaces:**
- Consumes: `pulse` CLI/modules (`run_pulse` sample path)
- Produces: `run_weekly(live: bool = False) -> WeeklyArtifacts` with paths to `themes.json`, `pulse-*.md`, window meta

- [x] **Step 1: Write test that with sample mode returns existing theme/pulse artifact paths (tmpdir monkeypatch or call real sample once)**

- [x] **Step 2: Implement wrapper calling pulse sample by default; `live=True` optional**

- [x] **Step 3: Assert wrapper never calls MCP**

- [x] **Step 4: Commit** — `support-deck: wrap pulse weekly run into artifacts`

---

## Phase 2 — Fee explainer + approval store

### Task 4: Fee confusion detect + explainer generator

**Files:**
- Create: `support-deck/src/weekly/fee_detect.py`, `support-deck/src/weekly/fee_explainer.py`, `support-deck/prompts/fee_explainer_system.txt`, `support-deck/tests/test_fee_explainer.py`

**Interfaces:**
- Produces: `detect_fee_confusion(themes: ThemeResult) -> bool`; `generate_fee_explainer(question_hint: str, sources: list[str]) -> FeeExplainer` with `bullets: list[str]` (≤6), `links: list[str]` (len==2), `last_checked: date`

- [x] **Step 1: Failing test — explainer with 7 bullets or 1 link fails validation**

```python
def test_explainer_rejects_bad_shape():
    with pytest.raises(ValidationError):
        FeeExplainer(bullets=["a"]*7, links=["https://a", "https://b"], last_checked="2026-11-18")
```

- [x] **Step 2: Implement Pydantic validation + generator (Groq structured output; fixture mode without API for unit tests)**

- [x] **Step 3: Persist via `explainers` table upsert**

- [x] **Step 4: Commit** — `support-deck: fee detect + explainer store`

### Task 5: Approval store — create, edit, approve, reject (isolation)

**Files:**
- Create: `support-deck/src/approval/store.py`, `support-deck/src/approval/service.py`, `support-deck/tests/test_approval_isolation.py`

**Interfaces:**
- Produces: `create_action(...) -> ApprovalAction`; `edit_action(action_id, content) -> ApprovalAction`; `approve(action_id) -> ApprovalAction`; `reject(action_id) -> ApprovalAction`
- **Invariant:** mutate only the target `action_id`

- [x] **Step 1: Write isolation tests**

```python
def test_reject_one_leaves_other_pending(tmp_path):
    # create act-1, act-2 pending; reject act-1; assert act-2 still pending_approval
    ...

def test_edit_one_does_not_change_sibling_hash(tmp_path):
    ...
```

- [x] **Step 2: Implement store/service; pass tests**

- [x] **Step 3: Ensure `approve` does not invoke MCP inside store (bridge is separate)**

- [x] **Step 4: Commit** — `support-deck: approval gate store with edit isolation`

### Task 6: Weekly path creates pending Docs + Gmail actions

**Files:**
- Modify: `support-deck/src/weekly/runner.py`
- Test: extend `test_weekly_pending.py`

**Interfaces:**
- After successful pulse (+ optional explainer), create two `ApprovalAction`s: `docs_append`, `gmail_draft` with `payload_preview` and `content_hash`
- Status both `pending_approval`

- [x] **Step 1: Failing test — `run_weekly_to_pending` yields 2 pending actions, 0 MCP calls**

- [x] **Step 2: Implement; pass**

- [x] **Step 3: Commit** — `support-deck: weekly run stops at pending approvals`

---

## Phase 3 — Multi-agent response desk

### Task 7: Policy + Retrieve + Draft agents (parallel)

**Files:**
- Create: `support-deck/src/desk/policy_agent.py`, `retrieve_agent.py`, `draft_agent.py`, prompts, `tests/test_desk_agents.py`

**Interfaces:**
- `run_policy(q) -> PolicyResult`
- `run_retrieve(q) -> RetrieveResult`
- `run_draft(q, retrieve: RetrieveResult) -> str`
- Pipeline runs the three concurrently (`asyncio.gather` or `ThreadPoolExecutor`)

- [x] **Step 1: Unit-test policy refuses advice and PII-laden questions without calling draft**

- [x] **Step 2: Implement agents; retrieve must always populate `searched`**

- [x] **Step 3: Commit** — `support-deck: parallel retrieve/draft/policy agents`

### Task 8: Orchestrator + Reviewer + desk pipeline

**Files:**
- Create: `support-deck/src/desk/orchestrator.py`, `reviewer.py`, `pipeline.py`, `tests/test_desk_pipeline.py`

**Interfaces:**
- `process_question(text: str) -> QueueItem`
- Orchestrator: if policy refuse → `not_covered` or refused draft path per Architecture (routing `not_covered` / escalate); else one citation URL; ≤3 sentences
- Reviewer: flags for cap/PII/missing citation; may force `not_covered` if ungrounded

- [x] **Step 1: Failing tests**
  - factual in-corpus → `drafted` with citation
  - unknown → `not_covered` with non-empty `searched`
  - advisory → refused / not answered as advice

- [x] **Step 2: Implement orchestrator + reviewer + `process_question` persisting `QueueItem`**

- [x] **Step 3: On `drafted`, create `reply_finalize` pending approval action**

- [x] **Step 4: Commit** — `support-deck: desk pipeline to queue + reply approval`

---

## Phase 4 — Dual-loop connectors

### Task 9: Frequency aggregator → pulse signal

**Files:**
- Create: `support-deck/src/connectors/frequency.py`, `tests/test_frequency.py`

**Interfaces:**
- `normalize_question(text: str) -> str`
- `record_question(text: str, at: datetime) -> FrequencyBucket`
- `signals_for_pulse(window_days: int = 7, threshold: int = 5) -> list[FrequencySignal]`

- [x] **Step 1: Test — 5 normalized duplicates in 7 days → one signal with count≥5**

- [x] **Step 2: Hook `record_question` into desk pipeline after enqueue**

- [x] **Step 3: Hook `signals_for_pulse` into weekly runner input / pulse prompt appendix**

- [x] **Step 4: Commit** — `support-deck: frequency→pulse connector`

### Task 10: Explainer reuse path

**Files:**
- Create: `support-deck/src/connectors/explainer_reuse.py`, `tests/test_explainer_reuse.py`
- Modify: `support-deck/src/desk/pipeline.py`

**Interfaces:**
- `match_explainer(question: str) -> FeeExplainer | None`
- On match: skip parallel draft agents (still may run policy); set `routing_note=reuse_explainer`, `explainer_id=...`, draft ≤3 sentences from bullets

- [x] **Step 1: Seed explainer; fee-like question → reuse; unrelated question → full desk**

- [x] **Step 2: Implement and pass**

- [x] **Step 3: Commit** — `support-deck: fee explainer reuse in response loop`

---

## Phase 5 — FastAPI + Support Deck UI

### Task 11: FastAPI routes

**Files:**
- Create: `support-deck/src/api/app.py`, `queue_routes.py`, `weekly_routes.py`, `approval_routes.py`, `sources_routes.py`, `main.py`
- Test: `support-deck/tests/test_api.py` with `TestClient`

**Routes (prefix `/api/support-deck`):**

| Method | Path | Behavior |
|--------|------|----------|
| GET | `/queue` | List queue items |
| POST | `/queue` | Enqueue + run desk pipeline |
| PATCH | `/queue/{id}` | Edit draft text only |
| POST | `/weekly/run` | `live` query flag → pending approvals |
| GET | `/pulse` | Latest pulse + themes + window |
| GET | `/explainers` | Canonical explainers |
| GET | `/approvals` | Pending/approved/rejected actions |
| POST | `/approvals/{id}/approve` | Approve then optional MCP (flag) |
| POST | `/approvals/{id}/reject` | Reject only |
| GET | `/sources` | Claims/sources panel data |

- [x] **Step 1: Failing API tests for enqueue → drafted/not_covered; approve isolation**

- [x] **Step 2: Implement routers; wire CORS for local frontend**

- [x] **Step 3: Commit** — `support-deck: FastAPI operator API`

### Task 12: Next.js Support Deck views

**Files:**
- Create: `frontend/app/support-deck/**`, `frontend/lib/support-deck-api.ts`
- Modify: `frontend` nav to link Support Deck (minimal)

**Views:** Queue, Pulse, Sources, Approvals, Explainers — match Architecture §11

- [x] **Step 1: API client pointing at Support Deck base URL env `NEXT_PUBLIC_SUPPORT_DECK_URL`**

- [x] **Step 2: Queue page — list, detail, edit, approve/reject reply actions**

- [x] **Step 3: Pulse + Explainers pages — show artifacts; button “Prepare publish” → pending actions**

- [x] **Step 4: Approvals page — exact payload + destination; approve/reject**

- [x] **Step 5: Sources page — claim → URL + last-checked**

- [x] **Step 6: Manual smoke on localhost (FAQ `/` still works)**

- [x] **Step 7: Commit** — `frontend: Support Deck operator UI`

---

## Phase 6 — Gated MCP delivery

### Task 13: MCP bridge + runbook

**Files:**
- Create: `support-deck/src/mcp_bridge.py`, `DOCS-AI-Agent-Support-Deck/mcp-runbook.md`
- Modify: `support-deck/src/approval/service.py` (call bridge **only** on approve for `docs_append` / `gmail_draft`)
- Test: mock bridge; assert reject never calls it; approve calls once

**Interfaces:**
- `publish_docs_append(action: ApprovalAction) -> None`
- `publish_gmail_draft(action: ApprovalAction) -> None`
- Default local mode: write dry-run receipt under `support-deck/data/fixtures/mcp-receipts/` unless `MCP_LIVE=1`

- [x] **Step 1: Isolation test with mock**

- [x] **Step 2: Implement dry-run bridge + document live Cursor/MCP operator steps in `mcp-runbook.md` (reuse MCP-Server-1 tool names)**

- [x] **Step 3: Commit** — `support-deck: gated MCP bridge + runbook`

---

## Phase 7 — Evals, docs, deploy notes

### Task 14: Assembled-system eval suite

**Files:**
- Create: `DOCS-AI-Agent-Support-Deck/eval.md`, `support-deck/tests/test_eval_feasibility.py`, `test_eval_edits.py`, `test_eval_grounding.py`

**Coverage (from Problem Statement):**

1. **Feasibility** — every seed question → draft or not_covered; themes have review ids + window; caps; weekly completes to pending without manual mid-steps  
2. **Correctness of edits** — edit/approve/reject isolation diffs  
3. **Grounding/compliance** — sample ≥15 claims; OOS names searched; advice/returns/PII refused or redacted; log scrub assertion  

- [ ] **Step 1: Add seed questions JSONL (≥20) including advice, returns, PII, fee, factual**

- [ ] **Step 2: Implement automated tests for (1)(2) and a scripted checklist for (3) live claims sampling**

- [ ] **Step 3: Record results template in `eval.md`**

- [ ] **Step 4: Commit** — `support-deck: assembled-system evals`

### Task 15: README + root blurb + deploy composition notes

**Files:**
- Create: `DOCS-AI-Agent-Support-Deck/README.md`, `support-deck/README.md`
- Modify: root `README.md` (add Support Deck track row)

**Content:** setup (venv, env, run API + frontend), sample vs live weekly, approval + MCP dry-run vs live, known limitations (MCP doc-create gap, Play fetch flakiness), compose-not-replace FAQ hosts

- [ ] **Step 1: Write READMEs**

- [ ] **Step 2: Sanity — FAQ `/api/ask` still healthy; Support Deck sample weekly + one queue item end-to-end dry-run**

- [ ] **Step 3: Commit** — `docs: Support Deck README and root track blurb`

---

## Out of Scope (explicit — later)

- Auto-send Gmail (`gmail_send_email`)
- Indexing Play reviews into Chroma
- Full CRM / ticketing sync
- Replacing Vercel/Railway FAQ apps with a greenfield monolith
- App Store ingest
- CSV-primary ingest productization

---

## Execution Notes

- Prefer implementing phases in order; Phase 3 can start after Task 2 even if weekly UI is incomplete
- Keep FAQ `frontend/` chat and `backend` `/api/ask` green after every phase that touches shared code
- Use sample Play path for CI/tests; reserve `--live` for manual/ops
- When unsure, fail closed (no publish, `not_covered`, redact)
- Commit per task as listed; do not commit secrets

## Self-Review (author)

- [x] Maps to Problem Statement dual loops, live ingest, gate, connectors, evals  
- [x] Maps to Architecture agents (Retrieve/Draft/Policy), approval units, MCP boundary  
- [x] Reuses `pulse/` + `backend/` instead of reimplementing M1/M2  
- [x] File map + task interfaces named for agentic execution  
- [x] Out of scope explicit  
