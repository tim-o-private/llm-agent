"""Unit tests for ManageBriefingPreferencesTool (AC-18..AC-21, AC-28)."""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from chatServer.tools.briefing_tools import ManageBriefingPreferencesTool


@pytest.fixture
def tool():
    return ManageBriefingPreferencesTool(user_id="user-1")


# --- AC-18: Tool surfaces current briefing settings ---

@pytest.mark.asyncio
async def test_ac_18_get_returns_current_settings(tool):
    """get action returns formatted briefing preferences."""
    mock_prefs = {
        "timezone": "America/New_York",
        "morning_briefing_enabled": True,
        "morning_briefing_time": "07:30:00",
        "evening_briefing_enabled": False,
        "evening_briefing_time": "20:00:00",
        "briefing_sections": {"calendar": True, "tasks": True, "email": False},
    }

    mock_service = MagicMock()
    mock_service.get_user_preferences = AsyncMock(return_value=mock_prefs)

    with (
        patch("chatServer.database.supabase_client.get_supabase_client", new_callable=AsyncMock),
        patch("chatServer.database.scoped_client.UserScopedClient"),
        patch("chatServer.tools.briefing_tools._get_briefing_service", return_value=MagicMock(return_value=mock_service)),  # noqa: E501
    ):
        result = await tool._arun(action="get")

    assert "07:30" in result
    assert "enabled" in result
    assert "disabled" in result
    assert "America/New_York" in result
    assert "calendar, tasks" in result


@pytest.mark.asyncio
async def test_ac_18_get_strips_seconds_from_time(tool):
    """HH:MM:SS is displayed as HH:MM."""
    mock_prefs = {
        "timezone": "UTC",
        "morning_briefing_enabled": True,
        "morning_briefing_time": "08:00:00",
        "evening_briefing_enabled": True,
        "evening_briefing_time": "21:30:00",
        "briefing_sections": {},
    }

    mock_service = MagicMock()
    mock_service.get_user_preferences = AsyncMock(return_value=mock_prefs)

    with (
        patch("chatServer.database.supabase_client.get_supabase_client", new_callable=AsyncMock),
        patch("chatServer.database.scoped_client.UserScopedClient"),
        patch("chatServer.tools.briefing_tools._get_briefing_service", return_value=MagicMock(return_value=mock_service)),  # noqa: E501
    ):
        result = await tool._arun(action="get")

    assert "08:00" in result
    assert "21:30" in result
    # Should NOT contain the :00 seconds suffix in display
    assert "08:00:00" not in result
    assert "21:30:00" not in result


# --- AC-19: Tool updates preferences ---

@pytest.mark.asyncio
async def test_ac_19_update_calls_service(tool):
    """update action delegates to service and returns confirmation."""
    mock_service = MagicMock()
    mock_service.get_user_preferences = AsyncMock(return_value={
        "morning_briefing_enabled": True,
        "evening_briefing_enabled": False,
    })
    mock_service.update_user_preferences = AsyncMock(return_value={
        "morning_briefing_enabled": True,
        "evening_briefing_enabled": False,
        "timezone": "Europe/London",
    })

    mock_db_manager = MagicMock()
    mock_job_service = MagicMock()
    mock_job_service.create = AsyncMock()
    mock_job_service.fail_by_type = AsyncMock(return_value=0)

    with (
        patch("chatServer.database.supabase_client.get_supabase_client", new_callable=AsyncMock),
        patch("chatServer.database.scoped_client.UserScopedClient"),
        patch("chatServer.tools.briefing_tools._get_briefing_service", return_value=MagicMock(return_value=mock_service)),  # noqa: E501
        patch("chatServer.database.connection.get_database_manager", return_value=mock_db_manager),
        patch("chatServer.services.job_service.JobService", return_value=mock_job_service),
        patch("chatServer.services.briefing_service.compute_first_briefing_time", return_value=datetime.now(timezone.utc)),  # noqa: E501
    ):
        result = await tool._arun(action="update", preferences={"timezone": "Europe/London"})

    assert "Preferences updated" in result
    mock_service.update_user_preferences.assert_awaited_once()


