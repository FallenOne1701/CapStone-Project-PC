from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path

from fastapi import Request

from src.db import connect
from src.models import ApprovalAction, FeeExplainer, QueueItem, QueueStatus


def get_db_path(request: Request) -> Path:
    return Path(request.app.state.db_path)


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace(" ", "T"))
    except ValueError:
        return None


def row_to_queue_item(row) -> QueueItem:
    keys = row.keys() if hasattr(row, "keys") else []
    raw_pkg = row["agent_package_json"] if "agent_package_json" in keys else "{}"
    try:
        package = json.loads(raw_pkg or "{}")
    except json.JSONDecodeError:
        package = {}
    if not isinstance(package, dict):
        package = {}
    return QueueItem(
        question_id=row["question_id"],
        question_text=row["question_text"] or "",
        status=QueueStatus(row["status"]),
        draft=row["draft"],
        citation_url=row["citation_url"],
        routing_note=row["routing_note"],
        searched=json.loads(row["searched_json"] or "[]"),
        reviewer_flags=json.loads(row["reviewer_flags_json"] or "[]"),
        explainer_id=row["explainer_id"],
        agent_package=package,
        created_at=_parse_dt(row["created_at"]),
        updated_at=_parse_dt(row["updated_at"]),
    )


def list_queue_items(db_path: Path) -> list[QueueItem]:
    con = connect(db_path)
    try:
        rows = con.execute(
            "SELECT * FROM queue_items ORDER BY created_at DESC, question_id ASC"
        ).fetchall()
    finally:
        con.close()
    return [row_to_queue_item(r) for r in rows]


def get_queue_item(db_path: Path, question_id: str) -> QueueItem | None:
    con = connect(db_path)
    try:
        row = con.execute(
            "SELECT * FROM queue_items WHERE question_id = ?",
            (question_id,),
        ).fetchone()
    finally:
        con.close()
    if row is None:
        return None
    return row_to_queue_item(row)


def update_queue_draft(db_path: Path, question_id: str, draft: str) -> QueueItem:
    """Edit draft text only — citation/status/siblings unchanged."""
    item = get_queue_item(db_path, question_id)
    if item is None:
        raise KeyError(f"unknown question_id: {question_id}")
    con = connect(db_path)
    try:
        con.execute(
            """
            UPDATE queue_items
            SET draft = ?, updated_at = datetime('now')
            WHERE question_id = ?
            """,
            (draft, question_id),
        )
        con.commit()
    finally:
        con.close()
    updated = get_queue_item(db_path, question_id)
    assert updated is not None
    return updated


def update_queue_status(
    db_path: Path, question_id: str, status: QueueStatus
) -> QueueItem | None:
    """Set queue item status only (used when reply_finalize is decided)."""
    item = get_queue_item(db_path, question_id)
    if item is None:
        return None
    con = connect(db_path)
    try:
        con.execute(
            """
            UPDATE queue_items
            SET status = ?, updated_at = datetime('now')
            WHERE question_id = ?
            """,
            (status.value, question_id),
        )
        con.commit()
    finally:
        con.close()
    return get_queue_item(db_path, question_id)


def list_approval_actions(db_path: Path) -> list[ApprovalAction]:
    from src.approval.service import ApprovalService

    return ApprovalService(db_path).list_actions()


def list_explainers(db_path: Path, *, active_only: bool = False) -> list[FeeExplainer]:
    con = connect(db_path)
    try:
        if active_only:
            rows = con.execute(
                """
                SELECT * FROM explainers WHERE active = 1
                ORDER BY updated_at DESC, explainer_id ASC
                """
            ).fetchall()
        else:
            rows = con.execute(
                """
                SELECT * FROM explainers
                ORDER BY updated_at DESC, explainer_id ASC
                """
            ).fetchall()
    finally:
        con.close()
    out: list[FeeExplainer] = []
    for row in rows:
        out.append(
            FeeExplainer(
                explainer_id=row["explainer_id"],
                bullets=json.loads(row["bullets_json"]),
                links=json.loads(row["links_json"]),
                last_checked=date.fromisoformat(row["last_checked"]),
                active=bool(row["active"]),
            )
        )
    return out


def sources_panel(db_path: Path) -> list[dict]:
    """Claim → URL + last_checked for the Sources view."""
    claims: list[dict] = []
    for explainer in list_explainers(db_path):
        url = explainer.links[0] if explainer.links else ""
        checked = explainer.last_checked.isoformat()
        for bullet in explainer.bullets:
            claims.append(
                {
                    "claim": bullet,
                    "url": url,
                    "last_checked": checked,
                    "explainer_id": explainer.explainer_id,
                }
            )
        # Include second official link as its own source row when present
        if len(explainer.links) > 1:
            claims.append(
                {
                    "claim": f"Official source (explainer {explainer.explainer_id})",
                    "url": explainer.links[1],
                    "last_checked": checked,
                    "explainer_id": explainer.explainer_id,
                }
            )
    return claims


def serialize_model(model) -> dict:
    if hasattr(model, "model_dump"):
        return model.model_dump(mode="json")
    return dict(model)
