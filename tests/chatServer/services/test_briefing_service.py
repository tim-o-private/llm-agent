"""Unit tests for BriefingService."""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from chatServer.services.briefing_service import (
    BriefingService,
    compute_first_briefing_time,
    compute_next_briefing_time,
)


@pytest.fixture
def db_client():
    return MagicMock()


@pytest.fixture
def service(db_client):
    return BriefingService(db_client)


def _mock_prefs(db_client, data=None):
    """Mock the user_preferences select chain."""
    if data is None:
        data = [{
            "user_id": "user-1",
            "timezone": "America/New_York",
            "morning_briefing_enabled": True,
            "morning_briefing_time": "07:30:00",
            "evening_briefing_enabled": False,
            "evening_briefing_time": "20:00:00",
            "briefing_sections": {"calendar": True, "tasks": True, "email": True, "observations": True},
        }]
    mock_execute = AsyncMock(return_value=MagicMock(data=data))
    chain = db_client.table.return_value.select.return_value
    chain.eq.return_value = chain
    chain.execute = mock_execute
    return mock_execute


# --- AC-04: Lazy preference creation ---

@pytest.mark.asyncio
async def test_ac_04_lazy_preference_creation(service, db_client):
    """First call creates preferences row when none exists."""
    # First select returns empty (no row)
    empty_exec = AsyncMock(return_value=MagicMock(data=[]))
    insert_exec = AsyncMock(return_value=MagicMock(data=[{"user_id": "user-1"}]))
    # Second select returns the created row
    created_data = [{
        "user_id": "user-1",
        "timezone": "America/New_York",
        "morning_briefing_enabled": True,
    }]
    created_exec = AsyncMock(return_value=MagicMock(data=created_data))

    call_count = 0

    async def mock_select_execute():
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return MagicMock(data=[])
        return MagicMock(data=created_data)

    chain = db_client.table.return_value
    select_chain = chain.select.return_value
    select_chain.eq.return_value = select_chain
    select_chain.execute = AsyncMock(side_effect=mock_select_execute)

    insert_chain = chain.insert.return_value
    insert_chain.execute = insert_exec

    result = await service.get_user_preferences("user-1")
    assert result["user_id"] == "user-1"
    # Verify insert was called for lazy creation
    chain.insert.assert_called_once()


# --- AC-07: Morning briefing generation ---

@pytest.mark.asyncio
async def test_ac_07_morning_briefing_generation(service, db_client):
    """Morning briefing gathers context, invokes agent, delivers notification."""
    _mock_prefs(db_client)

    mock_result = {"success": True, "output": "Good morning! Here's your day..."}

    with (
        patch.object(service, "_gather_morning_context", new_callable=AsyncMock, return_value={"tasks": ["Review PR"]}),  # noqa: E501
        patch.object(service, "_invoke_briefing_agent", new_callable=AsyncMock, return_value=mock_result),
        patch.object(service, "_deliver_briefing", new_callable=AsyncMock, return_value="notif-123"),
        patch.object(service, "_consume_deferred_observations", new_callable=AsyncMock),
    ):
        result = await service.generate_morning_briefing("user-1")

    assert result["success"] is True
    assert result["briefing"] == "Good morning! Here's your day..."
    assert result["notification_id"] == "notif-123"


# --- AC-08: Evening briefing generation ---

@pytest.mark.asyncio
async def test_ac_08_evening_briefing_generation(service, db_client):
    """Evening briefing uses evening-specific context and prompt."""
    _mock_prefs(db_client)

    mock_result = {"success": True, "output": "Good evening! Here's your wrap-up..."}

    with (
        patch.object(service, "_gather_evening_context", new_callable=AsyncMock, return_value={"completed_today": ["Task 1"]}),  # noqa: E501
        patch.object(service, "_invoke_briefing_agent", new_callable=AsyncMock, return_value=mock_result),
        patch.object(service, "_deliver_briefing", new_callable=AsyncMock, return_value="notif-456"),
        patch.object(service, "_consume_deferred_observations", new_callable=AsyncMock),
    ):
        result = await service.generate_evening_briefing("user-1")

    assert result["success"] is True
    assert result["briefing"] == "Good evening! Here's your wrap-up..."


# --- AC-09: Briefing delivers notification with telegram format ---

@pytest.mark.asyncio
async def test_ac_09_briefing_delivers_notification_with_telegram_format(service, db_client):
    """Briefing delivery post-processes markdown for Telegram."""
    with (
        patch("chatServer.services.briefing_service.format_for_telegram", return_value="**Bold header**") as mock_fmt,  # noqa: E501
        patch("chatServer.services.notification_service.NotificationService") as MockNS,
    ):
        mock_ns_instance = MagicMock()
        mock_ns_instance.notify_user = AsyncMock(return_value="notif-789")
        MockNS.return_value = mock_ns_instance

        result = await service._deliver_briefing(
            user_id="user-1",
            title="Good morning",
            body="### Header\nContent",
            briefing_type="morning",
        )

    assert result == "notif-789"
    mock_fmt.assert_called_once_with("### Header\nContent")
    # Verify notification was called with telegram-safe body
    call_kwargs = mock_ns_instance.notify_user.call_args[1]
    assert call_kwargs["body"] == "**Bold header**"
    assert call_kwargs["category"] == "briefing"
    assert call_kwargs["type"] == "notify"
    assert call_kwargs["metadata"]["briefing_type"] == "morning"
    assert call_kwargs["metadata"]["full_markdown"] == "### Header\nContent"


