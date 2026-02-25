"""Unit tests for NotificationService."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from chatServer.services.notification_service import NotificationService


@pytest.fixture
def db_client():
    """Create a mock Supabase db client with method chaining support."""
    client = MagicMock()
    return client


@pytest.fixture
def service(db_client):
    return NotificationService(db_client)


def _setup_insert_chain(db_client, data=None):
    """Set up mock chain for table(...).insert(...).execute()."""
    if data is None:
        data = [{"id": "notif-123"}]
    mock_execute = AsyncMock(return_value=MagicMock(data=data))
    db_client.table.return_value.insert.return_value.execute = mock_execute
    return mock_execute


def _setup_select_chain(db_client, data=None, count=None):
    """Set up mock chain for table(...).select(...).eq(...).order(...).range(...).execute()."""
    if data is None:
        data = []
    mock_result = MagicMock(data=data, count=count)
    mock_execute = AsyncMock(return_value=mock_result)
    chain = db_client.table.return_value.select.return_value
    chain.eq.return_value = chain
    chain.order.return_value = chain
    chain.range.return_value = chain
    chain.execute = mock_execute
    return mock_execute


def _setup_update_chain(db_client, data=None):
    """Set up mock chain for table(...).update(...).eq(...).execute()."""
    if data is None:
        data = []
    mock_execute = AsyncMock(return_value=MagicMock(data=data))
    chain = db_client.table.return_value.update.return_value
    chain.eq.return_value = chain
    chain.execute = mock_execute
    return mock_execute


def _setup_telegram_lookup(db_client, channel_id=None):
    """Set up mock chain for user_channels telegram lookup."""
    if channel_id:
        result_data = {"channel_id": channel_id}
    else:
        result_data = None
    mock_execute = AsyncMock(return_value=MagicMock(data=result_data))
    chain = db_client.table.return_value.select.return_value
    chain.eq.return_value = chain
    chain.single.return_value = chain
    chain.execute = mock_execute
    return mock_execute


# ---------------------------------------------------------------------------
# notify_user
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_notify_user_stores_web_notification(service, db_client):
    """Verify insert is called with correct args for web notification."""
    _setup_insert_chain(db_client)
    # Telegram lookup returns None (no linked account)
    _setup_telegram_lookup(db_client, channel_id=None)

    result = await service.notify_user(
        user_id="user-1",
        title="Test Title",
        body="Test body",
        category="info",
        metadata={"key": "val"},
    )

    assert result == "notif-123"
    db_client.table.assert_any_call("notifications")
    insert_call = db_client.table.return_value.insert.call_args
    inserted = insert_call[0][0]
    assert inserted["user_id"] == "user-1"
    assert inserted["title"] == "Test Title"
    assert inserted["body"] == "Test body"
    assert inserted["category"] == "info"
    assert inserted["metadata"] == {"key": "val"}


@pytest.mark.asyncio
async def test_notify_user_routes_to_telegram_when_linked(service, db_client):
    """When user has a linked Telegram, send_notification should be called."""
    _setup_insert_chain(db_client)

    mock_bot = MagicMock()
    mock_bot.send_notification = AsyncMock()
    mock_telegram_module = MagicMock()
    mock_telegram_module.get_telegram_bot_service.return_value = mock_bot

    with (
        patch.object(service, "_get_telegram_chat_id", new_callable=AsyncMock, return_value="chat-999"),
        patch.dict("sys.modules", {"chatServer.channels.telegram_bot": mock_telegram_module}),
    ):
        await service.notify_user(
            user_id="user-1",
            title="Alert",
            body="Something happened",
        )

        mock_bot.send_notification.assert_awaited_once_with("chat-999", "*Alert*\n\nSomething happened")


@pytest.mark.asyncio
async def test_notify_user_skips_telegram_when_not_linked(service, db_client):
    """When user has no linked Telegram, no telegram call should happen."""
    _setup_insert_chain(db_client)

    mock_bot = MagicMock()
    mock_bot.send_notification = AsyncMock()
    mock_telegram_module = MagicMock()
    mock_telegram_module.get_telegram_bot_service.return_value = mock_bot

    with (
        patch.object(service, "_get_telegram_chat_id", new_callable=AsyncMock, return_value=None),
        patch.dict("sys.modules", {"chatServer.channels.telegram_bot": mock_telegram_module}),
    ):
        await service.notify_user(
            user_id="user-1",
            title="Alert",
            body="Something happened",
        )

        mock_bot.send_notification.assert_not_awaited()


# ---------------------------------------------------------------------------
# get_notifications
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_notifications_returns_results(service, db_client):
    """Verify get_notifications returns data from DB query."""
    expected = [{"id": "n1", "title": "Hello"}]
    _setup_select_chain(db_client, data=expected)

    result = await service.get_notifications(user_id="user-1")

    assert result == expected
    db_client.table.assert_called_with("notifications")


@pytest.mark.asyncio
async def test_get_notifications_filters_unread_only(service, db_client):
    """When unread_only=True, an extra .eq('read', False) should be applied."""
    _setup_select_chain(db_client, data=[])

    await service.get_notifications(user_id="user-1", unread_only=True)

    chain = db_client.table.return_value.select.return_value
    # eq is called multiple times; check that ('read', False) is among them
    eq_calls = [call.args for call in chain.eq.call_args_list]
    assert ("read", False) in eq_calls


# ---------------------------------------------------------------------------
# get_unread_count
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_unread_count(service, db_client):
    """Verify unread count is returned from the count query."""
    mock_result = MagicMock(count=7)
    mock_execute = AsyncMock(return_value=mock_result)
    chain = db_client.table.return_value.select.return_value
    chain.eq.return_value = chain
    chain.execute = mock_execute

    result = await service.get_unread_count(user_id="user-1")

    assert result == 7


# ---------------------------------------------------------------------------
# mark_read
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_mark_read(service, db_client):
    """Verify mark_read calls update with correct filters."""
    _setup_update_chain(db_client)

    result = await service.mark_read(user_id="user-1", notification_id="notif-42")

    assert result is True
    db_client.table.assert_called_with("notifications")
    db_client.table.return_value.update.assert_called_once_with({"read": True})
    eq_calls = [call.args for call in db_client.table.return_value.update.return_value.eq.call_args_list]
    assert ("id", "notif-42") in eq_calls
    assert ("user_id", "user-1") in eq_calls


# ---------------------------------------------------------------------------
# mark_all_read
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_mark_all_read(service, db_client):
    """Verify mark_all_read updates unread notifications and returns count."""
    _setup_update_chain(db_client, data=[{"id": "a"}, {"id": "b"}, {"id": "c"}])

    result = await service.mark_all_read(user_id="user-1")

    assert result == 3
    db_client.table.return_value.update.assert_called_once_with({"read": True})
    eq_calls = [call.args for call in db_client.table.return_value.update.return_value.eq.call_args_list]
    assert ("user_id", "user-1") in eq_calls
    assert ("read", False) in eq_calls


# ---------------------------------------------------------------------------
# body truncation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_body_truncation_at_10000_chars(service, db_client):
    """Body longer than 10000 chars should be truncated on insert."""
    _setup_insert_chain(db_client)
    _setup_telegram_lookup(db_client, channel_id=None)

    long_body = "x" * 20000
    await service.notify_user(user_id="user-1", title="T", body=long_body)

    insert_call = db_client.table.return_value.insert.call_args
    inserted_body = insert_call[0][0]["body"]
    assert len(inserted_body) == 10000


# ---------------------------------------------------------------------------
# submit_feedback
# ---------------------------------------------------------------------------


def _setup_maybe_single_chain(db_client, data=None):
    """Set up mock chain for table(...).select(...).eq(...).maybe_single().execute()."""
    mock_result = MagicMock(data=data)
    mock_execute = AsyncMock(return_value=mock_result)
    chain = db_client.table.return_value.select.return_value
    chain.eq.return_value = chain
    chain.maybe_single.return_value = chain
    chain.execute = mock_execute
    return mock_execute


@pytest.mark.asyncio
async def test_submit_feedback_updates_notification(service, db_client):
    """Verify UPDATE is called with feedback and feedback_at when notification exists."""
    row = {"id": "notif-1", "feedback": None, "category": "info", "title": "Hello"}
    _setup_maybe_single_chain(db_client, data=row)
    update_mock = _setup_update_chain(db_client)

    with patch.dict("os.environ", {"MEMORY_SERVER_URL": "", "MEMORY_SERVER_BACKEND_KEY": ""}):
        result = await service.submit_feedback("notif-1", "useful", "user-1")

    assert result == {"status": "ok"}
    db_client.table.return_value.update.assert_called_once_with(
        {"feedback": "useful", "feedback_at": "now()"}
    )
    eq_calls = [call.args for call in db_client.table.return_value.update.return_value.eq.call_args_list]
    assert ("id", "notif-1") in eq_calls
    assert ("user_id", "user-1") in eq_calls


@pytest.mark.asyncio
async def test_submit_feedback_stores_memory(service, db_client):
    """Verify MemoryClient.call_tool is called with correct args on successful feedback."""
    row = {"id": "notif-2", "feedback": None, "category": "agent_result", "title": "Agent ran"}
    _setup_maybe_single_chain(db_client, data=row)
    _setup_update_chain(db_client)

    with (
        patch.dict("os.environ", {"MEMORY_SERVER_URL": "http://mem", "MEMORY_SERVER_BACKEND_KEY": "key123"}),
        patch("chatServer.services.notification_service.MemoryClient") as MockMemoryClient,
    ):
        mock_client = MagicMock()
        mock_client.call_tool = AsyncMock(return_value={})
        MockMemoryClient.return_value = mock_client

        result = await service.submit_feedback("notif-2", "not_useful", "user-1")

    assert result == {"status": "ok"}
    MockMemoryClient.assert_called_once_with(base_url="http://mem", backend_key="key123", user_id="user-1")
    mock_client.call_tool.assert_awaited_once()
    call_args = mock_client.call_tool.call_args
    assert call_args[0][0] == "store_memory"
    payload = call_args[0][1]
    assert payload["entity"] == "notification_preference"
    assert "not_useful" in payload["text"]
    assert "agent_result" in payload["tags"]
    assert "not_useful" in payload["tags"]


@pytest.mark.asyncio
async def test_submit_feedback_returns_409_on_duplicate(service, db_client):
    """Returns already_set when notification already has feedback."""
    row = {"id": "notif-3", "feedback": "useful", "category": "info", "title": "Hi"}
    _setup_maybe_single_chain(db_client, data=row)

    result = await service.submit_feedback("notif-3", "not_useful", "user-1")

    assert result == {"status": "already_set"}
    db_client.table.return_value.update.assert_not_called()


@pytest.mark.asyncio
async def test_submit_feedback_returns_404_when_not_found(service, db_client):
    """Returns not_found when notification doesn't exist for this user."""
    _setup_maybe_single_chain(db_client, data=None)

    result = await service.submit_feedback("notif-missing", "useful", "user-1")

    assert result == {"status": "not_found"}
    db_client.table.return_value.update.assert_not_called()


@pytest.mark.asyncio
async def test_submit_feedback_memory_failure_does_not_block(service, db_client):
    """Memory storage failure should not prevent successful feedback submission."""
    row = {"id": "notif-4", "feedback": None, "category": "info", "title": "Test"}
    _setup_maybe_single_chain(db_client, data=row)
    _setup_update_chain(db_client)

    with (
        patch.dict("os.environ", {"MEMORY_SERVER_URL": "http://mem", "MEMORY_SERVER_BACKEND_KEY": "key"}),
        patch("chatServer.services.notification_service.MemoryClient") as MockMemoryClient,
    ):
        mock_client = MagicMock()
        mock_client.call_tool = AsyncMock(side_effect=RuntimeError("memory server down"))
        MockMemoryClient.return_value = mock_client

        result = await service.submit_feedback("notif-4", "useful", "user-1")

    assert result == {"status": "ok"}
