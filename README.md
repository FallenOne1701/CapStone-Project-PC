# Mutual Fund FAQ Assistant

Facts-only FAQ for five HDFC schemes (Groww corpus). **No investment advice.**

| Layer | Stack | Host |
|-------|--------|------|
| UI design | Google Stitch (`stitch_hdfc_mutual_fund_faq_assistant/`) | — |
| Frontend | Next.js App Router + React + Tailwind | Vercel |
| Backend | FastAPI + RAG (Groq + Chroma) | Railway |

Disclaimer: **Facts-only. No investment advice.**

## Tracks

| Track | Docs | Code | Host |
|-------|------|------|------|
| FAQ | `Docs-FAQ/` | `frontend/`, `backend/` | Vercel + Railway |
| Weekly pulse | `Docs-MCP-&-RAG/` | `pulse/` | Local CLI + MCP-Server-1 |
| Support Deck | `DOCS-AI-Agent-Support-Deck/` | `support-deck/` (+ Support Deck routes in `frontend/`) | Compose FAQ hosts + local/API `:8001`; MCP after approve |

## Local development

### Backend

```bash
cd backend
# copy .env.example → .env and set GROQ_API_KEY
..\..\.venv\Scripts\pip install -r requirements.txt   # or use project venv
# from repo root with venv active:
pip install -r backend/requirements.txt
cd backend
uvicorn main:app --reload --port 8000
```

- Health: `GET http://127.0.0.1:8000/health`
- Ask: `POST http://127.0.0.1:8000/api/ask` with `{"question":"..."}`

Ensure `backend/corpus_index/` exists (shipped in git for Railway; locally rebuild with `python -m src.ingest.index` from `backend/` if needed).

### Frontend

```bash
cd frontend
cp .env.example .env.local   # BACKEND_URL=http://127.0.0.1:8000
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

## Deploy

1. **Railway** — set **Root Directory** to `backend` (Settings → Root Directory). Railpack uses `backend/railpack.json` / `Procfile` for `uvicorn`. If Root Directory is left as `/`, root `railpack.json` / `Procfile` start the API from `backend/`. Set env from `backend/.env.example` (`GROQ_API_KEY`, `CORS_ORIGINS`, etc.). Optional dashboard Start Command: `uvicorn main:app --host 0.0.0.0 --port $PORT` (with Root Directory `backend`).
2. **Vercel** — Root Directory `frontend`; set **`BACKEND_URL`** to the Railway HTTPS URL (e.g. `https://….up.railway.app`, no trailing slash). The UI calls same-origin `/api/ask`, which proxies to Railway.
3. On Railway, set `CORS_ORIGINS` to your Vercel URL(s) + localhost (needed if anything calls Railway directly).

## Docs

- `Docs/Architecture.md`
- `Docs/implementation-plan.md`
- `Docs/superpowers/specs/2026-11-17-vercel-railway-stitch-design.md`
