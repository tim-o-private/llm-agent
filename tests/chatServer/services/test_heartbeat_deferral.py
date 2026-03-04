"""Unit tests for heartbeat deferral in ScheduledExecutionService (AC-22, AC-23)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from chatServer.services.scheduled_execution_service import ScheduledExecutionService


@pytest.fixture
def service():
    return ScheduledExecutionService()


def _build_heartbeat_schedule(user_id="user-123"):
    return {
        "id": "schedule-hb",
        "user_id": user_id,
        "agent_name": "assistant",
        "prompt": "Check for updates",
        "config": {"schedule_type": "heartbeat"},
    }


def _mock_agent_executor():
    mock = MagicMock()
    mock.ainvoke = AsyncMock(return_value={"output": "Found something important!"})
    mock.tools = []
    mock.agent = MagicMock()
    mock.agent.middle = []
    mock.agent.last = MagicMock()
    mock.agent.last.bound = MagicMock()
    mock.agent.last.bound.model = "test-model"
    return mock


# --- AC-22: Heartbeat deferred when briefings enabled ---

@pytest.mark.asyncio
async def test_ac_22_heartbeat_deferred_in_execute_when_briefings_enabled(service):
    """Non-HEARTBEAT_OK output is deferred when briefings are enabled."""
    schedule = _build_heartbeat_schedule()
    mock_executor = _mock_agent_executor()

    mock_prefs = {"morning_briefing_enabled": True}

    mock_supabase = MagicMock()
    mock_supabase.table.return_value.insert.return_value.execute = AsyncMock(
        return_value=MagicMock(data=[{"id": "result-1"}])
    )
    mock_supabase.table.return_value.update.return_value.eq.return_value.execute = AsyncMock(
        return_value=MagicMock(data=[])
    )

    mock_pending = MagicMock()
    mock_pending.get_pending_count = AsyncMock(return_value=0)

    mock_briefing_svc = MagicMock()
    mock_briefing_svc.get_user_preferences = AsyncMock(return_value=mock_prefs)

    with (
        patch("chatServer.services.scheduled_execution_service.load_agent_executor_db_async", new_callable=AsyncMock, return_value=mock_executor),  # noqa: E501
        patch("chatServer.services.scheduled_execution_service.create_user_scoped_client", new_callable=AsyncMock, return_value=mock_supabase),  # noqa: E501
        patch("chatServer.services.scheduled_execution_service.wrap_tools_with_approval"),
        patch("chatServer.services.scheduled_execution_service.AuditService"),
        patch("chatServer.services.scheduled_execution_service.PendingActionsService", return_value=mock_pending),  # noqa: E501
        patch("chatServer.services.scheduled_execution_service.NotificationService"),
        patch("chatServer.services.briefing_service.BriefingService", return_value=mock_briefing_svc),
    ):
        result = await service.execute(schedule)

    assert result["success"] is True
    assert result.get("deferred") is True
    insert_calls = [
        call for call in mock_supabase.table.call_args_list
        if call[0] == ("deferred_observations",)
    ]
    assert len(insert_calls) > 0


# --- AC-23: Heartbeat immediate when briefings disabled ---

@pytest.mark.asyncio
async def test_ac_23_heartbeat_immediate_when_briefings_disabled(service):
    """Heartbeat output is delivered immediately when briefings are disabled."""
    schedule = _build_heartbeat_schedule()
    mock_executor = _mock_agent_executor()

    mock_prefs = {"morning_briefing_enabled": False}

    mock_supabase = MagicMock()
    mock_supabase.table.return_value.insert.return_value.execute = AsyncMock(
        return_value=MagicMock(data=[{"id": "result-1"}])
    )
    mock_supabase.table.return_value.update.return_value.eq.return_value.execute = AsyncMock(
        return_value=MagicMock(data=[])
    )

    mock_pending = MagicMock()
    mock_pending.get_pending_count = AsyncMock(return_value=0)

    mock_briefing_svc = MagicMock()
    mock_briefing_svc.get_user_preferences = AsyncMock(return_value=mock_prefs)

    mock_notify = MagicMock()
    mock_notify.notify_user = AsyncMock(return_value="notif-1")

    with (
        patch("chatServer.services.scheduled_execution_service.load_agent_executor_db_async", new_callable=AsyncMock, return_value=mock_executor),  # noqa: E501
        patch("chatServer.services.scheduled_execution_service.create_user_scoped_client", new_callable=AsyncMock, return_value=mock_supabase),  # noqa: E501
        patch("chatServer.services.scheduled_execution_service.wrap_tools_with_approval"),
        patch("chatServer.services.scheduled_execution_service.AuditService"),
        patch("chatServer.services.scheduled_execution_service.PendingActionsService", return_value=mock_pending),  # noqa: E501
        patch("chatServer.services.scheduled_execution_service.NotificationService", return_value=mock_notify),
        patch("chatServer.services.briefing_service.BriefingService", return_value=mock_briefing_svc),
    ):
        result = await service.execute(schedule)

    assert result["success"] is True
    assert result.get("deferred") is not True
