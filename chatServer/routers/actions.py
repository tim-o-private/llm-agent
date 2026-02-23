"""
Actions router for the approval system.

Provides API endpoints for:
- Listing pending actions
- Approving actions
- Rejecting actions
- Viewing audit history
- Managing tool preferences
"""

import logging
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from ..database.scoped_client import UserScopedClient
from ..database.supabase_client import get_supabase_client, get_user_scoped_client
from ..dependencies.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/actions", tags=["actions"])


# =============================================================================
# Request/Response Models
# =============================================================================

class PendingActionResponse(BaseModel):
    id: str
    tool_name: str
    tool_args: dict
    status: str
    created_at: datetime
    expires_at: datetime
    context: dict = {}


class ActionRejectionRequest(BaseModel):
    reason: Optional[str] = Field(None, description="Optional rejection reason")


class ActionResultResponse(BaseModel):
    success: bool
    message: str
    result: Optional[dict] = None
    error: Optional[str] = None


class AuditLogEntryResponse(BaseModel):
    id: str
    tool_name: str
    approval_status: str
    execution_status: Optional[str] = None
    created_at: datetime
    session_id: Optional[str] = None
    agent_name: Optional[str] = None


class ToolPreferenceRequest(BaseModel):
    tool_name: str = Field(..., description="Name of the tool")
    preference: str = Field(..., description="Preference: 'auto' or 'requires_approval'")


class ToolPreferenceResponse(BaseModel):
    tool_name: str
    current_tier: str
    is_overridable: bool
    user_preference: Optional[str] = None


class PendingCountResponse(BaseModel):
    count: int


# =============================================================================
# Service initialization (lazy)
# =============================================================================

def _build_pending_actions_service(db: UserScopedClient):
    """Build a PendingActionsService with a user-scoped client."""
    from ..services.audit_service import AuditService
    from ..services.pending_actions import PendingActionsService

    audit_service = AuditService(db)
    return PendingActionsService(db_client=db, audit_service=audit_service)


def _build_audit_service(db: UserScopedClient):
    """Build an AuditService with a user-scoped client."""
    from ..services.audit_service import AuditService

    return AuditService(db)


# =============================================================================
# Endpoints
# =============================================================================

@router.get("/pending", response_model=List[PendingActionResponse])
async def get_pending_actions(
    user_id: str = Depends(get_current_user),
    db: UserScopedClient = Depends(get_user_scoped_client),
    limit: int = Query(default=50, ge=1, le=100),
):
    """Get all pending actions for the current user."""
    try:
        service = _build_pending_actions_service(db)
        actions = await service.get_pending_actions(user_id, limit=limit)

        return [
            PendingActionResponse(
                id=str(action.id),
                tool_name=action.tool_name,
                tool_args=action.tool_args,
                status=action.status,
                created_at=action.created_at,
                expires_at=action.expires_at,
                context=action.context,
            )
            for action in actions
        ]
    except Exception as e:
        logger.error(f"Failed to get pending actions for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/pending/count", response_model=PendingCountResponse)
async def get_pending_count(
    user_id: str = Depends(get_current_user),
    db: UserScopedClient = Depends(get_user_scoped_client),
):
    """Get count of pending actions for the current user."""
    try:
        service = _build_pending_actions_service(db)
        count = await service.get_pending_count(user_id)
        return PendingCountResponse(count=count)
    except Exception as e:
        logger.error(f"Failed to get pending count for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{action_id}/approve", response_model=ActionResultResponse)
async def approve_action(
    action_id: str,
    user_id: str = Depends(get_current_user),
    db: UserScopedClient = Depends(get_user_scoped_client),
):
    """Approve a pending action. Executes and logs to audit trail."""
    try:
        service = _build_pending_actions_service(db)
        result = await service.approve_action(action_id, user_id)

        if result.success:
            return ActionResultResponse(
                success=True,
                message="Action approved and executed successfully",
                result={"execution_result": result.result} if result.result else None,
            )
        else:
            return ActionResultResponse(
                success=False,
                message="Action approval failed",
                error=result.error,
            )
    except Exception as e:
        logger.error(f"Failed to approve action {action_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{action_id}/reject", response_model=ActionResultResponse)
