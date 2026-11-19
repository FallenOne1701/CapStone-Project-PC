# Edge Cases — Groww Support Deck (Integrated Support + Product Loop)

Corner scenarios for the Support Deck integrate track, derived from [`ImplementationPlan.md`](./ImplementationPlan.md) and [`Architecture.md`](./Architecture.md). Use while implementing `support-deck/`, writing evals, and operating the weekly job + approval gate.

**System:** live/sample Play ingest (`pulse/`) → themes + pulse + fee explainer → **PendingApproval** → human gate → MCP Docs/Gmail; plus question queue → Retrieve/Draft/Policy → orchestrator → reviewer → approve/edit/reject; dual-loop connectors (frequency → pulse, fee → explainer reuse).

**Scheduler (yes — already in the monorepo):**

| Layer | What exists | What Support Deck adds |
|-------|-------------|------------------------|
| M2 pulse | [`.github/workflows/pulse-weekly.yml`](../.github/workflows/pulse-weekly.yml) — cron `0 3 * * 1` (Mondays 03:00 UTC) + `workflow_dispatch`; runs `python -m src.run_pulse --live`; uploads artifacts only | Keep as artifact generator |
| Support Deck | Architecture: GitHub Actions weekly **or** `POST /api/support-deck/weekly/run` | Creates **pending** Docs/Gmail actions; **never** auto-publishes |
| Publish | Not scheduled | Human approve only → MCP bridge |

So: **generation can be scheduled; Docs/Gmail/reply writes cannot.** CI must not call MCP or mark actions approved.

**Legend**

| Severity | Meaning |
|----------|---------|
| **Block** | Stop; no pending-success publish path; no MCP; no reply finalize |
| **Hard fail** | Validator/reviewer rejects; API/CLI non-zero or item forced `not_covered` / rejected |
| **Soft / harden** | Prefer fix in code; document if accepted |
| **Ops** | Env / MCP setup — not core batch logic |

---

## 1. Scheduler & weekly trigger

| ID | Scenario | Expected behavior | Severity |
|----|----------|-------------------|----------|
| SCH1 | `pulse-weekly.yml` cron fires | Live pulse artifacts generated; uploaded; **no** Docs/Gmail; **no** auto-approve | Soft / harden (correct by design) |
| SCH2 | CI missing `GROQ_API_KEY` | Job fails early with clear message; no empty “success” artifacts | Block |
| SCH3 | Live Play fetch fails in CI | Fail job **or** documented fallback to sample — never invent reviews; never hang | Block |
| SCH4 | Support Deck API `POST /weekly/run?live=true` while Play down | Fall back to sample **or** fail closed with error; never create approved MCP actions | Block |
| SCH5 | Scheduled run creates `docs_append` + `gmail_draft` pending | Both `pending_approval`; MCP bridge not invoked | Soft / harden |
| SCH6 | Someone assumes cron “sent the email” | Runbook: drafts/Docs only after Approvals UI; Gmail is draft-only | Ops |
| SCH7 | Two overlapping weekly runs (cron + manual) | Last-writer-wins on artifact paths **or** timestamped outs; do not double-approve silently; two pending sets OK if distinct `action_id`s | Soft / harden |
| SCH8 | Cron succeeds but Support Deck DB unreachable | Pulse artifacts may exist; Support Deck shows no pending — ops reconcile; do not MCP from CI | Ops |
| SCH9 | Treating scheduler as required for “demo done” | Demo can use one-click `/weekly/run` + sample; scheduler is ops cadence | Soft / harden |

---

## 2. Config & environment

| ID | Scenario | Expected behavior | Severity |
|----|----------|-------------------|----------|
| C1 | `GROQ_API_KEY` missing for desk/weekly LLM steps | Fail before writing success artifacts / drafts | Block |
| C2 | `SUPPORT_DECK_DB` path missing parent dirs | Create parents or clear error on `init_db` | Soft / harden |
| C3 | `PULSE_DOC_ID` empty at approve Docs | Do not call MCP; keep action pending or fail approve with message | Ops / Block (delivery) |
| C4 | `PULSE_DRAFT_TO` empty at approve Gmail | Do not call `gmail_create_draft` | Ops / Block (delivery) |
| C5 | `FREQUENCY_THRESHOLD` ≤ 0 | Reject config; default 5 | Soft / harden |
| C6 | `PULSE_LOOKBACK_WEEKS` outside 8–12 | Inherit pulse `window_bounds` error | Block |
| C7 | Frontend `NEXT_PUBLIC_SUPPORT_DECK_URL` wrong | UI errors visibly; FAQ `/` still works | Ops |
| C8 | Committing `.env` / MCP tokens / Google secrets | Forbidden | Block (design) |

---

