"""Integration tests for /api/workflows/runs — auth + cross-user isolation.

The router delegates to ``WorkflowRunsService``; these tests patch the
service to assert auth wiring, the ``template_name`` filter, the
``limit`` parameter, and newest-first ordering. Cross-user isolation is
exercised by swapping ``get_current_user`` + ``get_user_scoped_client``
overrides and asserting each request only ever receives rows scoped to
its own user.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from chatServer.database.supabase_client import get_user_scoped_client
from chatServer.dependencies.auth import get_current_user
from chatServer.routers.workflows_router import router

TEST_USER_A = "user-a"
TEST_USER_B = "user-b"


def _build_app(user_id: str) -> tuple[FastAPI, MagicMock]:
    """Build an isolated FastAPI app with auth + scoped-client overrides.

    The scoped-client override returns a MagicMock stamped with the user's
    id — subsequent assertions rely on which mock instance reached the
    service to confirm cross-user isolation.
    """
    app = FastAPI()
    app.include_router(router)
    scoped_client = MagicMock(user_id=user_id)
    app.dependency_overrides[get_current_user] = lambda: user_id
    app.dependency_overrides[get_user_scoped_client] = lambda: scoped_client
    return app, scoped_client


@pytest.mark.asyncio
async def test_list_runs_requires_auth():
    """Without an auth override the dependency must reject the request."""
    app = FastAPI()
    app.include_router(router)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get("/api/workflows/runs")
    assert r.status_code in (401, 403)


@pytest.mark.asyncio
async def test_list_runs_returns_rows_newest_first():
    app, _ = _build_app(TEST_USER_A)
    rows = [
        {
            "id": "run-2",
            "template_name": "regenerate-today",
            "status": "completed",
            "current_step": "finalize",
            "error": None,
            "started_at": "2026-04-21T10:00:00+00:00",
            "completed_at": "2026-04-21T10:00:30+00:00",
            "created_at": "2026-04-21T10:00:00+00:00",
        },
        {
            "id": "run-1",
            "template_name": "regenerate-today",
            "status": "completed",
            "current_step": "finalize",
            "error": None,
            "started_at": "2026-04-20T10:00:00+00:00",
            "completed_at": "2026-04-20T10:00:30+00:00",
            "created_at": "2026-04-20T10:00:00+00:00",
        },
    ]
    service = MagicMock()
    service.list_runs = AsyncMock(return_value=rows)
    with patch(
        "chatServer.routers.workflows_router.WorkflowRunsService",
        return_value=service,
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            r = await c.get("/api/workflows/runs")
    assert r.status_code == 200
    body = r.json()
    assert [row["id"] for row in body] == ["run-2", "run-1"]
    service.list_runs.assert_awaited_once_with(template_name=None, limit=10)


@pytest.mark.asyncio
async def test_list_runs_applies_template_name_and_limit():
    app, _ = _build_app(TEST_USER_A)
    service = MagicMock()
    service.list_runs = AsyncMock(return_value=[])
    with patch(
        "chatServer.routers.workflows_router.WorkflowRunsService",
        return_value=service,
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            r = await c.get(
                "/api/workflows/runs",
                params={"template_name": "regenerate-today", "limit": 1},
            )
    assert r.status_code == 200
    service.list_runs.assert_awaited_once_with(
        template_name="regenerate-today", limit=1
    )


@pytest.mark.asyncio
async def test_list_runs_validates_limit_bounds():
    app, _ = _build_app(TEST_USER_A)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        too_high = await c.get("/api/workflows/runs", params={"limit": 101})
        too_low = await c.get("/api/workflows/runs", params={"limit": 0})
    assert too_high.status_code == 422
    assert too_low.status_code == 422


@pytest.mark.asyncio
async def test_list_runs_cross_user_isolation():
    """Each request must reach the service with its own user-scoped client.

    Ensures a request authenticated as user B cannot receive the scoped
    client (and therefore data) belonging to user A.
    """
    seen_clients: dict[str, object] = {}

    def fake_service_factory(db):
        seen_clients[db.user_id] = db
        service = MagicMock()
        service.list_runs = AsyncMock(return_value=[])
        return service

    with patch(
        "chatServer.routers.workflows_router.WorkflowRunsService",
        side_effect=fake_service_factory,
    ):
        for user in (TEST_USER_A, TEST_USER_B):
            app, scoped = _build_app(user)
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as c:
                r = await c.get("/api/workflows/runs")
            assert r.status_code == 200
            assert seen_clients[user] is scoped

    assert seen_clients[TEST_USER_A] is not seen_clients[TEST_USER_B]
