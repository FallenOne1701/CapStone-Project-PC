# Support Deck Queue — Agent Transparency Design

**Date:** 2026-11-19  
**Status:** Ready for user review (self-reviewed)  
**Priority:** Agent transparency  
**Reference (inspiration only):** https://multi-agentic-system-aj1q.vercel.app/

## 1. Intent

The linked app is a **reference only** (more customer-intake shaped). Support Deck stays **multi-tab** and should be **better than that reference**.

This change makes the **Queue** detail pane a transparent multi-agent workbench: keep tabs (Queue / Pulse / Explainers / Approvals / Sources), keep Architecture agent names, and persist a real per-ticket `agent_package` so Retrieve, Draft, Policy, Pattern (frequency), Orchestrator, and Reviewer outputs are visible on the ticket.

**Out of product scope for this change:** cloning the reference’s single-page intake, renaming agents to Facts/Pattern/Compliance, session URLs, or refine rounds.

## 2. Constraints

- Dual-loop Support Deck and human approval gate remain authoritative (`DOCS-AI-Agent-Support-Deck/ProblemStatement.txt`, `Architecture.md`).
- Flat queue fields (`draft`, `citation_url`, `routing_note`, `searched`, `reviewer_flags`, `explainer_id`, `status`) stay the source of truth for Approvals, PATCH draft, and existing tests.
- PII redaction at ingress stays as today (`redact_pii` in `process_question`).
- No silent external writes; `reply_finalize` / Docs / Gmail gates unchanged.
- Do not index reviews into FAQ Chroma; Pattern is frequency-connector data only.
- UI stays focused on the two loops and the gate (not a general analytics dashboard).

## 3. Approach (approved)

**Persist a structured `agent_package` on each queue item** and render it in the Queue detail UI. Multi-tab shell and other tabs are unchanged unless they consume the extended `QueueItem` type.

## 4. Data model — `agent_package`

Stored as `agent_package_json` on `queue_items` (SQLite TEXT, default `'{}'`). Exposed on API as `agent_package` (object).

Architecture roles: **Retrieve · Draft · Policy · Orchestrator · Reviewer**. **Pattern** is a frequency-connector snapshot, not a new LLM agent.

### 4.1 Shape

```json
{
  "retrieve": {
    "path": "faq | reuse_explainer",
    "chunk_count": 0,
    "source_urls": [],
    "searched": []
  },
  "draft": {
    "text": "",
    "word_count": 0
  },
  "policy": {
    "refuse": false,
    "allow": true,
    "category": "factual",
    "reasons": []
  },
  "pattern": {
    "normalized_text": "",
    "count": 0,
    "window_days": 7,
    "threshold": 5,
    "recurring": false,
    "window_start": null,
    "window_end": null
  },
  "orchestrator": {
    "routing_note": "answer",
    "status": "drafted",
    "citation_url": null
  },
  "reviewer": {
    "passed": true,
    "flags": [],
    "round": 1
  },
  "agents_fired": ["retrieve", "draft", "policy", "orchestrator", "reviewer", "pattern"]
}
```

### 4.2 Population rules

| Panel | Source | Notes |
|--------|--------|--------|
| Retrieve | `RetrieveResult` (or synthetic explainer retrieve) | `path`: `reuse_explainer` when fee explainer matched; else `faq` |
| Draft | Final candidate draft text | `word_count` from whitespace tokens |
| Policy | `PolicyResult` | On explainer-reuse path, still run policy |
| Pattern | After `record_question`, look up frequency for this normalized question | Always include a Pattern object. `count` = bucket/lifetime or window count available from frequency helpers; `recurring` = `count >= FREQUENCY_THRESHOLD`. Use settings `frequency_threshold` and a 7-day window for `window_days` unless an existing helper already returns richer fields. |
| Orchestrator | `CandidateReply` after review’s candidate | Mirror flat fields |
| Reviewer | `review()` result | `round` fixed at `1` for v1 |
| Agents fired | Pipeline path | FAQ path: `["retrieve","draft","policy","orchestrator","reviewer","pattern"]`. Explainer reuse: `["policy","retrieve","orchestrator","reviewer","pattern"]` (no draft LLM agent; draft text comes from explainer). Always append `"pattern"` after a successful `record_question`. |

