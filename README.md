# Mutual Fund FAQ Assistant

Facts-only FAQ for five HDFC schemes (Groww corpus). **No investment advice.**

| Layer | Stack | Host |
|-------|--------|------|
| UI design | Google Stitch (`stitch_hdfc_mutual_fund_faq_assistant/`) | — |
| Frontend | Next.js App Router + React + Tailwind | Vercel |
| Backend | FastAPI + RAG (Groq + Chroma) | Railway |

Disclaimer: **Facts-only. No investment advice.**

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

Ensure `backend/corpus_index/` exists (run ingest/index from existing scripts if needed).

### Frontend

```bash
cd frontend
cp .env.example .env.local   # NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

## Deploy

1. **Railway** — root directory / service path `backend`; set env from `backend/.env.example`; start via `railway.toml`.
2. **Vercel** — Root Directory `frontend`; set `NEXT_PUBLIC_API_URL` to the Railway URL.
3. On Railway, add your Vercel URL to `CORS_ORIGINS`.

## Docs

- `Docs/Architecture.md`
- `Docs/implementation-plan.md`
- `Docs/superpowers/specs/2026-11-17-vercel-railway-stitch-design.md`
