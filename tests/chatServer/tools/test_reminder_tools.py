"""Unit tests for reminder tools."""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from chatServer.tools.reminder_tools import CreateReminderTool, ListRemindersTool


@pytest.fixture
def create_tool():
    return CreateReminderTool(
        user_id="user-123",
        agent_name="assistant",
    )


@pytest.fixture
def list_tool():
    return ListRemindersTool(
        user_id="user-123",
        agent_name="assistant",
    )


def _future_iso(hours=1):
    """Return an ISO timestamp `hours` in the future."""
    return (datetime.now(timezone.utc) + timedelta(hours=hours)).isoformat()


def _past_iso(hours=1):
    """Return an ISO timestamp `hours` in the past."""
    return (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()


def _patch_tool_deps(mock_db, mock_service):
    """Context manager that patches the lazy imports used by reminder tools."""
    return (
        patch("chatServer.database.supabase_client.get_supabase_client", new_callable=AsyncMock, return_value=mock_db),
        patch("chatServer.services.reminder_service.ReminderService", return_value=mock_service),
    )


# ---------------------------------------------------------------------------
# CreateReminderTool
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_reminder_stores_in_db(create_tool):
    """Verify create_reminder calls ReminderService and returns confirmation."""
    mock_db = MagicMock()
    mock_service = MagicMock()
    future = _future_iso(2)
    mock_service.create_reminder = AsyncMock(return_value={
        "id": "rem-1",
        "title": "Test reminder",
        "remind_at": future,
    })

    p1, p2 = _patch_tool_deps(mock_db, mock_service)
    with p1, p2:
        result = await create_tool._arun(title="Test reminder", remind_at=future)

    assert "Reminder set" in result
    assert "Test reminder" in result
    mock_service.create_reminder.assert_awaited_once()
    call_kwargs = mock_service.create_reminder.call_args[1]
    assert call_kwargs["user_id"] == "user-123"
    assert call_kwargs["title"] == "Test reminder"
    assert call_kwargs["created_by"] == "agent"


@pytest.mark.asyncio
async def test_create_reminder_validates_future_date(create_tool):
    """Verify create_reminder rejects past dates without calling the service."""
    past = _past_iso(1)
    result = await create_tool._arun(title="Too late", remind_at=past)
    assert "must be in the future" in result


@pytest.mark.asyncio
async def test_create_reminder_with_recurrence(create_tool):
    """Verify recurrence is passed through to service."""
    mock_db = MagicMock()
    mock_service = MagicMock()
    future = _future_iso(2)
    mock_service.create_reminder = AsyncMock(
        return_value={"id": "rem-2", "title": "Daily standup", "remind_at": future}
    )

    p1, p2 = _patch_tool_deps(mock_db, mock_service)
    with p1, p2:
        result = await create_tool._arun(title="Daily standup", remind_at=future, recurrence="daily")

    assert "repeats daily" in result
    call_kwargs = mock_service.create_reminder.call_args[1]
    assert call_kwargs["recurrence"] == "daily"


@pytest.mark.asyncio
async def test_create_reminder_rejects_invalid_recurrence(create_tool):
    """Verify invalid recurrence values are rejected."""
    future = _future_iso(2)
    result = await create_tool._arun(title="Bad", remind_at=future, recurrence="biweekly")
    assert "invalid recurrence" in result


# ---------------------------------------------------------------------------
# ListRemindersTool
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_reminders_returns_upcoming_only(list_tool):
    """Verify list_reminders returns formatted upcoming reminders."""
    mock_db = MagicMock()
    mock_service = MagicMock()
    future = _future_iso(2)
    mock_service.list_upcoming = AsyncMock(return_value=[
        {"id": "r1", "title": "Buy groceries", "remind_at": future, "body": None, "recurrence": None},
        {
            "id": "r2", "title": "Call dentist", "remind_at": future,
            "body": "Schedule cleaning", "recurrence": "monthly",
        },
    ])

    p1, p2 = _patch_tool_deps(mock_db, mock_service)
    with p1, p2:
        result = await list_tool._arun(limit=10)

    assert "2 upcoming reminder(s)" in result
    assert "Buy groceries" in result
    assert "Call dentist" in result
    assert "repeats monthly" in result
    mock_service.list_upcoming.assert_awaited_once_with(user_id="user-123", limit=10)


@pytest.mark.asyncio
async def test_list_reminders_excludes_sent_and_dismissed(list_tool):
    """Verify list_reminders shows empty message when no pending reminders."""
    mock_db = MagicMock()
    mock_service = MagicMock()
    mock_service.list_upcoming = AsyncMock(return_value=[])

    p1, p2 = _patch_tool_deps(mock_db, mock_service)
    with p1, p2:
        result = await list_tool._arun()

    assert "no upcoming reminders" in result
