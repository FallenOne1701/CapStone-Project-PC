"""Compose Support Deck FastAPI routes onto the FAQ backend (Railway one-process).

Backend and Support Deck both use a top-level ``src`` package. We import Support
Deck in an isolated ``sys.modules`` window, ``include_router`` its APIs onto the
FAQ app, then restore FAQ ``src.*``.

Lazy ``from src...`` inside Support Deck handlers would otherwise resolve the FAQ
``src`` at request time. An HTTP middleware reinstalls Support Deck modules for
``/api/support-deck/*`` requests (and restores FAQ ``src`` afterward).

Looks for Support Deck at:
1. ``backend/support-deck`` (bundled mirror — Railway Root Directory ``/backend``)
2. ``../support-deck`` (monorepo sibling when Root Directory is repo ``/``)
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from typing import Any, Callable

from fastapi import FastAPI, Request
from starlette.responses import Response

log = logging.getLogger("support_deck_embed")


def _resolve_support_deck_root() -> Path | None:
    if os.environ.get("SUPPORT_DECK_ROOT"):
        p = Path(os.environ["SUPPORT_DECK_ROOT"]).resolve()
        return p if (p / "src" / "api" / "app.py").is_file() else None

    backend_dir = Path(__file__).resolve().parent
    candidates = [
        backend_dir / "support-deck",  # bundled for Railway Root=/backend
        backend_dir.parent / "support-deck",  # monorepo sibling
    ]
    for cand in candidates:
        if (cand / "src" / "api" / "app.py").is_file():
            return cand.resolve()
    return None


def _install_src_middleware(host: FastAPI, sd_root: Path, api_prefix: str) -> None:
    """Swap Support Deck ``src.*`` into ``sys.modules`` for Support Deck routes."""

    @host.middleware("http")
    async def support_deck_src_context(
        request: Request, call_next: Callable
    ) -> Response:
        if not request.url.path.startswith(api_prefix):
            return await call_next(request)

        sd_mods: dict[str, Any] = getattr(
            request.app.state, "_support_deck_modules", None
        ) or {}
        if not sd_mods:
            return await call_next(request)

        stashed = {
            key: sys.modules.pop(key)
            for key in list(sys.modules)
            if key == "src" or key.startswith("src.")
        }
        root = str(sd_root)
        path_inserted = False
        if root not in sys.path:
            sys.path.insert(0, root)
            path_inserted = True
        sys.modules.update(sd_mods)
        try:
            return await call_next(request)
        finally:
            for key in list(sys.modules):
                if key == "src" or key.startswith("src."):
                    sd_mods[key] = sys.modules.pop(key)
            request.app.state._support_deck_modules = sd_mods
            if path_inserted:
                try:
                    sys.path.remove(root)
                except ValueError:
                    pass
            sys.modules.update(stashed)


def attach_support_deck(host: FastAPI) -> bool:
    """Attach Support Deck routes when the package is present. Returns True if attached."""
    sd_root = _resolve_support_deck_root()
    if sd_root is None:
        log.warning("Support Deck package not found — skipping embed")
        return False

    # FAQ retrieve/classify live in this backend tree.
    backend_dir = Path(__file__).resolve().parent
    os.environ["BACKEND_ROOT"] = str(backend_dir)
    pulse = backend_dir.parent / "pulse"
    if pulse.is_dir():
        os.environ.setdefault("PULSE_ROOT", str(pulse))

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

        try:
            get_settings.cache_clear()  # type: ignore[attr-defined]
        except Exception:
            pass

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
        _install_src_middleware(host, sd_root, prefix)

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
        host.state._support_deck_modules = sd_mods
        host.state._support_deck_root = str(sd_root)
        if inserted:
            try:
                sys.path.remove(str(sd_root))
            except ValueError:
                pass
        sys.modules.update(stashed)
