"""Unit tests for job handler functions."""

import sys
import types
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _inject_module(name, **attrs):
    """Inject a fake module into sys.modules, returning (module, original)."""
    mod = types.ModuleType(name)
    for k, v in attrs.items():
        setattr(mod, k, v)
    original = sys.modules.get(name)
    sys.modules[name] = mod
    return mod, original


def _restore_module(name, original):
    """Restore a module in sys.modules to its original state."""
    if original is None:
        sys.modules.pop(name, None)
    else:
        sys.modules[name] = original


# ---------------------------------------------------------------------------
# handle_email_processing
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_handle_email_processing_success():
    """handle_email_processing calls EmailOnboardingService.process_job and returns output."""
    from chatServer.services.job_handlers import handle_email_processing

    mock_service_instance = AsyncMock()
    mock_service_instance.process_job = AsyncMock(
        return_value={"success": True, "output": "Relationships identified: 3"}
    )
    mock_service_cls = MagicMock(return_value=mock_service_instance)

    _, original = _inject_module(
        "chatServer.services.email_onboarding_service",
        EmailOnboardingService=mock_service_cls,
    )

    try:
        job = {
            "id": "job-1",
            "user_id": "user-1",
            "job_type": "email_processing",
            "status": "claimed",
            "input": {"connection_id": "conn-1"},
        }
        result = await handle_email_processing(job)
    finally:
        _restore_module("chatServer.services.email_onboarding_service", original)

    assert result["success"] is True
    mock_service_instance.process_job.assert_called_once()
    adapted = mock_service_instance.process_job.call_args[0][0]
    assert adapted["id"] == "job-1"
    assert adapted["user_id"] == "user-1"
    assert adapted["connection_id"] == "conn-1"


@pytest.mark.asyncio
async def test_handle_email_processing_failure_raises():
    """handle_email_processing raises RuntimeError when process_job returns success=False."""
    from chatServer.services.job_handlers import handle_email_processing

    mock_service_instance = AsyncMock()
    mock_service_instance.process_job = AsyncMock(
        return_value={"success": False, "error": "LLM error"}
    )
    mock_service_cls = MagicMock(return_value=mock_service_instance)

    _, original = _inject_module(
        "chatServer.services.email_onboarding_service",
        EmailOnboardingService=mock_service_cls,
    )

    try:
        job = {
            "id": "job-1",
            "user_id": "user-1",
            "status": "claimed",
            "input": {"connection_id": "conn-1"},
        }
        with pytest.raises(RuntimeError, match="LLM error"):
            await handle_email_processing(job)
    finally:
        _restore_module("chatServer.services.email_onboarding_service", original)


# ---------------------------------------------------------------------------
# handle_agent_invocation
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_handle_agent_invocation_success():
    """handle_agent_invocation calls ScheduledExecutionService.execute with job input as schedule."""
    from chatServer.services.job_handlers import handle_agent_invocation

    mock_service_instance = AsyncMock()
    mock_service_instance.execute = AsyncMock(
        return_value={"success": True, "output": "Done", "duration_ms": 1200}
    )
    mock_service_cls = MagicMock(return_value=mock_service_instance)

    _, original = _inject_module(
        "chatServer.services.scheduled_execution_service",
        ScheduledExecutionService=mock_service_cls,
    )

    schedule = {
        "id": "sched-1",
        "user_id": "user-1",
        "agent_name": "assistant",
        "prompt": "Do something",
        "config": {},
    }
    job = {
        "id": "job-1",
        "user_id": "user-1",
        "job_type": "agent_invocation",
        "input": schedule,
    }

    try:
        result = await handle_agent_invocation(job)
    finally:
        _restore_module("chatServer.services.scheduled_execution_service", original)

    assert result["success"] is True
    mock_service_instance.execute.assert_called_once_with(schedule)


