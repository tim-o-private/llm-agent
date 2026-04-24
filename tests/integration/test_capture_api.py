"""Integration tests for /api/capture/* — auth + capture flow.

These tests wire the real router against a mocked CaptureService.
Auth goes through dependency_overrides.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from chatServer.database.supabase_client import get_user_scoped_client
from chatServer.dependencies.auth import get_current_user
from chatServer.routers.capture_router import (
    get_capture_service,
    router,
)

TEST_USER_A = "user-a"
TEST_USER_B = "user-b"


def _build_app(user_id: str):
    """Build an isolated FastAPI app with the capture router + auth override."""
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_current_user] = lambda: user_id
    app.dependency_overrides[get_user_scoped_client] = lambda: MagicMock(user_id=user_id)
    return app


def _capture_row(capture_id="cap-123", status="placed", **overrides):
    row = {
        "id": capture_id,
        "user_id": TEST_USER_A,
        "text": "test capture",
        "source": "today",
        "context": None,
        "status": status,
        "target_path": "today.md",
        "target_section": "Notes",
        "method": "append",
        "reasoning": "Fallback",
        "fallback": False,
        "confirmation": "Added to `today.md` under Notes",
        "redirect": None,
        "created_at": "2026-04-21T14:00:00Z",
        "placed_at": "2026-04-21T14:00:01Z",
        "error_detail": None,
    }
    row.update(overrides)
    return row


@pytest.mark.asyncio
async def test_create_capture_requires_auth():
    """Without an auth override, POST /api/capture must return 401/403."""
    app = FastAPI()
    app.include_router(router)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.post("/api/capture", json={"text": "hello", "source": "today"})
    assert r.status_code in (401, 403)


@pytest.mark.asyncio
async def test_create_capture_returns_202():
    """POST /api/capture should return 202 with capture state."""
    app = _build_app(TEST_USER_A)
    service = MagicMock()
    service.create_capture = AsyncMock(return_value=_capture_row())
    app.dependency_overrides[get_capture_service] = lambda: service
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.post("/api/capture", json={"text": "test capture", "source": "today"})
    assert r.status_code == 202
    body = r.json()
    assert body["capture_id"] == "cap-123"
    assert body["status"] == "placed"


@pytest.mark.asyncio
async def test_get_capture_returns_state():
    """GET /api/capture/{id} should return the capture state."""
    app = _build_app(TEST_USER_A)
    service = MagicMock()
    service.get_capture = AsyncMock(return_value=_capture_row())
    app.dependency_overrides[get_capture_service] = lambda: service
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get("/api/capture/cap-123")
    assert r.status_code == 200
    body = r.json()
    assert body["capture_id"] == "cap-123"
    assert body["confirmation"] is not None


@pytest.mark.asyncio
async def test_redirect_capture():
    """POST /api/capture/{id}/redirect should return updated state."""
    app = _build_app(TEST_USER_A)
    service = MagicMock()
    service.redirect_capture = AsyncMock(
        return_value=_capture_row(
            target_path="projects/acme.md",
            confirmation="Moved to `projects/acme.md` under Notes",
            redirect={"from_path": "today.md", "target_hint": "acme"},
        )
    )
    app.dependency_overrides[get_capture_service] = lambda: service
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.post(
            "/api/capture/cap-123/redirect",
            json={"target_hint": "acme"},
        )
    assert r.status_code == 200
    body = r.json()
    assert body["target_path"] == "projects/acme.md"
    assert body["redirect"] is not None


@pytest.mark.asyncio
async def test_create_capture_validates_source():
    """POST /api/capture with invalid source should return 422."""
    app = _build_app(TEST_USER_A)
    service = MagicMock()
    app.dependency_overrides[get_capture_service] = lambda: service
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.post("/api/capture", json={"text": "hello", "source": "invalid"})
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_create_capture_validates_empty_text():
    """POST /api/capture with empty text should return 422."""
    app = _build_app(TEST_USER_A)
    service = MagicMock()
    app.dependency_overrides[get_capture_service] = lambda: service
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.post("/api/capture", json={"text": "", "source": "today"})
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_cross_user_isolation():
    """User B should not be able to read User A's captures."""
    app_b = _build_app(TEST_USER_B)
    from fastapi import HTTPException
    service = MagicMock()
    service.get_capture = AsyncMock(
        side_effect=HTTPException(status_code=404, detail="Capture not found")
    )
    app_b.dependency_overrides[get_capture_service] = lambda: service
    transport = ASGITransport(app=app_b)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get("/api/capture/cap-123")
    assert r.status_code == 404
