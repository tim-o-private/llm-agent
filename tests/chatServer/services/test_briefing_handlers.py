"""Unit tests for briefing job handlers — self-scheduling, failure recovery."""

from datetime import timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# --- AC-13: Morning handler self-schedules with expires ---

@pytest.mark.asyncio
async def test_ac_13_morning_handler_self_schedules_with_expires():
    """Morning handler self-schedules next day's job with expires_at."""
    mock_prefs = {
        "user_id": "user-1",
        "timezone": "America/New_York",
        "morning_briefing_enabled": True,
        "morning_briefing_time": "07:30:00",
        "briefing_sections": {},
    }

    mock_job_service = MagicMock()
    mock_job_service.create = AsyncMock(return_value="job-123")

    mock_briefing_service = MagicMock()
    mock_briefing_service.get_user_preferences = AsyncMock(return_value=mock_prefs)
    mock_briefing_service.generate_morning_briefing = AsyncMock(
        return_value={"success": True, "briefing": "test", "notification_id": "n-1"}
    )

    mock_db_manager = MagicMock()
    mock_db_manager.pool = MagicMock()

    job = {"input": {"user_id": "user-1"}}

    with (
        patch("chatServer.services.job_handlers.create_system_client", new_callable=AsyncMock),
        patch("chatServer.services.briefing_service.BriefingService", return_value=mock_briefing_service),
        patch("chatServer.services.job_service.JobService", return_value=mock_job_service),
        patch("chatServer.database.connection.get_database_manager", return_value=mock_db_manager),
    ):
        from chatServer.services.job_handlers import handle_morning_briefing
        result = await handle_morning_briefing(job)

    assert result["success"] is True
    mock_job_service.create.assert_awaited_once()
    create_kwargs = mock_job_service.create.call_args[1]
    assert create_kwargs["job_type"] == "morning_briefing"
    assert create_kwargs["user_id"] == "user-1"
    assert create_kwargs["expires_at"] is not None
    assert create_kwargs["expires_at"] == create_kwargs["scheduled_for"] + timedelta(hours=4)
    assert create_kwargs["max_retries"] == 2


# --- AC-14: Evening handler self-schedules ---

@pytest.mark.asyncio
async def test_ac_14_evening_handler_self_schedules():
    """Evening handler follows same self-scheduling pattern."""
    mock_prefs = {
        "user_id": "user-1",
        "timezone": "America/New_York",
        "evening_briefing_enabled": True,
        "evening_briefing_time": "20:00:00",
        "briefing_sections": {},
    }

    mock_job_service = MagicMock()
    mock_job_service.create = AsyncMock(return_value="job-456")

    mock_briefing_service = MagicMock()
    mock_briefing_service.get_user_preferences = AsyncMock(return_value=mock_prefs)
    mock_briefing_service.generate_evening_briefing = AsyncMock(
        return_value={"success": True, "briefing": "test", "notification_id": "n-2"}
    )

    mock_db_manager = MagicMock()
    mock_db_manager.pool = MagicMock()

    job = {"input": {"user_id": "user-1"}}

    with (
        patch("chatServer.services.job_handlers.create_system_client", new_callable=AsyncMock),
        patch("chatServer.services.briefing_service.BriefingService", return_value=mock_briefing_service),
        patch("chatServer.services.job_service.JobService", return_value=mock_job_service),
        patch("chatServer.database.connection.get_database_manager", return_value=mock_db_manager),
    ):
        from chatServer.services.job_handlers import handle_evening_briefing
        result = await handle_evening_briefing(job)

    assert result["success"] is True
    mock_job_service.create.assert_awaited_once()
    create_kwargs = mock_job_service.create.call_args[1]
    assert create_kwargs["job_type"] == "evening_briefing"


# --- AC-16: Failed briefing schedules next day ---

@pytest.mark.asyncio
async def test_ac_16_failed_briefing_schedules_next_day():
    """When generation fails, next occurrence is still scheduled."""
    mock_prefs = {
        "user_id": "user-1",
        "timezone": "UTC",
        "morning_briefing_enabled": True,
        "morning_briefing_time": "07:30:00",
        "briefing_sections": {},
    }

    mock_job_service = MagicMock()
    mock_job_service.create = AsyncMock(return_value="job-789")

    mock_briefing_service = MagicMock()
    mock_briefing_service.get_user_preferences = AsyncMock(return_value=mock_prefs)
    mock_briefing_service.generate_morning_briefing = AsyncMock(
        side_effect=RuntimeError("LLM API error")
    )

    mock_db_manager = MagicMock()
    mock_db_manager.pool = MagicMock()

    job = {"input": {"user_id": "user-1"}}

    with (
        patch("chatServer.services.job_handlers.create_system_client", new_callable=AsyncMock),
        patch("chatServer.services.briefing_service.BriefingService", return_value=mock_briefing_service),
        patch("chatServer.services.job_service.JobService", return_value=mock_job_service),
        patch("chatServer.database.connection.get_database_manager", return_value=mock_db_manager),
    ):
        from chatServer.services.job_handlers import handle_morning_briefing

        with pytest.raises(RuntimeError, match="LLM API error"):
            await handle_morning_briefing(job)

    mock_job_service.create.assert_awaited_once()
    create_kwargs = mock_job_service.create.call_args[1]
    assert create_kwargs["job_type"] == "morning_briefing"
    assert create_kwargs["expires_at"] is not None