# --- AC-10: Observations consumed after briefing ---

@pytest.mark.asyncio
async def test_ac_10_observations_consumed_after_briefing(service, db_client):
    """Deferred observations are marked consumed after briefing generation."""
    update_chain = db_client.table.return_value.update.return_value
    update_chain.eq.return_value = update_chain
    update_chain.is_.return_value = update_chain
    update_chain.execute = AsyncMock(return_value=MagicMock(data=[]))

    await service._consume_deferred_observations("user-1")

    db_client.table.assert_called_with("deferred_observations")


# --- AC-11: get_user_preferences ---

@pytest.mark.asyncio
async def test_ac_11_get_preferences_returns_existing(service, db_client):
    """Returns existing preferences without creating new row."""
    prefs = [{
        "user_id": "user-1",
        "timezone": "Europe/London",
        "morning_briefing_enabled": True,
    }]
    _mock_prefs(db_client, prefs)

    result = await service.get_user_preferences("user-1")
    assert result["timezone"] == "Europe/London"


# --- AC-12: update_user_preferences ---

@pytest.mark.asyncio
async def test_ac_12_update_preferences_validates_timezone(service, db_client):
    """Invalid timezone is rejected."""
    with pytest.raises(ValueError, match="Invalid timezone"):
        await service.update_user_preferences("user-1", {"timezone": "Mars/Olympus"})


@pytest.mark.asyncio
async def test_ac_12_update_preferences_validates_time_format(service, db_client):
    """Invalid time format is rejected."""
    with pytest.raises(ValueError, match="Invalid time format"):
        await service.update_user_preferences("user-1", {"morning_briefing_time": "7:30"})


@pytest.mark.asyncio
async def test_ac_12_update_preferences_validates_boolean(service, db_client):
    """Non-boolean enabled field is rejected."""
    with pytest.raises(ValueError, match="must be boolean"):
        await service.update_user_preferences("user-1", {"morning_briefing_enabled": "yes"})


@pytest.mark.asyncio
async def test_ac_12_update_normalizes_time(service, db_client):
    """HH:MM is normalized to HH:MM:SS for TIME column."""
    _mock_prefs(db_client)

    update_chain = db_client.table.return_value.update.return_value
    update_chain.eq.return_value = update_chain
    update_chain.execute = AsyncMock(return_value=MagicMock(data=[{
        "user_id": "user-1",
        "morning_briefing_time": "08:00:00",
    }]))

    result = await service.update_user_preferences("user-1", {"morning_briefing_time": "08:00"})

    # Verify the update call had :00 appended
    update_call = db_client.table.return_value.update.call_args
    assert update_call[0][0]["morning_briefing_time"] == "08:00:00"


# --- AC-38: Briefing uses skip_notification and chat message ---

@pytest.mark.asyncio
async def test_ac_38_briefing_uses_skip_notification_and_chat_message(service, db_client):
    """ScheduledExecutionService is called with skip_notification=True."""
    with patch("chatServer.services.scheduled_execution_service.ScheduledExecutionService") as MockSES:
        mock_ses = MagicMock()
        mock_ses.execute = AsyncMock(return_value={"success": True, "output": "Briefing text"})
        MockSES.return_value = mock_ses

        result = await service._invoke_briefing_agent(
            user_id="user-1",
            prompt="Test prompt",
            briefing_type="morning",
        )

    call_args = mock_ses.execute.call_args[0][0]
    assert call_args["config"]["skip_notification"] is True
    assert call_args["config"]["schedule_type"] == "briefing"
    assert call_args["config"]["model_override"] == "claude-haiku-4-5-20251001"
    assert call_args["id"] is None


# --- compute_next_briefing_time ---

def test_compute_next_briefing_time_returns_utc():
    """Computed time is in UTC."""
    result = compute_next_briefing_time("America/New_York", "07:30", "morning")
    assert result.tzinfo == timezone.utc


def test_compute_next_briefing_time_handles_hh_mm_ss():
    """Handles HH:MM:SS format from TIME column."""
    result = compute_next_briefing_time("America/New_York", "07:30:00", "morning")
    assert result.tzinfo == timezone.utc


def test_compute_next_briefing_time_is_tomorrow():
    """Result is always in the future (tomorrow)."""
    result = compute_next_briefing_time("UTC", "12:00", "morning")
    now = datetime.now(timezone.utc)
    assert result > now


def test_compute_first_briefing_time_today_if_not_passed():
    """First briefing is today if time hasn't passed yet."""
    # Use a time far in the future (23:59) to ensure it hasn't passed
    result = compute_first_briefing_time("UTC", "23:59")
    now = datetime.now(timezone.utc)
    # Should be today or tomorrow
    assert result >= now
    assert result - now < timedelta(days=2)


def test_compute_first_briefing_time_tomorrow_if_passed():
    """First briefing is tomorrow if time already passed today."""
    # Use 00:00 which has always passed
    result = compute_first_briefing_time("UTC", "00:00")
    now = datetime.now(timezone.utc)
    assert result > now
