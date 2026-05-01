"""Tests for ScheduledExecutionService."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from chatServer.services.scheduled_execution_service import ScheduledExecutionService


@pytest.fixture
def service():
    return ScheduledExecutionService()


@pytest.fixture
def mock_schedule():
    return {
        "id": "schedule-123",
        "user_id": "user-123",
        "agent_name": "assistant",
        "prompt": "What's new?",
        "config": {"schedule_type": "heartbeat"},
    }


@pytest.fixture
def mock_supabase():
    client = MagicMock()
    client.table.return_value.insert.return_value.execute = AsyncMock(
        return_value=MagicMock(data=[{"id": "result-123"}])
    )
    # Support for update(...).eq(...).execute() chain (session deactivation)
    update_chain = client.table.return_value.update.return_value
    update_chain.eq.return_value = update_chain
    update_chain.execute = AsyncMock(return_value=MagicMock(data=[]))
    return client


def _standard_patches():
    """Return the common set of patch context managers."""
    return {
        "execute_agent": patch.object(
            ScheduledExecutionService,
            "_execute_agent",
            new_callable=AsyncMock,
            return_value=("Test response", "test-model"),
        ),
        "resolve_thread": patch.object(
            ScheduledExecutionService,
            "_resolve_main_thread",
            new_callable=AsyncMock,
            return_value="main-thread-123",
        ),
        "persist_thread": patch.object(
            ScheduledExecutionService,
            "_persist_to_thread",
            new_callable=AsyncMock,
        ),
        "get_supabase": patch(
            "chatServer.services.scheduled_execution_service.create_user_scoped_client",
            new_callable=AsyncMock,
        ),
        "pending_svc": patch(
            "chatServer.services.scheduled_execution_service.PendingActionsService"
        ),
        "audit_svc": patch(
            "chatServer.services.scheduled_execution_service.AuditService"
        ),
        "notification_svc": patch(
            "chatServer.services.notification_service.NotificationService"
        ),
    }


@pytest.mark.asyncio
async def test_execute_success(service, mock_schedule, mock_supabase):
    """Agent invoked, result stored with status=success, user notified."""
    patches = _standard_patches()
    with (
        patches["execute_agent"] as mock_exec_v2,
        patches["resolve_thread"],
        patches["persist_thread"],
        patches["get_supabase"] as mock_get_sb,
        patches["pending_svc"] as mock_pending_cls,
        patches["audit_svc"],
        patches["notification_svc"] as mock_notif_cls,
    ):
        mock_get_sb.return_value = mock_supabase
        mock_pending_instance = mock_pending_cls.return_value
        mock_pending_instance.get_pending_count = AsyncMock(return_value=0)
        mock_notif_instance = mock_notif_cls.return_value
        mock_notif_instance.notify_user = AsyncMock()
        mock_notif_instance.notify_pending_actions = AsyncMock()

        result = await service.execute(mock_schedule)

    assert result["success"] is True
    assert result["output"] == "Test response"

    # Verify _execute_agent was called
    mock_exec_v2.assert_awaited_once()

    # Verify result stored in DB
    mock_supabase.table.assert_any_call("agent_execution_results")
    insert_calls = mock_supabase.table.return_value.insert.call_args_list
    result_inserts = [c for c in insert_calls if "status" in c[0][0]]
    assert len(result_inserts) == 1
    stored_data = result_inserts[0][0][0]
    assert stored_data["status"] == "success"
    assert stored_data["result_content"] == "Test response"
    assert stored_data["user_id"] == "user-123"

    # Verify notification sent
    mock_notif_instance.notify_user.assert_awaited_once()


@pytest.mark.asyncio
async def test_execute_passes_channel_based_on_schedule_type(service, mock_supabase):
    """_execute_agent is called with channel matching schedule_type."""
    heartbeat_schedule = {
        "id": "schedule-123",
        "user_id": "user-123",
        "agent_name": "assistant",
        "prompt": "What's new?",
        "config": {"schedule_type": "heartbeat"},
    }
    regular_schedule = {
        "id": "schedule-456",
        "user_id": "user-123",
        "agent_name": "assistant",
        "prompt": "What's new?",
        "config": {"schedule_type": "scheduled"},
    }
    for schedule, expected_channel in [
        (heartbeat_schedule, "heartbeat"),
        (regular_schedule, "scheduled"),
    ]:
        patches = _standard_patches()
        with (
            patches["execute_agent"] as mock_exec_v2,
            patches["resolve_thread"],
            patches["persist_thread"],
            patches["get_supabase"] as mock_get_sb,
            patches["pending_svc"] as mock_pending_cls,
            patches["audit_svc"],
            patches["notification_svc"] as mock_notif_cls,
        ):
            mock_get_sb.return_value = mock_supabase
            mock_pending_cls.return_value.get_pending_count = AsyncMock(return_value=0)
            mock_notif_cls.return_value.notify_user = AsyncMock()
            mock_notif_cls.return_value.notify_pending_actions = AsyncMock()

            await service.execute(schedule)

        call_kwargs = mock_exec_v2.call_args.kwargs
        assert call_kwargs["channel"] == expected_channel, (
            f"Expected channel='{expected_channel}' for schedule_type='{schedule['config']['schedule_type']}'"
        )


@pytest.mark.asyncio
async def test_execute_does_not_prepend_ltm(service, mock_schedule, mock_supabase):
    """LTM is NOT prepended to the prompt — agents use read_memory tool on-demand."""
    patches = _standard_patches()
    with (
        patches["execute_agent"] as mock_exec_v2,
        patches["resolve_thread"],
        patches["persist_thread"],
        patches["get_supabase"] as mock_get_sb,
        patches["pending_svc"] as mock_pending_cls,
        patches["audit_svc"],
        patches["notification_svc"] as mock_notif_cls,
    ):
        mock_get_sb.return_value = mock_supabase
        mock_pending_cls.return_value.get_pending_count = AsyncMock(return_value=0)
        mock_notif_cls.return_value.notify_user = AsyncMock()
        mock_notif_cls.return_value.notify_pending_actions = AsyncMock()

        await service.execute(mock_schedule)

    # Verify the prompt is passed unchanged (no LTM prefix)
    call_kwargs = mock_exec_v2.call_args.kwargs
    assert call_kwargs["prompt"] == "What's new?"
    assert "User context (from memory):" not in call_kwargs["prompt"]


@pytest.mark.asyncio
async def test_execute_error(service, mock_schedule, mock_supabase):
    """Agent execution failure stores error result and returns success=False."""
    patches = _standard_patches()
    with (
        patches["execute_agent"] as mock_exec_v2,
        patches["resolve_thread"],
        patches["persist_thread"],
        patches["get_supabase"] as mock_get_sb,
        patches["pending_svc"],
        patches["audit_svc"],
        patches["notification_svc"],
    ):
        mock_exec_v2.side_effect = RuntimeError("Agent not found")
        mock_get_sb.return_value = mock_supabase

        result = await service.execute(mock_schedule)

    assert result["success"] is False
    assert "Agent not found" in result["error"]

    # Error result stored in DB
    mock_supabase.table.assert_any_call("agent_execution_results")
    insert_calls = mock_supabase.table.return_value.insert.call_args_list
    error_inserts = [c for c in insert_calls if isinstance(c[0][0], dict) and c[0][0].get("status") == "error"]
    assert len(error_inserts) == 1
    assert "Agent not found" in error_inserts[0][0][0]["result_content"]


@pytest.mark.asyncio
async def test_execute_normalizes_content_blocks(service, mock_schedule, mock_supabase):
    """_execute_agent response text is stored as-is."""
    patches = _standard_patches()
    # Override to return a specific response
    patches["execute_agent"] = patch.object(
        ScheduledExecutionService,
        "_execute_agent",
        new_callable=AsyncMock,
        return_value=("hello world", "test-model"),
    )
    with (
        patches["execute_agent"],
        patches["resolve_thread"],
        patches["persist_thread"],
        patches["get_supabase"] as mock_get_sb,
        patches["pending_svc"] as mock_pending_cls,
        patches["audit_svc"],
        patches["notification_svc"] as mock_notif_cls,
    ):
        mock_get_sb.return_value = mock_supabase
        mock_pending_cls.return_value.get_pending_count = AsyncMock(return_value=0)
        mock_notif_cls.return_value.notify_user = AsyncMock()
        mock_notif_cls.return_value.notify_pending_actions = AsyncMock()

        result = await service.execute(mock_schedule)

    assert result["output"] == "hello world"
    stored_data = mock_supabase.table.return_value.insert.call_args[0][0]
    assert stored_data["result_content"] == "hello world"


@pytest.mark.asyncio
async def test_execute_stores_duration_ms(service, mock_schedule, mock_supabase):
    """execution_duration_ms is a positive integer in the stored result."""
    patches = _standard_patches()
    with (
        patches["execute_agent"],
        patches["resolve_thread"],
        patches["persist_thread"],
        patches["get_supabase"] as mock_get_sb,
        patches["pending_svc"] as mock_pending_cls,
        patches["audit_svc"],
        patches["notification_svc"] as mock_notif_cls,
    ):
        mock_get_sb.return_value = mock_supabase
        mock_pending_cls.return_value.get_pending_count = AsyncMock(return_value=0)
        mock_notif_cls.return_value.notify_user = AsyncMock()
        mock_notif_cls.return_value.notify_pending_actions = AsyncMock()

        result = await service.execute(mock_schedule)

    stored_data = mock_supabase.table.return_value.insert.call_args[0][0]
    assert isinstance(stored_data["execution_duration_ms"], int)
    assert stored_data["execution_duration_ms"] >= 0
    assert isinstance(result["duration_ms"], int)


@pytest.mark.asyncio
async def test_execute_truncates_result_at_50000_chars(service, mock_schedule, mock_supabase):
    """Result content longer than 50000 chars is truncated before storage."""
    long_output = "x" * 60000
    patches = _standard_patches()
    patches["execute_agent"] = patch.object(
        ScheduledExecutionService,
        "_execute_agent",
        new_callable=AsyncMock,
        return_value=(long_output, "test-model"),
    )
    with (
        patches["execute_agent"],
        patches["resolve_thread"],
        patches["persist_thread"],
        patches["get_supabase"] as mock_get_sb,
        patches["pending_svc"] as mock_pending_cls,
        patches["audit_svc"],
        patches["notification_svc"] as mock_notif_cls,
    ):
        mock_get_sb.return_value = mock_supabase
        mock_pending_cls.return_value.get_pending_count = AsyncMock(return_value=0)
        mock_notif_cls.return_value.notify_user = AsyncMock()
        mock_notif_cls.return_value.notify_pending_actions = AsyncMock()

        await service.execute(mock_schedule)

    stored_data = mock_supabase.table.return_value.insert.call_args[0][0]
    assert len(stored_data["result_content"]) <= 50000


@pytest.mark.asyncio
async def test_execute_resolves_main_thread(service, mock_schedule, mock_supabase):
    """Execute should use _resolve_main_thread to find the user's main chat thread."""
    patches = _standard_patches()
    with (
        patches["execute_agent"],
        patches["resolve_thread"] as mock_resolve,
        patches["persist_thread"],
        patches["get_supabase"] as mock_get_sb,
        patches["pending_svc"] as mock_pending_cls,
        patches["audit_svc"],
        patches["notification_svc"] as mock_notif_cls,
    ):
        mock_get_sb.return_value = mock_supabase
        mock_pending_cls.return_value.get_pending_count = AsyncMock(return_value=0)
        mock_notif_cls.return_value.notify_user = AsyncMock()
        mock_notif_cls.return_value.notify_pending_actions = AsyncMock()

        result = await service.execute(mock_schedule)

    assert result["success"] is True
    mock_resolve.assert_awaited_once()