@pytest.mark.asyncio
async def test_handle_agent_invocation_failure_raises():
    """handle_agent_invocation raises RuntimeError when execute returns success=False."""
    from chatServer.services.job_handlers import handle_agent_invocation

    mock_service_instance = AsyncMock()
    mock_service_instance.execute = AsyncMock(
        return_value={"success": False, "error": "Agent crashed"}
    )
    mock_service_cls = MagicMock(return_value=mock_service_instance)

    _, original = _inject_module(
        "chatServer.services.scheduled_execution_service",
        ScheduledExecutionService=mock_service_cls,
    )

    job = {
        "id": "job-1",
        "user_id": "user-1",
        "input": {"id": "s-1", "user_id": "user-1", "agent_name": "x", "prompt": "", "config": {}},
    }

    try:
        with pytest.raises(RuntimeError, match="Agent crashed"):
            await handle_agent_invocation(job)
    finally:
        _restore_module("chatServer.services.scheduled_execution_service", original)


# ---------------------------------------------------------------------------
# handle_reminder_delivery
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_handle_reminder_delivery_success():
    """handle_reminder_delivery notifies, marks sent, handles recurrence."""
    from chatServer.services.job_handlers import handle_reminder_delivery

    reminder = {
        "id": "rem-1",
        "user_id": "user-1",
        "title": "Call Sarah",
        "body": "Follow up on proposal",
        "recurrence": None,
    }

    mock_reminder_svc = AsyncMock()
    mock_reminder_svc.get_by_id = AsyncMock(return_value=reminder)
    mock_reminder_svc.mark_sent = AsyncMock()
    mock_reminder_svc.handle_recurrence = AsyncMock()

    mock_notification_svc = AsyncMock()
    mock_notification_svc.notify_user = AsyncMock()

    mock_db_client = AsyncMock()

    # Services are lazy-imported inside the handler — inject via sys.modules.
    # Save originals so other tests aren't polluted.
    _, orig_reminder = _inject_module(
        "chatServer.services.reminder_service",
        ReminderService=MagicMock(return_value=mock_reminder_svc),
    )
    _, orig_notif = _inject_module(
        "chatServer.services.notification_service",
        NotificationService=MagicMock(return_value=mock_notification_svc),
    )

    try:
        with patch(
            "chatServer.services.job_handlers.create_system_client",
            new_callable=AsyncMock,
            return_value=mock_db_client,
        ):
            job = {
                "id": "job-1",
                "user_id": "user-1",
                "input": {"reminder_id": "rem-1", "user_id": "user-1"},
            }
            result = await handle_reminder_delivery(job)
    finally:
        _restore_module("chatServer.services.reminder_service", orig_reminder)
        _restore_module("chatServer.services.notification_service", orig_notif)

    assert result == {"delivered": True, "reminder_id": "rem-1"}
    mock_notification_svc.notify_user.assert_called_once()
    call_kwargs = mock_notification_svc.notify_user.call_args[1]
    assert call_kwargs["title"] == "Reminder: Call Sarah"
    assert call_kwargs["body"] == "Follow up on proposal"
    assert call_kwargs["category"] == "reminder"
    mock_reminder_svc.mark_sent.assert_called_once_with("rem-1")
    mock_reminder_svc.handle_recurrence.assert_called_once_with(reminder)


@pytest.mark.asyncio
async def test_handle_reminder_delivery_not_found():
    """handle_reminder_delivery returns {skipped: True} when reminder not found."""
    from chatServer.services.job_handlers import handle_reminder_delivery

    mock_reminder_svc = AsyncMock()
    mock_reminder_svc.get_by_id = AsyncMock(return_value=None)

    mock_db_client = AsyncMock()

    _, orig_reminder = _inject_module(
        "chatServer.services.reminder_service",
        ReminderService=MagicMock(return_value=mock_reminder_svc),
    )

    try:
        with patch(
            "chatServer.services.job_handlers.create_system_client",
            new_callable=AsyncMock,
            return_value=mock_db_client,
        ):
            job = {
                "id": "job-1",
                "user_id": "user-1",
                "input": {"reminder_id": "rem-missing", "user_id": "user-1"},
            }
            result = await handle_reminder_delivery(job)
    finally:
        _restore_module("chatServer.services.reminder_service", orig_reminder)

    assert result == {"skipped": True}
    mock_reminder_svc.mark_sent.assert_not_called()
