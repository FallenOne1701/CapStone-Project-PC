from __future__ import annotations

import os
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from openai import APIError, AuthenticationError, NotFoundError
from pydantic import BaseModel, Field

from src.api.respond import map_answer_to_response
from src.config import get_settings
from src.rag.orchestrator import answer_query

APP_BUILD = "support-deck-embed-1"

app = FastAPI(
    title="Mutual Fund FAQ Assistant API",
    description="Facts-only RAG FAQ for five HDFC schemes on Groww.",
    version="1.0.1",
)


def _cors_origins() -> list[str]:
    raw = os.getenv(
        "CORS_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:3000",
    )
    return [o.strip() for o in raw.split(",") if o.strip()]


app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Compose Support Deck (/api/support-deck/*) when sibling package is in the image.
from support_deck_embed import attach_support_deck  # noqa: E402

_SUPPORT_DECK_ATTACHED = attach_support_deck(app)


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)


@app.get("/health")
def health() -> dict[str, Any]:
    from src.ingest.ensure_index import index_status

    try:
        idx = index_status()
        active = idx.get("active", {})
        ok = bool(active.get("collection_exists") and active.get("chunk_count", 0) > 0)
        return {
            "status": "ok" if ok else "degraded",
            "build": APP_BUILD,
            "index": idx,
            "support_deck": _SUPPORT_DECK_ATTACHED,
        }
    except Exception as exc:  # pragma: no cover
        return {
            "status": "degraded",
            "build": APP_BUILD,
            "error": str(exc),
            "support_deck": _SUPPORT_DECK_ATTACHED,
        }


@app.post("/api/ask")
def ask(body: AskRequest) -> dict[str, Any]:
    question = body.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="question must not be empty")
    try:
        settings = get_settings()
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    try:
        text = answer_query(question, settings)
    except AuthenticationError as exc:
        raise HTTPException(
            status_code=502,
            detail="Groq API key is invalid. Check GROQ_API_KEY in backend/.env.",
        ) from exc
    except NotFoundError as exc:
        raise HTTPException(
            status_code=502,
            detail=(
                "Groq model not found. Set GROQ_CHAT_MODEL=openai/gpt-oss-120b "
                "in backend/.env (llama-3.3-70b-versatile is retired)."
            ),
        ) from exc
    except APIError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Groq API error: {exc.message or str(exc)}",
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"FAQ backend failed: {exc}",
        ) from exc

    return map_answer_to_response(text, settings)
