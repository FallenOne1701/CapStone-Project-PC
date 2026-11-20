from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException, Query, Request

from src.api.deps import get_db_path, serialize_model
from src.weekly import runner as weekly_runner

router = APIRouter(tags=["weekly"])


def _pulse_payload_from_artifacts(artifacts) -> dict:
    themes_raw: dict | list = {}
    try:
        themes_raw = json.loads(artifacts.themes_path.read_text(encoding="utf-8"))
    except Exception:
        themes_raw = {}
    pulse_markdown = ""
    try:
        pulse_markdown = artifacts.pulse_path.read_text(encoding="utf-8")
    except Exception:
        pulse_markdown = ""
    return {
        "themes": themes_raw.get("themes", themes_raw)
        if isinstance(themes_raw, dict)
        else themes_raw,
        "top_theme_ids": themes_raw.get("top_theme_ids", [])
        if isinstance(themes_raw, dict)
        else [],
        "pulse_markdown": pulse_markdown,
        "window_start": artifacts.window_start.isoformat(),
        "window_end": artifacts.window_end.isoformat(),
        "lookback_weeks": artifacts.lookback_weeks,
        "live": artifacts.live,
        "themes_path": str(artifacts.themes_path),
        "pulse_path": str(artifacts.pulse_path),
    }


@router.post("/weekly/run")
def weekly_run(
    request: Request,
    live: bool = Query(default=False),
) -> dict:
    db = get_db_path(request)
    result = weekly_runner.run_weekly_to_pending(live=live, db_path=db)
    pulse = _pulse_payload_from_artifacts(result.artifacts)
    request.app.state.last_pulse = pulse
    return {
        "artifacts": {
            "themes_path": str(result.artifacts.themes_path),
            "pulse_path": str(result.artifacts.pulse_path),
            "window_start": result.artifacts.window_start.isoformat(),
            "window_end": result.artifacts.window_end.isoformat(),
            "lookback_weeks": result.artifacts.lookback_weeks,
            "live": result.artifacts.live,
        },
        "actions": [serialize_model(a) for a in result.actions],
        "explainer_id": result.explainer_id,
    }


@router.get("/pulse")
def get_pulse(request: Request) -> dict:
    cached = getattr(request.app.state, "last_pulse", None)
    if cached:
        return cached
    raise HTTPException(
        status_code=404,
        detail="no pulse available — run POST /weekly/run first",
    )


@router.get("/explainers")
def get_explainers(request: Request) -> list[dict]:
    from src.api.deps import list_explainers

    return [serialize_model(e) for e in list_explainers(get_db_path(request))]
