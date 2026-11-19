from __future__ import annotations

import sys
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Callable, Iterator

from src.config import get_settings


@dataclass(frozen=True)
class WeeklyArtifacts:
    themes_path: Path
    pulse_path: Path
    window_start: date
    window_end: date
    lookback_weeks: int
    live: bool


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
