"""Workflow runs read API.

Thin router per A1 — delegates to ``WorkflowRunsService``. Consumed by
the Today surface's ``useRegenerationStatus`` hook, which polls the
latest ``regenerate-today`` run.
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from ..database.scoped_client import UserScopedClient
from ..database.supabase_client import get_user_scoped_client
from ..dependencies.auth import get_current_user
from ..services.workflow_runs_service import WorkflowRunsService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/workflows", tags=["workflows"])


class WorkflowRunResponse(BaseModel):
    id: str
    template_name: str
    status: str
    current_step: str = ""
    error: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    created_at: Optional[str] = None


@router.get("/runs", response_model=list[WorkflowRunResponse])
async def list_workflow_runs(
    template_name: Optional[str] = Query(None),
    limit: int = Query(10, ge=1, le=100),
    user_id: str = Depends(get_current_user),
    db: UserScopedClient = Depends(get_user_scoped_client),
) -> list[WorkflowRunResponse]:
    """List the caller's workflow runs, newest first.

    RLS + the user-scoped client enforce cross-user isolation — an
    authenticated user can only observe their own rows.
    """
    service = WorkflowRunsService(db)
    try:
        rows = await service.list_runs(template_name=template_name, limit=limit)
    except Exception as exc:
        logger.error("list_workflow_runs failed for %s: %s", user_id, exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to list workflow runs")

    return [WorkflowRunResponse(**row) for row in rows]
