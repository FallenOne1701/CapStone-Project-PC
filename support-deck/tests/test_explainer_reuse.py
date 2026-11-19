from __future__ import annotations

from datetime import date

import pytest

from src.db import init_db
from src.desk.faq_client import RetrieveResult
from src.desk.policy_agent import PolicyResult
from src.models import FeeExplainer, QueueStatus
from src.weekly.fee_explainer import upsert_explainer


def _seed_explainer(db, *, active: bool = True) -> FeeExplainer:
    explainer = FeeExplainer(
        explainer_id="fee-canonical-1",
        bullets=[
            "Brokerage on equity delivery is published on Groww's charges page.",
            "Mutual fund expense ratios are shown on each fund's fact sheet.",
            "Account maintenance and DP charges follow the official schedule.",
        ],
        links=[
            "https://groww.in/p/brokerage-charges",
            "https://groww.in/p/mutual-funds",
        ],
        last_checked=date(2026, 11, 18),
        active=active,
    )
    return upsert_explainer(db, explainer)


def _factual_retrieve() -> RetrieveResult:
    return RetrieveResult(
        chunks=[
            {
                "text": "Exit load is 1% if redeemed within 7 days.",
                "source_url": "https://groww.in/p/exit-load",
            }
        ],
        source_urls=["https://groww.in/p/exit-load"],
        searched=["FAQ corpus", "https://groww.in/p/exit-load"],
    )


def test_match_explainer_fee_question_hits_active(tmp_path):
    from src.connectors.explainer_reuse import match_explainer

    db = tmp_path / "reuse.db"
    init_db(db)
    seeded = _seed_explainer(db)

    hit = match_explainer("Why was I charged a brokerage fee?", db_path=db)
    assert hit is not None
    assert hit.explainer_id == seeded.explainer_id


def test_match_explainer_unrelated_or_inactive_returns_none(tmp_path):
    from src.connectors.explainer_reuse import match_explainer

    db = tmp_path / "reuse.db"
    init_db(db)
    _seed_explainer(db)

    assert match_explainer("How do I reset my Groww PIN?", db_path=db) is None

    db2 = tmp_path / "inactive.db"
    init_db(db2)
    _seed_explainer(db2, active=False)
    assert match_explainer("What are the brokerage charges?", db_path=db2) is None


def test_fee_question_reuses_explainer_skips_parallel_agents(tmp_path, monkeypatch):
    from src.desk import agents, pipeline

    db = tmp_path / "reuse.db"
    init_db(db)
    seeded = _seed_explainer(db)

    called = {"n": 0}

    def _boom(*_a, **_k):
        called["n"] += 1
        raise AssertionError("parallel desk agents must be skipped on explainer reuse")

    monkeypatch.setattr(agents, "run_agents_parallel", _boom)

    item = pipeline.process_question(
        "What fees and charges apply on Groww?",
        db_path=db,
        fixture_mode=True,
    )
    assert called["n"] == 0
    assert item.routing_note == "reuse_explainer"
    assert item.explainer_id == seeded.explainer_id
    assert item.status == QueueStatus.drafted
    assert item.citation_url in seeded.links
    assert item.draft
    assert item.agent_package
    assert item.agent_package["retrieve"]["path"] == "reuse_explainer"
    assert "draft" not in item.agent_package["agents_fired"]
    assert (item.agent_package.get("draft") or {}).get("text")
    from src.desk.reviewer import _sentence_count

    assert _sentence_count(item.draft) <= 3


def test_unrelated_question_uses_full_desk(tmp_path, monkeypatch):
    from src.desk import agents, draft_agent, pipeline

    db = tmp_path / "reuse.db"
    init_db(db)
    _seed_explainer(db)

    called = {"n": 0}

    def _fake(q, fixture_mode=None):
        called["n"] += 1
        return (
            PolicyResult(allow=True, refuse=False, reasons=["factual_ok"], category="factual"),
            _factual_retrieve(),
            draft_agent._fixture_draft(q, _factual_retrieve()),
        )

    monkeypatch.setattr(agents, "run_agents_parallel", _fake)

    item = pipeline.process_question(
        "How do I reset my Groww PIN?",
        db_path=db,
        fixture_mode=True,
    )
    assert called["n"] == 1
    assert item.routing_note != "reuse_explainer"
    assert item.explainer_id is None


def test_fee_question_without_explainer_uses_full_desk(tmp_path, monkeypatch):
    from src.desk import agents, draft_agent, pipeline

    db = tmp_path / "empty.db"
    init_db(db)

    called = {"n": 0}

    def _fake(q, fixture_mode=None):
        called["n"] += 1
        return (
            PolicyResult(allow=True, refuse=False, reasons=["factual_ok"], category="factual"),
            _factual_retrieve(),
            draft_agent._fixture_draft(q, _factual_retrieve()),
        )

    monkeypatch.setattr(agents, "run_agents_parallel", _fake)

    item = pipeline.process_question(
        "Why was I charged a fee?",
        db_path=db,
        fixture_mode=True,
    )
    assert called["n"] == 1
    assert item.routing_note != "reuse_explainer"
    assert item.explainer_id is None
