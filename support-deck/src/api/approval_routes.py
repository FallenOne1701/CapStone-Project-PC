from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Request

from src.api.deps import get_db_path, list_approval_actions, serialize_model
from src.approval.service import ApprovalService

router = APIRouter(tags=["approvals"])


@router.get("/approvals")
def get_approvals(request: Request) -> list[dict]:
    return [serialize_model(a) for a in list_approval_actions(get_db_path(request))]


@router.post("/approvals/{action_id}/approve")
def approve_action(
    action_id: str,
    request: Request,
    invoke_mcp: bool = Query(default=False),
) -> dict:
    """Approve one action. MCP is opt-in via ``invoke_mcp`` (Task 13 wires bridge)."""
    svc = ApprovalService(get_db_path(request))
    try:
        action = svc.approve(action_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    if invoke_mcp:
        # Soft hook — real bridge lands in Task 13; never fail closed here for missing module.
        try:
            from src import mcp_bridge  # type: ignore

            if action.type.value == "docs_append" and hasattr(
                mcp_bridge, "publish_docs_append"
            ):
                mcp_bridge.publish_docs_append(action)
            elif action.type.value == "gmail_draft" and hasattr(
                mcp_bridge, "publish_gmail_draft"
            ):
                mcp_bridge.publish_gmail_draft(action)
        except ImportError:
            pass
    return serialize_model(action)


@router.post("/approvals/{action_id}/reject")
def reject_action(action_id: str, request: Request) -> dict:
    svc = ApprovalService(get_db_path(request))
    try:
        action = svc.reject(action_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return serialize_model(action)
