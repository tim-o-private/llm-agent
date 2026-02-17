"""Unit tests for notifications router."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from chatServer.database.supabase_client import get_supabase_client
from chatServer.dependencies.auth import get_current_user
from chatServer.routers.notifications_router import router

# ---------------------------------------------------------------------------
# App setup with dependency overrides
# ---------------------------------------------------------------------------

app = FastAPI()
app.include_router(router)

TEST_USER_ID = "test-user-id"


def override_get_current_user():
    return TEST_USER_ID


def override_get_supabase_client():
    return MagicMock()


app.dependency_overrides[get_current_user] = override_get_current_user
app.dependency_overrides[get_supabase_client] = override_get_supabase_client


@pytest.fixture
def client():
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


# ---------------------------------------------------------------------------
# Sample data
# ---------------------------------------------------------------------------

SAMPLE_NOTIFICATION = {
    "id": "notif-1",
    "title": "Test",
    "body": "Body text",
    "category": "info",
    "metadata": {},
    "read": False,
    "created_at": datetime.now(tz=timezone.utc).isoformat(),
}


# ---------------------------------------------------------------------------
# GET /api/notifications
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_notifications_returns_list(client):
    with patch(
        "chatServer.routers.notifications_router.NotificationService"
    ) as MockService:
        instance = MockService.return_value
        instance.get_notifications = AsyncMock(return_value=[SAMPLE_NOTIFICATION])

        resp = await client.get("/api/notifications")

    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["id"] == "notif-1"


# ---------------------------------------------------------------------------
# GET /api/notifications/unread/count
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_unread_count_returns_count(client):
    with patch(
        "chatServer.routers.notifications_router.NotificationService"
    ) as MockService:
        instance = MockService.return_value
        instance.get_unread_count = AsyncMock(return_value=5)

        resp = await client.get("/api/notifications/unread/count")

    assert resp.status_code == 200
    assert resp.json() == {"count": 5}


# ---------------------------------------------------------------------------
# POST /api/notifications/{id}/read
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_mark_notification_read_returns_success(client):
    with patch(
        "chatServer.routers.notifications_router.NotificationService"
    ) as MockService:
        instance = MockService.return_value
        instance.mark_read = AsyncMock(return_value=True)

        resp = await client.post("/api/notifications/notif-1/read")

    assert resp.status_code == 200
    assert resp.json() == {"success": True}


# ---------------------------------------------------------------------------
# POST /api/notifications/read-all
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_mark_all_read_returns_count(client):
    with patch(
        "chatServer.routers.notifications_router.NotificationService"
    ) as MockService:
        instance = MockService.return_value
        instance.mark_all_read = AsyncMock(return_value=3)

        resp = await client.post("/api/notifications/read-all")

    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["count"] == 3


# ---------------------------------------------------------------------------
# Auth required
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_endpoints_require_auth():
    """Endpoints should return 401 when no auth dependency override is present."""
    # Create a fresh app without overrides
    unauth_app = FastAPI()
    unauth_app.include_router(router)
    # Override only supabase client, NOT auth
    unauth_app.dependency_overrides[get_supabase_client] = override_get_supabase_client

    transport = ASGITransport(app=unauth_app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        endpoints = [
            ("GET", "/api/notifications"),
            ("GET", "/api/notifications/unread/count"),
            ("POST", "/api/notifications/notif-1/read"),
            ("POST", "/api/notifications/read-all"),
        ]
        for method, url in endpoints:
            resp = await c.request(method, url)
            assert resp.status_code in (401, 403), f"{method} {url} returned {resp.status_code}, expected 401/403"
