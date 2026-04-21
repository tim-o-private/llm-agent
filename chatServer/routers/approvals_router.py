"""Approvals API — list pending, count, approve, reject, edit.

State machine and activity_log side-effects live in ApprovalService.
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ..database.scoped_client import UserScopedClient
from ..database.supabase_client import (
    create_system_client,
    get_user_scoped_client,
)
from ..dependencies.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/approvals", tags=["approvals"])


# --- Models -----------------------------------------------------------------


class ApproveRequest(BaseModel):
    decision_note: Optional[str] = None


class RejectRequest(BaseModel):
    reason: Optional[str] = None


class EditRequest(BaseModel):
    payload_patch: dict = Field(..., description="Non-empty dict merged into the card's payload")


class PendingCountResponse(BaseModel):
    count: int


# --- Service factory --------------------------------------------------------


async def _build_approval_service(db: UserScopedClient):
    from ..services.activity_log_service import ActivityLogService
    from ..services.approval_service import ApprovalService

    system_client = await create_system_client()
    activity_log = ActivityLogService(system_client=system_client, user_client=db)
    return ApprovalService(user_client=db, activity_log=activity_log)


# --- Endpoints --------------------------------------------------------------


@router.get("", response_model=list[dict])
async def list_pending_approvals(
    user_id: str = Depends(get_current_user),
    db: UserScopedClient = Depends(get_user_scoped_client),
):
    service = await _build_approval_service(db)
    try:
        return await service.list_pending(user_id)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("list_pending_approvals failed for %s: %s", user_id, exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to list approvals")


@router.get("/count", response_model=PendingCountResponse)
async def get_pending_count(
    user_id: str = Depends(get_current_user),
    db: UserScopedClient = Depends(get_user_scoped_client),
):
    service = await _build_approval_service(db)
    count = await service.count_pending(user_id)
    return PendingCountResponse(count=count)


@router.post("/{card_id}/approve", response_model=dict)
async def approve_card(
    card_id: str,
    payload: ApproveRequest = ApproveRequest(),
    user_id: str = Depends(get_current_user),
    db: UserScopedClient = Depends(get_user_scoped_client),
):
    service = await _build_approval_service(db)
    return await service.approve(user_id, card_id, decision_note=payload.decision_note)


@router.post("/{card_id}/reject", response_model=dict)
async def reject_card(
    card_id: str,
    payload: RejectRequest = RejectRequest(),
    user_id: str = Depends(get_current_user),
    db: UserScopedClient = Depends(get_user_scoped_client),
):
    service = await _build_approval_service(db)
    return await service.reject(user_id, card_id, reason=payload.reason)


@router.post("/{card_id}/edit", response_model=dict)
async def edit_card(
    card_id: str,
    payload: EditRequest,
    user_id: str = Depends(get_current_user),
    db: UserScopedClient = Depends(get_user_scoped_client),
):
    service = await _build_approval_service(db)
    return await service.edit(user_id, card_id, payload.payload_patch)
