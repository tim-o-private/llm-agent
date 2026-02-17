"""Unit tests for ChatHistoryService."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from chatServer.services.chat_history_service import ChatHistoryService


@pytest.fixture
def db_client():
    """Create a mock Supabase db client with method chaining support."""
    return MagicMock()


@pytest.fixture
def service(db_client):
    return ChatHistoryService(db_client)


def _setup_select_chain(db_client, data=None):
    """Set up mock chain for table(...).select(...).eq(...).order(...).range(...).execute()."""
    if data is None:
        data = []
    mock_result = MagicMock(data=data)
    mock_execute = AsyncMock(return_value=mock_result)
    chain = db_client.table.return_value.select.return_value
    chain.eq.return_value = chain
    chain.order.return_value = chain
    chain.range.return_value = chain
    chain.limit.return_value = chain
    chain.lt.return_value = chain
    chain.execute = mock_execute
    return mock_execute


# ---------------------------------------------------------------------------
# get_sessions
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_sessions_returns_user_sessions(service, db_client):
    """Verify get_sessions returns sessions for the given user."""
    expected = [
        {"id": "s1", "user_id": "user-1", "channel": "web", "session_id": "sess-1"},
        {"id": "s2", "user_id": "user-1", "channel": "telegram", "session_id": "sess-2"},
    ]
    _setup_select_chain(db_client, data=expected)

    result = await service.get_sessions(user_id="user-1")

    assert result == expected
    db_client.table.assert_called_with("chat_sessions")


@pytest.mark.asyncio
async def test_get_sessions_filters_by_channel(service, db_client):
    """When channel is provided, an extra .eq('channel', ...) should be applied."""
    _setup_select_chain(db_client, data=[])

    await service.get_sessions(user_id="user-1", channel="telegram")

    chain = db_client.table.return_value.select.return_value
    eq_calls = [call.args for call in chain.eq.call_args_list]
    assert ("user_id", "user-1") in eq_calls
    assert ("channel", "telegram") in eq_calls


@pytest.mark.asyncio
async def test_get_sessions_returns_empty_on_error(service, db_client):
    """On exception, get_sessions should return empty list."""
    db_client.table.side_effect = Exception("DB down")

    result = await service.get_sessions(user_id="user-1")

    assert result == []


# ---------------------------------------------------------------------------
# get_session_messages
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_session_messages_returns_messages(service, db_client):
    """Verify messages are returned for a valid session."""
    session_data = [{"id": "s1"}]
    message_data = [
        {"id": 1, "session_id": "sess-1", "message": {"type": "human", "content": "hi"}},
        {"id": 2, "session_id": "sess-1", "message": {"type": "ai", "content": "hello"}},
    ]

    # First call: session ownership check
    session_result = MagicMock(data=session_data)
    session_execute = AsyncMock(return_value=session_result)

    # Second call: message fetch
    message_result = MagicMock(data=message_data)
    message_execute = AsyncMock(return_value=message_result)

    # We need to handle two separate table() calls
    call_count = 0

    def table_side_effect(table_name):
        nonlocal call_count
        mock_table = MagicMock()
        chain = mock_table.select.return_value
        chain.eq.return_value = chain
        chain.order.return_value = chain
        chain.limit.return_value = chain
        chain.lt.return_value = chain

        if table_name == "chat_sessions":
            chain.execute = session_execute
        else:
            chain.execute = message_execute

        call_count += 1
        return mock_table

    db_client.table.side_effect = table_side_effect

    result = await service.get_session_messages(session_id="sess-1", user_id="user-1")

    assert result == message_data


@pytest.mark.asyncio
async def test_get_session_messages_respects_cursor(service, db_client):
    """When before_id is provided, .lt('id', before_id) should be called."""
    session_result = MagicMock(data=[{"id": "s1"}])
    session_execute = AsyncMock(return_value=session_result)

    message_result = MagicMock(data=[])
    message_execute = AsyncMock(return_value=message_result)

    message_chain = MagicMock()

    def table_side_effect(table_name):
        mock_table = MagicMock()
        chain = mock_table.select.return_value
        chain.eq.return_value = chain
        chain.order.return_value = chain
        chain.limit.return_value = chain
        chain.lt.return_value = chain

        if table_name == "chat_sessions":
            chain.execute = session_execute
        else:
            # Track the message chain so we can assert on it
            nonlocal message_chain
            message_chain = chain
            chain.execute = message_execute

        return mock_table

    db_client.table.side_effect = table_side_effect

    await service.get_session_messages(session_id="sess-1", user_id="user-1", before_id=100)

    message_chain.lt.assert_called_with("id", 100)


@pytest.mark.asyncio
async def test_get_session_messages_denies_other_user(service, db_client):
    """When session doesn't belong to user, return empty list."""
    # Session check returns empty — user doesn't own this session
    session_result = MagicMock(data=[])
    session_execute = AsyncMock(return_value=session_result)

    def table_side_effect(table_name):
        mock_table = MagicMock()
        chain = mock_table.select.return_value
        chain.eq.return_value = chain
        chain.execute = session_execute
        return mock_table

    db_client.table.side_effect = table_side_effect

    result = await service.get_session_messages(session_id="sess-1", user_id="other-user")

    assert result == []
