"""Integration tests for /api/today/* — auth + cross-user isolation.

These tests wire the real router against a mocked VaultService /
ApprovalService. Auth goes through dependency_overrides — unauthenticated
requests must reach a 401/403 path via the real `get_current_user`
dependency when no override is supplied.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from chatServer.database.supabase_client import get_user_scoped_client
from chatServer.dependencies.auth import get_current_user
from chatServer.routers.today_router import router

TEST_USER_A = "user-a"
TEST_USER_B = "user-b"


def _build_app(user_id: str):
    """Build an isolated FastAPI app with the today router + auth override."""
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_current_user] = lambda: user_id
    app.dependency_overrides[get_user_scoped_client] = lambda: MagicMock(user_id=user_id)
    return app


@pytest.fixture
def today_response():
    return {
        "date": "2026-04-20",
        "header": {"framing": "Shipping"},
        "your_day": [],
        "to_do": [],
        "notes": [],
        "agent": {"running": [], "watching": [], "recent": [], "blocked": []},
        "approvals": [],
        "recent": [],
        "source_mtime": 1.0,
        "unknown_sections": [],
    }


@pytest.mark.asyncio
async def test_get_today_requires_auth():
    """Without an auth override, GET /api/today must return 401/403."""
    app = FastAPI()
    app.include_router(router)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get("/api/today")
    assert r.status_code in (401, 403)


@pytest.mark.asyncio
async def test_get_today_returns_user_scoped_response(today_response):
    app = _build_app(TEST_USER_A)
    service = MagicMock()
    service.get_today = AsyncMock(return_value=today_response)
    with patch(
        "chatServer.routers.today_router._build_today_service",
        new=AsyncMock(return_value=service),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            r = await c.get("/api/today")
    assert r.status_code == 200
    body = r.json()
    assert body["header"]["framing"] == "Shipping"
    service.get_today.assert_awaited_once_with(TEST_USER_A)


@pytest.mark.asyncio
async def test_get_today_passes_correct_user_id_cross_user_isolation(today_response):
    """Two apps with different users must see their own user_id passed through."""
    service = MagicMock()
    service.get_today = AsyncMock(return_value=today_response)
    with patch(
        "chatServer.routers.today_router._build_today_service",
        new=AsyncMock(return_value=service),
    ):
        for user in (TEST_USER_A, TEST_USER_B):
            app = _build_app(user)
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as c:
                await c.get("/api/today")
            service.get_today.assert_awaited_with(user)


@pytest.mark.asyncio
async def test_append_note_rejects_empty():
    app = _build_app(TEST_USER_A)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.post("/api/today/notes", json={"text": ""})
    # Pydantic min_length=1 → 422; acceptable.
    assert r.status_code in (400, 422)


@pytest.mark.asyncio
async def test_append_note_forwards_to_service():
    app = _build_app(TEST_USER_A)
    service = MagicMock()
    service.append_note = AsyncMock(
        return_value={"created_at": "2026-04-20T12:00:00Z", "text": "ok", "source_mtime": 1.0}
    )
    with patch(
        "chatServer.routers.today_router._build_today_service",
        new=AsyncMock(return_value=service),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            r = await c.post("/api/today/notes", json={"text": "ok"})
    assert r.status_code == 200
    assert r.json()["text"] == "ok"
    service.append_note.assert_awaited_with(TEST_USER_A, "ok")


@pytest.mark.asyncio
async def test_toggle_todo_forwards_expected_mtime():
    app = _build_app(TEST_USER_A)
    service = MagicMock()
    service.toggle_todo = AsyncMock(
        return_value={"line_id": "abc", "checked": True, "source_mtime": 2.0}
    )
    with patch(
        "chatServer.routers.today_router._build_today_service",
        new=AsyncMock(return_value=service),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            r = await c.post(
                "/api/today/todo/toggle",
                json={"line_id": "abc", "checked": True, "expected_mtime": 1.5},
            )
    assert r.status_code == 200
    service.toggle_todo.assert_awaited_with(
        TEST_USER_A, "abc", checked=True, expected_mtime=1.5
    )


@pytest.mark.asyncio
async def test_regenerate_returns_run_id():
    app = _build_app(TEST_USER_A)
    service = MagicMock()
    service.regenerate = AsyncMock(return_value="run-123")
    run_mgr = MagicMock()
    with patch(
        "chatServer.routers.today_router._build_today_service",
        new=AsyncMock(return_value=service),
    ), patch(
        "chatServer.routers.today_router._build_run_manager",
        new=AsyncMock(return_value=run_mgr),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            r = await c.post("/api/today/regenerate")
    assert r.status_code == 200
    assert r.json() == {"run_id": "run-123"}
    service.regenerate.assert_awaited_with(TEST_USER_A, run_mgr)
