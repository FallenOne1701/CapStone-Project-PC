# Vercel + Railway + Stitch Plan Pointer

The executable implementation plan lives at:

**`Docs/implementation-plan.md`**

Stack/UI design spec:

**`Docs/superpowers/specs/2026-11-17-vercel-railway-stitch-design.md`**

Architecture (updated):

**`Docs/Architecture.md`**

## Phase 4 summary (new work)

1. **Task 12** — Move RAG into `backend/`; FastAPI `/health` + `/api/ask` (Railway)
2. **Task 12b** — Port `stitch_hdfc_mutual_fund_faq_assistant/` → `frontend/` Next.js (Vercel)
3. **Task 12c** — Deploy Railway + Vercel; wire `NEXT_PUBLIC_API_URL` + CORS