## 3. Review ingest (live / sample — no CSV-primary)

| ID | Scenario | Expected behavior | Severity |
|----|----------|-------------------|----------|
| F1 | Zero reviews in window | Weekly fails; **no** pending publish actions | Block |
| F2 | Live rate-limit / helper breakage | Clear error; sample fallback if configured; no fabricated reviews | Block |
| F3 | CSV uploaded as “primary product path” | Out of scope; reject design — normalized emergency export only if same schema | Block (design) |
| F4 | Raw Play dump still has usernames | Never copy into clean/queue/UI; strip at pulse clean | Hard fail if leaked |
| F5 | Duplicate `review_id`s | Dedupe before theme counts / frequency of quotes | Soft / harden |
| F6 | Sample fixture dates outside lookback | Empty window — fix fixture or freeze as-of date in tests | Soft / harden |

(See also `Docs-MCP-&-RAG/edge-case.md` §2–6 for pulse-internal theme/quote/audit cases; Support Deck inherits them before pending approval.)

---

## 4. PII & logging

| ID | Scenario | Expected behavior | Severity |
|----|----------|-------------------|----------|
| P1 | Question contains PAN / phone / email / account-like token | Refuse or redact before agents; **do not** echo into draft, logs, or `audit_events` raw | Hard fail / Block |
| P2 | Review quote still has email/phone | Skip quote; pulse audit fails if present in artifact | Hard fail |
| P3 | Agent state stores raw PII “for debugging” | Forbidden | Block (design) |
| P4 | Approval payload preview includes redacted user paste | Show redacted form only | Soft / harden |
| P5 | Eval suite injects PAN/phone | Confirm refusal/redaction **and** log scrub assertion | Hard fail if leaked |

---

## 5. Fee explainer

| ID | Scenario | Expected behavior | Severity |
|----|----------|-------------------|----------|
| E1 | Explainer with &gt;6 bullets or ≠2 links | Pydantic/validator reject; do not upsert | Hard fail |
| E2 | Links not in M1 corpus allowlist | Reject | Hard fail |
| E3 | Explainer contains advice / returns / buy-sell | Policy + validator reject | Hard fail |
| E4 | No fee confusion in themes | Skip auto-generate; do not invent fee crisis | Soft / harden |
| E5 | Fee question but no canonical explainer yet | Full desk path; may `not_covered` if corpus empty | Soft / harden |
| E6 | Fee question with active explainer | `routing_note=reuse_explainer`; skip fresh draft agents (policy may still run) | Soft / harden |
| E7 | Stale `last_checked` (ops judgment) | Show date in UI; regenerate on weekly fee flag | Ops |

---

## 6. Multi-agent desk & queue

| ID | Scenario | Expected behavior | Severity |
|----|----------|-------------------|----------|
| D1 | Advisory / “should I buy” | Policy refuse; not a factual draft | Hard fail if answered as advice |
| D2 | Returns / performance ask | Refuse or point to official page only — no computed figures | Hard fail |
| D3 | In-corpus factual ask | ≤3 sentences; exactly one citation URL; status `drafted` | Soft / harden |
| D4 | Out-of-corpus ask | `not_covered`; `searched` non-empty naming what was searched | Hard fail if silent invent |
| D5 | Empty / whitespace question | Reject enqueue; no LLM call | Soft / harden |
| D6 | Retrieve empty + draft invents URL | Reviewer fails; force `not_covered` | Hard fail |
| D7 | Draft &gt;3 sentences | Truncate or reviewer flag → fix before human sees pass | Soft / harden |
| D8 | Parallel agent timeout / one agent crash | Fail closed for that item; do not partial-publish | Block |
| D9 | Explainer reuse produces &gt;3 sentence reply surface | Compress to ≤3 for reply; keep links in sources panel | Soft / harden |
| D10 | Reviewer flags present | UI shows flags; human may still edit/reject; do not auto-approve | Soft / harden |

---

## 7. Approval gate (isolation & no cascade)

| ID | Scenario | Expected behavior | Severity |
|----|----------|-------------------|----------|
| G1 | Approve `docs_append` | Does **not** auto-approve `gmail_draft` or `reply_finalize` | Hard fail if cascades |
| G2 | Reject one action | Sibling actions unchanged; no MCP | Hard fail if siblings flip |
| G3 | Edit draft on queue item A | Item B draft/hash unchanged | Hard fail if B mutates |
| G4 | Approve already rejected action | No-op or 409; no MCP | Soft / harden |
| G5 | Double-approve same `action_id` | Idempotent; MCP at most once (receipt / status check) | Soft / harden |
| G6 | Approve without MCP live / dry-run | Dry-run writes receipt; live needs MCP; either way status approved only after bridge attempt policy is documented | Soft / harden |
| G7 | CI or cron calls approve API | Forbidden; no service account auto-approve in v1 | Block (design) |
| G8 | Content changed after `content_hash` computed | Re-hash on edit; stale approve rejected | Soft / harden |

