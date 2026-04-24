"""Capture API — route text into the vault.

Thin router. All business logic lives in ``CaptureService``. Auth enforced by
``get_current_user``; DB access scoped via ``get_user_scoped_client``.

See SPEC-051 §"API Contract".
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from ..database.scoped_client import UserScopedClient
from ..database.supabase_client import (
    create_system_client,
    get_user_scoped_client,
)
from ..dependencies.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/capture", tags=["capture"])


# --- Models -----------------------------------------------------------------


class CaptureRequest(BaseModel):
    text: str = Field(..., min_length=1)
    source: str = Field(..., pattern="^(today|cmdk|chat)$")
    context: Optional[dict] = None


class CaptureResponse(BaseModel):
    capture_id: str
    status: str
    target_path: Optional[str] = None
    target_section: Optional[str] = None
    method: Optional[str] = None
    confirmation: Optional[str] = None
    fallback: bool = False
    redirect: Optional[dict] = None
    created_at: Optional[str] = None
    placed_at: Optional[str] = None
    reasoning: Optional[str] = None
    error_detail: Optional[str] = None


class RedirectRequest(BaseModel):
    target_hint: str = Field(..., min_length=1)


# --- Dependencies -----------------------------------------------------------


def _data_dir() -> Path:
    return Path(os.getenv("SANDBOX_DATA_DIR", "/data"))


async def get_capture_service(
    db: UserScopedClient = Depends(get_user_scoped_client),
):
    """FastAPI dependency that assembles a CaptureService for the caller."""
    from ..config.settings import get_settings
    from ..services.activity_log_service import ActivityLogService
    from ..services.approval_service import ApprovalService
    from ..services.capture_service import CaptureService
    from ..services.storage_sync import StorageSync
    from ..services.today_service import TodayService
    from ..services.vault_service import VaultService

    settings = get_settings()
    data_dir = _data_dir()

    sync = None
    if settings.supabase_url and settings.supabase_service_key:
        sync = StorageSync(
            supabase_url=settings.supabase_url,
            supabase_key=settings.supabase_service_key,
            data_dir=data_dir,
        )

    vault = VaultService(storage_sync=sync, data_dir=data_dir)

    system_client = await create_system_client()
    activity_log = ActivityLogService(system_client=system_client, user_client=db)
    approvals = ApprovalService(user_client=db, activity_log=activity_log)
    today = TodayService(vault=vault, approvals=approvals)

    return CaptureService(
        vault=vault,
        today=today,
        system_client=system_client,
        user_client=db,
        activity_log=activity_log,
    )


# --- Endpoints --------------------------------------------------------------


@router.post("", response_model=CaptureResponse, status_code=202)
async def create_capture(
    payload: CaptureRequest,
    user_id: str = Depends(get_current_user),
    service=Depends(get_capture_service),
):
    """Accept a capture and route it into the vault.

    Returns 202 with the capture state (typically already placed for
    Stage 2 rule-based routing).
    """
    result = await service.create_capture(
        user_id=user_id,
        text=payload.text,
        source=payload.source,
        context=payload.context,
    )
    return _to_response(result)


@router.get("/{capture_id}", response_model=CaptureResponse)
async def get_capture(
    capture_id: str,
    user_id: str = Depends(get_current_user),
    service=Depends(get_capture_service),
):
    """Poll the current state of a capture."""
    result = await service.get_capture(user_id, capture_id)
    return _to_response(result)


@router.post("/{capture_id}/redirect", response_model=CaptureResponse)
async def redirect_capture(
    capture_id: str,
    payload: RedirectRequest,
    user_id: str = Depends(get_current_user),
    service=Depends(get_capture_service),
):
    """Move a placed capture to a new location."""
    result = await service.redirect_capture(user_id, capture_id, payload.target_hint)
    return _to_response(result)


def _to_response(row: dict) -> CaptureResponse:
    """Map a DB row to the API response model."""
    return CaptureResponse(
        capture_id=row["id"],
        status=row["status"],
        target_path=row.get("target_path"),
        target_section=row.get("target_section"),
        method=row.get("method"),
        confirmation=row.get("confirmation"),
        fallback=row.get("fallback", False),
        redirect=row.get("redirect"),
        created_at=row.get("created_at"),
        placed_at=row.get("placed_at"),
        reasoning=row.get("reasoning"),
        error_detail=row.get("error_detail"),
    )
