"""Unit tests for session_open router."""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from chatServer.dependencies.auth import get_current_user
from chatServer.routers.session_open_router import router

# ---------------------------------------------------------------------------
# App setup with dependency overrides
# ---------------------------------------------------------------------------

app = FastAPI()
app.include_router(router)

TEST_USER_ID = "test-user-id"


def override_get_current_user():
    return TEST_USER_ID


app.dependency_overrides[get_current_user] = override_get_current_user


@pytest.fixture
def client():
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


# ---------------------------------------------------------------------------
# POST /api/chat/session_open — 200 with valid auth
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_session_open_200_with_valid_auth(client):
    mock_result = {
        "session_id": "s1",
        "response": "Hello! I'm Clarity.",
        "is_new_user": True,
        "silent": False,
    }

    with patch(
        "chatServer.routers.session_open_router.SessionOpenService"
    ) as MockService:
        instance = MockService.return_value
        instance.run = AsyncMock(return_value=mock_result)

        resp = await client.post(
            "/api/chat/session_open",
            json={"agent_name": "clarity", "session_id": "s1"},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["session_id"] == "s1"
    assert data["response"] == "Hello! I'm Clarity."
    assert data["is_new_user"] is True
    assert data["silent"] is False


# ---------------------------------------------------------------------------
# POST /api/chat/session_open — 401 without auth
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_session_open_401_without_auth():
    """Endpoint returns 401 when no auth dependency override is present."""
    unauth_app = FastAPI()
    unauth_app.include_router(router)

    transport = ASGITransport(app=unauth_app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        resp = await c.post(
            "/api/chat/session_open",
            json={"agent_name": "clarity", "session_id": "s1"},
        )
        assert resp.status_code in (401, 403), f"Expected 401/403, got {resp.status_code}"
