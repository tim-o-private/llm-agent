"""Integration tests for /api/approvals/* — state machine + auth."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI, HTTPException
from httpx import ASGITransport, AsyncClient

from chatServer.database.supabase_client import get_user_scoped_client
from chatServer.dependencies.auth import get_current_user
from chatServer.routers.approvals_router import router

USER_A = "user-a"


def _build_app(user_id: str = USER_A):
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_current_user] = lambda: user_id
    app.dependency_overrides[get_user_scoped_client] = lambda: MagicMock(user_id=user_id)
    return app


@pytest.mark.asyncio
async def test_list_pending_requires_auth():
    app = FastAPI()
    app.include_router(router)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get("/api/approvals")
    assert r.status_code in (401, 403)


@pytest.mark.asyncio
async def test_list_pending_returns_service_payload():
    app = _build_app()
    service = MagicMock()
    service.list_pending = AsyncMock(return_value=[{"id": "c1", "status": "pending"}])
    with patch(
        "chatServer.routers.approvals_router._build_approval_service",
        new=AsyncMock(return_value=service),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            r = await c.get("/api/approvals")
    assert r.status_code == 200
    assert r.json() == [{"id": "c1", "status": "pending"}]


@pytest.mark.asyncio
async def test_count_endpoint_returns_integer():
    app = _build_app()
    service = MagicMock()
    service.count_pending = AsyncMock(return_value=7)
    with patch(
        "chatServer.routers.approvals_router._build_approval_service",
        new=AsyncMock(return_value=service),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            r = await c.get("/api/approvals/count")
    assert r.status_code == 200
    assert r.json() == {"count": 7}


@pytest.mark.asyncio
async def test_approve_forwards_decision_note():
    app = _build_app()
    service = MagicMock()
    service.approve = AsyncMock(return_value={"id": "c1", "status": "approved"})
    with patch(
        "chatServer.routers.approvals_router._build_approval_service",
        new=AsyncMock(return_value=service),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            r = await c.post("/api/approvals/c1/approve", json={"decision_note": "LGTM"})
    assert r.status_code == 200
    service.approve.assert_awaited_with(USER_A, "c1", decision_note="LGTM")


@pytest.mark.asyncio
async def test_approve_non_pending_surfaces_409():
    app = _build_app()
    service = MagicMock()
    service.approve = AsyncMock(
        side_effect=HTTPException(status_code=409, detail="Already approved")
    )
    with patch(
        "chatServer.routers.approvals_router._build_approval_service",
        new=AsyncMock(return_value=service),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            r = await c.post("/api/approvals/c1/approve", json={})
    assert r.status_code == 409


@pytest.mark.asyncio
async def test_reject_forwards_reason():
    app = _build_app()
    service = MagicMock()
    service.reject = AsyncMock(return_value={"id": "c1", "status": "rejected"})
    with patch(
        "chatServer.routers.approvals_router._build_approval_service",
        new=AsyncMock(return_value=service),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            r = await c.post("/api/approvals/c1/reject", json={"reason": "wrong tone"})
    assert r.status_code == 200
    service.reject.assert_awaited_with(USER_A, "c1", reason="wrong tone")


@pytest.mark.asyncio
async def test_edit_rejects_empty_payload_via_service():
    app = _build_app()
    service = MagicMock()
    service.edit = AsyncMock(
        side_effect=HTTPException(status_code=400, detail="payload_patch must be a non-empty object")
    )
    with patch(
        "chatServer.routers.approvals_router._build_approval_service",
        new=AsyncMock(return_value=service),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            r = await c.post("/api/approvals/c1/edit", json={"payload_patch": {}})
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_edit_merges_payload_patch():
    app = _build_app()
    service = MagicMock()
    service.edit = AsyncMock(return_value={"id": "c1", "payload": {"body": "new"}})
    with patch(
        "chatServer.routers.approvals_router._build_approval_service",
        new=AsyncMock(return_value=service),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            r = await c.post(
                "/api/approvals/c1/edit", json={"payload_patch": {"body": "new"}}
            )
    assert r.status_code == 200
    service.edit.assert_awaited_with(USER_A, "c1", {"body": "new"})