@pytest.mark.asyncio
async def test_execute_persists_output_to_thread(service, mock_supabase):
    """Non-heartbeat-OK output should be persisted to the main thread as a chat message."""
    schedule = {
        "id": "schedule-123",
        "user_id": "user-123",
        "agent_name": "assistant",
        "prompt": "briefing",
        "config": {"schedule_type": "scheduled"},
    }
    patches = _standard_patches()
    with (
        patches["execute_agent"],
        patches["resolve_thread"],
        patches["persist_thread"] as mock_persist,
        patches["get_supabase"] as mock_get_sb,
        patches["pending_svc"] as mock_pending_cls,
        patches["audit_svc"],
        patches["notification_svc"] as mock_notif_cls,
    ):
        mock_get_sb.return_value = mock_supabase
        mock_pending_cls.return_value.get_pending_count = AsyncMock(return_value=0)
        mock_notif_cls.return_value.notify_user = AsyncMock()
        mock_notif_cls.return_value.notify_pending_actions = AsyncMock()

        await service.execute(schedule)

    mock_persist.assert_awaited_once_with("main-thread-123", "Test response")


@pytest.mark.asyncio
async def test_execute_logs_model_override_warning(service, mock_supabase, caplog):
    """When config has model_override, a warning is logged (not supported at runtime)."""
    schedule = {
        "id": "schedule-123",
        "user_id": "user-123",
        "agent_name": "assistant",
        "prompt": "What's new?",
        "config": {
            "schedule_type": "heartbeat",
            "model_override": "claude-sonnet-4-6",
        },
    }

    patches = _standard_patches()
    with (
        patches["execute_agent"],
        patches["resolve_thread"],
        patches["persist_thread"],
        patches["get_supabase"] as mock_get_sb,
        patches["pending_svc"] as mock_pending_cls,
        patches["audit_svc"],
        patches["notification_svc"] as mock_notif_cls,
    ):
        mock_get_sb.return_value = mock_supabase
        mock_pending_cls.return_value.get_pending_count = AsyncMock(return_value=0)
        mock_notif_cls.return_value.notify_user = AsyncMock()
        mock_notif_cls.return_value.notify_pending_actions = AsyncMock()

        import logging
        with caplog.at_level(logging.WARNING):
            await service.execute(schedule)

    assert any("model override" in r.message.lower() for r in caplog.records)


