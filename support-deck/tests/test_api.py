from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.db import init_db
from src.desk.faq_client import RetrieveResult
from src.desk.policy_agent import PolicyResult
from src.models import ApprovalActionType, ApprovalStatus, FeeExplainer, QueueStatus
from src.weekly.fee_explainer import upsert_explainer
from src.weekly.runner import WeeklyArtifacts, WeeklyPendingResult


PREFIX = "/api/support-deck"


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


@pytest.fixture
def api_env(tmp_path, monkeypatch):
    db = tmp_path / "api.db"
    init_db(db)

    from src.api import app as app_mod

    application = app_mod.create_app(db_path=db)
    client = TestClient(application)
    return {"client": client, "db": db, "app": application, "tmp": tmp_path}


def test_post_queue_drafted_and_not_covered(api_env, monkeypatch):
    from src.desk import agents, draft_agent

    client = api_env["client"]

    def _fake(q, fixture_mode=None):
        if "unknown" in q.lower() or "xyz" in q.lower():
            empty = _empty_retrieve(q)
            return (
                PolicyResult(
                    allow=True, refuse=False, reasons=["factual_ok"], category="factual"
                ),
                empty,
                draft_agent._fixture_draft(q, empty),
            )
        grounded = _factual_retrieve()
        return (
            PolicyResult(
                allow=True, refuse=False, reasons=["factual_ok"], category="factual"
            ),
            grounded,
            draft_agent._fixture_draft(q, grounded),
        )

    monkeypatch.setattr(agents, "run_agents_parallel", _fake)

    drafted = client.post(f"{PREFIX}/queue", json={"question": "What is the exit load?"})
    assert drafted.status_code == 200
    body = drafted.json()
    assert body["status"] == QueueStatus.drafted.value
    assert body["citation_url"] == "https://groww.in/p/exit-load"
    assert body["question_id"]

    listed = client.get(f"{PREFIX}/queue")
    assert listed.status_code == 200
    assert any(i["question_id"] == body["question_id"] for i in listed.json())

    missed = client.post(
        f"{PREFIX}/queue", json={"question": "totally unknown product xyz"}
    )
    assert missed.status_code == 200
    miss = missed.json()
    assert miss["status"] == QueueStatus.not_covered.value
    assert isinstance(miss["searched"], list) and len(miss["searched"]) > 0


def test_enqueue_returns_agent_package(api_env, monkeypatch):
    from src.desk import agents, draft_agent

    client = api_env["client"]
    grounded = _factual_retrieve()
    monkeypatch.setattr(
        agents,
        "run_agents_parallel",
        lambda q, fixture_mode=None: (
            PolicyResult(
                allow=True, refuse=False, reasons=["factual_ok"], category="factual"
            ),
            grounded,
            draft_agent._fixture_draft(q, grounded),
        ),
    )
    body = client.post(f"{PREFIX}/queue", json={"question": "What is the exit load?"}).json()
    pkg = body.get("agent_package") or {}
    assert pkg.get("retrieve", {}).get("path") == "faq"
    assert "pattern" in (pkg.get("agents_fired") or [])
    listed = client.get(f"{PREFIX}/queue").json()
    match = next(i for i in listed if i["question_id"] == body["question_id"])
    assert match["agent_package"]["orchestrator"]["citation_url"] == body["citation_url"]


def test_patch_draft_does_not_wipe_agent_package(api_env, monkeypatch):
    from src.db import connect
    from src.desk import agents, draft_agent

    client = api_env["client"]
    db = api_env["db"]
    grounded = _factual_retrieve()
    monkeypatch.setattr(
        agents,
        "run_agents_parallel",
        lambda q, fixture_mode=None: (
            PolicyResult(
                allow=True, refuse=False, reasons=["factual_ok"], category="factual"
            ),
            grounded,
            draft_agent._fixture_draft(q, grounded),
        ),
    )
    created = client.post(f"{PREFIX}/queue", json={"question": "exit load package?"}).json()
    qid = created["question_id"]
    original_pkg = created["agent_package"]
    assert original_pkg

    con = connect(db)
    before = con.execute(
        "SELECT agent_package_json FROM queue_items WHERE question_id = ?",
        (qid,),
    ).fetchone()["agent_package_json"]
    con.close()

    patched = client.patch(
        f"{PREFIX}/queue/{qid}",
        json={"draft": "edited draft text only"},
    )
    assert patched.status_code == 200
    assert patched.json()["draft"] == "edited draft text only"
    assert patched.json()["agent_package"] == original_pkg

    con = connect(db)
    after = con.execute(
        "SELECT agent_package_json FROM queue_items WHERE question_id = ?",
        (qid,),
    ).fetchone()["agent_package_json"]
    con.close()
    assert after == before


