"""Unit tests for email processing background task loop."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from chatServer.services.background_tasks import BackgroundTaskService


def _make_db_manager(rows=None):
    """Build a mock db_manager that returns given rows from fetchall."""
    mock_cursor = AsyncMock()
    mock_cursor.fetchall = AsyncMock(return_value=rows or [])
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

    return mock_manager, mock_cursor


@pytest.mark.asyncio
async def test_check_email_processing_jobs_picks_up_pending():
    """When a pending job exists, EmailOnboardingService.process_job is called."""
    pending_row = ("job-1", "user-1", "conn-1", "pending")
    mock_db, _ = _make_db_manager(rows=[pending_row])

    service = BackgroundTaskService()

    with patch(
        "chatServer.services.background_tasks.get_database_manager",
        return_value=mock_db,
    ), patch(
        "chatServer.services.background_tasks.BackgroundTaskService._process_email_job",
        new_callable=AsyncMock,
    ) as mock_process, patch("asyncio.sleep", new_callable=AsyncMock):

        # Run one iteration by manually calling the inner loop logic
        mock_db.pool.connection.return_value.__aenter__.return_value.cursor.return_value.__aenter__.return_value.fetchall = AsyncMock(  # noqa: E501
            return_value=[pending_row]
        )

        # Simulate one cycle (sleep + body) by patching sleep to raise after first call
        call_count = 0

        async def sleep_then_stop(seconds):
            nonlocal call_count
            call_count += 1
            if call_count > 1:
                raise asyncio.CancelledError()

        with patch("asyncio.sleep", side_effect=sleep_then_stop):
            try:
                await service.check_email_processing_jobs()
            except asyncio.CancelledError:
                pass

    mock_process.assert_called_once()
    call_job = mock_process.call_args[0][0]
    assert call_job["id"] == "job-1"
    assert call_job["user_id"] == "user-1"


@pytest.mark.asyncio
async def test_check_email_processing_jobs_updates_status():
    """Status transitions: pending → processing → complete."""
    execute_calls = []

    mock_cursor = AsyncMock()
    mock_cursor.__aenter__ = AsyncMock(return_value=mock_cursor)
    mock_cursor.__aexit__ = AsyncMock(return_value=None)

    async def capture_execute(sql, params=None):
        execute_calls.append((sql.strip(), params))

    mock_cursor.execute = capture_execute
    mock_cursor.fetchall = AsyncMock(return_value=[("job-1", "user-1", "conn-1", "pending")])

    mock_conn = AsyncMock()
    mock_conn.cursor = MagicMock(return_value=mock_cursor)
    mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_conn.__aexit__ = AsyncMock(return_value=None)

    mock_pool = MagicMock()
    mock_pool.connection = MagicMock(return_value=mock_conn)

    mock_manager = MagicMock()
    mock_manager.pool = mock_pool

    mock_process_result = {"success": True, "output": "Relationships identified: 2"}

    with patch(
        "chatServer.services.background_tasks.get_database_manager",
        return_value=mock_manager,
    ), patch(
        "chatServer.services.email_onboarding_service.EmailOnboardingService.process_job",
        new_callable=AsyncMock,
        return_value=mock_process_result,
    ):
        from chatServer.services.background_tasks import BackgroundTaskService

        svc = BackgroundTaskService()
        job = {"id": "job-1", "user_id": "user-1", "connection_id": "conn-1", "status": "pending"}
        await svc._process_email_job(job)

    sqls = [call[0] for call in execute_calls]
    assert any("processing" in sql for sql in sqls), "Should UPDATE to processing"
    assert any("complete" in sql for sql in sqls), "Should UPDATE to complete"


@pytest.mark.asyncio
async def test_check_email_processing_jobs_handles_failure():
    """When process_job raises, status is set to 'failed' with error_message."""
    execute_calls = []

    mock_cursor = AsyncMock()
    mock_cursor.__aenter__ = AsyncMock(return_value=mock_cursor)
    mock_cursor.__aexit__ = AsyncMock(return_value=None)

    async def capture_execute(sql, params=None):
        execute_calls.append((sql.strip(), params))

    mock_cursor.execute = capture_execute

    mock_conn = AsyncMock()
    mock_conn.cursor = MagicMock(return_value=mock_cursor)
    mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_conn.__aexit__ = AsyncMock(return_value=None)

    mock_pool = MagicMock()
    mock_pool.connection = MagicMock(return_value=mock_conn)

    mock_manager = MagicMock()
    mock_manager.pool = mock_pool

    with patch(
        "chatServer.services.background_tasks.get_database_manager",
        return_value=mock_manager,
    ), patch(
        "chatServer.services.email_onboarding_service.EmailOnboardingService.process_job",
        new_callable=AsyncMock,
        side_effect=RuntimeError("LLM call failed"),
    ):
        from chatServer.services.background_tasks import BackgroundTaskService

        svc = BackgroundTaskService()
        job = {"id": "job-1", "user_id": "user-1", "connection_id": "conn-1", "status": "pending"}
        await svc._process_email_job(job)

    sqls_and_params = execute_calls
    failed_updates = [
        (sql, params)
        for sql, params in sqls_and_params
        if "failed" in sql
    ]
    assert failed_updates, "Should have at least one UPDATE to failed"
    # Verify error message is passed
    _, params = failed_updates[-1]
    assert params is not None
    assert "LLM call failed" in str(params)
