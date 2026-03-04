"""Tests for SPEC-025 notification type system (agent_only/silent/notify)."""

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


def _setup_insert_chain(db_client, notification_id="notif-123"):
    """Set up mock chain for table(...).insert(...).execute()."""
    mock_execute = AsyncMock(return_value=MagicMock(data=[{"id": notification_id}]))
    db_client.table.return_value.insert.return_value.execute = mock_execute
    return mock_execute


# ---------------------------------------------------------------------------
# agent_only: no DB, no Telegram, returns None
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_notify_agent_only_not_stored(service, db_client):
    """agent_only notifications must not be stored and must return None."""
    mock_execute = _setup_insert_chain(db_client)

    with patch.object(
        service, "_send_telegram_notification", new_callable=AsyncMock
    ) as mock_telegram:
        result = await service.notify_user(
            user_id="user-1",
            title="Heartbeat OK",
            body="All systems normal",
            type="agent_only",
        )

    assert result is None
    mock_execute.assert_not_awaited()
    mock_telegram.assert_not_awaited()


# ---------------------------------------------------------------------------
# silent: DB stored, no Telegram
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_notify_silent_stores_but_no_telegram(service, db_client):
    """silent notifications must be stored in DB but NOT sent to Telegram."""
    _setup_insert_chain(db_client, notification_id="notif-silent-1")

    with patch.object(
        service, "_send_telegram_notification", new_callable=AsyncMock
    ) as mock_telegram:
        result = await service.notify_user(
            user_id="user-1",
            title="Silent update",
            body="Stored but not pushed",
            type="silent",
        )

    assert result == "notif-silent-1"
    db_client.table.return_value.insert.assert_called_once()
    inserted = db_client.table.return_value.insert.call_args[0][0]
    assert inserted["type"] == "silent"
    mock_telegram.assert_not_awaited()


# ---------------------------------------------------------------------------
# notify: DB stored + Telegram sent
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_notify_sends_telegram(service, db_client):
    """notify type must store in DB and send to Telegram."""
    _setup_insert_chain(db_client, notification_id="notif-notify-1")

    with patch.object(
        service, "_send_telegram_notification", new_callable=AsyncMock
    ) as mock_telegram:
        result = await service.notify_user(
            user_id="user-1",
            title="Agent done",
            body="Task completed",
            type="notify",
        )

    assert result == "notif-notify-1"
    db_client.table.return_value.insert.assert_called_once()
    mock_telegram.assert_awaited_once()


# ---------------------------------------------------------------------------
# Default type is 'notify' (backward compat)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_notify_default_type_is_notify(service, db_client):
    """Calling notify_user without 'type' must behave like type='notify'."""
    _setup_insert_chain(db_client, notification_id="notif-default-1")

    with patch.object(
        service, "_send_telegram_notification", new_callable=AsyncMock
    ) as mock_telegram:
        result = await service.notify_user(
            user_id="user-1",
            title="Default",
            body="Should send telegram",
        )

    assert result == "notif-default-1"
    mock_telegram.assert_awaited_once()
    inserted = db_client.table.return_value.insert.call_args[0][0]
    assert inserted["type"] == "notify"


# ---------------------------------------------------------------------------
# silent with requires_approval and pending_action_id
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_notify_silent_stores_requires_approval(service, db_client):
    """silent + requires_approval=True + pending_action_id must be stored correctly."""
    _setup_insert_chain(db_client, notification_id="notif-approval-1")

    with patch.object(
        service, "_send_telegram_notification", new_callable=AsyncMock
    ) as mock_telegram:
        result = await service.notify_user(
            user_id="user-1",
            title="Approval needed",
            body="Please review",
            type="silent",
            requires_approval=True,
            pending_action_id="pa-uuid-999",
        )

    assert result == "notif-approval-1"
    inserted = db_client.table.return_value.insert.call_args[0][0]
    assert inserted["type"] == "silent"
    assert inserted["requires_approval"] is True
    assert inserted["pending_action_id"] == "pa-uuid-999"
    mock_telegram.assert_not_awaited()


# ---------------------------------------------------------------------------
# Heartbeat uses agent_only type
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_heartbeat_uses_agent_only_type():
    """ScheduledExecutionService._notify_user must pass type='agent_only' for heartbeats."""
    from chatServer.services.scheduled_execution_service import ScheduledExecutionService

    service = ScheduledExecutionService()
    mock_supabase = MagicMock()
    mock_notify = AsyncMock()

    with patch(
        "chatServer.services.notification_service.NotificationService"
    ) as MockNotifService:
        mock_notif_instance = MagicMock()
        mock_notif_instance.notify_user = mock_notify
        mock_notif_instance.notify_pending_actions = AsyncMock()
        MockNotifService.return_value = mock_notif_instance

        await service._notify_user(
            supabase_client=mock_supabase,
            user_id="user-1",
            agent_name="my-agent",
            result_content="HEARTBEAT_OK",
            pending_count=0,
            config={"schedule_type": "heartbeat"},
        )

    mock_notify.assert_awaited_once()
    call_kwargs = mock_notify.call_args[1]
    assert call_kwargs["type"] == "agent_only"


@pytest.mark.asyncio
async def test_scheduled_non_heartbeat_uses_notify_type():
    """ScheduledExecutionService._notify_user must pass type='notify' for non-heartbeats."""
    from chatServer.services.scheduled_execution_service import ScheduledExecutionService

    service = ScheduledExecutionService()
    mock_supabase = MagicMock()
    mock_notify = AsyncMock()

    with patch(
        "chatServer.services.notification_service.NotificationService"
    ) as MockNotifService:
        mock_notif_instance = MagicMock()
        mock_notif_instance.notify_user = mock_notify
        mock_notif_instance.notify_pending_actions = AsyncMock()
        MockNotifService.return_value = mock_notif_instance

        await service._notify_user(
            supabase_client=mock_supabase,
            user_id="user-1",
            agent_name="my-agent",
            result_content="Agent output here",
            pending_count=0,
            config={"schedule_type": "scheduled"},
        )

    mock_notify.assert_awaited_once()
    call_kwargs = mock_notify.call_args[1]
    assert call_kwargs["type"] == "notify"


# ---------------------------------------------------------------------------
# Telegram skipped for silent and agent_only
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_telegram_skips_silent_and_agent_only(service, db_client):
    """_send_telegram_notification must NOT be called for silent or agent_only types."""
    _setup_insert_chain(db_client)

    with patch.object(
        service, "_send_telegram_notification", new_callable=AsyncMock
    ) as mock_telegram:
        # silent
        await service.notify_user(
            user_id="user-1", title="T", body="B", type="silent"
        )
        # agent_only
        await service.notify_user(
            user_id="user-1", title="T", body="B", type="agent_only"
        )

    mock_telegram.assert_not_awaited()
