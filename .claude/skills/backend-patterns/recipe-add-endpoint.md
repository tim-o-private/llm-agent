# Recipe: Add a New API Endpoint

Prescriptive guide for adding a new REST endpoint. Per A1: thin routers, fat services.

**Reference implementations:** `notification_router.py` / `notification_service.py`

## Prerequisites

- Database table exists (or created in the same spec's DB migration)
- Resource name chosen: `{resource}` (singular for models, plural for routes)

## Step 1: Pydantic Models — `chatServer/models/{resource}.py`

```python
"""Pydantic models for {resource} endpoints."""

from pydantic import BaseModel, Field


class {Resource}Create(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    # Domain-specific fields


class {Resource}Update(BaseModel):
    title: str | None = Field(None, max_length=200)
    # Optional fields for partial update


class {Resource}Response(BaseModel):
    id: str
    title: str
    created_at: str
    updated_at: str
    user_id: str
```

**Never use `request.json()` with manual validation. Always Pydantic models.**

## Step 2: Service — `chatServer/services/{resource}_service.py`

Same pattern as [recipe-add-tool.md](recipe-add-tool.md) Step 1. If the service already exists for tools, reuse it. Routers and tools share the same service layer.

## Step 3: Router — `chatServer/routers/{resource}_router.py`

```python
"""Router for {resource} endpoints."""

import logging

from fastapi import APIRouter, Depends, HTTPException

from ..dependencies.auth import get_current_user
from ..database.scoped_client import get_user_scoped_client
from ..models.{resource} import {Resource}Create, {Resource}Response, {Resource}Update
from ..services.{resource}_service import {Resource}Service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/{resource}s", tags=["{resource}s"])


def _get_service(db=Depends(get_user_scoped_client)) -> {Resource}Service:
    return {Resource}Service(db)


@router.get("", response_model=list[{Resource}Response])
async def list_{resource}s(
    user_id: str = Depends(get_current_user),
    service: {Resource}Service = Depends(_get_service),
):
    return await service.list_{resource}s(user_id)


@router.post("", response_model={Resource}Response, status_code=201)
async def create_{resource}(
    data: {Resource}Create,
    user_id: str = Depends(get_current_user),
    service: {Resource}Service = Depends(_get_service),
):
    return await service.create_{resource}(user_id, **data.model_dump())


@router.get("/{{resource_id}}", response_model={Resource}Response)
async def get_{resource}(
    resource_id: str,
    user_id: str = Depends(get_current_user),
    service: {Resource}Service = Depends(_get_service),
):
    result = await service.get_{resource}(user_id, resource_id)
    if not result:
        raise HTTPException(status_code=404, detail="{Resource} not found")
    return result


@router.patch("/{{resource_id}}", response_model={Resource}Response)
async def update_{resource}(
    resource_id: str,
    data: {Resource}Update,
    user_id: str = Depends(get_current_user),
    service: {Resource}Service = Depends(_get_service),
):
    result = await service.update_{resource}(user_id, resource_id, **data.model_dump(exclude_unset=True))
    if not result:
        raise HTTPException(status_code=404, detail="{Resource} not found")
    return result


@router.delete("/{{resource_id}}", status_code=204)
async def delete_{resource}(
    resource_id: str,
    user_id: str = Depends(get_current_user),
    service: {Resource}Service = Depends(_get_service),
):
    await service.delete_{resource}(user_id, resource_id)
```

**Rules:**
- Router does ZERO business logic — only wires deps and delegates to service.
- No `.select()`, `.insert()`, `.table()` calls in routers (A1, enforced by `validate-patterns.sh`).
- Auth via `Depends(get_current_user)` — never manual header parsing (A5).
- DB via `Depends(get_user_scoped_client)` — never raw `get_supabase_client` (A8).
- `_get_service` factory creates the service with injected deps.

## Step 4: Register Router — `chatServer/main.py`

```python
from chatServer.routers.{resource}_router import router as {resource}_router

app.include_router({resource}_router)
```

Add near the other `include_router` calls.

## Step 5: Tests — `tests/chatServer/routers/test_{resource}_router.py`

```python
"""Unit tests for {resource} router."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from chatServer.main import app


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture
def auth_headers():
    """Mock auth headers. Patch get_current_user to bypass real auth."""
    return {"Authorization": "Bearer test-token"}


@pytest.mark.asyncio
async def test_list_{resource}s_requires_auth(client):
    response = await client.get("/api/{resource}s")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_list_{resource}s_returns_list(client, auth_headers):
    with patch("chatServer.dependencies.auth.get_current_user", return_value="user-123"):
        with patch("chatServer.routers.{resource}_router._get_service") as mock_svc:
            mock_svc.return_value.list_{resource}s = AsyncMock(return_value=[])
            response = await client.get("/api/{resource}s", headers=auth_headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_create_{resource}_validates_input(client, auth_headers):
    with patch("chatServer.dependencies.auth.get_current_user", return_value="user-123"):
        response = await client.post("/api/{resource}s", json={}, headers=auth_headers)
    assert response.status_code == 422  # Pydantic validation
```

## Checklist

- [ ] Pydantic models: `chatServer/models/{resource}.py`
- [ ] Service: `chatServer/services/{resource}_service.py` (or reuse existing)
- [ ] Router: `chatServer/routers/{resource}_router.py`
- [ ] Registered in `chatServer/main.py`
- [ ] No business logic in router (A1)
- [ ] Auth via `Depends(get_current_user)` (A5)
- [ ] DB via `Depends(get_user_scoped_client)` (A8)
- [ ] Router tests: `tests/chatServer/routers/test_{resource}_router.py`
- [ ] Service tests: `tests/chatServer/services/test_{resource}_service.py`
- [ ] All tests pass
