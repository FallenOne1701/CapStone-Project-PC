from __future__ import annotations

import json
import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock

import pytest

from src.db import init_db
from src.models import ApprovalActionType, ApprovalStatus


def _svc(tmp_path):
    from src.approval.service import ApprovalService

    db = tmp_path / "mcp.db"
    init_db(db)
    return ApprovalService(db)


def _pulse_artifact(tmp_path: Path, body: str = "# Pulse\nhello") -> Path:
    path = tmp_path / "pulse-2026-11-19.md"
    path.write_text(body, encoding="utf-8")
    return path


def test_reject_never_calls_mcp_bridge(tmp_path, monkeypatch):
    svc = _svc(tmp_path)
    artifact = _pulse_artifact(tmp_path)
    calls: list[str] = []

    fake = ModuleType("src.mcp_bridge")

    def docs(action):
        calls.append(f"docs:{action.action_id}")

    def gmail(action):
        calls.append(f"gmail:{action.action_id}")

    fake.publish_docs_append = docs
    fake.publish_gmail_draft = gmail
    monkeypatch.setitem(sys.modules, "src.mcp_bridge", fake)
    monkeypatch.setattr(
        "src.approval.service.mcp_bridge", fake, raising=False
    )
    # Force re-import path used by service if it imports at call time
    import src.approval.service as service_mod

    monkeypatch.setattr(
        service_mod, "mcp_bridge", fake, raising=False
    )

    # Re-bind if service imports functions at module level later
    if hasattr(service_mod, "publish_docs_append"):
        monkeypatch.setattr(service_mod, "publish_docs_append", docs)
    if hasattr(service_mod, "publish_gmail_draft"):
        monkeypatch.setattr(service_mod, "publish_gmail_draft", gmail)

    action = svc.create_action(
        action_type=ApprovalActionType.docs_append,
        payload_preview={
            "summary": "doc",
            "destinations": ["doc_id:DOC123"],
            "artifact": str(artifact),
        },
        content=artifact.read_text(encoding="utf-8"),
    )
    rejected = svc.reject(action.action_id)
    assert rejected.status == ApprovalStatus.rejected
    assert calls == []


def test_approve_docs_calls_bridge_once(tmp_path, monkeypatch):
    svc = _svc(tmp_path)
    artifact = _pulse_artifact(tmp_path)
    calls: list[tuple[str, str]] = []

    fake = ModuleType("src.mcp_bridge")

    def docs(action):
        calls.append(("docs", action.action_id))

    def gmail(action):
        calls.append(("gmail", action.action_id))

    fake.publish_docs_append = docs
    fake.publish_gmail_draft = gmail

    import src.approval.service as service_mod

    monkeypatch.setitem(sys.modules, "src.mcp_bridge", fake)
    monkeypatch.setattr(service_mod, "mcp_bridge", fake, raising=False)

    action = svc.create_action(
        action_type=ApprovalActionType.docs_append,
        payload_preview={
            "summary": "doc",
            "destinations": ["doc_id:DOC123"],
            "artifact": str(artifact),
        },
        content=artifact.read_text(encoding="utf-8"),
    )
    approved = svc.approve(action.action_id)
    assert approved.status == ApprovalStatus.approved
    assert calls == [("docs", action.action_id)]


def test_approve_gmail_calls_bridge_once(tmp_path, monkeypatch):
    svc = _svc(tmp_path)
    artifact = _pulse_artifact(tmp_path)
    calls: list[tuple[str, str]] = []

    fake = ModuleType("src.mcp_bridge")

    def docs(action):
        calls.append(("docs", action.action_id))

    def gmail(action):
        calls.append(("gmail", action.action_id))

    fake.publish_docs_append = docs
    fake.publish_gmail_draft = gmail

    import src.approval.service as service_mod

    monkeypatch.setitem(sys.modules, "src.mcp_bridge", fake)
    monkeypatch.setattr(service_mod, "mcp_bridge", fake, raising=False)

    action = svc.create_action(
        action_type=ApprovalActionType.gmail_draft,
        payload_preview={
            "summary": "mail",
            "destinations": ["to:ops@example.com"],
            "artifact": str(artifact),
        },
        content=artifact.read_text(encoding="utf-8"),
    )
    approved = svc.approve(action.action_id)
    assert approved.status == ApprovalStatus.approved
    assert calls == [("gmail", action.action_id)]


