from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api import approval_routes, queue_routes, sources_routes, weekly_routes
from src.config import get_settings
from src.db import init_db

_LOCAL_ORIGINS = (
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3001",
    "http://localhost:3010",
    "http://127.0.0.1:3010",
)

# Any localhost / 127.0.0.1 port (Next may pick 3000–3010+, Cursor preview, etc.)
_LOCAL_ORIGIN_REGEX = r"https?://(localhost|127\.0\.0\.1)(:\d+)?"


def create_app(db_path: str | Path | None = None) -> FastAPI:
    """Build the Support Deck API (queue, weekly, approvals, sources)."""
    settings = get_settings()
    path = Path(db_path) if db_path is not None else Path(settings.support_deck_db)
    init_db(path)

    app = FastAPI(title="Groww Support Deck", version="0.1.0")
    app.state.db_path = path
    app.state.last_pulse = None

    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(_LOCAL_ORIGINS),
        allow_origin_regex=_LOCAL_ORIGIN_REGEX,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    prefix = settings.support_deck_api_prefix or "/api/support-deck"
    app.include_router(queue_routes.router, prefix=prefix)
    app.include_router(weekly_routes.router, prefix=prefix)
    app.include_router(approval_routes.router, prefix=prefix)
    app.include_router(sources_routes.router, prefix=prefix)

    @app.get("/health")
    def health() -> dict:
        return {"ok": True, "db": str(path)}

    return app
