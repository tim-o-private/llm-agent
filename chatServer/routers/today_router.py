"""Today surface API — GET/regenerate/append-note/toggle-todo/source.

Thin router. All business logic lives in ``TodayService``. Auth enforced by
``get_current_user``; DB access scoped via ``get_user_scoped_client``.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from chatServer.dependencies.llm import get_llm_client_dep as get_anthropic_client

from ..database.scoped_client import UserScopedClient
from ..database.supabase_client import (
    create_system_client,
    get_user_scoped_client,
)
from ..dependencies.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/today", tags=["today"])


# --- Models -----------------------------------------------------------------


class AppendNoteRequest(BaseModel):
    text: str = Field(..., min_length=1)


class ToggleTodoRequest(BaseModel):
    line_id: str = Field(..., min_length=1)
    checked: bool
    expected_mtime: Optional[float] = None


class TodayResponse(BaseModel):
    date: str
    header: dict
    your_day: list
    to_do: list
    notes: list
    agent: dict
    approvals: list
    recent: list
    source_mtime: Optional[float] = None
    unknown_sections: list = []


class SourceResponse(BaseModel):
    body: str
    source_mtime: Optional[float] = None


class NoteResponse(BaseModel):
    created_at: str
    text: str
    source_mtime: Optional[float] = None


class TodoToggleResponse(BaseModel):
    line_id: str
    checked: bool
    source_mtime: Optional[float] = None


class RegenerateResponse(BaseModel):
    run_id: str


# --- Dependencies -----------------------------------------------------------


def _data_dir() -> Path:
    return Path(os.getenv("SANDBOX_DATA_DIR", "/data"))


async def get_today_service(
    db: UserScopedClient = Depends(get_user_scoped_client),
):
    """FastAPI dependency that assembles a TodayService for the caller.

    VaultService needs a StorageSync for fire-and-forget upload on writes.
    ApprovalService needs an ActivityLogService with a system client (RLS
    INSERT policy is service-role only).

    Tests override with ``app.dependency_overrides[get_today_service]``.
    """
    from ..config.settings import get_settings
    from ..services.activity_log_service import ActivityLogService
    from ..services.approval_service import ApprovalService
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

    return TodayService(vault=vault, approvals=approvals)




# --- Endpoints --------------------------------------------------------------


@router.get("", response_model=TodayResponse)
async def get_today(
    user_id: str = Depends(get_current_user),
    service=Depends(get_today_service),
):
    try:
        return await service.get_today(user_id)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("get_today failed for %s: %s", user_id, exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to load today")


@router.get("/source", response_model=SourceResponse)
async def get_today_source(
    user_id: str = Depends(get_current_user),
    service=Depends(get_today_service),
):
    try:
        return await service.get_source(user_id)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("get_today_source failed for %s: %s", user_id, exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to load source")


@router.post("/notes", response_model=NoteResponse)
async def append_note(
    payload: AppendNoteRequest,
    user_id: str = Depends(get_current_user),
    service=Depends(get_today_service),
):
    return await service.append_note(user_id, payload.text)


@router.post("/todo/toggle", response_model=TodoToggleResponse)
async def toggle_todo(
    payload: ToggleTodoRequest,
    user_id: str = Depends(get_current_user),
    service=Depends(get_today_service),
):
    return await service.toggle_todo(
        user_id,
        payload.line_id,
        checked=payload.checked,
        expected_mtime=payload.expected_mtime,
    )


@router.post("/regenerate", response_model=RegenerateResponse, status_code=202)
async def regenerate_today(
    user_id: str = Depends(get_current_user),
    db: UserScopedClient = Depends(get_user_scoped_client),
    service=Depends(get_today_service),
    anthropic_client=Depends(get_anthropic_client),
):
    run_id = await service.regenerate(user_id, db, anthropic_client)
    return RegenerateResponse(run_id=run_id)