### 4.3 Compatibility

- Keep writing all existing flat columns.
- `PATCH /queue/{id}` edits **draft text only** and does **not** update `agent_package` in v1 (package draft may diverge from the editable reply until a future re-run feature).
- Legacy rows with missing/empty package: UI shows “No agent package (legacy item)”.

## 5. Pipeline changes

File: `support-deck/src/desk/pipeline.py` (plus small helpers if needed).

1. Run existing paths (explainer reuse vs parallel agents).
2. Run reviewer.
3. Call `record_question`.
4. Build Pattern snapshot from frequency bucket / audit for this normalized question.
5. Build `agent_package`.
6. Persist `QueueItem` including package JSON.
7. Create `reply_finalize` when status is `drafted` (unchanged).

Prefer a pure function `build_agent_package(...)` for unit tests.

## 6. API / schema

- `queue_items.agent_package_json TEXT NOT NULL DEFAULT '{}'` via `init_db` / migration-friendly `ALTER` if DB already exists (idempotent ensure-column helper).
- `QueueItem` model gains `agent_package: dict[str, Any] = {}` (or a typed pydantic submodel if it stays thin).
- `GET /queue`, `POST /queue` responses include `agent_package`.
- No new routes.

## 7. Frontend — Queue detail

Files (primary): `frontend/app/support-deck/queue/page.tsx`, `frontend/lib/support-deck-api.ts`; optional small presentational components under `frontend/components/support-deck/`.

**Shell / other tabs:** keep multi-tab; no required feature changes on Pulse / Explainers / Approvals / Sources. Shell copy uses “Dual loops · human approval gate” (not “operator console”).

**Detail layout:**

1. **Top badges:** `REVIEWER PASS|FAIL`, `ROUTING: {routing_note}`, `PATTERN: RECURRING|NEW` when pattern present; existing status / explainer chips.
2. **Customer query** quote + short “PII redacted at ingress” note.
3. **Customer reply draft** — editable textarea, save, citation, word/char counts; Approve/Reject via pending `reply_finalize`.
4. **Internal routing note** — `routing_note` + short line from policy category + pattern recurring.
5. **Three columns:** Retrieve | Pattern | Policy.
6. **Reviewer** + **Agents fired**.
7. **List pane:** existing filters; optional recurring / reviewer-fail affordances.
8. **Loading:** while enqueue in flight, “Running Retrieve · Draft · Policy…”.

## 8. Non-goals

- Refine loops / refinement caps  
- Facts/Pattern/Compliance renames or `/sessions` routes  
- Streaming token UI  
- Changes to weekly Pulse runner, explainer generation, Docs/Gmail approve MCP path  
- Replacing Support Deck with the reference’s customer single-page flow  

## 9. Testing

- Unit: `build_agent_package` for FAQ path, explainer-reuse path, policy refuse, recurring vs non-recurring pattern.
- API/persistence: enqueue returns package; flat fields still match; PATCH draft does not wipe package column.
- Frontend: TypeScript types include `agent_package`; detail renders without crashing on `{}` / legacy null.
- Smoke: enqueue fee + PII-ish sample → panels + approve still work; Pulse/Approvals tabs still load.

## 10. Success criteria

Opening a drafted Queue item shows Retrieve, Pattern, Policy, Reviewer, and agents-fired panels from the real pipeline run; multi-tab dual loops and human approval gates stay intact; Queue transparency is clearer than the reference (visible Architecture agents + queue history + dual-loop tabs).

## 11. Decisions log

| Decision | Choice |
|----------|--------|
| Product shape | Multi-tab Support Deck; reference link is inspiration only |
| Goal vs reference | Better than the reference (agent transparency on Queue) |
| Priority | Agent transparency |
| Approach | Persist `agent_package` (B) |
| Agent naming | Architecture: Retrieve/Draft/Policy + Pattern connector |
| Audience labeling | Do not brand as “operator console”; follow ProblemStatement.txt (two loops + human gate) |
| Refine / sessions | Deferred |
