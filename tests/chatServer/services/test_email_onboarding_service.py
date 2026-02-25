"""Unit tests for EmailOnboardingService."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture
def mock_db_manager():
    """Mock get_database_manager with a pool that returns a connection."""
    mock_cursor = AsyncMock()
    mock_cursor.fetchone = AsyncMock(return_value=("test@example.com",))
    mock_cursor.__aenter__ = AsyncMock(return_value=mock_cursor)
    mock_cursor.__aexit__ = AsyncMock(return_value=None)

    mock_conn = AsyncMock()
    mock_conn.cursor = MagicMock(return_value=mock_cursor)
    mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_conn.__aexit__ = AsyncMock(return_value=None)

    mock_pool = MagicMock()
    mock_pool.connection = MagicMock(return_value=mock_conn)

    mock_manager = MagicMock()
    mock_manager.pool = mock_pool

    return mock_manager


@pytest.fixture
def job():
    return {
        "id": "job-uuid-1",
        "user_id": "user-uuid-1",
        "connection_id": "conn-uuid-1",
        "status": "pending",
    }


@pytest.mark.asyncio
async def test_process_job_success(job, mock_db_manager):
    """process_job returns success and calls notify_user with correct args."""
    mock_execute_result = {"success": True, "output": "Relationships identified: 3"}

    with patch(
        "chatServer.services.email_onboarding_service.get_database_manager",
        return_value=mock_db_manager,
    ), patch(
        "chatServer.services.email_onboarding_service.create_system_client",
        new_callable=AsyncMock,
        return_value=AsyncMock(),
    ), patch(
        "chatServer.services.email_onboarding_service.EmailOnboardingService._notify",
        new_callable=AsyncMock,
    ) as mock_notify, patch(
        "chatServer.services.scheduled_execution_service.ScheduledExecutionService.execute",
        new_callable=AsyncMock,
        return_value=mock_execute_result,
    ):
        from chatServer.services.email_onboarding_service import EmailOnboardingService

        service = EmailOnboardingService()
        result = await service.process_job(job)

    assert result["success"] is True
    assert "Relationships identified" in result["output"]
    mock_notify.assert_called_once()
    call_args = mock_notify.call_args
    assert call_args[0][0] == job["user_id"]


@pytest.mark.asyncio
async def test_process_job_failure(job, mock_db_manager):
    """process_job returns error dict and does not send notification when execute raises."""
    with patch(
        "chatServer.services.email_onboarding_service.get_database_manager",
        return_value=mock_db_manager,
    ), patch(
        "chatServer.services.email_onboarding_service.EmailOnboardingService._notify",
        new_callable=AsyncMock,
    ) as mock_notify, patch(
        "chatServer.services.scheduled_execution_service.ScheduledExecutionService.execute",
        new_callable=AsyncMock,
        side_effect=RuntimeError("Agent failed"),
    ):
        from chatServer.services.email_onboarding_service import EmailOnboardingService

        service = EmailOnboardingService()
        result = await service.process_job(job)

    assert result["success"] is False
    assert "Agent failed" in result["error"]
    mock_notify.assert_not_called()


@pytest.mark.asyncio
async def test_process_job_empty_inbox(job, mock_db_manager):
    """Notification is still sent even when agent reports no recent emails."""
    mock_execute_result = {"success": True, "output": "No recent emails found in this account."}

    with patch(
        "chatServer.services.email_onboarding_service.get_database_manager",
        return_value=mock_db_manager,
    ), patch(
        "chatServer.services.email_onboarding_service.EmailOnboardingService._notify",
        new_callable=AsyncMock,
    ) as mock_notify, patch(
        "chatServer.services.scheduled_execution_service.ScheduledExecutionService.execute",
        new_callable=AsyncMock,
        return_value=mock_execute_result,
    ):
        from chatServer.services.email_onboarding_service import EmailOnboardingService

        service = EmailOnboardingService()
        result = await service.process_job(job)

    assert result["success"] is True
    mock_notify.assert_called_once()


@pytest.mark.asyncio
async def test_onboarding_prompt_contains_account_email(job, mock_db_manager):
    """The prompt built for the agent includes the account email."""
    captured_schedule = {}

    async def capture_execute(schedule):
        captured_schedule.update(schedule)
        return {"success": True, "output": "Done"}

    with patch(
        "chatServer.services.email_onboarding_service.get_database_manager",
        return_value=mock_db_manager,
    ), patch(
        "chatServer.services.email_onboarding_service.EmailOnboardingService._notify",
        new_callable=AsyncMock,
    ), patch(
        "chatServer.services.scheduled_execution_service.ScheduledExecutionService.execute",
        side_effect=capture_execute,
    ):
        from chatServer.services.email_onboarding_service import EmailOnboardingService

        service = EmailOnboardingService()
        await service.process_job(job)

    assert "test@example.com" in captured_schedule.get("prompt", "")


@pytest.mark.asyncio
async def test_process_job_uses_model_override(job, mock_db_manager):
    """The synthetic schedule passed to execute() contains the model_override config."""
    captured_schedule = {}

    async def capture_execute(schedule):
        captured_schedule.update(schedule)
        return {"success": True, "output": "Done"}

    with patch(
        "chatServer.services.email_onboarding_service.get_database_manager",
        return_value=mock_db_manager,
    ), patch(
        "chatServer.services.email_onboarding_service.EmailOnboardingService._notify",
        new_callable=AsyncMock,
    ), patch(
        "chatServer.services.scheduled_execution_service.ScheduledExecutionService.execute",
        side_effect=capture_execute,
    ):
        from chatServer.services.email_onboarding_service import EmailOnboardingService

        service = EmailOnboardingService()
        await service.process_job(job)

    config = captured_schedule.get("config", {})
    assert "model_override" in config
    assert config["model_override"] == EmailOnboardingService.DEFAULT_MODEL
