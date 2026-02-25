"""Unit tests for notification feedback endpoint."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from chatServer.database.supabase_client import get_user_scoped_client
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


def override_get_user_scoped_client():
    return MagicMock()


app.dependency_overrides[get_current_user] = override_get_current_user
app.dependency_overrides[get_user_scoped_client] = override_get_user_scoped_client


@pytest.fixture
def client():
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


# ---------------------------------------------------------------------------
# POST /api/notifications/{id}/feedback
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_feedback_endpoint_success(client):
    """POST with valid feedback returns 200 and success=True."""
    with patch("chatServer.routers.notifications_router.NotificationService") as MockService:
        instance = MockService.return_value
        instance.submit_feedback = AsyncMock(return_value={"status": "ok"})

        resp = await client.post(
            "/api/notifications/notif-1/feedback",
            json={"feedback": "useful"},
        )

    assert resp.status_code == 200
    assert resp.json() == {"success": True}


@pytest.mark.asyncio
async def test_feedback_endpoint_not_found(client):
    """POST returns 404 when notification not found."""
    with patch("chatServer.routers.notifications_router.NotificationService") as MockService:
        instance = MockService.return_value
        instance.submit_feedback = AsyncMock(return_value={"status": "not_found"})

        resp = await client.post(
            "/api/notifications/notif-missing/feedback",
            json={"feedback": "useful"},
        )

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_feedback_endpoint_duplicate(client):
    """POST returns 409 when feedback was already submitted."""
    with patch("chatServer.routers.notifications_router.NotificationService") as MockService:
        instance = MockService.return_value
        instance.submit_feedback = AsyncMock(return_value={"status": "already_set"})

        resp = await client.post(
            "/api/notifications/notif-1/feedback",
            json={"feedback": "not_useful"},
        )

    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_feedback_endpoint_invalid_value(client):
    """POST with invalid feedback value returns 422."""
    resp = await client.post(
        "/api/notifications/notif-1/feedback",
        json={"feedback": "great"},
    )

    assert resp.status_code == 422
