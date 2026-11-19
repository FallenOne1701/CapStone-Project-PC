# Edge Cases — Groww Weekly Review Pulse

Corner scenarios for the pulse track, derived from `implementation-plan.md` and `Architecture.md`. Use this while implementing, testing, and writing `eval.md` / `mcp-runbook.md`.

**Pipeline:** fetch → window → PII clean → theme (≤5) → pulse (top 3 / 3 quotes / 3 actions) → audit → MCP-Server-1 (`google_docs_append_content` + `gmail_create_draft`).

**Legend**

| Severity | Meaning |
|----------|---------|
| **Block** | Must stop; do not write `out/` publish artifacts / do not MCP-publish |
| **Hard fail** | Auditor or validator rejects; CLI non-zero (or regenerate once then stop) |
| **Soft / harden** | Prefer fix in code or prompt; document if accepted |
| **Ops** | Env / MCP setup issue, not batch-code logic |

---

## 1. Config & CLI

| ID | Scenario | Expected behavior | Severity |
|----|----------|-------------------|----------|
| C1 | `PULSE_LOOKBACK_WEEKS` &lt; 8 or &gt; 12 | `window_bounds` raises; clear error | Block |
| C2 | `GROQ_API_KEY` missing on theme/pulse | `build_chat_model` raises; no empty artifacts | Block |
| C3 | Neither `--sample` nor `--live` | Default to **sample** (safe path) | Soft / harden |
| C4 | Both `--sample` and `--live` | Prefer documented precedence (plan: `--live` wins if set; otherwise sample) — pick one and document in README | Soft / harden |
| C5 | `PULSE_MAX_REVIEWS` hit mid-fetch | Stop fetching; proceed with collected in-window reviews | Soft / harden |
| C6 | `PULSE_DRAFT_TO` empty at MCP step | Do not call `gmail_create_draft`; fix env first | Ops / Block (delivery) |
| C7 | `PULSE_DOC_ID` empty/missing at MCP step | Do not call `google_docs_append_content`; create blank Doc once first | Ops / Block (delivery) |
| C8 | Wrong `PULSE_APP_ID` / country / lang | May return empty or wrong corpus; treat as empty-window or wrong-product risk — verify app id stays `com.nextbillion.groww` | Soft / harden |

---

## 2. Ingest & lookback window

| ID | Scenario | Expected behavior | Severity |
|----|----------|-------------------|----------|
| F1 | Zero reviews returned from Play | After filter/clean → ERROR; exit 1; **no** Doc publish | Block |
| F2 | Reviews exist but all outside lookback | Same as F1 | Block |
| F3 | All review bodies empty / whitespace | Dropped in clean/validate; may collapse to F1 | Block if none left |
| F4 | Review on window boundary (start/end date) | Inclusive bounds per `filter_by_window` contract; unit-test both edges | Soft / harden |
| F5 | Live fetch rate-limits / HTTP errors | Sleep between pages; surface clear error; do not invent reviews | Block (or retry once then stop) |
| F6 | Play public helper / markup breaks | Fail loudly; fall back to `--sample` or checked-in export for demo | Ops / Block |
| F7 | Duplicate `review_id`s in raw feed | Dedupe or last-wins before theme; avoid double-counting themes | Soft / harden |
| F8 | Non-English / mixed-language text with `PULSE_LANG=en` | Keep if returned by helper; do not invent translations; theming may be noisier | Soft / harden |
| F9 | Ratings outside 1–5 or missing dates | Reject invalid rows at parse; skip bad records with log | Soft / harden |
| F10 | Fetch returns more than needed older pages | Stop early when older than window (plan: stop past lookback) | Soft / harden |
| F11 | Sample fixture dates all outside “today − N weeks” | Sample run fails empty-window — keep fixture dates inside a rolling or fixed demo window, or document frozen “as-of” date for tests | Soft / harden |
| F12 | App Store / iOS reviews requested in v1 | Out of scope; do not scrape login-gated sources | Soft / harden |

---

## 3. PII & cleaning

| ID | Scenario | Expected behavior | Severity |
|----|----------|-------------------|----------|
| P1 | Email in review text | Strip/redact before `clean/` and before theme/pulse | Hard fail if still in `out/` |
| P2 | Phone number in review text | Same as P1 | Hard fail if still in `out/` |
| P3 | Username / display name in raw payload | Never persist into clean schema fields; drop | Hard fail if leaked |
| P4 | Device ID / account handle / `@handle` in quote candidate | Skip that snippet for quotes; strip if present in body | Soft / harden → Hard if in `out/` |
| P5 | PII only in `title`, not `text` | Strip title via same cleaner | Hard fail if leaked |
| P6 | After strip, text becomes empty | Drop review; may trigger empty window | Block if none left |
| P7 | PAN-like / other ID patterns (architecture auditor) | Treat as PII pattern in audit blob | Hard fail |
| P8 | PII re-introduced by LLM in actions/summary | Auditor rejects; no MCP publish | Hard fail |
| P9 | Raw dump under `data/raw/` still contains PII | Allowed for untouched export; **must not** commit secrets; prefer gitignore large raw; never publish raw | Soft / harden |

