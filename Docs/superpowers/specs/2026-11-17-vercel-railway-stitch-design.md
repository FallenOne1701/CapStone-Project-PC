# Design: Vercel Frontend + Railway Backend + Stitch UI

**Date:** 2026-11-17  
**Status:** Approved (conversational design complete)

## Intent

Ship the Mutual Fund FAQ Assistant as a monorepo with:

- **UI design source:** `stitch_hdfc_mutual_fund_faq_assistant/` (Stitch export: `code.html` + `screen.png`)
- **Frontend:** Next.js (App Router) + React on **Vercel**
- **Backend:** FastAPI wrapping the existing Python RAG pipeline on **Railway**

No Streamlit/Gradio.

## Repo layout

```text
RAG-1/
├── frontend/                 # Next.js App Router → Vercel
│   ├── app/
│   ├── components/
│   └── package.json
├── backend/                  # FastAPI + RAG → Railway
│   ├── src/                  # existing RAG modules (moved/kept)
│   ├── data/, prompts/, tests/, corpus_index/
│   ├── requirements.txt
│   └── main.py               # FastAPI entry
├── stitch_hdfc_mutual_fund_faq_assistant/   # design source of truth
│   ├── code.html
│   └── screen.png
├── Docs/
└── README.md
```

## API contract

- `GET /health` → `{ "status": "ok" }`
- `POST /api/ask` with `{ "question": "..." }`
- Factual response: `{ type, answer, citation_url, last_updated, scheme_id? }`
- Refusal response: `{ type, answer, educational_url, reason }`
- Stateless; no chat history DB
- Groq key only on Railway; CORS for Vercel + localhost

## Frontend

- Single route `/`
- Port Stitch HTML into React components (Tailwind, Plus Jakarta Sans, brand `#0D7A5F`)
- States: Welcome | Loading | Factual | Refusal (API-driven)
- Remove Stitch “Simulate View” tabs in production
- Persistent disclaimer: `Facts-only. No investment advice.`
- Three example chips; no PII fields; no login/charts/advice CTAs
- Env: `NEXT_PUBLIC_API_URL` → Railway base URL

## Backend

- FastAPI calls existing `answer_query` / orchestrator
- Map orchestrator string (or structured result) to JSON response types
- Persist Chroma index on Railway volume or bake into image after ingest
- Env: `GROQ_API_KEY`, model settings, `CORS_ORIGINS`, chroma/embed settings

## Deploy

| Host | Role |
|------|------|
| Vercel | `frontend/` Root Directory |
| Railway | `backend/` service, Python, expose FastAPI |

## Out of scope

- Multi-page marketing site
- User accounts / PII collection
- Moving embeddings/LLM into Next.js API routes
