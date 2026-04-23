"""Thread router — list, read, and change status of thread-docs.

Thin router per A1. All business logic lives in ``ThreadService``.
Auth enforced by ``get_current_user``; filesystem access via VaultService.

SPEC-054 §5 (Thread router).
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from ..dependencies.auth import get_current_user
from ..routers.vault_router import get_vault_service
from ..services.thread_service import ThreadService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/vault/threads", tags=["threads"])


# --- Request / Response models ----------------------------------------------


class ChangeStatusRequest(BaseModel):
    status: str = Field(
        ...,
        description="Target status: active, watching, paused, completed, archived",
    )


class ThreadSummaryResponse(BaseModel):
    path: str
    title: str
    status: str
    next_action: Optional[str] = None
    blocked_on: Optional[str] = None
    created_at: str
    updated_at: str


class ThreadListResponse(BaseModel):
    threads: list[ThreadSummaryResponse]


# --- Endpoints ---------------------------------------------------------------


@router.get("", response_model=ThreadListResponse)
async def list_threads(
    user_id: str = Depends(get_current_user),
    vault=Depends(get_vault_service),
    status: Optional[str] = Query(default=None),
):
    """List thread summaries. Optionally filter by status."""
    service = ThreadService(vault)
    threads = await service.list_active_threads(user_id)
    if status:
        threads = [t for t in threads if t["status"] == status]
    return ThreadListResponse(
        threads=[ThreadSummaryResponse(**t) for t in threads]
    )


@router.get("/{slug}")
async def get_thread(
    slug: str,
    user_id: str = Depends(get_current_user),
    vault=Depends(get_vault_service),
):
    """Read a thread-doc by slug. Delegates to VaultService."""
    # Find the file — slug may or may not include date prefix
    rel_path = _resolve_thread_path(slug)
    try:
        content, mtime, size = await vault.read_file_with_meta(user_id, rel_path)
    except HTTPException as exc:
        if exc.status_code == 404:
            raise HTTPException(404, f"Thread not found: {slug}")
        raise
    return {"content": content, "mtime": mtime, "size": size, "path": rel_path}


@router.post("/{slug}/status")
async def change_thread_status(
    slug: str,
    payload: ChangeStatusRequest,
    user_id: str = Depends(get_current_user),
    vault=Depends(get_vault_service),
):
    """Change a thread's status. Validates transition rules."""
    service = ThreadService(vault)
    rel_path = _resolve_thread_path(slug)
    await service.change_status(user_id, rel_path, payload.status)
    return {"status": payload.status}


# --- Helpers -----------------------------------------------------------------


def _resolve_thread_path(slug: str) -> str:
    """Build vault-relative path from slug.

    If the slug already ends in ``.md``, use it directly under ``_threads/``.
    Otherwise append ``.md``.
    """
    if not slug.endswith(".md"):
        slug = f"{slug}.md"
    return f"_threads/{slug}"
