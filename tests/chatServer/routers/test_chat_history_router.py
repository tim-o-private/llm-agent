"""Unit tests for chat history router."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from chatServer.database.supabase_client import get_supabase_client
from chatServer.dependencies.auth import get_current_user
from chatServer.routers.chat_history_router import router

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

NOW = datetime.now(tz=timezone.utc).isoformat()

SAMPLE_SESSION = {
    "id": "session-uuid-1",
    "user_id": TEST_USER_ID,
    "chat_id": "chat-uuid-1",
    "agent_name": "assistant",
    "channel": "web",
    "session_id": "sess-1",
    "is_active": True,
    "created_at": NOW,
    "updated_at": NOW,
}

SAMPLE_MESSAGE = {
    "id": 1,
    "session_id": "sess-1",
    "message": {"type": "human", "content": "hello"},
    "created_at": NOW,
}


# ---------------------------------------------------------------------------
# GET /api/chat/sessions
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_sessions_returns_list(client):
    with patch(
        "chatServer.routers.chat_history_router.ChatHistoryService"
    ) as MockService:
        instance = MockService.return_value
        instance.get_sessions = AsyncMock(return_value=[SAMPLE_SESSION])

        resp = await client.get("/api/chat/sessions")

    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["id"] == "session-uuid-1"
    assert data[0]["channel"] == "web"


@pytest.mark.asyncio
async def test_get_sessions_passes_channel_filter(client):
    with patch(
        "chatServer.routers.chat_history_router.ChatHistoryService"
    ) as MockService:
        instance = MockService.return_value
        instance.get_sessions = AsyncMock(return_value=[])

        await client.get("/api/chat/sessions?channel=telegram")

        instance.get_sessions.assert_awaited_once_with(
            user_id=TEST_USER_ID,
            channel="telegram",
            limit=50,
            offset=0,
        )


# ---------------------------------------------------------------------------
# GET /api/chat/sessions/{session_id}/messages
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_messages_returns_list(client):
    with patch(
        "chatServer.routers.chat_history_router.ChatHistoryService"
    ) as MockService:
        instance = MockService.return_value
        instance.get_session_messages = AsyncMock(return_value=[SAMPLE_MESSAGE])

        resp = await client.get("/api/chat/sessions/sess-1/messages")

    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["session_id"] == "sess-1"


@pytest.mark.asyncio
async def test_get_messages_passes_cursor(client):
    with patch(
        "chatServer.routers.chat_history_router.ChatHistoryService"
    ) as MockService:
        instance = MockService.return_value
        instance.get_session_messages = AsyncMock(return_value=[])

        await client.get("/api/chat/sessions/sess-1/messages?before_id=42&limit=10")

        instance.get_session_messages.assert_awaited_once_with(
            session_id="sess-1",
            user_id=TEST_USER_ID,
            limit=10,
            before_id=42,
        )


# ---------------------------------------------------------------------------
# Auth required
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sessions_require_auth():
    """Endpoints should return 401 when no auth dependency override is present."""
    unauth_app = FastAPI()
    unauth_app.include_router(router)
    unauth_app.dependency_overrides[get_supabase_client] = override_get_supabase_client

    transport = ASGITransport(app=unauth_app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        resp = await c.get("/api/chat/sessions")
        assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_messages_require_auth():
    """Endpoints should return 401 when no auth dependency override is present."""
    unauth_app = FastAPI()
    unauth_app.include_router(router)
    unauth_app.dependency_overrides[get_supabase_client] = override_get_supabase_client

    transport = ASGITransport(app=unauth_app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        resp = await c.get("/api/chat/sessions/sess-1/messages")
        assert resp.status_code in (401, 403)