@pytest.mark.asyncio
async def test_execute_stores_metadata_with_model(service, mock_supabase):
    """Execution metadata includes the model name from _execute_agent."""
    patches = _standard_patches()
    patches["execute_agent"] = patch.object(
        ScheduledExecutionService,
        "_execute_agent",
        new_callable=AsyncMock,
        return_value=("response", "test-model-v1"),
    )
    with (
        patches["execute_agent"],
        patches["resolve_thread"],
        patches["persist_thread"],
        patches["get_supabase"] as mock_get_sb,
        patches["pending_svc"] as mock_pending_cls,
        patches["audit_svc"],
        patches["notification_svc"] as mock_notif_cls,
    ):
        mock_get_sb.return_value = mock_supabase
        mock_pending_cls.return_value.get_pending_count = AsyncMock(return_value=0)
        mock_notif_cls.return_value.notify_user = AsyncMock()
        mock_notif_cls.return_value.notify_pending_actions = AsyncMock()

        schedule = {
            "id": "schedule-123",
            "user_id": "user-123",
            "agent_name": "assistant",
            "prompt": "What's new?",
            "config": {},
        }
        await service.execute(schedule)

    insert_calls = mock_supabase.table.return_value.insert.call_args_list
    result_inserts = [c for c in insert_calls if "metadata" in c[0][0]]
    assert len(result_inserts) >= 1
    stored = result_inserts[0][0][0]
    assert stored["metadata"]["model"] == "test-model-v1"


def test_no_load_ltm_method(service):
    """_load_ltm method should no longer exist."""
    assert not hasattr(service, '_load_ltm')


# --- Heartbeat prompt builder ---


class TestBuildHeartbeatPrompt:
    def test_with_checklist(self, service):
        """Checklist items are formatted into the prompt."""
        result = service._build_heartbeat_prompt(
            "Check on things",
            ["Check for new emails", "Check pending approvals"],
        )
        assert "Check on things" in result
        assert "## Heartbeat Checklist" in result
        assert "- Check for new emails" in result
        assert "- Check pending approvals" in result
        assert "HEARTBEAT_OK" in result

    def test_empty_checklist_falls_back(self, service):
        """Empty checklist returns the original prompt unchanged."""
        result = service._build_heartbeat_prompt("Check on things", [])
        assert result == "Check on things"

    def test_none_checklist_falls_back(self, service):
        """None-ish checklist (evaluated as falsy) returns original prompt."""
        result = service._build_heartbeat_prompt("Check on things", None)
        assert result == "Check on things"
