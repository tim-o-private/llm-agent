"""Entity index and search API — thin router over EntityService.

Endpoints:
    GET /api/vault/entities/index  → entity index for wikilink resolution (AC-07)
    GET /api/vault/entities/search → substring search on name/aliases

All filesystem logic lives in EntityService → VaultService.
Auth enforced by ``get_current_user``.
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from ..dependencies.auth import get_current_user
from ..services.entity_service import EntityService
from .vault_router import get_vault_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/vault/entities", tags=["entities"])


# --- Response models --------------------------------------------------------


class EntitySummaryModel(BaseModel):
    slug: str
    name: str
    entity_type: str
    path: str
    aliases: list[str]


class EntityIndexResponse(BaseModel):
    entities: list[EntitySummaryModel]


class EntitySearchResponse(BaseModel):
    results: list[EntitySummaryModel]


# --- Dependency -------------------------------------------------------------


def get_entity_service(vault=Depends(get_vault_service)) -> EntityService:
    """FastAPI dependency: EntityService wrapping the VaultService."""
    return EntityService(vault)


# --- Endpoints --------------------------------------------------------------


@router.get("/index", response_model=EntityIndexResponse)
async def get_entity_index(
    entity_type: Optional[str] = Query(None, description="Filter by entity type"),
    user_id: str = Depends(get_current_user),
    entity_svc: EntityService = Depends(get_entity_service),
):
    """Return the lightweight entity index for wikilink resolution (AC-07).

    Seeds the entity directory structure on first access (AC-01).
    """
    try:
        await entity_svc.ensure_entity_dirs(user_id)
        entities = await entity_svc.list_entities(user_id, entity_type)
        return EntityIndexResponse(
            entities=[
                EntitySummaryModel(
                    slug=e.slug,
                    name=e.name,
                    entity_type=e.entity_type,
                    path=e.path,
                    aliases=e.aliases,
                )
                for e in entities
            ]
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("get_entity_index failed for %s: %s", user_id, exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to list entities")


@router.get("/search", response_model=EntitySearchResponse)
async def search_entities(
    q: str = Query(..., description="Search query"),
    user_id: str = Depends(get_current_user),
    entity_svc: EntityService = Depends(get_entity_service),
):
    """Search entities by name/alias substring match."""
    try:
        results = await entity_svc.search_entities(user_id, q)
        return EntitySearchResponse(
            results=[
                EntitySummaryModel(
                    slug=e.slug,
                    name=e.name,
                    entity_type=e.entity_type,
                    path=e.path,
                    aliases=e.aliases,
                )
                for e in results
            ]
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("search_entities failed for %s: %s", user_id, exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to search entities")