def test_patch_queue_edits_draft_only(api_env, monkeypatch):
    from src.desk import agents, draft_agent

    client = api_env["client"]
    grounded = _factual_retrieve()
    monkeypatch.setattr(
        agents,
        "run_agents_parallel",
        lambda q, fixture_mode=None: (
            PolicyResult(
                allow=True, refuse=False, reasons=["factual_ok"], category="factual"
            ),
            grounded,
            draft_agent._fixture_draft(q, grounded),
        ),
    )
    created = client.post(f"{PREFIX}/queue", json={"question": "exit load?"}).json()
    qid = created["question_id"]
    original_citation = created["citation_url"]

    patched = client.patch(
        f"{PREFIX}/queue/{qid}",
        json={"draft": "Exit load is 1% within 7 days. Source: https://groww.in/p/exit-load"},
    )
    assert patched.status_code == 200
    assert patched.json()["draft"].startswith("Exit load is 1%")
    assert patched.json()["citation_url"] == original_citation
    assert patched.json()["question_id"] == qid


def test_approve_isolation_via_api(api_env):
    from src.approval.service import ApprovalService

    client = api_env["client"]
    db = api_env["db"]
    svc = ApprovalService(db)
    a1 = svc.create_action(
        action_type=ApprovalActionType.docs_append,
        payload_preview={"summary": "doc A", "destinations": ["doc_id:x"]},
        content="body A",
    )
    a2 = svc.create_action(
        action_type=ApprovalActionType.gmail_draft,
        payload_preview={"summary": "mail B", "destinations": ["to:ops@example.com"]},
        content="body B",
    )

    approved = client.post(f"{PREFIX}/approvals/{a1.action_id}/approve")
    assert approved.status_code == 200
    assert approved.json()["status"] == ApprovalStatus.approved.value

    sibling = client.get(f"{PREFIX}/approvals").json()
    by_id = {row["action_id"]: row for row in sibling}
    assert by_id[a2.action_id]["status"] == ApprovalStatus.pending_approval.value

    rejected = client.post(f"{PREFIX}/approvals/{a2.action_id}/reject")
    assert rejected.status_code == 200
    assert rejected.json()["status"] == ApprovalStatus.rejected.value

    # Approving again must not cascade — a1 stays approved, a2 rejected
    again = client.get(f"{PREFIX}/approvals").json()
    by_id = {row["action_id"]: row for row in again}
    assert by_id[a1.action_id]["status"] == ApprovalStatus.approved.value
    assert by_id[a2.action_id]["status"] == ApprovalStatus.rejected.value


def test_reply_approve_updates_queue_status(api_env, monkeypatch):
    """Queue is the human gate for replies: approve/reject flips the queue item."""
    from src.desk import agents, draft_agent

    client = api_env["client"]
    grounded = _factual_retrieve()
    monkeypatch.setattr(
        agents,
        "run_agents_parallel",
        lambda q, fixture_mode=None: (
            PolicyResult(
                allow=True, refuse=False, reasons=["factual_ok"], category="factual"
            ),
            grounded,
            draft_agent._fixture_draft(q, grounded),
        ),
    )
    created = client.post(
        f"{PREFIX}/queue", json={"question": "What is the exit load?"}
    ).json()
    qid = created["question_id"]
    assert created["status"] == QueueStatus.drafted.value

    actions = client.get(f"{PREFIX}/approvals").json()
    reply = next(
        a
        for a in actions
        if a["type"] == ApprovalActionType.reply_finalize.value
        and a["payload_preview"].get("question_id") == qid
    )

    approved = client.post(f"{PREFIX}/approvals/{reply['action_id']}/approve")
    assert approved.status_code == 200
    assert approved.json()["status"] == ApprovalStatus.approved.value

    item = next(i for i in client.get(f"{PREFIX}/queue").json() if i["question_id"] == qid)
    assert item["status"] == QueueStatus.approved.value

    # Sibling publish actions stay untouched; a fresh reject path on another item
    created2 = client.post(
        f"{PREFIX}/queue", json={"question": "exit load again?"}
    ).json()
    qid2 = created2["question_id"]
    reply2 = next(
        a
        for a in client.get(f"{PREFIX}/approvals").json()
        if a["type"] == ApprovalActionType.reply_finalize.value
        and a["payload_preview"].get("question_id") == qid2
        and a["status"] == ApprovalStatus.pending_approval.value
    )
    rejected = client.post(f"{PREFIX}/approvals/{reply2['action_id']}/reject")
    assert rejected.status_code == 200
    item2 = next(
        i for i in client.get(f"{PREFIX}/queue").json() if i["question_id"] == qid2
    )
    assert item2["status"] == QueueStatus.rejected.value


