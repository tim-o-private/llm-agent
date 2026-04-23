"""Integration tests for /api/activity/* — auth, pagination, filtering,
mark-viewed, and cross-user isolation.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from chatServer.database.supabase_client import get_user_scoped_client
from chatServer.dependencies.auth import get_current_user
from chatServer.routers.activity_router import router

USER_A = "user-a"
USER_B = "user-b"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_app(user_id: str = USER_A):
    """Stand up a minimal FastAPI with the activity router + auth override."""
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_current_user] = lambda: user_id
    app.dependency_overrides[get_user_scoped_client] = lambda: MagicMock(
        user_id=user_id
    )
    return app


def _mock_service(
    *,
    items: list[dict] | None = None,
    has_more: bool = False,
    total: int = 0,
    counts: dict | None = None,
    mark_ts: str = "2026-04-21T12:00:00+00:00",
):
    """Return a mock ActivityLogService with sensible defaults."""
    svc = MagicMock()
    svc.list_paginated = AsyncMock(
        return_value=(items or [], has_more)
    )
    svc.count = AsyncMock(return_value=total)
    svc.get_counts_with_last_viewed = AsyncMock(
        return_value=counts or {"total": total, "since_last_viewed": 0}
    )
    svc.mark_viewed = AsyncMock(return_value=mark_ts)
    return svc


# ---------------------------------------------------------------------------
# AC-08: Auth required
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_requires_auth():
    app = FastAPI()
    app.include_router(router)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get("/api/activity")
    assert r.status_code in (401, 403)


@pytest.mark.asyncio
async def test_count_requires_auth():
    app = FastAPI()
    app.include_router(router)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get("/api/activity/count")
    assert r.status_code in (401, 403)


@pytest.mark.asyncio
async def test_mark_viewed_requires_auth():
    app = FastAPI()
    app.include_router(router)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.post("/api/activity/mark-viewed")
    assert r.status_code in (401, 403)


# ---------------------------------------------------------------------------
# AC-01: Paginated list
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_returns_items_total_has_more():
    app = _build_app()
    svc = _mock_service(
        items=[{"id": "e1", "action": "Did thing"}],
        has_more=False,
        total=1,
    )
    with patch(
        "chatServer.routers.activity_router._build_service",
        return_value=svc,
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            r = await c.get("/api/activity")
    assert r.status_code == 200
    body = r.json()
    assert body["items"] == [{"id": "e1", "action": "Did thing"}]
    assert body["total"] == 1
    assert body["has_more"] is False


# ---------------------------------------------------------------------------
# AC-02: Cursor pagination via ?before=
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_passes_before_cursor():
    app = _build_app()
    svc = _mock_service(total=5)
    with patch(
        "chatServer.routers.activity_router._build_service",
        return_value=svc,
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            await c.get("/api/activity?before=2026-04-21T00:05:00%2B00:00")
    svc.list_paginated.assert_awaited_once()
    call_kwargs = svc.list_paginated.call_args
    assert call_kwargs.kwargs["before"] == "2026-04-21T00:05:00+00:00"


# ---------------------------------------------------------------------------
# AC-01: Limit enforcement
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_with_limit():
    app = _build_app()
    svc = _mock_service(
        items=[{"id": "e1"}, {"id": "e2"}],
        has_more=True,
        total=5,
    )
    with patch(
        "chatServer.routers.activity_router._build_service",
        return_value=svc,
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            r = await c.get("/api/activity?limit=2")
    assert r.status_code == 200
    body = r.json()
    assert body["has_more"] is True
    svc.list_paginated.assert_awaited_once()
    assert svc.list_paginated.call_args.kwargs["limit"] == 2


@pytest.mark.asyncio
async def test_list_rejects_limit_above_100():
    app = _build_app()
    svc = _mock_service()
    with patch(
        "chatServer.routers.activity_router._build_service",
        return_value=svc,
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            r = await c.get("/api/activity?limit=200")
    assert r.status_code == 422  # FastAPI validation error


# ---------------------------------------------------------------------------
# AC-03: Filter by workflow_run_id
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_passes_workflow_run_id():
    app = _build_app()
    svc = _mock_service()
    with patch(
        "chatServer.routers.activity_router._build_service",
        return_value=svc,
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            await c.get("/api/activity?workflow_run_id=abc-123")
    assert svc.list_paginated.call_args.kwargs["workflow_run_id"] == "abc-123"


# ---------------------------------------------------------------------------
# AC-04: Filter by status
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_parses_comma_separated_status():
    app = _build_app()
    svc = _mock_service()
    with patch(
        "chatServer.routers.activity_router._build_service",
        return_value=svc,
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            await c.get("/api/activity?status=done,failed")
    assert svc.list_paginated.call_args.kwargs["status"] == ["done", "failed"]


# ---------------------------------------------------------------------------
# AC-05: Text search
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_passes_q_search():
    app = _build_app()
    svc = _mock_service()
    with patch(
        "chatServer.routers.activity_router._build_service",
        return_value=svc,
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            await c.get("/api/activity?q=regenerate")
    assert svc.list_paginated.call_args.kwargs["q"] == "regenerate"


# ---------------------------------------------------------------------------
# AC-06: Count endpoint
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_count_returns_total_and_since_last_viewed():
    app = _build_app()
    svc = _mock_service(
        counts={"total": 25, "since_last_viewed": 3}
    )
    with patch(
        "chatServer.routers.activity_router._build_service",
        return_value=svc,
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            r = await c.get("/api/activity/count")
    assert r.status_code == 200
    body = r.json()
    assert body == {"total": 25, "since_last_viewed": 3}


# ---------------------------------------------------------------------------
# AC-07: Mark viewed
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_mark_viewed_returns_timestamp():
    app = _build_app()
    svc = _mock_service(mark_ts="2026-04-21T12:00:00+00:00")
    with patch(
        "chatServer.routers.activity_router._build_service",
        return_value=svc,
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            r = await c.post("/api/activity/mark-viewed")
    assert r.status_code == 200
    assert r.json() == {"marked_at": "2026-04-21T12:00:00+00:00"}
    svc.mark_viewed.assert_awaited_once_with(USER_A)


@pytest.mark.asyncio
async def test_mark_viewed_then_count_shows_zero():
    """After mark-viewed, since_last_viewed should reflect 0."""
    app = _build_app()

    # First call: mark_viewed
    svc_mark = _mock_service(mark_ts="2026-04-21T12:00:00+00:00")
    with patch(
        "chatServer.routers.activity_router._build_service",
        return_value=svc_mark,
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            r1 = await c.post("/api/activity/mark-viewed")
    assert r1.status_code == 200

    # Second call: count — should show 0 since_last_viewed
    svc_count = _mock_service(
        counts={"total": 10, "since_last_viewed": 0}
    )
    with patch(
        "chatServer.routers.activity_router._build_service",
        return_value=svc_count,
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            r2 = await c.get("/api/activity/count")
    assert r2.json()["since_last_viewed"] == 0


# ---------------------------------------------------------------------------
# AC-08 / AC-19: Cross-user isolation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cross_user_isolation_list():
    """User B's request hits the service with User B's user_id, not A's."""
    app = _build_app(user_id=USER_B)
    svc = _mock_service(items=[], total=0)
    with patch(
        "chatServer.routers.activity_router._build_service",
        return_value=svc,
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            r = await c.get("/api/activity")
    assert r.status_code == 200
    # The service was called with USER_B
    svc.list_paginated.assert_awaited_once()
    assert svc.list_paginated.call_args[0][0] == USER_B


@pytest.mark.asyncio
async def test_cross_user_isolation_count():
    """User B's count request is scoped to User B."""
    app = _build_app(user_id=USER_B)
    svc = _mock_service(counts={"total": 0, "since_last_viewed": 0})
    with patch(
        "chatServer.routers.activity_router._build_service",
        return_value=svc,
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            r = await c.get("/api/activity/count")
    assert r.status_code == 200
    svc.get_counts_with_last_viewed.assert_awaited_once_with(USER_B)


@pytest.mark.asyncio
async def test_cross_user_isolation_mark_viewed():
    """User B's mark-viewed is scoped to User B."""
    app = _build_app(user_id=USER_B)
    svc = _mock_service()
    with patch(
        "chatServer.routers.activity_router._build_service",
        return_value=svc,
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            r = await c.post("/api/activity/mark-viewed")
    assert r.status_code == 200
    svc.mark_viewed.assert_awaited_once_with(USER_B)
