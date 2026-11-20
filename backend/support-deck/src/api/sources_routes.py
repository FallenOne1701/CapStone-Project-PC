from __future__ import annotations

from fastapi import APIRouter, Request

from src.api.deps import get_db_path, sources_panel

router = APIRouter(tags=["sources"])


@router.get("/sources")
def get_sources(request: Request) -> list[dict]:
    return sources_panel(get_db_path(request))
