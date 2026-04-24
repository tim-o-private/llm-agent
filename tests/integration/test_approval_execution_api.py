"""Integration tests for SPEC-052 approve->execute round-trip, retry flow, cross-user."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from chatServer.database.supabase_client import get_user_scoped_client
from chatServer.dependencies.auth import get_current_user
from chatServer.routers.approvals_router import router

USER_A = "user-a"
USER_B = "user-b"


def _build_app(user_id: str = USER_A):
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_current_user] = lambda: user_id
    app.dependency_overrides[get_user_scoped_client] = lambda: MagicMock(user_id=user_id)
    return app


# ===========================================================================
# Approve triggers execution
# ===========================================================================


@pytest.mark.asyncio
async def test_approve_returns_card_with_execution():
    """POST /approve should return the card. Execution happens in the service."""
    app = _build_app()
    service = MagicMock()
    service.approve = AsyncMock(return_value={
        "id": "c1",
        "status": "approved",
        "executed_at": "2026-04-21T12:00:00Z",
        "execution_result": {"message_id": "msg-1"},
        "execution_error": None,
    })
    with patch(
        "chatServer.routers.approvals_router._build_approval_service",
        new=AsyncMock(return_value=service),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            r = await c.post("/api/approvals/c1/approve", json={})
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "approved"
    assert data["executed_at"] is not None
    assert data["execution_result"]["message_id"] == "msg-1"


# ===========================================================================
# Retry flow
# ===========================================================================


@pytest.mark.asyncio
async def test_retry_endpoint_success():
    """POST /retry on a failed card should return the updated card."""
    app = _build_app()
    service = MagicMock()
    service.retry = AsyncMock(return_value={
        "id": "c1",
        "status": "approved",
        "executed_at": "2026-04-21T12:05:00Z",
        "execution_result": {"message_id": "msg-retry"},
        "execution_error": None,
    })
    with patch(
        "chatServer.routers.approvals_router._build_approval_service",
        new=AsyncMock(return_value=service),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            r = await c.post("/api/approvals/c1/retry")
    assert r.status_code == 200
    data = r.json()
    assert data["execution_error"] is None


@pytest.mark.asyncio
async def test_retry_returns_409_on_precondition_failure():
    """POST /retry when pre-conditions fail should return 409."""
    from fastapi import HTTPException

    app = _build_app()
    service = MagicMock()
    service.retry = AsyncMock(
        side_effect=HTTPException(status_code=409, detail="Card is pending, not approved")
    )
    with patch(
        "chatServer.routers.approvals_router._build_approval_service",
        new=AsyncMock(return_value=service),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            r = await c.post("/api/approvals/c1/retry")
    assert r.status_code == 409


# ===========================================================================
# Auth
# ===========================================================================


@pytest.mark.asyncio
async def test_retry_requires_auth():
    """POST /retry without auth should return 401 or 403."""
    app = FastAPI()
    app.include_router(router)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.post("/api/approvals/c1/retry")
    assert r.status_code in (401, 403)


# ===========================================================================
# Cross-user isolation
# ===========================================================================


@pytest.mark.asyncio
async def test_cross_user_retry_returns_404():
    """User B cannot retry User A's card (service.get filters by user_id)."""
    from fastapi import HTTPException

    app = _build_app(USER_B)
    service = MagicMock()
    # Service's get() raises 404 because user B doesn't own card c1
    service.retry = AsyncMock(
        side_effect=HTTPException(status_code=404)
    )
    with patch(
        "chatServer.routers.approvals_router._build_approval_service",
        new=AsyncMock(return_value=service),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            r = await c.post("/api/approvals/c1/retry")
    assert r.status_code == 404
