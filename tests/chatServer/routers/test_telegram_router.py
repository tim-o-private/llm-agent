"""Unit tests for Telegram router endpoints."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from chatServer.routers.telegram_router import router

app = FastAPI()
app.include_router(router)


def _mock_bot_service():
    """Create a mock TelegramBotService."""
    bot_service = MagicMock()
    bot_service.process_update = AsyncMock()
    bot_service.bot = MagicMock()
    bot_info = MagicMock()
    bot_info.username = "test_bot"
    bot_service.bot.get_me = AsyncMock(return_value=bot_info)
    return bot_service


@pytest.mark.asyncio
async def test_webhook_returns_ok():
    bot_service = _mock_bot_service()

    with patch("chatServer.routers.telegram_router.get_telegram_bot_service", return_value=bot_service):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/api/telegram/webhook", json={"update_id": 1})

    assert response.status_code == 200
    assert response.json() == {"ok": True}
    bot_service.process_update.assert_awaited_once_with({"update_id": 1})


@pytest.mark.asyncio
async def test_webhook_503_when_bot_not_configured():
    with patch("chatServer.routers.telegram_router.get_telegram_bot_service", return_value=None):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/api/telegram/webhook", json={"update_id": 1})

    assert response.status_code == 503


@pytest.mark.asyncio
async def test_get_link_token_requires_auth():
    """Calling /link-token without auth should return 401 or 422 (missing dependency)."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/telegram/link-token")

    # FastAPI returns 401/403 when auth dependency fails, or 422 if dependency raises validation error
    assert response.status_code in (401, 403, 422, 500)


@pytest.mark.asyncio
async def test_get_status_requires_auth():
    """Calling /status without auth should fail."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/telegram/status")

    assert response.status_code in (401, 403, 422, 500)


@pytest.mark.asyncio
async def test_unlink_requires_auth():
    """Calling /unlink without auth should fail."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/telegram/unlink")

    assert response.status_code in (401, 403, 422, 500)
