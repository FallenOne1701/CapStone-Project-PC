from __future__ import annotations

import json
import sys
from datetime import date, timedelta
from pathlib import Path
from types import ModuleType

import pytest

from src.db import init_db
from src.models import ApprovalActionType, ApprovalStatus, FeeExplainer, QueueStatus
from tests.eval_helpers import agents_for_eval, load_seeds


def test_seed_file_has_at_least_20_tagged_questions():
    seeds = load_seeds()
    assert len(seeds) >= 20
    tags_seen: set[str] = set()
    for row in seeds:
        assert row.get("id")
        assert row.get("question")
        tags = row.get("tags") or []
        assert tags, f"{row['id']} missing tags"
        tags_seen.update(tags)
        assert row.get("expect_status"), f"{row['id']} missing expect_status"
    for required in ("factual", "oos", "advisory", "returns", "pii", "fee", "process"):
        assert required in tags_seen, f"missing tag class: {required}"


def test_every_seed_reaches_drafted_or_not_covered(tmp_path, monkeypatch):
    from src.desk import agents, pipeline

    seeds = load_seeds()
    db = tmp_path / "eval_feasibility.db"
    init_db(db)
    monkeypatch.setattr(agents, "run_agents_parallel", agents_for_eval(seeds))

    for seed in seeds:
        item = pipeline.process_question(
            seed["question"],
            db_path=db,
            fixture_mode=True,
        )
        assert item.status in {QueueStatus.drafted, QueueStatus.not_covered}, seed["id"]
        allowed = {QueueStatus(s) for s in seed["expect_status"]}
        assert item.status in allowed, (
            f"{seed['id']}: got {item.status.value}, expected one of "
            f"{[s.value for s in allowed]}"
        )
        if item.status == QueueStatus.not_covered:
            assert item.searched, f"{seed['id']} not_covered without searched"
        for banned in seed.get("must_not_include") or []:
            blob = f"{item.question_text}\n{item.draft or ''}".lower()
            assert banned.lower() not in blob, f"{seed['id']} leaked {banned!r}"
        if seed.get("expect_routing"):
            assert item.routing_note == seed["expect_routing"], seed["id"]


def test_weekly_sample_reaches_pending_with_theme_ids_and_window(
    tmp_path, monkeypatch
):
    from src.weekly import runner

    end = date(2026, 11, 19)
    start = end - timedelta(weeks=10)
    out = tmp_path / "out"
    out.mkdir()
    themes = out / "themes.json"
    pulse = out / f"pulse-{end.isoformat()}.md"
    themes.write_text(
        json.dumps(
            {
                "themes": [
                    {
                        "theme_id": "t1",
                        "label": "Fees",
                        "review_ids": ["r1", "r2"],
                        "count": 2,
                    },
                    {
                        "theme_id": "t2",
                        "label": "KYC",
                        "review_ids": ["r3"],
                        "count": 1,
                    },
                ],
                "top_theme_ids": ["t1", "t2"],
                "window_start": start.isoformat(),
                "window_end": end.isoformat(),
            }
        ),
        encoding="utf-8",
    )
    pulse.write_text(
        f"# Pulse\nWindow: {start.isoformat()} → {end.isoformat()}\n"
        "Top themes summarized with grounded quotes.\n",
        encoding="utf-8",
    )

    db = tmp_path / "weekly.db"
    init_db(db)

    mcp_calls: list[str] = []
    fake_mcp = ModuleType("src.mcp_bridge")

    def boom(name):
        def _inner(*_a, **_k):
            mcp_calls.append(name)
            raise AssertionError(f"MCP must not be called: {name}")

        return _inner

    fake_mcp.publish_docs_append = boom("docs")
    fake_mcp.publish_gmail_draft = boom("gmail")
    monkeypatch.setitem(sys.modules, "src.mcp_bridge", fake_mcp)

    monkeypatch.setattr(
        runner,
        "_run_pulse_pipeline",
        lambda live=False: runner.WeeklyArtifacts(
            themes_path=themes,
            pulse_path=pulse,
            window_start=start,
            window_end=end,
            lookback_weeks=10,
            live=False,
        ),
    )

    result = runner.run_weekly_to_pending(live=False, db_path=db)
    assert mcp_calls == []
    assert len(result.actions) == 2
    assert {a.type for a in result.actions} == {
        ApprovalActionType.docs_append,
        ApprovalActionType.gmail_draft,
    }
    assert all(a.status == ApprovalStatus.pending_approval for a in result.actions)

    raw = json.loads(themes.read_text(encoding="utf-8"))
    theme_list = raw["themes"]
    assert 1 <= len(theme_list) <= 5
    for theme in theme_list:
        assert theme.get("review_ids"), theme
    assert 8 <= result.artifacts.lookback_weeks <= 12
    assert result.artifacts.window_start == start
    assert result.artifacts.window_end == end


def test_caps_reply_explainer_pulse_bounds():
    from src.desk.draft_agent import _sentence_cap

    long = "One. Two. Three. Four. Five."
    capped = _sentence_cap(long, max_sentences=3)
    assert capped.count(".") <= 3

    explainer = FeeExplainer(
        bullets=["a", "b", "c", "d", "e", "f"],
        links=[
            "https://groww.in/p/brokerage-charges",
            "https://groww.in/p/mutual-funds",
        ],
        last_checked=date(2026, 11, 19),
    )
    assert len(explainer.bullets) <= 6
    assert len(explainer.links) == 2

    with pytest.raises(Exception):
        FeeExplainer(
            bullets=["1", "2", "3", "4", "5", "6", "7"],
            links=[
                "https://groww.in/p/brokerage-charges",
                "https://groww.in/p/mutual-funds",
            ],
            last_checked=date(2026, 11, 19),
        )
