from __future__ import annotations

import hashlib
import sys
from types import ModuleType

from fastapi.testclient import TestClient

from src.db import connect, init_db
from src.models import ApprovalActionType, ApprovalStatus, QueueStatus
from tests.eval_helpers import agents_for_eval, load_seeds


PREFIX = "/api/support-deck"


def test_edit_draft_a_does_not_change_draft_b(tmp_path, monkeypatch):
    from src.api import app as app_mod
    from src.desk import agents

    db = tmp_path / "edits.db"
    init_db(db)
    seeds = load_seeds()
    monkeypatch.setattr(agents, "run_agents_parallel", agents_for_eval(seeds))

    client = TestClient(app_mod.create_app(db_path=db))
    a = client.post(
        f"{PREFIX}/queue", json={"question": "What is the exit load on Groww mutual funds?"}
    ).json()
    b = client.post(
        f"{PREFIX}/queue", json={"question": "How do I redeem a mutual fund on Groww?"}
    ).json()
    assert a["status"] == QueueStatus.drafted.value
    assert b["status"] == QueueStatus.drafted.value
    b_draft_before = b["draft"]

    patched = client.patch(
        f"{PREFIX}/queue/{a['question_id']}",
        json={"draft": "Edited draft for ticket A only. Source: https://groww.in/p/exit-load"},
    )
    assert patched.status_code == 200
    assert patched.json()["draft"].startswith("Edited draft for ticket A")

    listed = {i["question_id"]: i for i in client.get(f"{PREFIX}/queue").json()}
    assert listed[b["question_id"]]["draft"] == b_draft_before
    assert listed[a["question_id"]]["draft"].startswith("Edited draft for ticket A")


def test_approve_and_reject_isolation_no_cascade(tmp_path, monkeypatch):
    from src.approval.service import ApprovalService

    db = tmp_path / "approve_iso.db"
    init_db(db)
    svc = ApprovalService(db)

    docs = svc.create_action(
        action_type=ApprovalActionType.docs_append,
        payload_preview={"summary": "docs", "destinations": ["doc:1"]},
        content="docs body",
    )
    gmail = svc.create_action(
        action_type=ApprovalActionType.gmail_draft,
        payload_preview={"summary": "mail", "destinations": ["to:ops@example.com"]},
        content="mail body",
    )
    reply = svc.create_action(
        action_type=ApprovalActionType.reply_finalize,
        payload_preview={"summary": "reply"},
        content="reply body",
    )

    mcp_calls: list[str] = []
    fake = ModuleType("src.mcp_bridge")
    fake.publish_docs_append = lambda *_a, **_k: mcp_calls.append("docs")
    fake.publish_gmail_draft = lambda *_a, **_k: mcp_calls.append("gmail")

    import src.approval.service as service_mod

    monkeypatch.setitem(sys.modules, "src.mcp_bridge", fake)
    monkeypatch.setattr(service_mod, "mcp_bridge", fake)

    rejected = svc.reject(gmail.action_id)
    assert rejected.status == ApprovalStatus.rejected
    assert mcp_calls == []

    approved_docs = svc.approve(docs.action_id)
    assert approved_docs.status == ApprovalStatus.approved
    assert mcp_calls == ["docs"]

    # Approving Docs must not auto-approve Gmail or reply
    assert svc.get_action(gmail.action_id).status == ApprovalStatus.rejected
    assert svc.get_action(reply.action_id).status == ApprovalStatus.pending_approval

    approved_reply = svc.approve(reply.action_id)
    assert approved_reply.status == ApprovalStatus.approved
    assert mcp_calls == ["docs"]  # reply_finalize does not call Docs/Gmail bridge


def test_edit_action_content_does_not_mutate_sibling_hash(tmp_path):
    from src.approval.service import ApprovalService

    db = tmp_path / "edit_hash.db"
    init_db(db)
    svc = ApprovalService(db)
    a1 = svc.create_action(
        action_type=ApprovalActionType.docs_append,
        payload_preview={"summary": "A"},
        content="original A",
    )
    a2 = svc.create_action(
        action_type=ApprovalActionType.gmail_draft,
        payload_preview={"summary": "B"},
        content="original B",
    )
    before = a2.content_hash
    edited = svc.edit_action(a1.action_id, "edited A only")
    assert edited.content_hash == hashlib.sha256(b"edited A only").hexdigest()
    sibling = svc.get_action(a2.action_id)
    assert sibling.content_hash == before
    assert sibling.edited_content is None

    con = connect(db)
    rows = {
        r["action_id"]: r
        for r in con.execute(
            "SELECT action_id, content_hash, edited_content, status FROM approval_actions"
        )
    }
    con.close()
    assert rows[a2.action_id]["content_hash"] == before
    assert rows[a1.action_id]["edited_content"] == "edited A only"