# --- AC-17: Bootstrap creates missing jobs ---

@pytest.mark.asyncio
async def test_ac_17_bootstrap_creates_missing_jobs():
    """Bootstrap creates briefing jobs for users with enabled briefings."""
    from chatServer.services.background_tasks import BackgroundTaskService

    service = BackgroundTaskService()

    mock_job_service = MagicMock()
    mock_job_service.create = AsyncMock(return_value="job-bootstrap")
    mock_job_service.pool = MagicMock()
    service._job_service = mock_job_service

    mock_db_client = MagicMock()
    select_chain = mock_db_client.table.return_value.select.return_value
    select_chain.or_.return_value = select_chain
    select_chain.execute = AsyncMock(return_value=MagicMock(data=[{
        "user_id": "user-1",
        "timezone": "UTC",
        "morning_briefing_enabled": True,
        "morning_briefing_time": "07:30:00",
        "evening_briefing_enabled": False,
        "evening_briefing_time": "20:00:00",
    }]))

    with (
        patch("chatServer.services.background_tasks.create_system_client", new_callable=AsyncMock, return_value=mock_db_client),  # noqa: E501
        patch.object(service, "_check_pending_briefing_job", new_callable=AsyncMock, return_value=False),
    ):
        await service._bootstrap_briefing_jobs()

    mock_job_service.create.assert_awaited_once()
    create_kwargs = mock_job_service.create.call_args[1]
    assert create_kwargs["job_type"] == "morning_briefing"
    assert create_kwargs["user_id"] == "user-1"
    assert create_kwargs["expires_at"] is not None


@pytest.mark.asyncio
async def test_ac_17_bootstrap_skips_existing_jobs():
    """Bootstrap doesn't create duplicates when pending jobs exist."""
    from chatServer.services.background_tasks import BackgroundTaskService

    service = BackgroundTaskService()

    mock_job_service = MagicMock()
    mock_job_service.create = AsyncMock()
    mock_job_service.pool = MagicMock()
    service._job_service = mock_job_service

    mock_db_client = MagicMock()
    select_chain = mock_db_client.table.return_value.select.return_value
    select_chain.or_.return_value = select_chain
    select_chain.execute = AsyncMock(return_value=MagicMock(data=[{
        "user_id": "user-1",
        "timezone": "UTC",
        "morning_briefing_enabled": True,
        "morning_briefing_time": "07:30:00",
        "evening_briefing_enabled": False,
        "evening_briefing_time": "20:00:00",
    }]))

    with (
        patch("chatServer.services.background_tasks.create_system_client", new_callable=AsyncMock, return_value=mock_db_client),  # noqa: E501
        patch.object(service, "_check_pending_briefing_job", new_callable=AsyncMock, return_value=True),
    ):
        await service._bootstrap_briefing_jobs()

    mock_job_service.create.assert_not_awaited()


# --- AC-35: fail_by_type cancels pending jobs ---

@pytest.mark.asyncio
async def test_ac_35_fail_by_type_cancels_pending_jobs():
    """fail_by_type marks all pending jobs as failed."""
    from chatServer.services.job_service import JobService

    mock_pool = MagicMock()
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.execute = AsyncMock()
    mock_cursor.fetchall = AsyncMock(return_value=[("job-1",), ("job-2",)])

    mock_cursor_cm = MagicMock()
    mock_cursor_cm.__aenter__ = AsyncMock(return_value=mock_cursor)
    mock_cursor_cm.__aexit__ = AsyncMock(return_value=None)
    mock_conn.cursor = MagicMock(return_value=mock_cursor_cm)

    mock_conn_cm = MagicMock()
    mock_conn_cm.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_conn_cm.__aexit__ = AsyncMock(return_value=None)
    mock_pool.connection = MagicMock(return_value=mock_conn_cm)

    job_service = JobService(mock_pool)
    count = await job_service.fail_by_type("user-1", "morning_briefing", "Disabled by user")

    assert count == 2
    mock_cursor.execute.assert_awaited_once()
    call_args = mock_cursor.execute.call_args
    assert "status = 'failed'" in call_args[0][0]
    assert call_args[0][1] == ("Disabled by user", "user-1", "morning_briefing")
