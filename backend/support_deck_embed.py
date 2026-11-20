"""Compose Support Deck FastAPI routes onto the FAQ backend (Railway one-process).

Backend and Support Deck both use a top-level ``src`` package. We import Support
Deck in an isolated ``sys.modules`` window, ``include_router`` its APIs onto the
FAQ app, then restore FAQ ``src.*``. Route callables keep Support Deck module refs.
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from typing import Any

from fastapi import FastAPI

log = logging.getLogger("support_deck_embed")


def attach_support_deck(host: FastAPI) -> bool:
    """Attach Support Deck routes when ``../support-deck`` is present. Returns True if attached."""
    repo_root = Path(__file__).resolve().parents[1]
    sd_root = Path(
        os.environ.get("SUPPORT_DECK_ROOT", str(repo_root / "support-deck"))
    ).resolve()
    marker = sd_root / "src" / "api" / "app.py"
    if not marker.is_file():
        log.warning("Support Deck not found at %s — skipping embed", sd_root)
        return False

    stashed = {
        key: sys.modules.pop(key)
        for key in list(sys.modules)
        if key == "src" or key.startswith("src.")
    }
    inserted = False
    if str(sd_root) not in sys.path:
        sys.path.insert(0, str(sd_root))
        inserted = True

    sd_mods: dict[str, Any] = {}
    try:
        from src.api import (  # type: ignore
            approval_routes,
            queue_routes,
            sources_routes,
            weekly_routes,
        )
        from src.config import get_settings  # type: ignore
        from src.db import init_db  # type: ignore

        settings = get_settings()
        db_path = Path(settings.support_deck_db)
        if not db_path.is_absolute():
            db_path = (sd_root / db_path).resolve()
        init_db(db_path)
        host.state.db_path = db_path
        host.state.last_pulse = None

        prefix = settings.support_deck_api_prefix or "/api/support-deck"
        host.include_router(queue_routes.router, prefix=prefix)
        host.include_router(weekly_routes.router, prefix=prefix)
        host.include_router(approval_routes.router, prefix=prefix)
        host.include_router(sources_routes.router, prefix=prefix)

        log.info(
            "Support Deck embedded from %s (prefix=%s, db=%s)",
            sd_root,
            prefix,
            db_path,
        )
        return True
    except Exception:
        log.exception("Failed to embed Support Deck from %s", sd_root)
        return False
    finally:
        for key in list(sys.modules):
            if key == "src" or key.startswith("src."):
                sd_mods[key] = sys.modules.pop(key)
        # Keep modules alive so route closures do not break after GC.
        host.state._support_deck_modules = sd_mods
        if inserted:
            try:
                sys.path.remove(str(sd_root))
            except ValueError:
                pass
        sys.modules.update(stashed)
