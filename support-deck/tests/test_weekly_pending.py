from __future__ import annotations

import sys
from datetime import date, timedelta
from types import ModuleType, SimpleNamespace

import pytest


def _seed_artifacts(tmp_path, end: date):
    themes = tmp_path / "themes.json"
    pulse_md = tmp_path / f"pulse-{end.isoformat()}.md"
    themes.write_text('{"themes": [], "top_theme_ids": []}', encoding="utf-8")
    pulse_md.write_text("# Pulse\n", encoding="utf-8")
    return themes, pulse_md


def test_finalize_artifacts_sample_returns_paths(tmp_path):
    from src.weekly.runner import WeeklyArtifacts, _finalize_artifacts

    end = date(2026, 11, 18)
    start = end - timedelta(weeks=10)
    themes, pulse_md = _seed_artifacts(tmp_path, end)

    def fake_main(argv=None):
        assert argv == ["--sample"]
        assert themes.exists() and pulse_md.exists()
        return 0

    art = _finalize_artifacts(
        pulse_main=fake_main,
        live=False,
        get_settings=lambda: SimpleNamespace(
            pulse_lookback_weeks=10, out_dir=tmp_path
        ),
        window_bounds=lambda weeks: (start, end),
    )
    assert isinstance(art, WeeklyArtifacts)
    assert art.themes_path == themes
    assert art.pulse_path == pulse_md
    assert art.themes_path.is_file()
    assert art.pulse_path.is_file()
    assert art.live is False
    assert art.window_end == end
    assert art.lookback_weeks == 10


def test_run_weekly_defaults_to_sample(monkeypatch, tmp_path):
    from src.weekly import runner

    end = date(2026, 11, 18)
    themes, pulse_md = _seed_artifacts(tmp_path, end)
    seen: dict[str, bool] = {}

    def fake_pipeline(live: bool = False):
        seen["live"] = live
        return runner.WeeklyArtifacts(
            themes_path=themes,
            pulse_path=pulse_md,
            window_start=end - timedelta(weeks=10),
            window_end=end,
            lookback_weeks=10,
            live=live,
        )

    monkeypatch.setattr(runner, "_run_pulse_pipeline", fake_pipeline)
    art = runner.run_weekly()
    assert seen["live"] is False
    assert art.pulse_path.name.startswith("pulse-")
    assert art.themes_path.name == "themes.json"


def test_run_weekly_never_calls_mcp(monkeypatch, tmp_path):
    from src.weekly import runner

    end = date(2026, 11, 18)
    themes, pulse_md = _seed_artifacts(tmp_path, end)
    mcp_calls: list[str] = []

    fake_mcp = ModuleType("src.mcp_bridge")

    def boom(name):
        def _inner(*_a, **_k):
            mcp_calls.append(name)
            raise AssertionError(f"MCP must not be called: {name}")

        return _inner

    fake_mcp.publish_docs_append = boom("publish_docs_append")
    fake_mcp.publish_gmail_draft = boom("publish_gmail_draft")
    monkeypatch.setitem(sys.modules, "src.mcp_bridge", fake_mcp)

    monkeypatch.setattr(
        runner,
        "_run_pulse_pipeline",
        lambda live=False: runner.WeeklyArtifacts(
            themes_path=themes,
            pulse_path=pulse_md,
            window_start=end - timedelta(weeks=10),
            window_end=end,
            lookback_weeks=10,
            live=live,
        ),
    )

    art = runner.run_weekly(live=False)
    assert art.themes_path.exists()
    assert mcp_calls == []
    # Production runner must not import/call MCP bridge
    assert "src.mcp_bridge" not in getattr(runner, "__dict__", {})
    source = __import__("pathlib").Path(runner.__file__).read_text(encoding="utf-8")
    assert "mcp_bridge" not in source
    assert "google_docs_append" not in source
    assert "gmail_create_draft" not in source


def test_finalize_artifacts_raises_on_pulse_failure(tmp_path):
    from src.weekly.runner import _finalize_artifacts

    with pytest.raises(RuntimeError, match="pulse run failed"):
        _finalize_artifacts(
            pulse_main=lambda argv=None: 2,
            live=False,
            get_settings=lambda: SimpleNamespace(
                pulse_lookback_weeks=10, out_dir=tmp_path
            ),
            window_bounds=lambda weeks: (date(2026, 1, 1), date(2026, 3, 1)),
        )
