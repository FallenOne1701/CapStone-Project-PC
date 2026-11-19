from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from src.approval.service import ApprovalService
from src.config import get_settings
from src.db import connect, init_db
from src.desk import agents
from src.desk.orchestrator import orchestrate
from src.desk.reviewer import review
from src.models import ApprovalActionType, QueueItem, QueueStatus
from src.pii import redact_pii


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _persist_queue_item(db_path: Path, item: QueueItem) -> None:
    con = connect(db_path)
    try:
        con.execute(
            """
            INSERT INTO queue_items (
                question_id, question_text, status, draft, citation_url,
                routing_note, searched_json, reviewer_flags_json, explainer_id,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(question_id) DO UPDATE SET
                question_text = excluded.question_text,
                status = excluded.status,
                draft = excluded.draft,
                citation_url = excluded.citation_url,
                routing_note = excluded.routing_note,
                searched_json = excluded.searched_json,
                reviewer_flags_json = excluded.reviewer_flags_json,
                explainer_id = excluded.explainer_id,
                updated_at = excluded.updated_at
            """,
            (
                item.question_id,
                item.question_text,
                item.status.value,
                item.draft,
                item.citation_url,
                item.routing_note,
                json.dumps(item.searched),
                json.dumps(item.reviewer_flags),
                item.explainer_id,
                (item.created_at or _utcnow()).isoformat(sep=" "),
                (item.updated_at or _utcnow()).isoformat(sep=" "),
            ),
        )
        con.commit()
    finally:
        con.close()


def process_question(
    text: str,
    *,
    db_path: str | Path | None = None,
    fixture_mode: bool | None = None,
) -> QueueItem:
    """Enqueue → parallel agents → orchestrate → review → persist QueueItem.

    On ``drafted``, also creates a ``reply_finalize`` pending approval action.
    """
    settings = get_settings()
    path = Path(db_path) if db_path is not None else Path(settings.support_deck_db)
    init_db(path)

    safe_text = redact_pii(text or "")
    policy, retrieve, draft = agents.run_agents_parallel(
        safe_text, fixture_mode=fixture_mode
    )
    candidate = orchestrate(policy, retrieve, draft)
    reviewed = review(candidate, retrieve)
    final = reviewed.candidate

    now = _utcnow()
    item = QueueItem(
        question_id=f"q-{uuid.uuid4().hex[:12]}",
        question_text=safe_text,
        status=final.status,
        draft=final.draft,
        citation_url=final.citation_url,
        routing_note=final.routing_note,
        searched=list(final.searched),
        reviewer_flags=list(reviewed.flags),
        explainer_id=None,
        created_at=now,
        updated_at=now,
    )
    _persist_queue_item(path, item)

    if item.status == QueueStatus.drafted:
        service = ApprovalService(path)
        service.create_action(
            action_type=ApprovalActionType.reply_finalize,
            payload_preview={
                "question_id": item.question_id,
                "citation_url": item.citation_url,
                "routing_note": item.routing_note,
                "draft_preview": (item.draft or "")[:240],
            },
            content=item.draft or "",
        )

    return item
