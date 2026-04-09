"""Tests for telegram_push utility — cross-channel notification sync.

Covers AC-33 (shared Telegram push utility).
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from chatServer.services.telegram_push import push_to_telegram_if_linked


def _mock_db_client(channel_data=None, session_data=None):
    """Build a mock Supabase client with chained query API."""
    client = MagicMock()

    def _build_chain(data):
        chain = MagicMock()
        chain.select.return_value = chain
        chain.eq.return_value = chain
        chain.order.return_value = chain
        chain.limit.return_value = chain
        result = MagicMock()
        result.data = data
        chain.execute = AsyncMock(return_value=result)
        return chain

    # First call: user_channels lookup
    channel_chain = _build_chain(channel_data)
    # Second call: chat_sessions lookup
    session_chain = _build_chain(session_data)

    client.table = MagicMock(side_effect=[channel_chain, session_chain])
    return client


class TestPushToTelegramIfLinked:
    @pytest.mark.asyncio
    async def test_no_telegram_link(self):
        """No-op when user has no Telegram channel."""
        db = _mock_db_client(channel_data=None)
        # Should not raise
        await push_to_telegram_if_linked("u1", "s1", "Hello", db)

    @pytest.mark.asyncio
    async def test_no_telegram_link_empty_list(self):
        """No-op when channel query returns empty list."""
        db = _mock_db_client(channel_data=[])
        await push_to_telegram_if_linked("u1", "s1", "Hello", db)

    @pytest.mark.asyncio
    async def test_session_mismatch(self):
        """No-op when session_id doesn't match most recent web session."""
        db = _mock_db_client(
            channel_data=[{"channel_id": "12345"}],
            session_data=[{"chat_id": "different-session"}],
        )
        with patch("chatServer.channels.telegram_bot.get_telegram_bot_service") as mock_get:
            await push_to_telegram_if_linked("u1", "my-session", "Hello", db)
            mock_get.assert_not_called()

    @pytest.mark.asyncio
    async def test_sends_when_linked_and_matching(self):
        """Sends notification when user is linked and session matches."""
        db = _mock_db_client(
            channel_data=[{"channel_id": "12345"}],
            session_data=[{"chat_id": "my-session"}],
        )
        mock_bot = MagicMock()
        mock_bot.send_notification = AsyncMock()

        with patch(
            "chatServer.channels.telegram_bot.get_telegram_bot_service",
            return_value=mock_bot,
        ):
            await push_to_telegram_if_linked("u1", "my-session", "Hello", db)
            mock_bot.send_notification.assert_awaited_once_with("12345", "Hello")

    @pytest.mark.asyncio
    async def test_no_bot_service(self):
        """No-op when bot service is not initialized."""
        db = _mock_db_client(
            channel_data=[{"channel_id": "12345"}],
            session_data=[{"chat_id": "my-session"}],
        )
        with patch(
            "chatServer.channels.telegram_bot.get_telegram_bot_service",
            return_value=None,
        ):
            # Should not raise
            await push_to_telegram_if_linked("u1", "my-session", "Hello", db)
