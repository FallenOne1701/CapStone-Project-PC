"""Gated MCP publish bridge for Docs append + Gmail draft.

Called only after human approve of ``docs_append`` / ``gmail_draft``.
Default local mode writes dry-run receipts under
``data/fixtures/mcp-receipts/``. Set ``MCP_LIVE=1`` to invoke MCP-Server-1
over HTTP (``MCP_URL`` + ``MCP_API_KEY``). Cursor chat tool calls are
documented in ``DOCS-AI-Agent-Support-Deck/mcp-runbook.md``.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.models import ApprovalAction, ApprovalActionType

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
RECEIPTS_DIR = PACKAGE_ROOT / "data" / "fixtures" / "mcp-receipts"


def _mcp_live() -> bool:
    return os.environ.get("MCP_LIVE", "").strip().lower() in {"1", "true", "yes"}


def _resolve_content(action: ApprovalAction) -> str:
    if action.edited_content:
        return action.edited_content
    artifact = action.payload_preview.get("artifact")
    if isinstance(artifact, str) and artifact:
        path = Path(artifact)
        if path.is_file():
            return path.read_text(encoding="utf-8")
    for key in ("_publish_body", "content", "body"):
        stored = action.payload_preview.get(key)
        if isinstance(stored, str) and stored:
            return stored
    raise ValueError(
        f"No publish content for action {action.action_id}: "
        "set edited_content, artifact file, or payload_preview._publish_body"
    )


def _dest_value(action: ApprovalAction, prefix: str) -> str:
    for dest in action.payload_preview.get("destinations") or []:
        if isinstance(dest, str) and dest.startswith(prefix):
            return dest[len(prefix) :]
    return ""


def _is_unset(value: str) -> bool:
    v = (value or "").strip()
    return not v or v.startswith("(unset")


def _write_receipt(
    tool: str, arguments: dict[str, Any], action: ApprovalAction
) -> Path:
    RECEIPTS_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    path = RECEIPTS_DIR / f"{ts}_{action.type.value}_{action.action_id}.json"
    payload = {
        "mode": "dry_run",
        "tool": tool,
        "action_id": action.action_id,
        "action_type": action.type.value,
        "arguments": arguments,
        "written_at": datetime.now(timezone.utc).isoformat(),
    }
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def _rpc(method: str, params: dict | None = None, req_id: int = 1) -> dict:
    mcp_url = os.environ.get("MCP_URL", "").rstrip("/")
    mcp_key = os.environ.get("MCP_API_KEY", "")
    if not mcp_url or not mcp_key:
        raise RuntimeError("MCP_LIVE=1 requires MCP_URL and MCP_API_KEY")
    body = {
        "jsonrpc": "2.0",
        "id": req_id,
        "method": method,
        "params": params or {},
    }
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        mcp_url,
        data=data,
        method="POST",
        headers={
            "Authorization": f"Bearer {mcp_key}",
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        err_body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"MCP HTTP {exc.code}: {err_body[:500]}") from exc
    if raw.startswith("event:") or (
        raw.splitlines() and raw.splitlines()[0].startswith("data:")
    ):
        payloads = [
            line[5:].strip()
            for line in raw.splitlines()
            if line.startswith("data:")
        ]
        raw = payloads[-1] if payloads else raw
    return json.loads(raw)


def _live_call(tool: str, arguments: dict[str, Any]) -> dict:
    _rpc(
        "initialize",
        {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "support-deck-mcp-bridge", "version": "0.1"},
        },
        req_id=1,
    )
    return _rpc(
        "tools/call",
        {"name": tool, "arguments": arguments},
        req_id=2,
    )


def publish_docs_append(action: ApprovalAction) -> None:
    """Publish pulse body via ``google_docs_append_content`` (or dry-run receipt)."""
    if action.type != ApprovalActionType.docs_append:
        raise ValueError(
            f"publish_docs_append requires docs_append, got {action.type}"
        )
    content = _resolve_content(action)
    from src.config import get_settings

    doc_id = _dest_value(action, "doc_id:") or get_settings().pulse_doc_id
    arguments: dict[str, Any] = {
        "document_id": doc_id,
        "content": content,
        "add_newline_before": True,
    }
    if _mcp_live():
        if _is_unset(doc_id):
            raise RuntimeError(
                "MCP_LIVE docs append blocked: set PULSE_DOC_ID / doc_id"
            )
        _live_call("google_docs_append_content", arguments)
        return
    _write_receipt("google_docs_append_content", arguments, action)


def publish_gmail_draft(action: ApprovalAction) -> None:
    """Create Gmail draft via ``gmail_create_draft`` (or dry-run receipt)."""
    if action.type != ApprovalActionType.gmail_draft:
        raise ValueError(
            f"publish_gmail_draft requires gmail_draft, got {action.type}"
        )
    content = _resolve_content(action)
    from src.config import get_settings

    settings = get_settings()
    draft_to = _dest_value(action, "to:") or settings.pulse_draft_to
    doc_id = settings.pulse_doc_id
    date_hint = ""
    artifact = action.payload_preview.get("artifact")
    if isinstance(artifact, str) and artifact:
        stem = Path(artifact).stem
        if stem.startswith("pulse-"):
            date_hint = stem.replace("pulse-", "", 1)
    subject = (
        f"Groww Weekly Review Pulse — {date_hint}"
        if date_hint
        else "Groww Weekly Review Pulse"
    )
    doc_line = ""
    if doc_id and not _is_unset(doc_id):
        doc_line = f"Doc: https://docs.google.com/document/d/{doc_id}/edit\n\n"
    body = f"Weekly pulse ready.\n\n{doc_line}---\n{content}"
    arguments: dict[str, Any] = {
        "to": [draft_to] if draft_to else [],
        "subject": subject,
        "body": body,
    }
    if _mcp_live():
        if _is_unset(draft_to):
            raise RuntimeError(
                "MCP_LIVE gmail draft blocked: set PULSE_DRAFT_TO / to:"
            )
        _live_call("gmail_create_draft", arguments)
        return
    _write_receipt("gmail_create_draft", arguments, action)
