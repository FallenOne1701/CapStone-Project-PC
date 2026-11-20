from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src import mcp_bridge
from src.approval.store import ApprovalStore
from src.models import ApprovalAction, ApprovalActionType, ApprovalStatus, QueueStatus


def content_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


class ApprovalService:
    """Approval gate API.

    ``approve`` marks status, then for ``docs_append`` / ``gmail_draft`` only
    invokes ``mcp_bridge`` (dry-run receipts by default). Reject and
    ``reply_finalize`` never call the bridge.
    """

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        self.store = ApprovalStore(self.db_path)

    def create_action(
        self,
        *,
        action_type: ApprovalActionType,
        payload_preview: dict[str, Any],
        content: str,
        action_id: str | None = None,
    ) -> ApprovalAction:
        aid = action_id or f"act-{uuid.uuid4().hex[:12]}"
        # Persist body for gated publish (DB stores hash + optional edits only).
        preview = dict(payload_preview)
        preview.setdefault("_publish_body", content)
        action = ApprovalAction(
            action_id=aid,
            type=action_type,
            payload_preview=preview,
            content_hash=content_hash(content),
            status=ApprovalStatus.pending_approval,
            edited_content=None,
        )
        return self.store.insert(action)

    def get_action(self, action_id: str) -> ApprovalAction:
        return self.store.get(action_id)

    def list_actions(self) -> list[ApprovalAction]:
        return self.store.list_all()

    def edit_action(self, action_id: str, content: str) -> ApprovalAction:
        """Edit only ``action_id``; siblings unchanged."""
        return self.store.update_fields(
            action_id,
            edited_content=content,
            content_hash=content_hash(content),
        )

    def _sync_queue_for_reply(
        self, action: ApprovalAction, *, status: QueueStatus
    ) -> None:
        """When a reply_finalize is decided, mirror that onto the Queue item."""
        if action.type != ApprovalActionType.reply_finalize:
            return
        qid = action.payload_preview.get("question_id")
        if not isinstance(qid, str) or not qid:
            return
        from src.api.deps import update_queue_status

        update_queue_status(self.db_path, qid, status)

    def _publish_if_needed(self, action: ApprovalAction) -> None:
        """Invoke MCP bridge only for Docs/Gmail publish actions."""
        if action.type == ApprovalActionType.docs_append:
            mcp_bridge.publish_docs_append(action)
        elif action.type == ApprovalActionType.gmail_draft:
            mcp_bridge.publish_gmail_draft(action)

    def approve(self, action_id: str) -> ApprovalAction:
        """Mark approved, then publish Docs/Gmail via bridge when applicable."""
        action = self.store.update_fields(
            action_id,
            status=ApprovalStatus.approved,
            decided_at=datetime.now(timezone.utc).replace(tzinfo=None),
            set_decided=True,
        )
        self._sync_queue_for_reply(action, status=QueueStatus.approved)
        self._publish_if_needed(action)
        return action

    def reject(self, action_id: str) -> ApprovalAction:
        """Reject only ``action_id``; siblings unchanged. No MCP call."""
        action = self.store.update_fields(
            action_id,
            status=ApprovalStatus.rejected,
            decided_at=datetime.now(timezone.utc).replace(tzinfo=None),
            set_decided=True,
        )
        self._sync_queue_for_reply(action, status=QueueStatus.rejected)
        return action


# Module-level helpers matching the plan Interfaces block (require a service).
def create_action(service: ApprovalService, **kwargs: Any) -> ApprovalAction:
    return service.create_action(**kwargs)


def edit_action(
    service: ApprovalService, action_id: str, content: str
) -> ApprovalAction:
    return service.edit_action(action_id, content)


def approve(service: ApprovalService, action_id: str) -> ApprovalAction:
    return service.approve(action_id)


def reject(service: ApprovalService, action_id: str) -> ApprovalAction:
    return service.reject(action_id)
