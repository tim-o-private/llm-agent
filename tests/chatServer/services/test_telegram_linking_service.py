"""Unit tests for Telegram linking service."""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from chatServer.services.telegram_linking_service import (
    create_linking_token,
    get_telegram_status,
    link_telegram_account,
    unlink_telegram_account,
)


def _make_db_client():
    """Create a mock Supabase client with chainable methods."""
    db = MagicMock()
    chain = MagicMock()
    # Make every chained method return the same chain object
    chain.select.return_value = chain
    chain.insert.return_value = chain
    chain.update.return_value = chain
    chain.upsert.return_value = chain
    chain.eq.return_value = chain
    chain.single.return_value = chain
    chain.execute = AsyncMock()
    db.table.return_value = chain
    return db, chain


@pytest.mark.asyncio
async def test_create_linking_token_stores_in_db():
    db, chain = _make_db_client()

    with patch("chatServer.services.telegram_linking_service.secrets") as mock_secrets:
        mock_secrets.token_urlsafe.return_value = "test-token-abc"
        token = await create_linking_token(db, "user-123")

    assert token == "test-token-abc"
    db.table.assert_called_with("channel_linking_tokens")
    chain.insert.assert_called_once()
    insert_arg = chain.insert.call_args[0][0]
    assert insert_arg["user_id"] == "user-123"
    assert insert_arg["channel_type"] == "telegram"
    assert insert_arg["token"] == "test-token-abc"
    chain.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_link_telegram_account_valid_token():
    db, chain = _make_db_client()

    expires = (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat()
    mock_result = MagicMock()
    mock_result.data = {
        "id": "token-row-1",
        "user_id": "user-123",
        "token": "valid-token",
        "expires_at": expires,
        "used": False,
    }
    chain.execute = AsyncMock(return_value=mock_result)

    result = await link_telegram_account(db, "valid-token", "chat-456")

    assert result is True
    # Should have called table 3 times: select token, upsert user_channels, update token used
    assert db.table.call_count == 3
    table_calls = [c[0][0] for c in db.table.call_args_list]
    assert "channel_linking_tokens" in table_calls
    assert "user_channels" in table_calls


@pytest.mark.asyncio
async def test_link_telegram_account_expired_token():
    db, chain = _make_db_client()

    expired = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
    mock_result = MagicMock()
    mock_result.data = {
        "id": "token-row-1",
        "user_id": "user-123",
        "token": "expired-token",
        "expires_at": expired,
        "used": False,
    }
    chain.execute = AsyncMock(return_value=mock_result)

    result = await link_telegram_account(db, "expired-token", "chat-456")

    assert result is False
    # Should only query the token table, not upsert user_channels
    assert db.table.call_count == 1


@pytest.mark.asyncio
async def test_link_telegram_account_used_token():
    db, chain = _make_db_client()

    mock_result = MagicMock()
    mock_result.data = None  # No data means token not found / already used
    chain.execute = AsyncMock(return_value=mock_result)

    result = await link_telegram_account(db, "used-token", "chat-456")

    assert result is False
    assert db.table.call_count == 1


@pytest.mark.asyncio
async def test_unlink_telegram_account():
    db, chain = _make_db_client()

    result = await unlink_telegram_account(db, "user-123")

    assert result is True
    db.table.assert_called_with("user_channels")
    chain.update.assert_called_once_with({"is_active": False})
    chain.eq.assert_any_call("user_id", "user-123")
    chain.eq.assert_any_call("channel_type", "telegram")
    chain.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_telegram_status_linked():
    db, chain = _make_db_client()

    mock_result = MagicMock()
    mock_result.data = {
        "channel_id": "chat-456",
        "is_active": True,
        "linked_at": "2026-01-15T10:00:00Z",
    }
    chain.execute = AsyncMock(return_value=mock_result)

    status = await get_telegram_status(db, "user-123")

    assert status == {"linked": True, "linked_at": "2026-01-15T10:00:00Z"}
    db.table.assert_called_with("user_channels")


@pytest.mark.asyncio
async def test_get_telegram_status_not_linked():
    db, chain = _make_db_client()

    mock_result = MagicMock()
    mock_result.data = None
    chain.execute = AsyncMock(return_value=mock_result)

    status = await get_telegram_status(db, "user-123")

    assert status == {"linked": False}