def test_weekly_run_and_pulse_explainers_sources(api_env, monkeypatch):
    from src.approval.service import ApprovalService
    from src.weekly import runner

    client = api_env["client"]
    db = api_env["db"]
    tmp = api_env["tmp"]
    end = date(2026, 11, 18)
    start = end - timedelta(weeks=10)
    themes = tmp / "themes.json"
    pulse_md = tmp / f"pulse-{end.isoformat()}.md"
    themes.write_text(
        json.dumps(
            {
                "themes": [
                    {
                        "theme_id": "t1",
                        "label": "Fees confusion",
                        "review_ids": ["r1"],
                        "count": 3,
                    }
                ],
                "top_theme_ids": ["t1"],
            }
        ),
        encoding="utf-8",
    )
    pulse_md.write_text("# Pulse\nFee theme summary.\n", encoding="utf-8")

    upsert_explainer(
        db,
        FeeExplainer(
            explainer_id="fee-api-1",
            bullets=["Brokerage is published on the charges page."],
            links=[
                "https://groww.in/p/brokerage-charges",
                "https://groww.in/p/mutual-funds",
            ],
            last_checked=date(2026, 11, 18),
            active=True,
        ),
    )

    def fake_pending(live: bool = False, **_kwargs):
        svc = ApprovalService(db)
        arts = WeeklyArtifacts(
            themes_path=themes,
            pulse_path=pulse_md,
            window_start=start,
            window_end=end,
            lookback_weeks=10,
            live=live,
        )
        actions = [
            svc.create_action(
                action_type=ApprovalActionType.docs_append,
                payload_preview={"summary": "doc", "destinations": ["doc_id:x"]},
                content=pulse_md.read_text(encoding="utf-8"),
            ),
            svc.create_action(
                action_type=ApprovalActionType.gmail_draft,
                payload_preview={"summary": "mail", "destinations": ["to:ops@x"]},
                content=pulse_md.read_text(encoding="utf-8"),
            ),
        ]
        return WeeklyPendingResult(
            artifacts=arts, actions=actions, explainer_id="fee-api-1"
        )

    monkeypatch.setattr(runner, "run_weekly_to_pending", fake_pending)

    run = client.post(f"{PREFIX}/weekly/run?live=false")
    assert run.status_code == 200
    payload = run.json()
    assert len(payload["actions"]) == 2
    assert payload["artifacts"]["window_end"] == end.isoformat()

    pulse = client.get(f"{PREFIX}/pulse")
    assert pulse.status_code == 200
    pdata = pulse.json()
    assert "Fee theme" in pdata["pulse_markdown"] or "Pulse" in pdata["pulse_markdown"]
    assert pdata["window_end"] == end.isoformat()
    assert pdata["themes"]

    explainers = client.get(f"{PREFIX}/explainers")
    assert explainers.status_code == 200
    assert any(e["explainer_id"] == "fee-api-1" for e in explainers.json())

    sources = client.get(f"{PREFIX}/sources")
    assert sources.status_code == 200
    claims = sources.json()
    assert isinstance(claims, list) and len(claims) >= 1
    assert all("url" in c and "last_checked" in c and "claim" in c for c in claims)


def test_cors_allows_localhost_frontend(api_env):
    client = api_env["client"]
    resp = client.options(
        f"{PREFIX}/queue",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert resp.status_code in {200, 204}
    assert resp.headers.get("access-control-allow-origin") in {
        "*",
        "http://localhost:3000",
    }
