from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.approval.store import ApprovalStore
from src.models import ApprovalAction, ApprovalActionType, ApprovalStatus


def content_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


class ApprovalService:
    """Approval gate API. ``approve`` marks status only — never calls MCP."""

    def __init__(self, db_path: str | Path) -> None:
        self.store = ApprovalStore(db_path)

    def create_action(
        self,
        *,
        action_type: ApprovalActionType,
        payload_preview: dict[str, Any],
        content: str,
        action_id: str | None = None,
    ) -> ApprovalAction:
        aid = action_id or f"act-{uuid.uuid4().hex[:12]}"
        action = ApprovalAction(
            action_id=aid,
            type=action_type,
            payload_preview=payload_preview,
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

    def approve(self, action_id: str) -> ApprovalAction:
        """Mark approved. Does not invoke MCP (bridge is a separate layer)."""
        return self.store.update_fields(
            action_id,
            status=ApprovalStatus.approved,
            decided_at=datetime.now(timezone.utc).replace(tzinfo=None),
            set_decided=True,
        )

    def reject(self, action_id: str) -> ApprovalAction:
        """Reject only ``action_id``; siblings unchanged. No MCP call."""
        return self.store.update_fields(
            action_id,
            status=ApprovalStatus.rejected,
            decided_at=datetime.now(timezone.utc).replace(tzinfo=None),
            set_decided=True,
        )


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
