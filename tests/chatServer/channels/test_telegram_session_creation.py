"""Tests for Telegram session creation in handle_message."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from chatServer.channels.telegram_bot import handle_message


def _make_message(text="hello", chat_id=12345):
    """Create a mock aiogram Message."""
    msg = MagicMock()
    msg.text = text
    msg.chat = MagicMock()
    msg.chat.id = chat_id
    msg.answer = AsyncMock()
    msg.bot = MagicMock()
    msg.bot.send_chat_action = AsyncMock()
    return msg


@pytest.mark.asyncio
async def test_handle_message_upserts_chat_session():
    """handle_message should upsert a chat_sessions row with channel='telegram'."""
    # Set up bot_service with db_client
    bot_service = MagicMock()
    db_client = MagicMock()

    # Track calls per table
    user_channels_chain = MagicMock()
    user_channels_chain.eq.return_value = user_channels_chain
    user_channels_chain.single.return_value = user_channels_chain
    user_channels_chain.execute = AsyncMock(
        return_value=MagicMock(data={"user_id": "user-123"})
    )

    # chat_sessions select chain (handles both web session lookup and existence check)
    cs_select_chain = MagicMock()
    cs_select_chain.eq.return_value = cs_select_chain
    cs_select_chain.order.return_value = cs_select_chain
    cs_select_chain.limit.return_value = cs_select_chain
    cs_select_chain.execute = AsyncMock(return_value=MagicMock(data=[]))

    # chat_sessions insert chain
    cs_insert_chain = MagicMock()
    cs_insert_chain.execute = AsyncMock(return_value=MagicMock(data=[]))

    chat_sessions_mock = MagicMock()
    # select is called twice: first for web session lookup, then for existence check
    # Both return empty data (no existing sessions)
    chat_sessions_mock.select.return_value = cs_select_chain
    chat_sessions_mock.insert.return_value = cs_insert_chain

    user_channels_mock = MagicMock()
    user_channels_mock.select.return_value = user_channels_chain

    def table_side_effect(table_name):
        if table_name == "user_channels":
            return user_channels_mock
        elif table_name == "chat_sessions":
            return chat_sessions_mock
        return MagicMock()

    db_client.table.side_effect = table_side_effect
    bot_service._db_client = db_client

    message = _make_message(text="hello", chat_id=12345)

    mock_executor = MagicMock()
    mock_executor.ainvoke = AsyncMock(return_value={"output": "hi there"})
    mock_executor.tools = []

    with (
        patch("chatServer.channels.telegram_bot.get_telegram_bot_service", return_value=bot_service),
        patch("src.core.agent_loader_db.load_agent_executor_db", return_value=mock_executor),
        patch.dict("sys.modules", {
            "chatServer.security.tool_wrapper": MagicMock(),
            "chatServer.services.audit_service": MagicMock(),
            "chatServer.services.pending_actions": MagicMock(),
        }),
    ):
        await handle_message(message)

    # Verify chat_sessions select was called (web session lookup + existence check)
    assert chat_sessions_mock.select.call_count == 2
    # Verify chat_sessions insert was called (since no existing session)
    chat_sessions_mock.insert.assert_called_once()
    insert_data = chat_sessions_mock.insert.call_args[0][0]
    assert insert_data["user_id"] == "user-123"
    assert insert_data["channel"] == "telegram"
    assert insert_data["agent_name"] == "assistant"
    assert insert_data["is_active"] is True


@pytest.mark.asyncio
async def test_handle_message_no_session_when_not_linked():
    """When user isn't linked, no session should be created."""
    bot_service = MagicMock()
    db_client = MagicMock()

    # User lookup returns no data (not linked)
    lookup_chain = MagicMock()
    lookup_chain.eq.return_value = lookup_chain
    lookup_chain.single.return_value = lookup_chain
    lookup_chain.execute = AsyncMock(return_value=MagicMock(data=None))

    user_channels_mock = MagicMock()
    user_channels_mock.select.return_value = lookup_chain

    chat_sessions_mock = MagicMock()

    def table_side_effect(table_name):
        if table_name == "user_channels":
            return user_channels_mock
        elif table_name == "chat_sessions":
            return chat_sessions_mock
        return MagicMock()

    db_client.table.side_effect = table_side_effect
    bot_service._db_client = db_client
    message = _make_message()

    with patch("chatServer.channels.telegram_bot.get_telegram_bot_service", return_value=bot_service):
        await handle_message(message)

    # Should NOT have called upsert on chat_sessions
    chat_sessions_mock.upsert.assert_not_called()
