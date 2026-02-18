"""Unit tests for ReminderService."""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from chatServer.services.reminder_service import ReminderService


@pytest.fixture
def db_client():
    """Create a mock Supabase db client with method chaining support."""
    return MagicMock()


@pytest.fixture
def service(db_client):
    return ReminderService(db_client)


def _setup_insert_chain(db_client, data=None):
    """Set up mock chain for table(...).insert(...).execute()."""
    if data is None:
        data = [{"id": "rem-1", "title": "Test", "user_id": "user-1", "remind_at": "2026-03-01T10:00:00+00:00"}]
    mock_execute = AsyncMock(return_value=MagicMock(data=data))
    db_client.table.return_value.insert.return_value.execute = mock_execute
    return mock_execute


def _setup_select_chain(db_client, data=None):
    """Set up mock chain for table(...).select(...).eq(...).order(...).limit(...).execute()."""
    if data is None:
        data = []
    mock_execute = AsyncMock(return_value=MagicMock(data=data))
    chain = db_client.table.return_value.select.return_value
    chain.eq.return_value = chain
    chain.lte.return_value = chain
    chain.order.return_value = chain
    chain.limit.return_value = chain
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


# ---------------------------------------------------------------------------
# get_due_reminders
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_due_reminders_returns_past_due_only(service, db_client):
    """Verify get_due_reminders queries for pending + remind_at <= now."""
    past_reminder = {
        "id": "rem-due",
        "title": "Overdue",
        "status": "pending",
        "remind_at": (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat(),
    }
    _setup_select_chain(db_client, data=[past_reminder])

    result = await service.get_due_reminders()

    assert len(result) == 1
    assert result[0]["id"] == "rem-due"
    db_client.table.assert_called_with("reminders")
    chain = db_client.table.return_value.select.return_value
    eq_calls = [call.args for call in chain.eq.call_args_list]
    assert ("status", "pending") in eq_calls


# ---------------------------------------------------------------------------
# mark_sent
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_mark_sent_updates_status(service, db_client):
    """Verify mark_sent sets status='sent'."""
    _setup_update_chain(db_client)

    await service.mark_sent("rem-1")

    db_client.table.assert_called_with("reminders")
    update_call = db_client.table.return_value.update.call_args[0][0]
    assert update_call["status"] == "sent"

    eq_calls = [call.args for call in db_client.table.return_value.update.return_value.eq.call_args_list]
    assert ("id", "rem-1") in eq_calls


# ---------------------------------------------------------------------------
# dismiss
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_dismiss_updates_status(service, db_client):
    """Verify dismiss sets status='dismissed' scoped to user."""
    _setup_update_chain(db_client)

    await service.dismiss(user_id="user-1", reminder_id="rem-1")

    db_client.table.assert_called_with("reminders")
    update_call = db_client.table.return_value.update.call_args[0][0]
    assert update_call["status"] == "dismissed"

    eq_calls = [call.args for call in db_client.table.return_value.update.return_value.eq.call_args_list]
    assert ("id", "rem-1") in eq_calls
    assert ("user_id", "user-1") in eq_calls


# ---------------------------------------------------------------------------
# handle_recurrence
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_handle_recurrence_creates_next_daily(service, db_client):
    """Verify daily recurrence creates a reminder +1 day ahead."""
    _setup_insert_chain(db_client)
    original_dt = datetime(2026, 3, 1, 10, 0, tzinfo=timezone.utc)
    reminder = {
        "id": "rem-rec",
        "user_id": "user-1",
        "title": "Daily standup",
        "body": None,
        "remind_at": original_dt.isoformat(),
        "recurrence": "daily",
        "created_by": "agent",
        "agent_name": "assistant",
    }

    await service.handle_recurrence(reminder)

    insert_call = db_client.table.return_value.insert.call_args[0][0]
    next_dt = datetime.fromisoformat(insert_call["remind_at"])
    expected = original_dt + timedelta(days=1)
    assert next_dt == expected
    assert insert_call["title"] == "Daily standup"
    assert insert_call["recurrence"] == "daily"


@pytest.mark.asyncio
async def test_handle_recurrence_creates_next_weekly(service, db_client):
    """Verify weekly recurrence creates a reminder +7 days ahead."""
    _setup_insert_chain(db_client)
    original_dt = datetime(2026, 3, 1, 10, 0, tzinfo=timezone.utc)
    reminder = {
        "id": "rem-wk",
        "user_id": "user-1",
        "title": "Weekly review",
        "body": None,
        "remind_at": original_dt.isoformat(),
        "recurrence": "weekly",
        "created_by": "user",
        "agent_name": None,
    }

    await service.handle_recurrence(reminder)

    insert_call = db_client.table.return_value.insert.call_args[0][0]
    next_dt = datetime.fromisoformat(insert_call["remind_at"])
    expected = original_dt + timedelta(weeks=1)
    assert next_dt == expected


@pytest.mark.asyncio
async def test_handle_recurrence_noop_for_non_recurring(service, db_client):
    """Verify handle_recurrence does nothing when recurrence is None."""
    reminder = {
        "id": "rem-once",
        "user_id": "user-1",
        "title": "One-time",
        "remind_at": "2026-03-01T10:00:00+00:00",
        "recurrence": None,
    }

    await service.handle_recurrence(reminder)

    # No insert should have been called
    db_client.table.return_value.insert.assert_not_called()
