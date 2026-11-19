# Support Deck

Python package for Groww’s dual **support** (cited reply drafts) and **product** (weekly pulse + fee explainer) loops, behind a coded human approval gate. Specs: [`DOCS-AI-Agent-Support-Deck/`](../DOCS-AI-Agent-Support-Deck/).

**Facts-only. No investment advice. No PII in UI, logs, or agent state.**

## Setup

From repo root, use the project venv (or create one):

```bash
# Windows
.\.venv\Scripts\activate
pip install -r support-deck/requirements.txt
pip install -r backend/requirements.txt   # FAQ retrieve/classify for desk
pip install -r pulse/requirements.txt     # weekly sample/live path

cd support-deck
copy .env.example .env    # set GROQ_API_KEY; leave MCP_LIVE=0 for dry-run
```

Key env (see `.env.example`):

| Variable | Purpose |
|----------|---------|
| `GROQ_API_KEY` | Desk / fee explainer LLM |
| `SUPPORT_DECK_DB` | SQLite path (default `./data/support_deck.db`) |
| `PULSE_ROOT` / `BACKEND_ROOT` | Sibling packages (`../pulse`, `../backend`) |
| `PULSE_DOC_ID` / `PULSE_DRAFT_TO` | Required for live MCP Docs/Gmail |
| `MCP_LIVE` | `0` dry-run receipts; `1` live HTTP bridge |

## Run API + frontend

```bash
# Terminal 1 — FAQ backend (port 8000) — keep /api/ask green
cd backend
uvicorn main:app --reload --port 8000

# Terminal 2 — Support Deck API (port 8001)
cd support-deck
python -m src.api.main
# or: uvicorn src.api.main:app --reload --port 8001

# Terminal 3 — Next.js (FAQ chat + Support Deck UI)
cd frontend
# .env.local: BACKEND_URL=http://127.0.0.1:8000
#            NEXT_PUBLIC_SUPPORT_DECK_URL=http://127.0.0.1:8001
npm run dev
```

- Support Deck UI: [http://localhost:3000/support-deck](http://localhost:3000/support-deck)
- Health: `GET http://127.0.0.1:8001/health`
- Prefix: `/api/support-deck` (queue, weekly, approvals, sources)

## Sample vs live weekly

| Mode | Command / API | Notes |
|------|---------------|--------|
| **Sample** | `POST /api/support-deck/weekly/run?live=false` | Default for demo/CI; uses pulse sample JSONL |
| **Live** | `?live=true` | Public Play fetch (`com.nextbillion.groww`); flaky under rate limits — fall back to sample or fail closed |

UI: **Pulse →** prepare / run weekly (sample unless you opt into live).

Creates pending approval actions (`docs_append`, `gmail_draft`) — nothing publishes until approve.

## Queue (response loop)

```bash
curl -X POST http://127.0.0.1:8001/api/support-deck/queue \
  -H "Content-Type: application/json" \
  -d "{\"question\":\"What is the exit load on HDFC Flexi Cap?\"}"
```

Or use **Queue** in the UI. Pipeline: Retrieve → Draft → Policy → reviewer → draft or `not_covered`. Reply finalize is a separate approval unit (no MCP Docs/Gmail).

## Approval + MCP dry-run vs live

| Mode | How | Result |
|------|-----|--------|
| **Dry-run (default)** | `MCP_LIVE=0` | Approve writes JSON receipt under `data/fixtures/mcp-receipts/` |
| **Live** | `MCP_LIVE=1` + `MCP_URL` / `MCP_API_KEY` | Bridge calls MCP-Server-1 after approve |
| **Reject** | Approvals UI / `POST .../reject` | Never calls MCP |

Ops checklist: [`DOCS-AI-Agent-Support-Deck/mcp-runbook.md`](../DOCS-AI-Agent-Support-Deck/mcp-runbook.md).

## Deploy composition (compose, do not replace)

Support Deck **extends** the FAQ hosts; it does not replace them.

| Piece | Host / run |
|-------|------------|
| FAQ UI + Support Deck routes | Vercel `frontend/` (update in place) |
| FAQ `/api/ask` + corpus | Railway `backend/` — keep healthy |
| Support Deck FastAPI | Separate process (`:8001` locally; deploy when ready) |
| Pulse | Invoked by weekly runner / existing CI; artifacts only |
| Google Docs/Gmail | MCP-Server-1 **after** human approve |

## Known limitations

- **No Doc create via MCP** — create the Doc once; set `PULSE_DOC_ID`
- **Play live fetch flakiness** — prefer sample for demos; reserve live for ops
- **No `gmail_send_email`** in v1 (draft only)
- **Do not** put `backend/` and `support-deck/` on `PYTHONPATH` together (both use top-level `src`)

## Import path strategy (FAQ adapter)

The FAQ corpus lives under `backend/` (Chroma + `src.rag.retrieve` / `src.rag.classify`). Support Deck does **not** duplicate the index.

Both trees use a top-level `src` package name, so do **not** put `backend/` and `support-deck/` on `PYTHONPATH` at the same time for ad-hoc imports.

**Preferred (what `src.desk.faq_client` does):**

1. Run Support Deck with `support-deck/` as the working package root (e.g. `cd support-deck && pytest` / `uvicorn`).
2. Set `BACKEND_ROOT` (default `../backend`) in `.env`.
3. `faq_client` temporarily prepends `BACKEND_ROOT` and isolates `src.*` imports when calling backend retrieve/classify, then restores Support Deck’s `src`.

```text
# From repo root — one process, one src tree only
cd support-deck
# BACKEND_ROOT=../backend  (default)
pytest tests/ -v
```

Do not change the FAQ HTTP contract (`backend` `/api/ask`); the adapter imports internal helpers only.

## Tests & evals

```bash
cd support-deck
pytest tests/ -v
```

Assembled-system checklist: [`DOCS-AI-Agent-Support-Deck/eval.md`](../DOCS-AI-Agent-Support-Deck/eval.md).