---

## 4. Theming (≤5 themes, top 3)

| ID | Scenario | Expected behavior | Severity |
|----|----------|-------------------|----------|
| T1 | LLM returns 6+ themes | `enforce_theme_cap` → keep top 5 by count | Soft / harden (must not write uncapped) |
| T2 | LLM returns 0 themes | Raise; do not write empty `themes.json` as success | Block |
| T3 | Only 1–2 themes with supporting reviews | Pulse writer needs **3** theme labels — fail with clear error **or** allow documented soft path (architecture requires top 3 in written pulse). Prefer: fail if &lt;3 themes after cluster | Hard fail / Block |
| T4 | Theme with zero `review_ids` | Drop; do not keep empty themes | Soft / harden |
| T5 | Invalid / unknown `review_id`s in theme payload | Filter to known ids; recount | Soft / harden |
| T6 | All reviews collapse into one theme | Cap still OK; pulse still needs 3 labels — cannot invent filler themes; fail or expand clustering | Hard fail |
| T7 | Unassigned reviews | Assign to `other` / 5th bucket or leave unthemed but counted in `review_count`; do not drop silently without rule | Soft / harden |
| T8 | Theme labels are investment advice / toxic | Prompt forbids investment advice; regenerate once / edit labels | Soft / harden |
| T9 | Live Groq structured-output failure | Fallback once: JSON-mode + `json.loads` + Pydantic validate; then stop | Soft / harden → Block |
| T10 | Prompt only sees first N reviews (`limit=80`) | Long-tail themes may be missed — accepted limitation; document | Soft / harden |

---

## 5. Quotes, actions, pulse body

| ID | Scenario | Expected behavior | Severity |
|----|----------|-------------------|----------|
| Q1 | Invented quote (not substring of cleaned text) | Auditor fails; exit 2; do not publish | Hard fail |
| Q2 | Paraphrased quote (same meaning, different words) | Fail grounding check (substring) | Hard fail |
| Q3 | Empty / whitespace quote | Schema/validator reject | Hard fail |
| Q4 | Fewer than 3 quote candidates after trim | Fallback: low-rating reviews (plan); if still &lt;3 unique grounded strings → fail write/audit | Hard fail |
| Q5 | Same quote repeated 3× to satisfy count | Prefer diversity; audit may pass if grounded — harden to require 3 distinct quotes | Soft / harden |
| Q6 | Quote longer than ~40 words | Trim contiguous verbatim prefix for candidates; keep grounding | Soft / harden |
| Q7 | Quote still contains email/phone after clean miss | Skip candidate; audit catches if in final pulse | Hard fail if published |
| Q8 | Exactly 2 actions or 4 actions | Structure audit fails | Hard fail |
| Q9 | Generic actions unrelated to themes | Prompt requires grounding; no automated theme-link check in v1 auditor — review manually in eval | Soft / harden |
| Q10 | Body &gt; 250 words | Auditor fails; one regenerate then stop (architecture) | Hard fail |
| Q11 | Word count with markdown `#` / `>` | `count_words` strips `#`; keep consistent in tests | Soft / harden |
| Q12 | Missing pulse sections in markdown render | `render_pulse_markdown` must always emit Top themes / What users said / Action ideas | Soft / harden |
| Q13 | `review_count` = 0 on PulseDoc | Auditor fails | Hard fail |
| Q14 | Candidate quotes passed to LLM but model “fixes” grammar | Fail grounding; regenerate with stricter instruction | Hard fail |

---

## 6. Audit & regenerate policy

| ID | Scenario | Expected behavior | Severity |
|----|----------|-------------------|----------|
| A1 | First audit fail | One constrained regenerate (architecture); re-audit | Soft / harden |
| A2 | Second audit fail | Stop; print errors; **do not** write successful pulse as publish-ready / do not MCP | Block |
| A3 | Themes.json has ≤5 but pulse lists ≠3 themes | Audit fails on prose theme count | Hard fail |
| A4 | Audit passes locally but the wrong file is pasted into MCP | Runbook: only use latest audited `pulse/out/pulse-*.md` | Ops |
| A5 | CLI writes nothing on audit fail | Plan exit 2 before write — keep that (no bad `out/pulse-*.md`) | Block |

