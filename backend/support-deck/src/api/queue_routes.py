from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from src.api.deps import (
    get_db_path,
    get_queue_item,
    list_queue_items,
    serialize_model,
    update_queue_draft,
)
from src.desk.pipeline import process_question

router = APIRouter(tags=["queue"])


class EnqueueBody(BaseModel):
    question: str = Field(min_length=1)


class PatchDraftBody(BaseModel):
    draft: str


@router.get("/queue")
def get_queue(request: Request) -> list[dict]:
    items = list_queue_items(get_db_path(request))
    return [serialize_model(i) for i in items]


@router.post("/queue")
def post_queue(body: EnqueueBody, request: Request) -> dict:
    db = get_db_path(request)
    try:
        item = process_question(body.question, db_path=db, fixture_mode=None)
    except Exception as exc:  # noqa: BLE001 — surface root cause to UI/ops
        raise HTTPException(
            status_code=500,
            detail=f"Support Deck enqueue failed: {type(exc).__name__}: {exc}",
        ) from exc
    return serialize_model(item)


@router.patch("/queue/{question_id}")
def patch_queue(question_id: str, body: PatchDraftBody, request: Request) -> dict:
    db = get_db_path(request)
    if get_queue_item(db, question_id) is None:
        raise HTTPException(status_code=404, detail="queue item not found")
    try:
        item = update_queue_draft(db, question_id, body.draft)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return serialize_model(item)
