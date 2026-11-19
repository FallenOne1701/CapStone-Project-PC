# Groww Support Deck (docs track)

Integrated **support + product** loops on top of the FAQ (`backend/` + `frontend/`) and weekly pulse (`pulse/`). Specs and ops docs live here; runnable code is under [`support-deck/`](../support-deck/).

**Facts-only. No investment advice. No PII in UI, logs, or agent state.**

## Docs in this folder

| Doc | Purpose |
|-----|---------|
| [ProblemStatement.md](./ProblemStatement.md) | Requirements / dual loops |
| [Architecture.md](./Architecture.md) | System design (primary spec) |
| [ImplementationPlan.md](./ImplementationPlan.md) | Phased tasks |
| [mcp-runbook.md](./mcp-runbook.md) | Gated Docs + Gmail via MCP-Server-1 |
| [eval.md](./eval.md) | Assembled-system eval checklist |
| [edge-case.md](./edge-case.md) | Edge cases / failure modes |

## Quick start (local)

See [`support-deck/README.md`](../support-deck/README.md) for venv, env, API (port **8001**), and frontend Support Deck routes. Keep FAQ `/api/ask` on the existing backend (port **8000**).

```bash
# FAQ API (unchanged)
cd backend && uvicorn main:app --reload --port 8000

# Support Deck API
cd support-deck && python -m src.api.main

# UI (FAQ + Support Deck)
cd frontend && npm run dev   # http://localhost:3000/support-deck
```

## Sample vs live weekly

| Mode | How | Use |
|------|-----|-----|
| **Sample (default)** | `POST /api/support-deck/weekly/run?live=false` or UI Pulse → run without live | Demo, CI, evals — uses pulse sample JSONL |
| **Live Play** | `?live=true` / pulse `--live` | Ops only; public fetch for `com.nextbillion.groww`. Expect rate-limit / helper flakiness; fall back to sample or fail closed |

Do **not** design around CSV as the primary ingest path.

## Approval + MCP (dry-run vs live)

Nothing is written to Google until a human **approves that action**.

| Mode | Env | Behavior |
|------|-----|----------|
| **Dry-run (default)** | `MCP_LIVE` unset/`0` | Receipts under `support-deck/data/fixtures/mcp-receipts/` |
| **Live HTTP** | `MCP_LIVE=1` + `MCP_URL` / `MCP_API_KEY` | Calls MCP-Server-1 after approve |
| **Cursor tools** | MCP registered in Cursor | Manual `google_docs_append_content` / `gmail_create_draft` from receipt |

Full checklist: [mcp-runbook.md](./mcp-runbook.md).

## Deploy composition (compose, do not replace)

| Host | Role |
|------|------|
| **Vercel** `frontend/` | FAQ UI **plus** Support Deck routes (`/support-deck/*`) — update in place |
| **Railway** `backend/` | FAQ `/api/ask` + corpus; keep healthy |
| **Support Deck API** | Separate FastAPI surface (`support-deck/`, local `:8001`; deploy separately when ready) |
| **pulse/** | Called by Support Deck weekly runner or existing CI workflow (artifacts only; no auto-publish) |
| **MCP-Server-1** | Primary Docs/Gmail path after approve |

**Non-goal:** Discarding Vercel/Railway FAQ apps for a greenfield monolith.

## Known limitations

- **MCP cannot create Google Docs** — pre-create a Doc and set `PULSE_DOC_ID`
- **Play live fetch is flaky** (rate limits / helper breakage) — prefer sample for demos; live for ops
- **No auto-send email** — `gmail_send_email` unused in v1
- **Reviews are not indexed into Chroma** — themes/quotes only

## Related code

- Package: [`support-deck/`](../support-deck/)
- Root track table: [`../README.md`](../README.md)