---

## 7. MCP-Server-1 delivery

| ID | Scenario | Expected behavior | Severity |
|----|----------|-------------------|----------|
| M1 | MCP server not registered in Cursor | Cannot deliver; batch artifacts still valid offline | Ops |
| M2 | Google OAuth expired / not run `npm run auth` | Tool returns auth error; re-auth; do not put tokens in `pulse/` | Ops |
| M3 | No create-doc tool | Pre-create Doc; set `PULSE_DOC_ID`; append only | Ops (accepted gap) |
| M4 | Wrong / deleted `document_id` | `RESOURCE_NOT_FOUND`; fix ID; do not invent Doc via Python Google client | Ops |
| M5 | Empty `content` append | Validation error; never append empty pulse | Hard fail |
| M6 | Concurrent edit / stale revision on Doc | MCP may return Google API / revision error; retry once or re-read runbook | Ops |
| M7 | Re-running same week appends duplicate pulse | Prefix dated heading; accept duplicate or use a fresh Doc / clear section manually | Soft / harden |
| M8 | Someone calls `gmail_send_email` | Out of v1 success path; draft-only for eval | Soft / harden |
| M9 | Invalid `PULSE_DRAFT_TO` email | MCP validation error; fix recipient | Ops |
| M10 | Draft created but Doc append failed (or reverse) | Partial delivery — retry failed step only; record both ids in runbook checklist | Ops |
| M11 | Publishing failed audit pulse | Forbidden — runbook prerequisite: audit passed / CLI exit 0 | Block |
| M12 | Adding `google-api-python-client` in `pulse/` for Docs/Gmail | Violates MCP-first constraint | Block (design) |
| M13 | Using LangChain Gmail/Drive toolkit as primary path | Same as M12 | Block (design) |
| M14 | Railway HTTP MCP deployed but `MCP_API_KEY` wrong | Auth failure on `/mcp`; fix bearer key | Ops |

---

## 8. FAQ isolation & monorepo safety

| ID | Scenario | Expected behavior | Severity |
|----|----------|-------------------|----------|
| I1 | Pulse reviews mixed into FAQ Chroma / corpus | Forbidden | Block (design) |
| I2 | Changing FAQ `frontend/` / `backend/` / Vercel / Railway in this track | Forbidden until combined-demo plan | Block (design) |
| I3 | Committing `pulse/.env`, MCP tokens, Google client secret | Forbidden; gitignore + never stage | Block |
| I4 | Scheduler / cron added as “required” for v1 | Out of scope; on-demand CLI only | Soft / harden |

---

## 9. Content / product semantics

| ID | Scenario | Expected behavior | Severity |
|----|----------|-------------------|----------|
| S1 | Reviews ask for stock tips / portfolio advice | Pulse stays product-feedback; no investment advice in actions | Soft / harden |
| S2 | Abusive / hateful review text | Prefer skip as quote; do not amplify in pulse | Soft / harden |
| S3 | Only 5-star praise in window | Still theme + 3 quotes + 3 actions grounded in data (may be “keep working” style) | Soft / harden |
| S4 | ≤250 words omits long-tail issues | Accepted limitation | Soft / harden |
| S5 | Theme labels unstable week-to-week | Accepted (model-assisted); not formal UX research | Soft / harden |

---

## 10. Suggested automated tests (map to plan tasks)

| Edge IDs | Test home (from plan) |
|----------|------------------------|
| C1, F4, F10 | `tests/test_fetch_window.py` |
| P1–P6 | `tests/test_clean.py` |
| T1, T4–T5 | `tests/test_theme.py` |
| Q1–Q6, Q10–Q11 | `tests/test_write_pulse.py` + `tests/test_audit.py` |
| A3, Q1, P8, Q8, Q13 | `tests/test_audit.py` |
| F1–F3 | CLI / integration: `run_pulse` exit 1 |
| Audit fail | CLI exit 2; no good pulse file |

Manual / ops only: **M\***, **I\***, live Play breakage (**F5–F6**), MCP dry-run (Task 8).

---

## 11. Fail-closed summary

Do **not** MCP-publish when any of these hold:

1. No cleaned reviews in lookback  
2. Theme cluster empty or cannot produce 3 pulse themes  
3. Audit fails (structure, grounding, PII, word count) after regenerate budget  
4. `PULSE_DOC_ID` / `PULSE_DRAFT_TO` / MCP auth missing  
5. Delivery would require non-MCP Google clients in `pulse/`

Offline success (`pulse/out/*` + audit OK) can still stand without Docs/Gmail if MCP is down — delivery is a separate manual step per the runbook.
