"""Unit tests for JobRunnerService."""

from unittest.mock import AsyncMock, MagicMock, call

import pytest

from chatServer.services.job_runner_service import JobRunnerService


def _make_job_service():
    """Build a mock JobService."""
    svc = MagicMock()
    svc.claim_next = AsyncMock(return_value=None)
    svc.mark_running = AsyncMock()
    svc.complete = AsyncMock()
    svc.fail = AsyncMock()
    svc.expire_stale = AsyncMock(return_value=0)
    return svc


def _make_job(job_type="email_processing"):
    return {
        "id": "job-1",
        "job_type": job_type,
        "user_id": "user-1",
        "input": {"connection_id": "conn-1"},
    }


def test_register_handler():
    """register_handler stores the handler callable."""
    job_svc = _make_job_service()
    runner = JobRunnerService(job_svc)

    handler = AsyncMock()
    runner.register_handler("email_processing", handler)

    assert runner._handlers["email_processing"] is handler


@pytest.mark.asyncio
async def test_dispatch_calls_correct_handler():
    """_dispatch routes to the correct handler based on job_type."""
    job_svc = _make_job_service()
    runner = JobRunnerService(job_svc)

    handler = AsyncMock(return_value={"ok": True})
    runner.register_handler("email_processing", handler)

    job = _make_job("email_processing")
    await runner._dispatch(job)

    handler.assert_called_once_with(job)


@pytest.mark.asyncio
async def test_dispatch_unknown_type_fails_job():
    """_dispatch with no registered handler calls fail(should_retry=False)."""
    job_svc = _make_job_service()
    runner = JobRunnerService(job_svc)
    # No handler registered for this type

    job = _make_job("unknown_type")
    await runner._dispatch(job)

    job_svc.fail.assert_called_once()
    _job_id, error, should_retry = (
        job_svc.fail.call_args[0][0],
        job_svc.fail.call_args[0][1],
        job_svc.fail.call_args[1].get("should_retry", True),
    )
    assert _job_id == "job-1"
    assert "unknown_type" in error
    assert should_retry is False
    job_svc.mark_running.assert_not_called()


@pytest.mark.asyncio
async def test_dispatch_handler_exception_fails_with_retry():
    """_dispatch when handler raises calls fail(should_retry=True)."""
    job_svc = _make_job_service()
    runner = JobRunnerService(job_svc)

    handler = AsyncMock(side_effect=RuntimeError("handler blew up"))
    runner.register_handler("email_processing", handler)

    job = _make_job("email_processing")
    await runner._dispatch(job)

    job_svc.fail.assert_called_once()
    assert job_svc.fail.call_args[1]["should_retry"] is True
    assert "handler blew up" in job_svc.fail.call_args[0][1]


@pytest.mark.asyncio
async def test_dispatch_marks_running_before_handler():
    """_dispatch calls mark_running before invoking the handler."""
    job_svc = _make_job_service()
    runner = JobRunnerService(job_svc)

    call_order = []
    job_svc.mark_running.side_effect = lambda jid: call_order.append("mark_running")
    handler = AsyncMock(side_effect=lambda j: call_order.append("handler"))
    runner.register_handler("email_processing", handler)

    job = _make_job("email_processing")
    await runner._dispatch(job)

    assert call_order.index("mark_running") < call_order.index("handler")


@pytest.mark.asyncio
async def test_dispatch_completes_after_handler():
    """_dispatch calls complete after the handler returns successfully."""
    job_svc = _make_job_service()
    runner = JobRunnerService(job_svc)

    call_order = []
    handler = AsyncMock(
        side_effect=lambda j: call_order.append("handler") or {"result": "done"}
    )
    job_svc.complete.side_effect = lambda jid, out: call_order.append("complete")
    runner.register_handler("email_processing", handler)

    job = _make_job("email_processing")
    await runner._dispatch(job)

    assert "complete" in call_order
    assert call_order.index("handler") < call_order.index("complete")
    job_svc.fail.assert_not_called()
