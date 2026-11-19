from __future__ import annotations

from datetime import datetime, timedelta, timezone


def test_five_normalized_duplicates_in_seven_days_yield_one_signal(tmp_path):
    from src.connectors.frequency import record_question, signals_for_pulse

    db = tmp_path / "freq.db"
    now = datetime(2026, 11, 18, 12, 0, tzinfo=timezone.utc)
    for i in range(5):
        record_question(
            "What is the exit load?",
            at=now - timedelta(hours=i),
            db_path=db,
        )

    signals = signals_for_pulse(
        window_days=7, threshold=5, db_path=db, as_of=now
    )
    assert len(signals) == 1
    assert signals[0].count >= 5
    assert signals[0].window_days == 7
    assert signals[0].normalized_text


def test_four_duplicates_in_seven_days_do_not_signal(tmp_path):
    from src.connectors.frequency import record_question, signals_for_pulse

    db = tmp_path / "freq.db"
    now = datetime(2026, 11, 18, 12, 0, tzinfo=timezone.utc)
    for i in range(4):
        record_question("What is the exit load?", at=now - timedelta(hours=i), db_path=db)

    signals = signals_for_pulse(window_days=7, threshold=5, db_path=db, as_of=now)
    assert signals == []


def test_event_older_than_window_does_not_count(tmp_path):
    from src.connectors.frequency import record_question, signals_for_pulse

    db = tmp_path / "freq.db"
    now = datetime(2026, 11, 18, 12, 0, tzinfo=timezone.utc)
    record_question("What is the exit load?", at=now - timedelta(days=8), db_path=db)
    for i in range(4):
        record_question("What is the exit load?", at=now - timedelta(hours=i), db_path=db)

    signals = signals_for_pulse(window_days=7, threshold=5, db_path=db, as_of=now)
    assert signals == []


def test_exit_load_paraphrases_share_one_bucket(tmp_path):
    from src.connectors.frequency import normalize_question, record_question, signals_for_pulse

    assert normalize_question("exit load?") == normalize_question("What is exit load")

    db = tmp_path / "freq.db"
    now = datetime(2026, 11, 18, 12, 0, tzinfo=timezone.utc)
    variants = [
        "exit load?",
        "What is exit load",
        "what is the exit load",
        "Exit load?",
        "What is exit load?",
    ]
    for i, text in enumerate(variants):
        record_question(text, at=now - timedelta(hours=i), db_path=db)

    signals = signals_for_pulse(window_days=7, threshold=5, db_path=db, as_of=now)
    assert len(signals) == 1
    assert signals[0].count >= 5
    assert signals[0].normalized_text == "exit load"


def test_recorded_bucket_does_not_store_raw_email(tmp_path):
    from src.connectors.frequency import record_question
    from src.db import connect

    db = tmp_path / "freq.db"
    now = datetime(2026, 11, 18, 12, 0, tzinfo=timezone.utc)
    record_question(
        "exit load for user@example.com please",
        at=now,
        db_path=db,
    )
    con = connect(db)
    tables = [
        r[0]
        for r in con.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        )
    ]
    dumped = []
    for name in tables:
        for row in con.execute(f"SELECT * FROM {name}"):
            dumped.append(" ".join(str(cell) for cell in row))
    con.close()
    assert dumped, "expected a persisted frequency row"
    assert "user@example.com" not in " ".join(dumped)


def test_desk_pipeline_records_question_after_enqueue(tmp_path, monkeypatch):
    from src.connectors.frequency import signals_for_pulse
    from src.desk import agents, pipeline
    from src.desk.draft_agent import _fixture_draft
    from src.desk.faq_client import RetrieveResult
    from src.desk.policy_agent import PolicyResult

    db = tmp_path / "desk.db"
    retrieve = RetrieveResult(
        chunks=[{"text": "Exit load is 1% if redeemed within 7 days.", "source_url": "https://groww.in/p/exit-load"}],
        source_urls=["https://groww.in/p/exit-load"],
        searched=["FAQ corpus"],
    )
    monkeypatch.setattr(
        agents,
        "run_agents_parallel",
        lambda q, fixture_mode=None: (
            PolicyResult(allow=True, refuse=False, reasons=["factual_ok"], category="factual"),
            retrieve,
            _fixture_draft(q, retrieve),
        ),
    )
    for _ in range(5):
        pipeline.process_question("What is the exit load?", db_path=db, fixture_mode=True)

    signals = signals_for_pulse(window_days=7, threshold=5, db_path=db)
    assert len(signals) == 1
    assert signals[0].count >= 5
    assert signals[0].normalized_text == "exit load"


def test_weekly_pending_appends_frequency_callout(monkeypatch, tmp_path):
    from datetime import date

    from src.approval.service import content_hash
    from src.connectors.frequency import record_question
    from src.weekly import runner

    end = date(2026, 11, 18)
    themes = tmp_path / "themes.json"
    pulse_md = tmp_path / f"pulse-{end.isoformat()}.md"
    themes.write_text('{"themes": [], "top_theme_ids": []}', encoding="utf-8")
    pulse_md.write_text("# Pulse\nWeek summary body\n", encoding="utf-8")
    db = tmp_path / "support_deck.db"
    now = datetime(2026, 11, 18, 12, 0, tzinfo=timezone.utc)
    for i in range(5):
        record_question("What is the exit load?", at=now - timedelta(hours=i), db_path=db)

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

    result = runner.run_weekly_to_pending(live=False, db_path=db)
    body = pulse_md.read_text(encoding="utf-8")
    assert "## Support queue frequency" in body
    assert "count 5" in body
    assert "rolling 7 days" in body
    assert "review_id" not in body
    assert all(action.content_hash == content_hash(body) for action in result.actions)
