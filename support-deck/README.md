# Support Deck

Groww Support Deck package for the dual support + product loops (see `DOCS-AI-Agent-Support-Deck/`).

## Import path strategy (FAQ adapter)

The FAQ corpus lives under `backend/` (Chroma + `src.rag.retrieve` / `src.rag.classify`). Support Deck does **not** duplicate the index.

Both trees use a top-level `src` package name, so do **not** put `backend/` and `support-deck/` on `PYTHONPATH` at the same time for ad-hoc imports.

**Preferred (what `src.desk.faq_client` does):**

1. Run Support Deck with `support-deck/` as the working package root (e.g. `cd support-deck && pytest` / `uvicorn`).
2. Set `BACKEND_ROOT` (default `../backend`) in `.env`.
3. `faq_client` temporarily prepends `BACKEND_ROOT` and isolates `src.*` imports when calling backend retrieve/classify, then restores Support Deck’s `src`.

**Manual / debug (optional):**

```text
# From repo root — one process, one src tree only
cd support-deck
# BACKEND_ROOT=../backend  (default)
pytest tests/test_faq_client.py -v
```

Do not change the FAQ HTTP contract (`backend` `/api/ask`); the adapter imports internal helpers only.