---

## 8. MCP delivery (gated)

| ID | Scenario | Expected behavior | Severity |
|----|----------|-------------------|----------|
| M1 | MCP called while status ≠ `approved` | Forbidden | Block |
| M2 | MCP auth expired | Approve may stay approved with failed delivery flag **or** stay pending — document; fix OAuth; no tokens in `support-deck/` | Ops |
| M3 | No create-doc tool | Pre-create Doc; append only (`PULSE_DOC_ID`) | Ops (accepted) |
| M4 | Partial success (Docs OK, Gmail fail) | Retry only failed action; do not re-append Docs blindly without ops note | Ops |
| M5 | `gmail_send_email` used for success criteria | Out of scope; draft only | Soft / harden |
| M6 | LangChain Google toolkit / raw Google REST as primary path | Violates MCP-first | Block (design) |
| M7 | Publishing failed pulse audit / empty content | Never create pending or never approve | Block |

---

## 9. Dual-loop connectors

| ID | Scenario | Expected behavior | Severity |
|----|----------|-------------------|----------|
| X1 | Same question 4× in 7 days | No frequency pulse signal (threshold 5) | Soft / harden |
| X2 | Same question 5× (normalized) in 7 days | Signal with count + window in next pulse inputs | Soft / harden |
| X3 | Paraphrases that should match (“exit load?” vs “What is exit load”) | `normalize_question` must bucket consistently for demo seeds; document limits | Soft / harden |
| X4 | Frequency signal without review ids | Pulse callout may cite queue counts; do not invent review ids | Soft / harden |
| X5 | Fee confusion theme but explainer gen fails | No silent reuse; desk stays full path; surface error | Soft / harden |
| X6 | Reuse path ignores policy (PII/advice) | Policy still runs; refuse wins | Hard fail |

---

## 10. UI / API robustness

| ID | Scenario | Expected behavior | Severity |
|----|----------|-------------------|----------|
| U1 | FAQ chat and Support Deck both open | FAQ `/api/ask` unchanged; Support Deck uses its prefix | Soft / harden |
| U2 | Concurrent edits on same queue item | Last-write-wins with hash check or 409 | Soft / harden |
| U3 | Approvals page missing destination | Block approve button until doc id / to-address present | Soft / harden |
| U4 | Sources panel claim without URL | Show `not_covered` / missing; never fabricate | Hard fail |
| U5 | Very large queue seed dump | Paginate; no crash | Soft / harden |

---

## 11. Monorepo / corpus isolation

| ID | Scenario | Expected behavior | Severity |
|----|----------|-------------------|----------|
| I1 | Indexing Play reviews into Chroma | Forbidden | Block (design) |
| I2 | Replacing Vercel/Railway FAQ with greenfield-only app | Prefer compose / update-in-place | Soft / harden |
| I3 | Breaking `/api/ask` while adding Support Deck routes | Regression — keep FAQ green each phase | Block |
| I4 | Mixing review text into factual citations | Citations only from M1 corpus URLs | Hard fail |

---

## 12. Suggested automated tests (map to plan)

| Edge IDs | Test home (from Implementation Plan) |
|----------|--------------------------------------|
| P1–P5 | `support-deck/tests/test_pii.py`, `test_eval_grounding.py` |
| E1–E3, E6 | `test_fee_explainer.py`, `test_explainer_reuse.py` |
| G1–G5, G8 | `test_approval_isolation.py` |
| D1–D7 | `test_desk_pipeline.py`, `test_desk_agents.py` |
| X1–X3 | `test_frequency.py` |
| F1, SCH5, SCH4 | `test_weekly_pending.py` |
| M1, G1 | `test_api.py` + mock `mcp_bridge` |
| Feasibility / edits / grounding suites | Task 14 eval tests |

Manual / ops: **SCH\***, **M2–M4**, live Play (**F2**), MCP OAuth, cron verification on Actions tab.

---

## 13. Fail-closed summary

Do **not** call MCP or finalize an outbound reply when any of these hold:

1. Action status ≠ `approved` (or content_hash mismatch after edit)  
2. Weekly pipeline had empty window / failed audit / failed explainer validation  
3. Desk item is advice, returns, PII, or ungrounded citation  
4. `not_covered` without an explicit human override path (v1: no override to invent facts)  
5. Scheduler/CI path attempting publish  
6. Delivery would require non-MCP Google clients as the primary path  

**Remember:** a green weekly **schedule** only means artifacts (and pending approvals) were prepared — not that Docs/Gmail were sent.
