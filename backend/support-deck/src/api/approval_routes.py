from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Request

from datetime import datetime, timezone

from src.api.deps import get_db_path, list_approval_actions, serialize_model
from src.approval.service import ApprovalService
from src.models import ApprovalStatus, QueueStatus

router = APIRouter(tags=["approvals"])


@router.get("/approvals")
def get_approvals(request: Request) -> list[dict]:
    try:
        return [
            serialize_model(a) for a in list_approval_actions(get_db_path(request))
        ]
    except Exception as exc:  # noqa: BLE001 — surface flaky lock/errors to UI
        raise HTTPException(
            status_code=500,
            detail=f"approvals list failed: {type(exc).__name__}: {exc}",
        ) from exc


@router.post("/approvals/{action_id}/approve")
def approve_action(
    action_id: str,
    request: Request,
    invoke_mcp: bool = Query(
        default=True,
        description=(
            "Legacy flag. Docs/Gmail publish is owned by ApprovalService.approve "
            "(dry-run receipts unless MCP_LIVE=1). False still approves status "
            "but skips the bridge."
        ),
    ),
) -> dict:
    """Approve one action; Docs/Gmail go through the gated MCP bridge."""
    svc = ApprovalService(get_db_path(request))
    try:
        if not invoke_mcp:
            action = svc.store.update_fields(
                action_id,
                status=ApprovalStatus.approved,
                decided_at=datetime.now(timezone.utc).replace(tzinfo=None),
                set_decided=True,
            )
            svc._sync_queue_for_reply(action, status=QueueStatus.approved)
        else:
            action = svc.approve(action_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return serialize_model(action)


@router.post("/approvals/{action_id}/reject")
def reject_action(action_id: str, request: Request) -> dict:
    svc = ApprovalService(get_db_path(request))
    try:
        action = svc.reject(action_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return serialize_model(action)