# --- AC-20: Enable/disable creates/cancels jobs ---

@pytest.mark.asyncio
async def test_ac_20_enable_creates_job(tool):
    """Enabling a briefing creates a scheduled job."""
    mock_service = MagicMock()
    mock_service.get_user_preferences = AsyncMock(return_value={
        "morning_briefing_enabled": False,
        "evening_briefing_enabled": False,
    })
    mock_service.update_user_preferences = AsyncMock(return_value={
        "morning_briefing_enabled": True,
        "morning_briefing_time": "07:30:00",
        "evening_briefing_enabled": False,
        "timezone": "America/New_York",
    })

    mock_db_manager = MagicMock()
    mock_job_service = MagicMock()
    mock_job_service.create = AsyncMock(return_value="job-1")
    mock_job_service.fail_by_type = AsyncMock(return_value=0)

    scheduled_time = datetime.now(timezone.utc) + timedelta(hours=12)

    with (
        patch("chatServer.database.supabase_client.get_supabase_client", new_callable=AsyncMock),
        patch("chatServer.database.scoped_client.UserScopedClient"),
        patch("chatServer.tools.briefing_tools._get_briefing_service", return_value=MagicMock(return_value=mock_service)),  # noqa: E501
        patch("chatServer.database.connection.get_database_manager", return_value=mock_db_manager),
        patch("chatServer.services.job_service.JobService", return_value=mock_job_service),
        patch("chatServer.services.briefing_service.compute_first_briefing_time", return_value=scheduled_time),
    ):
        result = await tool._arun(
            action="update",
            preferences={"morning_briefing_enabled": True},
        )

    assert "enabled" in result.lower()
    assert "scheduled" in result.lower()
    mock_job_service.create.assert_awaited_once()
    create_kwargs = mock_job_service.create.call_args[1]
    assert create_kwargs["job_type"] == "morning_briefing"
    assert create_kwargs["user_id"] == "user-1"
    assert create_kwargs["expires_at"] == scheduled_time + timedelta(hours=4)
    assert create_kwargs["max_retries"] == 2


@pytest.mark.asyncio
async def test_ac_20_disable_cancels_jobs(tool):
    """Disabling a briefing cancels pending jobs."""
    mock_service = MagicMock()
    mock_service.get_user_preferences = AsyncMock(return_value={
        "morning_briefing_enabled": True,
        "evening_briefing_enabled": False,
    })
    mock_service.update_user_preferences = AsyncMock(return_value={
        "morning_briefing_enabled": False,
        "evening_briefing_enabled": False,
    })

    mock_db_manager = MagicMock()
    mock_job_service = MagicMock()
    mock_job_service.create = AsyncMock()
    mock_job_service.fail_by_type = AsyncMock(return_value=3)

    with (
        patch("chatServer.database.supabase_client.get_supabase_client", new_callable=AsyncMock),
        patch("chatServer.database.scoped_client.UserScopedClient"),
        patch("chatServer.tools.briefing_tools._get_briefing_service", return_value=MagicMock(return_value=mock_service)),  # noqa: E501
        patch("chatServer.database.connection.get_database_manager", return_value=mock_db_manager),
        patch("chatServer.services.job_service.JobService", return_value=mock_job_service),
    ):
        result = await tool._arun(
            action="update",
            preferences={"morning_briefing_enabled": False},
        )

    assert "disabled" in result.lower()
    assert "3" in result
    mock_job_service.fail_by_type.assert_awaited_once_with(
        "user-1", "morning_briefing", "Briefing disabled by user"
    )


# --- AC-28: Time change reschedules ---

