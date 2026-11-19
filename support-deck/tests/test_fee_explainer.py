from __future__ import annotations

from datetime import date

import pytest
from pydantic import ValidationError

from src.models import FeeExplainer


def test_explainer_rejects_bad_shape():
    with pytest.raises(ValidationError):
        FeeExplainer(
            bullets=["a"] * 7,
            links=["https://a", "https://b"],
            last_checked="2026-11-18",
        )


def test_explainer_rejects_wrong_link_count():
    with pytest.raises(ValidationError):
        FeeExplainer(
            bullets=["a"],
            links=["https://a"],
            last_checked="2026-11-18",
        )


def test_detect_fee_confusion_true_on_fee_theme():
    from src.weekly.fee_detect import ThemeResult, Theme, detect_fee_confusion

    themes = ThemeResult(
        themes=[
            Theme(theme_id="t1", label="Hidden fees and charges", review_ids=["1"], count=1),
            Theme(theme_id="t2", label="App crashes", review_ids=["2"], count=1),
        ],
        top_theme_ids=["t1"],
    )
    assert detect_fee_confusion(themes) is True


def test_detect_fee_confusion_false_without_fee():
    from src.weekly.fee_detect import ThemeResult, Theme, detect_fee_confusion

    themes = ThemeResult(
        themes=[Theme(theme_id="t1", label="KYC delays", review_ids=["1"], count=1)],
        top_theme_ids=["t1"],
    )
    assert detect_fee_confusion(themes) is False


def test_generate_fee_explainer_fixture_mode():
    from src.weekly.fee_explainer import generate_fee_explainer

    sources = [
        "https://groww.in/p/brokerage-charges",
        "https://groww.in/p/mutual-funds",
    ]
    explainer = generate_fee_explainer(
        "Why was I charged a fee?",
        sources,
        fixture_mode=True,
    )
    assert isinstance(explainer, FeeExplainer)
    assert 1 <= len(explainer.bullets) <= 6
    assert len(explainer.links) == 2
    assert explainer.links == sources
    assert explainer.last_checked == date.today()


def test_upsert_explainer_roundtrip(tmp_path):
    from src.db import connect, init_db
    from src.weekly.fee_explainer import generate_fee_explainer, upsert_explainer

    db = tmp_path / "t.db"
    init_db(db)
    explainer = generate_fee_explainer(
        "exit load?",
        ["https://a.example/1", "https://a.example/2"],
        fixture_mode=True,
    )
    saved = upsert_explainer(db, explainer)
    assert saved.explainer_id

    con = connect(db)
    row = con.execute(
        "SELECT explainer_id, bullets_json, links_json, last_checked, active FROM explainers WHERE explainer_id = ?",
        (saved.explainer_id,),
    ).fetchone()
    con.close()
    assert row is not None
    assert row["last_checked"] == saved.last_checked.isoformat()
    assert row["active"] == 1

    # Upsert same id updates in place
    updated = saved.model_copy(
        update={"bullets": ["Updated fee fact"], "last_checked": date(2026, 11, 19)}
    )
    again = upsert_explainer(db, updated)
    assert again.explainer_id == saved.explainer_id
    con = connect(db)
    count = con.execute("SELECT COUNT(*) AS n FROM explainers").fetchone()["n"]
    bullets = con.execute(
        "SELECT bullets_json FROM explainers WHERE explainer_id = ?",
        (saved.explainer_id,),
    ).fetchone()["bullets_json"]
    con.close()
    assert count == 1
    assert "Updated fee fact" in bullets
