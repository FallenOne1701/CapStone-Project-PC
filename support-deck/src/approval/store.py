from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from src.db import connect
from src.models import ApprovalAction, ApprovalActionType, ApprovalStatus


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    # SQLite datetime('now') → "YYYY-MM-DD HH:MM:SS"
    try:
        return datetime.fromisoformat(value.replace(" ", "T"))
    except ValueError:
        return None


def _row_to_action(row) -> ApprovalAction:
    return ApprovalAction(
        action_id=row["action_id"],
        type=ApprovalActionType(row["type"]),
        payload_preview=json.loads(row["payload_preview_json"] or "{}"),
        content_hash=row["content_hash"] or "",
        status=ApprovalStatus(row["status"]),
        edited_content=row["edited_content"],
        created_at=_parse_dt(row["created_at"]),
        updated_at=_parse_dt(row["updated_at"]),
        decided_at=_parse_dt(row["decided_at"]),
    )


class ApprovalStore:
    """SQLite persistence for approval actions. No MCP side effects."""

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)

    def insert(self, action: ApprovalAction) -> ApprovalAction:
        con = connect(self.db_path)
        try:
            con.execute(
                """
                INSERT INTO approval_actions (
                    action_id, type, payload_preview_json, content_hash,
                    status, edited_content, decided_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    action.action_id,
                    action.type.value,
                    json.dumps(action.payload_preview),
                    action.content_hash,
                    action.status.value,
                    action.edited_content,
                    action.decided_at.isoformat(sep=" ") if action.decided_at else None,
                ),
            )
            con.commit()
        finally:
            con.close()
        return self.get(action.action_id)

    def get(self, action_id: str) -> ApprovalAction:
        con = connect(self.db_path)
        try:
            row = con.execute(
                "SELECT * FROM approval_actions WHERE action_id = ?",
                (action_id,),
            ).fetchone()
        finally:
            con.close()
        if row is None:
            raise KeyError(f"unknown action_id: {action_id}")
        return _row_to_action(row)

    def update_fields(
        self,
        action_id: str,
        *,
        content_hash: str | None = None,
        status: ApprovalStatus | None = None,
        edited_content: str | None = None,
        clear_edited: bool = False,
        decided_at: datetime | None = None,
        set_decided: bool = False,
    ) -> ApprovalAction:
        """Update only the row matching ``action_id`` (isolation invariant)."""
        # Ensure target exists first
        self.get(action_id)
        sets: list[str] = ["updated_at = datetime('now')"]
        params: list[object] = []
        if content_hash is not None:
            sets.append("content_hash = ?")
            params.append(content_hash)
        if status is not None:
            sets.append("status = ?")
            params.append(status.value)
        if clear_edited:
            sets.append("edited_content = NULL")
        elif edited_content is not None:
            sets.append("edited_content = ?")
            params.append(edited_content)
        if set_decided:
            sets.append("decided_at = ?")
            params.append(
                decided_at.isoformat(sep=" ") if decided_at else None
            )
        params.append(action_id)
        con = connect(self.db_path)
        try:
            con.execute(
                f"UPDATE approval_actions SET {', '.join(sets)} WHERE action_id = ?",
                params,
            )
            con.commit()
        finally:
            con.close()
        return self.get(action_id)