@pytest.mark.asyncio
async def test_ac_28_time_change_reschedules(tool):
    """Changing briefing time while enabled cancels old and creates new job."""
    mock_service = MagicMock()
    mock_service.get_user_preferences = AsyncMock(return_value={
        "morning_briefing_enabled": True,
        "morning_briefing_time": "07:30:00",
        "evening_briefing_enabled": False,
        "timezone": "UTC",
    })
    mock_service.update_user_preferences = AsyncMock(return_value={
        "morning_briefing_enabled": True,
        "morning_briefing_time": "08:00:00",
        "evening_briefing_enabled": False,
        "timezone": "UTC",
    })

    mock_db_manager = MagicMock()
    mock_job_service = MagicMock()
    mock_job_service.create = AsyncMock(return_value="job-new")
    mock_job_service.fail_by_type = AsyncMock(return_value=1)

    scheduled_time = datetime.now(timezone.utc) + timedelta(hours=12)

    with (
        patch("chatServer.database.supabase_client.get_supabase_client", new_callable=AsyncMock),
        patch("chatServer.database.scoped_client.UserScopedClient"),
        patch("chatServer.tools.briefing_tools._get_briefing_service", return_value=MagicMock(return_value=mock_service)),  # noqa: E501
        patch("chatServer.database.connection.get_database_manager", return_value=mock_db_manager),
        patch("chatServer.services.job_service.JobService", return_value=mock_job_service),
        patch("chatServer.services.briefing_service.compute_first_briefing_time", return_value=scheduled_time),
    ):
        result = await tool._arun(
            action="update",
            preferences={"morning_briefing_time": "08:00"},
        )

    assert "rescheduled" in result.lower()
    mock_job_service.fail_by_type.assert_awaited_once()
    mock_job_service.create.assert_awaited_once()


# --- AC-21: Unknown action ---

@pytest.mark.asyncio
async def test_ac_21_unknown_action_returns_error(tool):
    """Unknown action returns helpful error message."""
    with (
        patch("chatServer.database.supabase_client.get_supabase_client", new_callable=AsyncMock),
        patch("chatServer.database.scoped_client.UserScopedClient"),
        patch("chatServer.tools.briefing_tools._get_briefing_service", return_value=MagicMock()),
    ):
        result = await tool._arun(action="delete")

    assert "Unknown action" in result
    assert "delete" in result


# --- Validation error handling ---

@pytest.mark.asyncio
async def test_validation_error_returned_as_string(tool):
    """ValueError from service is returned as user-friendly message."""
    mock_service = MagicMock()
    mock_service.get_user_preferences = AsyncMock(return_value={
        "morning_briefing_enabled": True,
        "evening_briefing_enabled": False,
    })
    mock_service.update_user_preferences = AsyncMock(
        side_effect=ValueError("Invalid timezone: Mars/Olympus")
    )

    with (
        patch("chatServer.database.supabase_client.get_supabase_client", new_callable=AsyncMock),
        patch("chatServer.database.scoped_client.UserScopedClient"),
        patch("chatServer.tools.briefing_tools._get_briefing_service", return_value=MagicMock(return_value=mock_service)),  # noqa: E501
    ):
        result = await tool._arun(
            action="update",
            preferences={"timezone": "Mars/Olympus"},
        )

    assert "Validation error" in result
    assert "Mars/Olympus" in result


# --- prompt_section ---

def test_prompt_section_web_channel():
    """prompt_section returns guidance for web channel."""
    result = ManageBriefingPreferencesTool.prompt_section("web")
    assert result is not None
    assert "briefing" in result.lower()


def test_prompt_section_unsupported_channel():
    """prompt_section returns None for unsupported channels."""
    result = ManageBriefingPreferencesTool.prompt_section("discord")
    assert result is None


# --- sync _run returns message ---

def test_sync_run_returns_message(tool):
    """Sync _run returns message pointing to async."""
    result = tool._run()
    assert "async" in result.lower()