async def reject_action(
    action_id: str,
    request: ActionRejectionRequest,
    user_id: str = Depends(get_current_user),
    db: UserScopedClient = Depends(get_user_scoped_client),
):
    """Reject a pending action."""
    try:
        service = _build_pending_actions_service(db)
        success = await service.reject_action(action_id, user_id, reason=request.reason)

        if success:
            return ActionResultResponse(success=True, message="Action rejected")
        else:
            return ActionResultResponse(
                success=False,
                message="Failed to reject action",
                error="Action not found or already processed",
            )
    except Exception as e:
        logger.error(f"Failed to reject action {action_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history", response_model=List[AuditLogEntryResponse])
async def get_audit_history(
    user_id: str = Depends(get_current_user),
    db: UserScopedClient = Depends(get_user_scoped_client),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    tool_name: Optional[str] = Query(default=None),
    approval_status: Optional[str] = Query(default=None),
):
    """Get audit history for the current user."""
    try:
        service = _build_audit_service(db)
        entries = await service.get_audit_log(
            user_id=user_id,
            limit=limit,
            offset=offset,
            tool_name=tool_name,
            approval_status=approval_status,
        )

        return [
            AuditLogEntryResponse(
                id=entry.get("id"),
                tool_name=entry.get("tool_name"),
                approval_status=entry.get("approval_status"),
                execution_status=entry.get("execution_status"),
                created_at=entry.get("created_at"),
                session_id=entry.get("session_id"),
                agent_name=entry.get("agent_name"),
            )
            for entry in entries
        ]
    except Exception as e:
        logger.error(f"Failed to get audit history for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/preferences/{tool_name}", response_model=ToolPreferenceResponse)
async def get_tool_preference(
    tool_name: str,
    user_id: str = Depends(get_current_user),
):
    """Get the current approval preference for a tool."""
    try:
        from ..security.approval_tiers import (
            ApprovalTier,
            _get_user_preference,
            get_tool_default_tier,
        )

        tier, default = get_tool_default_tier(tool_name)

        user_preference = None
        if tier == ApprovalTier.USER_CONFIGURABLE:
            # TODO: SPEC-017 migrate to scoped client
            db_client = await get_supabase_client()
            user_preference = await _get_user_preference(db_client, user_id, tool_name)

        return ToolPreferenceResponse(
            tool_name=tool_name,
            current_tier=tier.value,
            is_overridable=(tier == ApprovalTier.USER_CONFIGURABLE),
            user_preference=user_preference,
        )
    except Exception as e:
        logger.error(f"Failed to get tool preference for {tool_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/preferences/{tool_name}", response_model=ActionResultResponse)
async def set_tool_preference(
    tool_name: str,
    request: ToolPreferenceRequest,
    user_id: str = Depends(get_current_user),
):
    """Set approval preference for a tool. Only works for USER_CONFIGURABLE tools."""
    try:
        from ..security.approval_tiers import set_user_preference

        if request.preference not in ("auto", "requires_approval"):
            raise HTTPException(
                status_code=400,
                detail="Preference must be 'auto' or 'requires_approval'"
            )

        # TODO: SPEC-017 migrate to scoped client
        db_client = await get_supabase_client()
        success = await set_user_preference(
            db_client=db_client,
            user_id=user_id,
            tool_name=tool_name,
            preference=request.preference,
        )

        if success:
            return ActionResultResponse(
                success=True,
                message=f"Preference for {tool_name} set to {request.preference}",
            )
        else:
            return ActionResultResponse(
                success=False,
                message="Failed to set preference",
                error="Tool is not configurable or preference is invalid",
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to set tool preference for {tool_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/expire-stale")
async def expire_stale_actions(
    user_id: str = Depends(get_current_user),
    db: UserScopedClient = Depends(get_user_scoped_client),
):
    """Manually trigger expiration of stale pending actions."""
    try:
        service = _build_pending_actions_service(db)
        count = await service.expire_stale_actions()

        return {
            "success": True,
            "expired_count": count,
            "message": f"Expired {count} stale actions",
        }
    except Exception as e:
        logger.error(f"Failed to expire stale actions: {e}")
        raise HTTPException(status_code=500, detail=str(e))
