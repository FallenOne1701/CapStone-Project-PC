from __future__ import annotations

import json
import sys
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any, Callable, Iterator

from src.approval.service import ApprovalService
from src.config import get_settings
from src.db import init_db
from src.models import ApprovalAction, ApprovalActionType


@dataclass(frozen=True)
class WeeklyArtifacts:
    themes_path: Path
    pulse_path: Path
    window_start: date
    window_end: date
    lookback_weeks: int
    live: bool


@dataclass(frozen=True)
class WeeklyPendingResult:
    artifacts: WeeklyArtifacts
    actions: list[ApprovalAction] = field(default_factory=list)
    explainer_id: str | None = None


# Fallback official links when fee confusion is detected but callers pass none.
_DEFAULT_FEE_SOURCES = (
    "https://groww.in/p/brokerage-charges",
    "https://groww.in/p/mutual-funds",
)


@contextmanager
def _pulse_import_context() -> Iterator[None]:
    """Prepend PULSE_ROOT and isolate `src.*` so pulse imports do not collide."""
    pulse_root = str(Path(get_settings().pulse_root).resolve())
    stashed = {
        key: sys.modules.pop(key)
        for key in list(sys.modules)
        if key == "src" or key.startswith("src.")
    }
    inserted = False
    if pulse_root not in sys.path:
        sys.path.insert(0, pulse_root)
        inserted = True
    try:
        yield
    finally:
        for key in list(sys.modules):
            if key == "src" or key.startswith("src."):
                sys.modules.pop(key, None)
        if inserted:
            try:
                sys.path.remove(pulse_root)
            except ValueError:
                pass
        sys.modules.update(stashed)


def _finalize_artifacts(
    *,
    pulse_main: Callable[..., int],
    live: bool,
    get_settings: Callable[[], Any],
    window_bounds: Callable[[int], tuple[date, date]],
) -> WeeklyArtifacts:
    settings = get_settings()
    argv = ["--live"] if live else ["--sample"]
    rc = pulse_main(argv)
    if rc != 0:
        raise RuntimeError(f"pulse run failed with code {rc}")

    lookback = int(settings.pulse_lookback_weeks)
    start, end = window_bounds(lookback)
    themes_path = Path(settings.out_dir) / "themes.json"
    pulse_path = Path(settings.out_dir) / f"pulse-{end.isoformat()}.md"
    if not themes_path.is_file():
        raise FileNotFoundError(f"missing themes artifact: {themes_path}")
    if not pulse_path.is_file():
        raise FileNotFoundError(f"missing pulse artifact: {pulse_path}")

    return WeeklyArtifacts(
        themes_path=themes_path,
        pulse_path=pulse_path,
        window_start=start,
        window_end=end,
        lookback_weeks=lookback,
        live=live,
    )


def _run_pulse_pipeline(live: bool = False) -> WeeklyArtifacts:
    """Invoke pulse CLI modules; artifacts only — never MCP."""
    with _pulse_import_context():
        from src.config import get_settings as pulse_get_settings
        from src.fetch_play import window_bounds
        from src.run_pulse import main as pulse_main

        return _finalize_artifacts(
            pulse_main=pulse_main,
            live=live,
            get_settings=pulse_get_settings,
            window_bounds=window_bounds,
        )


def run_weekly(live: bool = False) -> WeeklyArtifacts:
    """Run the weekly pulse path (sample by default) and return artifact paths.

    Does not create Docs/Gmail drafts and does not call MCP.
    """
    return _run_pulse_pipeline(live=live)


def _maybe_fee_explainer(
    artifacts: WeeklyArtifacts,
    *,
    db_path: Path,
    fee_sources: list[str] | None = None,
) -> str | None:
    """If themes show fee confusion, generate + upsert explainer. Never calls MCP."""
    from src.weekly.fee_detect import ThemeResult, detect_fee_confusion
    from src.weekly.fee_explainer import generate_fee_explainer, upsert_explainer

    try:
        raw = json.loads(artifacts.themes_path.read_text(encoding="utf-8"))
        themes = ThemeResult.model_validate(raw)
    except Exception:
        return None
    if not detect_fee_confusion(themes):
        return None
    sources = list(fee_sources) if fee_sources else list(_DEFAULT_FEE_SOURCES)
    explainer = generate_fee_explainer(
        "fee confusion from weekly themes",
        sources,
        fixture_mode=True,
    )
    saved = upsert_explainer(db_path, explainer)
    return saved.explainer_id


def _append_frequency_appendix(artifacts: WeeklyArtifacts, *, db_path: Path) -> None:
    """Merge queue frequency signals into the pulse artifact before it is hashed.

    The callout is queue counts plus the window. It does not invent Play review ids.
    """
    from src.connectors.frequency import render_pulse_appendix, signals_for_pulse

    threshold = int(get_settings().frequency_threshold)
    signals = signals_for_pulse(
        window_days=7, threshold=threshold, db_path=db_path
    )
    appendix = render_pulse_appendix(signals)
    if not appendix:
        return
    body = artifacts.pulse_path.read_text(encoding="utf-8")
    if "## Support queue frequency" in body:
        return
    artifacts.pulse_path.write_text(
        body.rstrip() + "\n\n" + appendix, encoding="utf-8"
    )


def _create_pending_publish_actions(
    artifacts: WeeklyArtifacts,
    *,
    service: ApprovalService,
) -> list[ApprovalAction]:
    settings = get_settings()
    body = artifacts.pulse_path.read_text(encoding="utf-8")
    window = f"{artifacts.window_start.isoformat()} → {artifacts.window_end.isoformat()}"
    doc_id = settings.pulse_doc_id or "(unset PULSE_DOC_ID)"
    draft_to = settings.pulse_draft_to or "(unset PULSE_DRAFT_TO)"

    docs = service.create_action(
        action_type=ApprovalActionType.docs_append,
        payload_preview={
            "summary": f"Append weekly pulse ({window})",
            "destinations": [f"doc_id:{doc_id}"],
            "artifact": str(artifacts.pulse_path),
        },
        content=body,
    )
    gmail = service.create_action(
        action_type=ApprovalActionType.gmail_draft,
        payload_preview={
            "summary": f"Gmail draft for weekly pulse ({window})",
            "destinations": [f"to:{draft_to}"],
            "artifact": str(artifacts.pulse_path),
        },
        content=body,
    )
    return [docs, gmail]


def run_weekly_to_pending(
    live: bool = False,
    *,
    db_path: str | Path | None = None,
    fee_sources: list[str] | None = None,
) -> WeeklyPendingResult:
    """Run weekly pulse, optionally upsert a fee explainer, then create pending
    Docs + Gmail approval actions. Stops before MCP — never publishes.
    """
    artifacts = run_weekly(live=live)
    path = Path(db_path) if db_path is not None else Path(get_settings().support_deck_db)
    init_db(path)
    explainer_id = _maybe_fee_explainer(
        artifacts, db_path=path, fee_sources=fee_sources
    )
    _append_frequency_appendix(artifacts, db_path=path)
    service = ApprovalService(path)
    actions = _create_pending_publish_actions(artifacts, service=service)
    return WeeklyPendingResult(
        artifacts=artifacts,
        actions=actions,
        explainer_id=explainer_id,
    )