def test_approve_reply_finalize_does_not_call_bridge(tmp_path, monkeypatch):
    svc = _svc(tmp_path)
    calls: list[str] = []

    fake = ModuleType("src.mcp_bridge")
    fake.publish_docs_append = lambda a: calls.append("docs")
    fake.publish_gmail_draft = lambda a: calls.append("gmail")

    import src.approval.service as service_mod

    monkeypatch.setitem(sys.modules, "src.mcp_bridge", fake)
    monkeypatch.setattr(service_mod, "mcp_bridge", fake, raising=False)

    action = svc.create_action(
        action_type=ApprovalActionType.reply_finalize,
        payload_preview={"summary": "reply", "question_id": "q-1"},
        content="draft text",
    )
    approved = svc.approve(action.action_id)
    assert approved.status == ApprovalStatus.approved
    assert calls == []


def test_dry_run_writes_receipt_when_mcp_live_unset(tmp_path, monkeypatch):
    from src import mcp_bridge
    from src.models import ApprovalAction

    receipts = tmp_path / "mcp-receipts"
    monkeypatch.delenv("MCP_LIVE", raising=False)
    monkeypatch.setattr(mcp_bridge, "RECEIPTS_DIR", receipts)
    monkeypatch.setattr(mcp_bridge, "PACKAGE_ROOT", tmp_path)

    artifact = _pulse_artifact(tmp_path, "# Pulse body")
    action = ApprovalAction(
        action_id="act-docs-1",
        type=ApprovalActionType.docs_append,
        payload_preview={
            "summary": "Append weekly pulse",
            "destinations": ["doc_id:DOCXYZ"],
            "artifact": str(artifact),
        },
        content_hash="abc",
        status=ApprovalStatus.approved,
    )
    mcp_bridge.publish_docs_append(action)

    files = list(receipts.glob("*.json"))
    assert len(files) == 1
    payload = json.loads(files[0].read_text(encoding="utf-8"))
    assert payload["tool"] == "google_docs_append_content"
    assert payload["mode"] == "dry_run"
    assert payload["arguments"]["document_id"] == "DOCXYZ"
    assert "Pulse body" in payload["arguments"]["content"]
    assert payload["action_id"] == "act-docs-1"


def test_store_still_has_no_mcp_bridge():
    from pathlib import Path

    import src.approval.store as store_mod

    assert "mcp_bridge" not in Path(store_mod.__file__).read_text(encoding="utf-8")


def test_gmail_publish_survives_faq_src_config_swap(tmp_path, monkeypatch):
    """After Railway embed, ``sys.modules['src']`` is FAQ — lazy config import must not run."""
    from types import SimpleNamespace

    from src import mcp_bridge
    from src.models import ApprovalAction

    receipts = tmp_path / "mcp-receipts"
    monkeypatch.delenv("MCP_LIVE", raising=False)
    monkeypatch.setattr(mcp_bridge, "RECEIPTS_DIR", receipts)

    # Simulate FAQ Settings (no pulse_* fields) winning the ``src.config`` name.
    faq_config = ModuleType("src.config")

    def faq_get_settings():
        return SimpleNamespace(
            chat_model="x",
            groq_api_key="y",
        )

    faq_config.get_settings = faq_get_settings
    monkeypatch.setitem(sys.modules, "src.config", faq_config)

    action = ApprovalAction(
        action_id="act-gmail-embed",
        type=ApprovalActionType.gmail_draft,
        payload_preview={
            "summary": "Gmail draft",
            "destinations": ["to:(unset PULSE_DRAFT_TO)"],
            "_publish_body": "# Pulse\nbody",
        },
        content_hash="abc",
        status=ApprovalStatus.approved,
    )
    mcp_bridge.publish_gmail_draft(action)
    assert list(receipts.glob("*.json"))
