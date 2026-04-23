"""Vault file API -- save, backlinks, file context, suggest card actions.

Thin router. Filesystem logic lives in ``VaultService``, suggest card
logic in ``FileContextService``. Auth enforced by ``get_current_user``.

See SPEC-047 ACs 19-23.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, Field

from ..database.scoped_client import UserScopedClient
from ..database.supabase_client import get_user_scoped_client
from ..dependencies.auth import get_current_user
from ..routers.vault_router import get_vault_service
from ..services.file_context_service import FileContextService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/vault", tags=["vault-file"])


# --- Request / Response models -----------------------------------------------


class SaveFileRequest(BaseModel):
    path: str = Field(..., min_length=1)
    content: str
    mtime: float


class SaveFileResponse(BaseModel):
    mtime: float


class BacklinkEntry(BaseModel):
    path: str
    name: str


class BacklinksResponse(BaseModel):
    backlinks: list[BacklinkEntry]


class AcceptResponse(BaseModel):
    text: str | None
    target_line: int


# --- Helpers ------------------------------------------------------------------


def _build_context_service(
    vault, db: UserScopedClient
) -> FileContextService:
    return FileContextService(
        vault_service=vault,
        user_client=db,
    )


# --- Endpoints ----------------------------------------------------------------


@router.put("/file", response_model=SaveFileResponse)
async def save_file(
    payload: SaveFileRequest,
    user_id: str = Depends(get_current_user),
    vault=Depends(get_vault_service),
):
    """Save file content with optimistic concurrency via mtime."""
    # VaultService.update_body handles path safety (403), mtime conflict (409),
    # size limit (413), and file creation (writes to disk).
    # For AC-19: return 404 if file doesn't exist (no create-via-PUT).
    stat = await vault.stat_file(user_id, payload.path)
    if stat is None:
        raise HTTPException(status_code=404, detail="File not found")

    new_mtime = await vault.update_body(
        user_id,
        payload.path,
        payload.content,
        expected_mtime=payload.mtime,
    )
    return SaveFileResponse(mtime=new_mtime)


@router.get("/backlinks", response_model=BacklinksResponse)
async def get_backlinks(
    path: str = Query(..., description="Relative path within the vault"),
    user_id: str = Depends(get_current_user),
    vault=Depends(get_vault_service),
):
    """Find all vault files that contain a wikilink to the given file."""
    backlinks = await vault.find_backlinks(user_id, path)
    return BacklinksResponse(
        backlinks=[BacklinkEntry(**bl) for bl in backlinks]
    )


@router.get("/file/context")
async def get_file_context(
    path: str = Query(..., description="Relative path within the vault"),
    user_id: str = Depends(get_current_user),
    vault=Depends(get_vault_service),
    db: UserScopedClient = Depends(get_user_scoped_client),
):
    """Return AI context for a file: summary, suggest cards, activity."""
    svc = _build_context_service(vault, db)
    return await svc.get_file_context(user_id, path)


@router.post("/file/suggest/{card_id}/accept", response_model=AcceptResponse)
async def accept_suggest_card(
    card_id: str,
    user_id: str = Depends(get_current_user),
    vault=Depends(get_vault_service),
    db: UserScopedClient = Depends(get_user_scoped_client),
):
    """Accept a suggest card -- returns the text to insert."""
    svc = _build_context_service(vault, db)
    result = await svc.accept_suggest_card(user_id, card_id)
    return AcceptResponse(**result)


@router.post("/file/suggest/{card_id}/dismiss", status_code=204)
async def dismiss_suggest_card(
    card_id: str,
    user_id: str = Depends(get_current_user),
    vault=Depends(get_vault_service),
    db: UserScopedClient = Depends(get_user_scoped_client),
):
    """Dismiss a suggest card."""
    svc = _build_context_service(vault, db)
    await svc.dismiss_suggest_card(user_id, card_id)
    return Response(status_code=204)
