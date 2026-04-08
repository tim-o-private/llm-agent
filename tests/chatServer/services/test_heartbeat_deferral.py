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


def _base_patches(output="Found something important!", mock_supabase=None, mock_pending=None):
    """Common patches for all heartbeat deferral tests."""
    if mock_supabase is None:
        mock_supabase = MagicMock()
        mock_supabase.table.return_value.insert.return_value.execute = AsyncMock(
            return_value=MagicMock(data=[{"id": "result-1"}])
        )
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute = AsyncMock(
            return_value=MagicMock(data=[])
        )
    if mock_pending is None:
        mock_pending = MagicMock()
        mock_pending.get_pending_count = AsyncMock(return_value=0)
    return mock_supabase, mock_pending


# --- AC-22: Heartbeat deferred when briefings enabled ---

@pytest.mark.asyncio
async def test_ac_22_heartbeat_deferred_in_execute_when_briefings_enabled(service):
    """Non-HEARTBEAT_OK output is deferred when briefings are enabled."""
    schedule = _build_heartbeat_schedule()
    mock_supabase, mock_pending = _base_patches()

    mock_prefs = {"morning_briefing_enabled": True}
    mock_briefing_svc = MagicMock()
    mock_briefing_svc.get_user_preferences = AsyncMock(return_value=mock_prefs)

    with (
        patch.object(
            ScheduledExecutionService, "_execute_v2",
            new_callable=AsyncMock,
            return_value=("Found something important!", "test-model"),
        ),
        patch(
            "chatServer.services.scheduled_execution_service.create_user_scoped_client",
            new_callable=AsyncMock,
            return_value=mock_supabase,
        ),
        patch("chatServer.services.scheduled_execution_service.AuditService"),
        patch(
            "chatServer.services.scheduled_execution_service.PendingActionsService",
            return_value=mock_pending,
        ),
        patch.object(ScheduledExecutionService, "_notify_user", new_callable=AsyncMock),
        patch(
            "chatServer.services.briefing_service.BriefingService",
            return_value=mock_briefing_svc,
        ),
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
    mock_supabase, mock_pending = _base_patches()

    mock_prefs = {"morning_briefing_enabled": False}
    mock_briefing_svc = MagicMock()
    mock_briefing_svc.get_user_preferences = AsyncMock(return_value=mock_prefs)

    with (
        patch.object(
            ScheduledExecutionService, "_execute_v2",
            new_callable=AsyncMock,
            return_value=("Found something important!", "test-model"),
        ),
        patch(
            "chatServer.services.scheduled_execution_service.create_user_scoped_client",
            new_callable=AsyncMock,
            return_value=mock_supabase,
        ),
        patch("chatServer.services.scheduled_execution_service.AuditService"),
        patch(
            "chatServer.services.scheduled_execution_service.PendingActionsService",
            return_value=mock_pending,
        ),
        patch.object(ScheduledExecutionService, "_notify_user", new_callable=AsyncMock),
        patch(
            "chatServer.services.briefing_service.BriefingService",
            return_value=mock_briefing_svc,
        ),
    ):
        result = await service.execute(schedule)

    assert result["success"] is True
    assert result.get("deferred") is not True
