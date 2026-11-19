from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from src.approval.service import ApprovalService
from src.config import get_settings
from src.connectors.explainer_reuse import draft_from_explainer, match_explainer
from src.connectors.frequency import record_question
from src.db import connect, init_db
from src.desk import agents
from src.desk import policy_agent
from src.desk.faq_client import RetrieveResult
from src.desk.orchestrator import CandidateReply, orchestrate
from src.desk.policy_agent import PolicyResult
from src.desk.reviewer import review
from src.models import ApprovalActionType, FeeExplainer, QueueItem, QueueStatus
from src.pii import redact_pii


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _explainer_retrieve(explainer: FeeExplainer) -> RetrieveResult:
    """Synthetic retrieve context so reviewer grounding uses explainer links."""
    links = list(explainer.links)
    chunks = [
        {"text": bullet, "source_url": links[0] if links else ""}
        for bullet in explainer.bullets
    ]
    searched = ["fee_explainer"]
    if explainer.explainer_id:
        searched.append(f"explainer:{explainer.explainer_id}")
    searched.extend(links)
    return RetrieveResult(chunks=chunks, source_urls=links, searched=searched)


def _reuse_explainer_path(
    question: str, explainer: FeeExplainer
) -> tuple[PolicyResult, RetrieveResult, CandidateReply]:
    """Policy-only path: skip parallel retrieve/draft; draft from explainer."""
    policy = policy_agent.run_policy(question)
    retrieve = _explainer_retrieve(explainer)
    if policy.refuse:
        return policy, retrieve, orchestrate(policy, retrieve, "")
    draft = draft_from_explainer(explainer)
    candidate = CandidateReply(
        status=QueueStatus.drafted,
        draft=draft,
        citation_url=explainer.links[0] if explainer.links else None,
        routing_note="reuse_explainer",
        searched=list(retrieve.searched),
        policy_category=policy.category,
    )
    return policy, retrieve, candidate


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
    matched = match_explainer(safe_text, db_path=path)
    if matched is not None:
        _policy, retrieve, candidate = _reuse_explainer_path(safe_text, matched)
        reused_id = matched.explainer_id
    else:
        policy, retrieve, draft = agents.run_agents_parallel(
            safe_text, fixture_mode=fixture_mode
        )
        candidate = orchestrate(policy, retrieve, draft)
        reused_id = None

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
        explainer_id=reused_id if final.routing_note == "reuse_explainer" else None,
        created_at=now,
        updated_at=now,
    )
    _persist_queue_item(path, item)
    record_question(safe_text, at=now, db_path=path)

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
