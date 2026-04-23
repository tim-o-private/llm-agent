"""Activity log API — paginated list, count, mark-viewed.

Thin router. Business logic lives in ``ActivityLogService``. Auth enforced
by ``get_current_user``; DB access scoped via ``get_user_scoped_client``.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Query

from ..database.scoped_client import UserScopedClient
from ..database.supabase_client import get_user_scoped_client
from ..dependencies.auth import get_current_user
from ..services.activity_log_service import ActivityLogService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/activity", tags=["activity"])


# --- Helpers ----------------------------------------------------------------


def _build_service(db: UserScopedClient) -> ActivityLogService:
    """Build an ``ActivityLogService`` with only the user client (read-only)."""
    return ActivityLogService(system_client=None, user_client=db)


# --- Endpoints --------------------------------------------------------------


@router.get("")
async def list_activity(
    user_id: str = Depends(get_current_user),
    db: UserScopedClient = Depends(get_user_scoped_client),
    limit: int = Query(default=50, ge=1, le=100),
    before: str | None = Query(default=None),
    workflow_run_id: str | None = Query(default=None),
    status: str | None = Query(default=None),
    q: str | None = Query(default=None),
):
    """Paginated, filterable activity log."""
    service = _build_service(db)
    status_list = [s.strip() for s in status.split(",")] if status else None
    items, has_more = await service.list_paginated(
        user_id,
        limit=limit,
        before=before,
        workflow_run_id=workflow_run_id,
        status=status_list,
        q=q,
    )
    total = await service.count(user_id)
    return {"items": items, "total": total, "has_more": has_more}


@router.get("/count")
async def activity_count(
    user_id: str = Depends(get_current_user),
    db: UserScopedClient = Depends(get_user_scoped_client),
):
    """Total entries + entries since last viewed."""
    service = _build_service(db)
    return await service.get_counts_with_last_viewed(user_id)


@router.post("/mark-viewed")
async def mark_viewed(
    user_id: str = Depends(get_current_user),
    db: UserScopedClient = Depends(get_user_scoped_client),
):
    """Update ``last_activity_viewed_at`` to now."""
    service = _build_service(db)
    now = await service.mark_viewed(user_id)
    return {"marked_at": now}
