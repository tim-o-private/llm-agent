"""Unit tests for JobService."""

import json
from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock, call

import pytest

from chatServer.services.job_service import JobService


def _make_pool(fetchone_return=None, fetchall_return=None):
    """Build a mock psycopg pool."""
    mock_cursor = AsyncMock()
    mock_cursor.fetchone = AsyncMock(return_value=fetchone_return)
    mock_cursor.fetchall = AsyncMock(return_value=fetchall_return or [])
    mock_cursor.description = []
    mock_cursor.rowcount = 0
    mock_cursor.__aenter__ = AsyncMock(return_value=mock_cursor)
    mock_cursor.__aexit__ = AsyncMock(return_value=None)

    mock_conn = AsyncMock()
    mock_conn.cursor = MagicMock(return_value=mock_cursor)
    mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_conn.__aexit__ = AsyncMock(return_value=None)

    mock_pool = MagicMock()
    mock_pool.connection = MagicMock(return_value=mock_conn)

    return mock_pool, mock_cursor


@pytest.mark.asyncio
async def test_create_returns_uuid():
    """create() inserts a pending job and returns its UUID string."""
    import uuid
    new_id = uuid.uuid4()
    pool, cursor = _make_pool(fetchone_return=(new_id,))

    service = JobService(pool)
    result = await service.create(
        job_type="email_processing",
        input={"connection_id": "conn-1"},
        user_id="user-1",
    )

    assert result == str(new_id)
    cursor.execute.assert_called_once()
    sql, params = cursor.execute.call_args[0]
    assert "INSERT INTO jobs" in sql
    assert params[0] == "user-1"
    assert params[1] == "email_processing"
    assert json.loads(params[2]) == {"connection_id": "conn-1"}


@pytest.mark.asyncio
async def test_claim_next_returns_job_dict():
    """claim_next() returns a dict with expected keys when a job is available."""
    import uuid
    job_id = uuid.uuid4()

    pool, cursor = _make_pool()

    # First fetchone: SELECT returns a row (job found)
    # Second fetchone: UPDATE RETURNING returns the claimed job
    claimed_row = (job_id, "user-1", "email_processing", "claimed", {}, 0, 0, 3, None, None, None, None, None)
    cursor.fetchone = AsyncMock(side_effect=[
        (job_id,),   # SELECT returns row with just id for the first query check
        claimed_row, # UPDATE RETURNING
    ])
    cursor.description = [
        (col,) for col in [
            "id", "user_id", "job_type", "status", "input", "priority",
            "retry_count", "max_retries", "scheduled_for", "expires_at",
            "created_at", "claimed_at", "updated_at",
        ]
    ]

    service = JobService(pool)
    result = await service.claim_next()

    assert result is not None
    assert result["job_type"] == "email_processing"
    assert result["status"] == "claimed"

    # Two execute calls: SELECT FOR UPDATE + UPDATE RETURNING
    assert cursor.execute.call_count == 2
    first_sql = cursor.execute.call_args_list[0][0][0]
    assert "FOR UPDATE SKIP LOCKED" in first_sql
    second_sql = cursor.execute.call_args_list[1][0][0]
    assert "status = 'claimed'" in second_sql


@pytest.mark.asyncio
async def test_claim_next_no_jobs_returns_none():
    """claim_next() returns None when no jobs are available."""
    pool, cursor = _make_pool(fetchone_return=None)

    service = JobService(pool)
    result = await service.claim_next()

    assert result is None
    # Only the SELECT is called, no UPDATE
    assert cursor.execute.call_count == 1


@pytest.mark.asyncio
async def test_claim_next_filters_by_job_types():
    """claim_next(job_types=...) passes types list to WHERE clause."""
    pool, cursor = _make_pool(fetchone_return=None)

    service = JobService(pool)
    await service.claim_next(job_types=["email_processing", "reminder_delivery"])

    sql, params = cursor.execute.call_args[0]
    assert "ANY(%s)" in sql
    assert params == (["email_processing", "reminder_delivery"],)


@pytest.mark.asyncio
async def test_mark_running_sets_started_at():
    """mark_running() transitions claimed -> running."""
    pool, cursor = _make_pool()

    service = JobService(pool)
    await service.mark_running("job-1")

    cursor.execute.assert_called_once()
    sql, params = cursor.execute.call_args[0]
    assert "status = 'running'" in sql
    assert "started_at = NOW()" in sql
    assert params == ("job-1",)


