from __future__ import annotations

import json

import pytest

from src.db import connect, init_db
from src.desk.faq_client import RetrieveResult
from src.desk.policy_agent import PolicyResult
from src.models import ApprovalActionType, ApprovalStatus, QueueStatus


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


def _empty_retrieve(q: str = "unknown") -> RetrieveResult:
    return RetrieveResult(
        chunks=[],
        source_urls=[],
        searched=["FAQ corpus", f"query:{q}"],
    )


def test_factual_in_corpus_drafted_with_citation(tmp_path, monkeypatch):
    from src.desk import agents, pipeline
    from src.desk import draft_agent

    db = tmp_path / "desk.db"
    init_db(db)

    monkeypatch.setattr(
        agents,
        "run_agents_parallel",
        lambda q, fixture_mode=None: (
            PolicyResult(allow=True, refuse=False, reasons=["factual_ok"], category="factual"),
            _factual_retrieve(),
            draft_agent._fixture_draft(q, _factual_retrieve()),
        ),
    )

    item = pipeline.process_question(
        "What is the exit load?",
        db_path=db,
        fixture_mode=True,
    )
    assert item.status == QueueStatus.drafted
    assert item.citation_url == "https://groww.in/p/exit-load"
    assert item.draft and "https://groww.in/p/exit-load" in (item.draft or "")
    assert item.routing_note == "answer"
    assert item.searched
    assert item.agent_package
    assert item.agent_package["retrieve"]["path"] == "faq"
    assert "pattern" in item.agent_package["agents_fired"]
    assert item.agent_package["orchestrator"]["citation_url"] == item.citation_url

    # Persisted + reply_finalize pending
    con = connect(db)
    row = con.execute(
        "SELECT status, citation_url, agent_package_json FROM queue_items WHERE question_id = ?",
        (item.question_id,),
    ).fetchone()
    assert row["status"] == "drafted"
    assert row["citation_url"] == "https://groww.in/p/exit-load"
    stored = json.loads(row["agent_package_json"])
    assert stored["reviewer"]["passed"] is True
    actions = con.execute(
        "SELECT type, status, payload_preview_json FROM approval_actions"
    ).fetchall()
    con.close()
    assert len(actions) == 1
    assert actions[0]["type"] == ApprovalActionType.reply_finalize.value
    assert actions[0]["status"] == ApprovalStatus.pending_approval.value
    payload = json.loads(actions[0]["payload_preview_json"])
    assert payload.get("question_id") == item.question_id


def test_unknown_not_covered_with_searched(tmp_path, monkeypatch):
    from src.desk import agents, pipeline
    from src.desk import draft_agent

    db = tmp_path / "desk.db"
    init_db(db)
    q = "totally unknown product xyz"

    monkeypatch.setattr(
        agents,
        "run_agents_parallel",
        lambda question, fixture_mode=None: (
            PolicyResult(allow=True, refuse=False, reasons=["factual_ok"], category="factual"),
            _empty_retrieve(q),
            draft_agent._fixture_draft(question, _empty_retrieve(q)),
        ),
    )

    item = pipeline.process_question(q, db_path=db, fixture_mode=True)
    assert item.status == QueueStatus.not_covered
    assert item.routing_note == "not_covered"
    assert isinstance(item.searched, list) and len(item.searched) > 0
    assert item.citation_url is None

    con = connect(db)
    n_actions = con.execute("SELECT COUNT(*) AS c FROM approval_actions").fetchone()["c"]
    con.close()
    assert n_actions == 0  # no reply_finalize without drafted


def test_advisory_refused_not_answered_as_advice(tmp_path, monkeypatch):
    from src.desk import agents, pipeline

    db = tmp_path / "desk.db"
    init_db(db)

    # Even if draft wrongly returns advice text, policy refuse must win
    monkeypatch.setattr(
        agents,
        "run_agents_parallel",
        lambda q, fixture_mode=None: (
            PolicyResult(
                allow=False,
                refuse=True,
                reasons=["advisory_or_advice"],
                category="advice",
            ),
            _factual_retrieve(),
            "You should buy this fund for better returns. https://groww.in/p/exit-load",
        ),
    )

    item = pipeline.process_question(
        "Should I buy this mutual fund?",
        db_path=db,
        fixture_mode=True,
    )
    assert item.status == QueueStatus.not_covered
    assert item.routing_note in {"not_covered", "escalate_human"}
    draft_l = (item.draft or "").lower()
    assert "should buy" not in draft_l
    assert "recommend" not in draft_l
    # Still record searched for audit
    assert item.searched
    assert item.agent_package
    assert item.agent_package["policy"]["refuse"] is True
    assert item.agent_package["policy"]["category"] == "advice"
    assert "agents_fired" in item.agent_package
    assert "reviewer" in item.agent_package

    con = connect(db)
    n_actions = con.execute("SELECT COUNT(*) AS c FROM approval_actions").fetchone()["c"]
    row = con.execute(
        "SELECT status FROM queue_items WHERE question_id = ?", (item.question_id,)
    ).fetchone()
    con.close()
    assert row["status"] == "not_covered"
    assert n_actions == 0


def test_reviewer_forces_not_covered_when_ungrounded(tmp_path, monkeypatch):
    from src.desk import agents, pipeline

    db = tmp_path / "desk.db"
    init_db(db)

    # Policy allows + in-corpus retrieve, but draft invents a non-allowlisted URL
    grounded = _factual_retrieve()
    monkeypatch.setattr(
        agents,
        "run_agents_parallel",
        lambda q, fixture_mode=None: (
            PolicyResult(allow=True, refuse=False, reasons=["factual_ok"], category="factual"),
            grounded,
            "Exit load is 1%. Source: https://evil.example/fake",
        ),
    )

    item = pipeline.process_question("exit load?", db_path=db, fixture_mode=True)
    assert item.status == QueueStatus.not_covered
    assert any("ungrounded" in f or "citation" in f for f in item.reviewer_flags)
