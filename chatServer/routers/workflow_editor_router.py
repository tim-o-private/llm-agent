"""Workflow editor API — list, create, dry-run, run.

Thin router per A1. All business logic lives in ``WorkflowEditorService``.
Auth enforced by ``get_current_user``; filesystem access scoped via
VaultService.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ..config.paths import get_data_dir
from ..database.scoped_client import UserScopedClient
from ..database.supabase_client import get_user_scoped_client
from ..dependencies.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/vault/workflows", tags=["workflow-editor"])


# --- Request / response models -----------------------------------------------


class WorkflowListItem(BaseModel):
    name: str
    filename: str
    description: str
    trigger_summary: str
    next_run_at: Optional[str] = None


class WorkflowListResponse(BaseModel):
    workflows: list[WorkflowListItem]


class CreateWorkflowRequest(BaseModel):
    name: str


class CreateWorkflowResponse(BaseModel):
    path: str


class DryRunRequest(BaseModel):
    template_name: str


class DryRunStepResult(BaseModel):
    name: str
    agent: str
    depends_on: list[str]
    tools: list[str]


class DryRunParameterResult(BaseModel):
    name: str
    required: bool
    description: str = ""


class DryRunResponse(BaseModel):
    valid: bool
    errors: list[str]
    steps: list[DryRunStepResult]
    parameters: list[DryRunParameterResult]


class RunWorkflowRequest(BaseModel):
    template_name: str
    parameters: Optional[dict[str, Any]] = None


class RunWorkflowResponse(BaseModel):
    run_id: str


# --- Dependencies -------------------------------------------------------------


def get_workflow_editor_service(
    db: UserScopedClient = Depends(get_user_scoped_client),
):
    """FastAPI dependency that assembles a WorkflowEditorService.

    Tests override with ``app.dependency_overrides[get_workflow_editor_service]``.
    """
    from ..config.settings import get_settings
    from ..services.storage_sync import StorageSync
    from ..services.vault_service import VaultService
    from ..services.workflow_editor_service import WorkflowEditorService

    settings = get_settings()
    data_dir = get_data_dir()

    sync = None
    if settings.supabase_url and settings.supabase_service_key:
        sync = StorageSync(
            supabase_url=settings.supabase_url,
            supabase_key=settings.supabase_service_key,
            data_dir=data_dir,
        )

    vault = VaultService(storage_sync=sync, data_dir=data_dir)
    return WorkflowEditorService(vault=vault, db=db)


def get_anthropic_client():
    """FastAPI dependency that returns an AsyncAnthropic client.

    Tests override with ``app.dependency_overrides[get_anthropic_client]``.
    """
    from anthropic import AsyncAnthropic

    return AsyncAnthropic()


# --- Endpoints ----------------------------------------------------------------


@router.get("/list", response_model=WorkflowListResponse)
async def list_workflows(
    user_id: str = Depends(get_current_user),
    service=Depends(get_workflow_editor_service),
):
    """List all ``.flow.md`` workflows in the user's ``_workflows/`` dir."""
    try:
        items = await service.list_workflows(user_id)
        return WorkflowListResponse(
            workflows=[WorkflowListItem(**item) for item in items]
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("list_workflows failed for %s: %s", user_id, exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to list workflows")


@router.post("/new", response_model=CreateWorkflowResponse)
async def create_workflow(
    payload: CreateWorkflowRequest,
    user_id: str = Depends(get_current_user),
    service=Depends(get_workflow_editor_service),
):
    """Create a new workflow file with seed template."""
    try:
        path = await service.create_workflow(user_id, payload.name)
        return CreateWorkflowResponse(path=path)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("create_workflow failed for %s: %s", user_id, exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to create workflow")


@router.post("/dry-run", response_model=DryRunResponse)
async def dry_run_workflow(
    payload: DryRunRequest,
    user_id: str = Depends(get_current_user),
    service=Depends(get_workflow_editor_service),
):
    """Parse and validate a workflow template without executing it."""
    try:
        result = await service.dry_run(user_id, payload.template_name)
        return DryRunResponse(**result)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("dry_run_workflow failed for %s: %s", user_id, exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to dry-run workflow")


@router.post("/run", response_model=RunWorkflowResponse, status_code=202)
async def run_workflow(
    payload: RunWorkflowRequest,
    user_id: str = Depends(get_current_user),
    db: UserScopedClient = Depends(get_user_scoped_client),
    service=Depends(get_workflow_editor_service),
    anthropic_client=Depends(get_anthropic_client),
):
    """Start a workflow run. Returns 202 with the run_id."""
    try:
        run_id = await service.run_workflow(
            user_id=user_id,
            template_name=payload.template_name,
            parameters=payload.parameters,
            db_client=db,
            anthropic_client=anthropic_client,
        )
        return RunWorkflowResponse(run_id=run_id)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("run_workflow failed for %s: %s", user_id, exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to run workflow")
