"""Vault browser API -- tree, file read, folder listing.

Thin router. All filesystem logic lives in ``VaultService``. Auth enforced
by ``get_current_user``; no DB access needed (filesystem-only endpoints).
"""

from __future__ import annotations

import logging
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from ..config.paths import get_data_dir
from ..dependencies.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/vault", tags=["vault"])


# --- Response models --------------------------------------------------------


class TreeNodeModel(BaseModel):
    name: str
    path: str
    type: Literal["file", "folder"]
    mtime: str
    size: int
    children: Optional[list["TreeNodeModel"]] = None


class TreeResponse(BaseModel):
    tree: list[TreeNodeModel]


class FileResponse(BaseModel):
    content: str
    mtime: str
    size: int


class FolderEntryModel(BaseModel):
    name: str
    path: str
    type: Literal["file", "folder"]
    mtime: str
    size: int


class FolderResponse(BaseModel):
    entries: list[FolderEntryModel]


class CreateFileRequest(BaseModel):
    path: str
    content: str = ""


class CreateFolderRequest(BaseModel):
    path: str


class CreateFileResponse(BaseModel):
    path: str
    mtime: float


class CreateFolderResponse(BaseModel):
    path: str


class RenameRequest(BaseModel):
    source: str
    target: str


class RenameResponse(BaseModel):
    path: str


# --- VaultService dependency ------------------------------------------------


def get_vault_service():
    """FastAPI dependency that assembles a VaultService.

    Tests override with ``app.dependency_overrides[get_vault_service]``.
    """
    from ..config.settings import get_settings
    from ..services.storage_sync import StorageSync
    from ..services.vault_service import VaultService

    settings = get_settings()
    data_dir = get_data_dir()

    sync = None
    if settings.supabase_url and settings.supabase_service_key:
        sync = StorageSync(
            supabase_url=settings.supabase_url,
            supabase_key=settings.supabase_service_key,
            data_dir=data_dir,
        )

    return VaultService(storage_sync=sync, data_dir=data_dir)


# --- Helpers ----------------------------------------------------------------


def _tree_node_to_model(node) -> TreeNodeModel:
    """Convert a VaultService TreeNode dataclass to the Pydantic model."""
    children = None
    if node.children is not None:
        children = [_tree_node_to_model(c) for c in node.children]
    return TreeNodeModel(
        name=node.name,
        path=node.path,
        type=node.type,
        mtime=node.mtime,
        size=node.size,
        children=children,
    )


# --- Endpoints --------------------------------------------------------------


@router.get("/tree", response_model=TreeResponse)
async def get_vault_tree(
    user_id: str = Depends(get_current_user),
    vault=Depends(get_vault_service),
):
    """Return the recursive directory tree of the user's vault."""
    try:
        nodes = await vault.list_tree(user_id)
        return TreeResponse(tree=[_tree_node_to_model(n) for n in nodes])
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("get_vault_tree failed for %s: %s", user_id, exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to list vault tree")


@router.get("/file", response_model=FileResponse)
async def get_vault_file(
    path: str = Query(..., description="Relative path within the vault"),
    user_id: str = Depends(get_current_user),
    vault=Depends(get_vault_service),
):
    """Read a single file from the user's vault."""
    try:
        content, mtime_iso, size = await vault.read_file_with_meta(user_id, path)
        return FileResponse(content=content, mtime=mtime_iso, size=size)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("get_vault_file failed for %s: %s", user_id, exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to read vault file")


@router.post("/file", response_model=CreateFileResponse, status_code=201)
async def create_vault_file(
    body: CreateFileRequest,
    user_id: str = Depends(get_current_user),
    vault=Depends(get_vault_service),
):
    """Create a new file in the user's vault."""
    try:
        mtime = await vault.create_file(user_id, body.path, body.content)
        return CreateFileResponse(path=body.path, mtime=mtime)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("create_vault_file failed for %s: %s", user_id, exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to create file")


@router.post("/folder", response_model=CreateFolderResponse, status_code=201)
async def create_vault_folder(
    body: CreateFolderRequest,
    user_id: str = Depends(get_current_user),
    vault=Depends(get_vault_service),
):
    """Create a new folder in the user's vault."""
    try:
        await vault.create_folder(user_id, body.path)
        return CreateFolderResponse(path=body.path)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("create_vault_folder failed for %s: %s", user_id, exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to create folder")


@router.get("/folder", response_model=FolderResponse)
async def get_vault_folder(
    path: str = Query("", description="Relative folder path (empty for root)"),
    user_id: str = Depends(get_current_user),
    vault=Depends(get_vault_service),
):
    """List the contents of a vault folder (flat, one level)."""
    try:
        entries = await vault.list_folder(user_id, path)
        return FolderResponse(
            entries=[
                FolderEntryModel(
                    name=e.name,
                    path=e.path,
                    type=e.type,
                    mtime=e.mtime,
                    size=e.size,
                )
                for e in entries
            ]
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("get_vault_folder failed for %s: %s", user_id, exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to list vault folder")


@router.patch("/rename", response_model=RenameResponse)
async def rename_vault_item(
    body: RenameRequest,
    user_id: str = Depends(get_current_user),
    vault=Depends(get_vault_service),
):
    """Rename/move a file or folder in the user's vault."""
    try:
        await vault.rename(user_id, body.source, body.target)
        return RenameResponse(path=body.target)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("rename_vault_item failed for %s: %s", user_id, exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to rename item")
