from __future__ import annotations

import hashlib
import sys
from types import ModuleType

import pytest

from src.db import init_db
from src.models import ApprovalActionType, ApprovalStatus


def _svc(tmp_path):
    from src.approval.service import ApprovalService

    db = tmp_path / "approvals.db"
    init_db(db)
    return ApprovalService(db)


def test_reject_one_leaves_other_pending(tmp_path):
    svc = _svc(tmp_path)
    a1 = svc.create_action(
        action_type=ApprovalActionType.docs_append,
        payload_preview={"summary": "pulse doc", "destinations": ["doc_id:x"]},
        content="pulse body A",
    )
    a2 = svc.create_action(
        action_type=ApprovalActionType.gmail_draft,
        payload_preview={"summary": "pulse mail", "destinations": ["to:ops@example.com"]},
        content="pulse body B",
    )
    rejected = svc.reject(a1.action_id)
    assert rejected.status == ApprovalStatus.rejected
    sibling = svc.get_action(a2.action_id)
    assert sibling.status == ApprovalStatus.pending_approval
    assert sibling.content_hash == a2.content_hash


def test_edit_one_does_not_change_sibling_hash(tmp_path):
    svc = _svc(tmp_path)
    a1 = svc.create_action(
        action_type=ApprovalActionType.docs_append,
        payload_preview={"summary": "doc"},
        content="original A",
    )
    a2 = svc.create_action(
        action_type=ApprovalActionType.gmail_draft,
        payload_preview={"summary": "mail"},
        content="original B",
    )
    sibling_hash_before = a2.content_hash
    edited = svc.edit_action(a1.action_id, "edited A content")
    assert edited.edited_content == "edited A content"
    assert edited.content_hash != a1.content_hash
    assert edited.content_hash == hashlib.sha256(b"edited A content").hexdigest()
    sibling = svc.get_action(a2.action_id)
    assert sibling.content_hash == sibling_hash_before
    assert sibling.edited_content is None
    assert sibling.status == ApprovalStatus.pending_approval


def test_approve_one_leaves_other_pending(tmp_path):
    svc = _svc(tmp_path)
    a1 = svc.create_action(
        action_type=ApprovalActionType.reply_finalize,
        payload_preview={"summary": "reply 1"},
        content="draft 1",
    )
    a2 = svc.create_action(
        action_type=ApprovalActionType.reply_finalize,
        payload_preview={"summary": "reply 2"},
        content="draft 2",
    )
    approved = svc.approve(a1.action_id)
    assert approved.status == ApprovalStatus.approved
    assert approved.decided_at is not None
    sibling = svc.get_action(a2.action_id)
    assert sibling.status == ApprovalStatus.pending_approval


def test_approve_docs_calls_bridge_reject_does_not(tmp_path, monkeypatch):
    """Task 13: approve docs/gmail invokes bridge once; reject never does.
    Store stays free of MCP imports.
    """
    svc = _svc(tmp_path)
    mcp_calls: list[str] = []
    fake = ModuleType("src.mcp_bridge")

    def track(name):
        def _inner(*_a, **_k):
            mcp_calls.append(name)

        return _inner

    fake.publish_docs_append = track("docs")
    fake.publish_gmail_draft = track("gmail")

    import src.approval.service as service_mod

    monkeypatch.setitem(sys.modules, "src.mcp_bridge", fake)
    monkeypatch.setattr(service_mod, "mcp_bridge", fake)

    docs = svc.create_action(
        action_type=ApprovalActionType.docs_append,
        payload_preview={"summary": "doc"},
        content="body",
    )
    mail = svc.create_action(
        action_type=ApprovalActionType.gmail_draft,
        payload_preview={"summary": "mail", "destinations": ["to:ops@example.com"]},
        content="body B",
    )
    svc.reject(mail.action_id)
    assert mcp_calls == []

    approved = svc.approve(docs.action_id)
    assert approved.status == ApprovalStatus.approved
    assert mcp_calls == ["docs"]

    from pathlib import Path
    import src.approval.store as store_mod

    assert "mcp_bridge" not in Path(store_mod.__file__).read_text(encoding="utf-8")


def test_get_missing_action_raises(tmp_path):
    svc = _svc(tmp_path)
    with pytest.raises(KeyError):
        svc.get_action("missing-id")