@pytest.mark.asyncio
async def test_complete_sets_output_and_completed_at():
    """complete() transitions running -> complete with output and completed_at."""
    pool, cursor = _make_pool()

    service = JobService(pool)
    await service.complete("job-1", {"result": "ok"})

    cursor.execute.assert_called_once()
    sql, params = cursor.execute.call_args[0]
    assert "status = 'complete'" in sql
    assert "completed_at = NOW()" in sql
    assert json.loads(params[0]) == {"result": "ok"}
    assert params[1] == "job-1"


@pytest.mark.asyncio
async def test_fail_with_retries_requeues():
    """fail() requeues with backoff when retry_count < max_retries."""
    pool, cursor = _make_pool()
    cursor.fetchone = AsyncMock(return_value=(1, 3))  # retry_count=1, max_retries=3

    service = JobService(pool)
    await service.fail("job-1", "something went wrong", should_retry=True)

    assert cursor.execute.call_count == 2
    update_sql = cursor.execute.call_args_list[1][0][0]
    update_params = cursor.execute.call_args_list[1][0][1]
    assert "status = 'pending'" in update_sql
    assert "retry_count = retry_count + 1" in update_sql
    assert "scheduled_for = NOW() + %s" in update_sql
    # backoff for retry_count=1: min(30 * 2^1, 900) = 60 seconds
    assert isinstance(update_params[0], timedelta)
    assert update_params[0].total_seconds() == 60.0
    assert update_params[1] == "something went wrong"


@pytest.mark.asyncio
async def test_fail_exhausted_stays_failed():
    """fail() marks permanently failed when retry_count >= max_retries."""
    pool, cursor = _make_pool()
    cursor.fetchone = AsyncMock(return_value=(3, 3))  # retry_count == max_retries

    service = JobService(pool)
    await service.fail("job-1", "too many errors", should_retry=True)

    update_sql = cursor.execute.call_args_list[1][0][0]
    assert "status = 'failed'" in update_sql
    assert "completed_at = NOW()" in update_sql


@pytest.mark.asyncio
async def test_fail_no_retry_stays_failed():
    """fail(should_retry=False) marks permanently failed immediately."""
    pool, cursor = _make_pool()
    cursor.fetchone = AsyncMock(return_value=(0, 3))  # retry_count=0, max_retries=3

    service = JobService(pool)
    await service.fail("job-1", "explicit no retry", should_retry=False)

    update_sql = cursor.execute.call_args_list[1][0][0]
    assert "status = 'failed'" in update_sql
    # Should NOT contain retry logic
    assert "retry_count = retry_count + 1" not in update_sql


@pytest.mark.asyncio
async def test_expire_stale_calls_db_function():
    """expire_stale() calls expire_stale_jobs() and returns the count."""
    pool, cursor = _make_pool(fetchone_return=(5,))

    service = JobService(pool)
    result = await service.expire_stale()

    assert result == 5
    cursor.execute.assert_called_once()
    sql = cursor.execute.call_args[0][0]
    assert "expire_stale_jobs()" in sql


@pytest.mark.asyncio
async def test_backoff_formula():
    """Verify backoff: min(30 * 2^retry_count, 900) seconds."""
    pool, cursor = _make_pool()

    async def run_fail_at_retry(retry_count):
        cursor.fetchone = AsyncMock(return_value=(retry_count, 99))
        cursor.execute.reset_mock()
        service = JobService(pool)
        await service.fail("job-1", "err", should_retry=True)
        return cursor.execute.call_args_list[1][0][1][0].total_seconds()

    assert await run_fail_at_retry(0) == 30.0   # min(30 * 1, 900)
    assert await run_fail_at_retry(1) == 60.0   # min(30 * 2, 900)
    assert await run_fail_at_retry(2) == 120.0  # min(30 * 4, 900)
    assert await run_fail_at_retry(3) == 240.0  # min(30 * 8, 900)
    assert await run_fail_at_retry(4) == 480.0  # min(30 * 16, 900)
    assert await run_fail_at_retry(5) == 900.0  # min(30 * 32, 900) = min(960, 900) = 900
