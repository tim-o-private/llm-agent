"""Unit tests for reminder tools (SPEC-019 batch API)."""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from chatServer.tools.reminder_tools import CreateRemindersTool, DeleteRemindersTool, GetRemindersTool


@pytest.fixture
def create_tool():
    return CreateRemindersTool(user_id="user-123", agent_name="search_test_agent")


@pytest.fixture
def get_tool():
    return GetRemindersTool(user_id="user-123", agent_name="search_test_agent")


@pytest.fixture
def delete_tool():
    return DeleteRemindersTool(user_id="user-123", agent_name="search_test_agent")


def _future_iso(hours=1):
    return (datetime.now(timezone.utc) + timedelta(hours=hours)).isoformat()


def _past_iso(hours=1):
    return (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()


def _patch_tool_deps(mock_db, mock_service):
    return (
        patch("chatServer.database.supabase_client.get_supabase_client", new_callable=AsyncMock, return_value=mock_db),
        patch("chatServer.services.reminder_service.ReminderService", return_value=mock_service),
    )


# ---------------------------------------------------------------------------
# CreateRemindersTool (batch)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_single_reminder(create_tool):
    """Single-item batch creates a reminder and returns confirmation."""
    mock_db = MagicMock()
    mock_service = MagicMock()
    future = _future_iso(2)
    mock_service.create_reminder = AsyncMock(return_value={
        "id": "rem-1", "title": "Test reminder", "remind_at": future,
    })

    p1, p2 = _patch_tool_deps(mock_db, mock_service)
    with p1, p2:
        result = await create_tool._arun(reminders=[{"title": "Test reminder", "remind_at": future}])

    assert "Reminder set" in result
    assert "Test reminder" in result
    mock_service.create_reminder.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_multiple_reminders(create_tool):
    """Batch of 2 reminders creates both."""
    mock_db = MagicMock()
    mock_service = MagicMock()
    f1, f2 = _future_iso(1), _future_iso(3)
    mock_service.create_reminder = AsyncMock(return_value={"id": "rem-x", "title": "x", "remind_at": f1})

    p1, p2 = _patch_tool_deps(mock_db, mock_service)
    with p1, p2:
        await create_tool._arun(reminders=[
            {"title": "A", "remind_at": f1},
            {"title": "B", "remind_at": f2},
        ])

    assert mock_service.create_reminder.await_count == 2


@pytest.mark.asyncio
async def test_create_reminder_rejects_past_date(create_tool):
    """Past date in a batch item produces an error line, not a service call."""
    mock_db = MagicMock()
    mock_service = MagicMock()
    past = _past_iso(1)
    p1, p2 = _patch_tool_deps(mock_db, mock_service)
    with p1, p2:
        result = await create_tool._arun(reminders=[{"title": "Too late", "remind_at": past}])
    assert "must be in the future" in result


@pytest.mark.asyncio
async def test_create_reminder_with_recurrence(create_tool):
    """Recurrence value is passed through and reported."""
    mock_db = MagicMock()
    mock_service = MagicMock()
    future = _future_iso(2)
    mock_service.create_reminder = AsyncMock(
        return_value={"id": "rem-2", "title": "Daily standup", "remind_at": future}
    )

    p1, p2 = _patch_tool_deps(mock_db, mock_service)
    with p1, p2:
        result = await create_tool._arun(reminders=[
            {"title": "Daily standup", "remind_at": future, "recurrence": "daily"}
        ])

    assert "repeats daily" in result
    call_kwargs = mock_service.create_reminder.call_args[1]
    assert call_kwargs["recurrence"] == "daily"


@pytest.mark.asyncio
async def test_create_reminder_rejects_invalid_recurrence(create_tool):
    mock_db = MagicMock()
    mock_service = MagicMock()
    future = _future_iso(2)
    p1, p2 = _patch_tool_deps(mock_db, mock_service)
    with p1, p2:
        result = await create_tool._arun(reminders=[
            {"title": "Bad", "remind_at": future, "recurrence": "biweekly"}
        ])
    assert "invalid recurrence" in result


# ---------------------------------------------------------------------------
# GetRemindersTool
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_reminders_returns_list(get_tool):
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
        result = await get_tool._arun(limit=10)

    assert "2 upcoming reminder(s)" in result
    assert "Buy groceries" in result
    assert "Call dentist" in result
    assert "repeats monthly" in result


@pytest.mark.asyncio
async def test_get_reminders_empty(get_tool):
    mock_db = MagicMock()
    mock_service = MagicMock()
    mock_service.list_upcoming = AsyncMock(return_value=[])

    p1, p2 = _patch_tool_deps(mock_db, mock_service)
    with p1, p2:
        result = await get_tool._arun()

    assert "no upcoming reminders" in result


# ---------------------------------------------------------------------------
# DeleteRemindersTool
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_delete_reminders(delete_tool):
    mock_db = MagicMock()
    mock_service = MagicMock()
    mock_service.delete_reminders = AsyncMock(return_value=["rem-1", "rem-2"])

    p1, p2 = _patch_tool_deps(mock_db, mock_service)
    with p1, p2:
        result = await delete_tool._arun(ids=["rem-1", "rem-2"])

    assert "Deleted 2 reminder(s)" in result


@pytest.mark.asyncio
async def test_delete_reminders_not_found(delete_tool):
    mock_db = MagicMock()
    mock_service = MagicMock()
    mock_service.delete_reminders = AsyncMock(return_value=[])

    p1, p2 = _patch_tool_deps(mock_db, mock_service)
    with p1, p2:
        result = await delete_tool._arun(ids=["rem-999"])

    assert "No reminders found" in result
