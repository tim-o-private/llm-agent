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


@pytest.fixture
def mock_agent_executor():
    executor = MagicMock()
    executor.ainvoke = AsyncMock(return_value={"output": "Test response"})
    executor.tools = [MagicMock(), MagicMock()]
    return executor


def _standard_patches():
    """Return the common set of patch decorators as a dict of target -> mock."""
    return {
        "load_agent": patch(
            "chatServer.services.scheduled_execution_service.load_agent_executor_db"
        ),
        "get_supabase": patch(
            "chatServer.services.scheduled_execution_service.get_supabase_client",
            new_callable=AsyncMock,
        ),
        "wrap_tools": patch(
            "chatServer.services.scheduled_execution_service.wrap_tools_with_approval"
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
async def test_execute_success(service, mock_schedule, mock_supabase, mock_agent_executor):
    """Agent invoked with correct input/chat_history, result stored with status=success, user notified."""
    patches = _standard_patches()
    with (
        patches["load_agent"] as mock_load,
        patches["get_supabase"] as mock_get_sb,
        patches["wrap_tools"],
        patches["pending_svc"] as mock_pending_cls,
        patches["audit_svc"],
        patches["notification_svc"] as mock_notif_cls,
    ):
        mock_load.return_value = mock_agent_executor
        mock_get_sb.return_value = mock_supabase
        mock_pending_instance = mock_pending_cls.return_value
        mock_pending_instance.get_pending_count = AsyncMock(return_value=0)
        mock_notif_instance = mock_notif_cls.return_value
        mock_notif_instance.notify_user = AsyncMock()
        mock_notif_instance.notify_pending_actions = AsyncMock()

        result = await service.execute(mock_schedule)

    assert result["success"] is True
    assert result["output"] == "Test response"

    # Verify agent invoked with correct args
    mock_agent_executor.ainvoke.assert_awaited_once_with(
        {"input": "What's new?", "chat_history": []}
    )

    # Verify result stored in DB
    mock_supabase.table.assert_any_call("agent_execution_results")
    insert_calls = mock_supabase.table.return_value.insert.call_args_list
    # Find the agent_execution_results insert (has 'status' key)
    result_inserts = [c for c in insert_calls if "status" in c[0][0]]
    assert len(result_inserts) == 1
    stored_data = result_inserts[0][0][0]
    assert stored_data["status"] == "success"
    assert stored_data["result_content"] == "Test response"
    assert stored_data["user_id"] == "user-123"

    # Verify notification sent
    mock_notif_instance.notify_user.assert_awaited_once()


@pytest.mark.asyncio
async def test_execute_error(service, mock_schedule, mock_supabase):
    """Agent load failure stores error result and returns success=False."""
    patches = _standard_patches()
    with (
        patches["load_agent"] as mock_load,
        patches["get_supabase"] as mock_get_sb,
        patches["wrap_tools"],
        patches["pending_svc"],
        patches["audit_svc"],
        patches["notification_svc"],
    ):
        mock_load.side_effect = RuntimeError("Agent not found")
        mock_get_sb.return_value = mock_supabase

        result = await service.execute(mock_schedule)

    assert result["success"] is False
    assert "Agent not found" in result["error"]

    # Error result stored in DB
    insert_call = mock_supabase.table.return_value.insert
    insert_call.assert_called_once()
    stored_data = insert_call.call_args[0][0]
    assert stored_data["status"] == "error"
    assert "Agent not found" in stored_data["result_content"]


@pytest.mark.asyncio
async def test_execute_wraps_tools_with_approval(service, mock_schedule, mock_supabase, mock_agent_executor):
    """Tools are wrapped with approval using correct ApprovalContext fields."""
    patches = _standard_patches()
    with (
        patches["load_agent"] as mock_load,
        patches["get_supabase"] as mock_get_sb,
        patches["wrap_tools"] as mock_wrap,
        patches["pending_svc"] as mock_pending_cls,
        patches["audit_svc"],
        patches["notification_svc"] as mock_notif_cls,
    ):
        mock_load.return_value = mock_agent_executor
        mock_get_sb.return_value = mock_supabase
        mock_pending_cls.return_value.get_pending_count = AsyncMock(return_value=0)
        mock_notif_cls.return_value.notify_user = AsyncMock()
        mock_notif_cls.return_value.notify_pending_actions = AsyncMock()

        await service.execute(mock_schedule)

    mock_wrap.assert_called_once()
    tools_arg, context_arg = mock_wrap.call_args[0]
    assert tools_arg == mock_agent_executor.tools
    assert context_arg.user_id == "user-123"
    assert context_arg.agent_name == "assistant"
    assert context_arg.session_id.startswith("scheduled_assistant_")


@pytest.mark.asyncio
async def test_execute_normalizes_content_blocks(service, mock_schedule, mock_supabase, mock_agent_executor):
    """Content block lists are joined into a single string."""
    mock_agent_executor.ainvoke = AsyncMock(
        return_value={
            "output": [
                {"type": "text", "text": "hello"},
                {"type": "text", "text": " world"},
            ]
        }
    )
    patches = _standard_patches()
    with (
        patches["load_agent"] as mock_load,
        patches["get_supabase"] as mock_get_sb,
        patches["wrap_tools"],
        patches["pending_svc"] as mock_pending_cls,
        patches["audit_svc"],
        patches["notification_svc"] as mock_notif_cls,
    ):
        mock_load.return_value = mock_agent_executor
        mock_get_sb.return_value = mock_supabase
        mock_pending_cls.return_value.get_pending_count = AsyncMock(return_value=0)
        mock_notif_cls.return_value.notify_user = AsyncMock()
        mock_notif_cls.return_value.notify_pending_actions = AsyncMock()

        result = await service.execute(mock_schedule)

    assert result["output"] == "hello world"
    stored_data = mock_supabase.table.return_value.insert.call_args[0][0]
    assert stored_data["result_content"] == "hello world"


@pytest.mark.asyncio
async def test_execute_stores_duration_ms(service, mock_schedule, mock_supabase, mock_agent_executor):
    """execution_duration_ms is a positive integer in the stored result."""
    patches = _standard_patches()
    with (
        patches["load_agent"] as mock_load,
        patches["get_supabase"] as mock_get_sb,
        patches["wrap_tools"],
        patches["pending_svc"] as mock_pending_cls,
        patches["audit_svc"],
        patches["notification_svc"] as mock_notif_cls,
    ):
        mock_load.return_value = mock_agent_executor
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
async def test_execute_notifies_pending_actions_when_count_gt_0(
    service, mock_schedule, mock_supabase, mock_agent_executor
):
    """When pending actions > 0, notify_pending_actions is called."""
    patches = _standard_patches()
    with (
        patches["load_agent"] as mock_load,
        patches["get_supabase"] as mock_get_sb,
        patches["wrap_tools"],
        patches["pending_svc"] as mock_pending_cls,
        patches["audit_svc"],
        patches["notification_svc"] as mock_notif_cls,
    ):
        mock_load.return_value = mock_agent_executor
        mock_get_sb.return_value = mock_supabase
        mock_pending_cls.return_value.get_pending_count = AsyncMock(return_value=3)
        mock_notif_instance = mock_notif_cls.return_value
        mock_notif_instance.notify_user = AsyncMock()
        mock_notif_instance.notify_pending_actions = AsyncMock()

        await service.execute(mock_schedule)

    mock_notif_instance.notify_pending_actions.assert_awaited_once_with(
        user_id="user-123",
        pending_count=3,
        agent_name="assistant",
    )


@pytest.mark.asyncio
async def test_execute_skips_pending_notification_when_count_0(
    service, mock_schedule, mock_supabase, mock_agent_executor
):
    """When pending actions == 0, notify_pending_actions is NOT called."""
    patches = _standard_patches()
    with (
        patches["load_agent"] as mock_load,
        patches["get_supabase"] as mock_get_sb,
        patches["wrap_tools"],
        patches["pending_svc"] as mock_pending_cls,
        patches["audit_svc"],
        patches["notification_svc"] as mock_notif_cls,
    ):
        mock_load.return_value = mock_agent_executor
        mock_get_sb.return_value = mock_supabase
        mock_pending_cls.return_value.get_pending_count = AsyncMock(return_value=0)
        mock_notif_instance = mock_notif_cls.return_value
        mock_notif_instance.notify_user = AsyncMock()
        mock_notif_instance.notify_pending_actions = AsyncMock()

        await service.execute(mock_schedule)

    mock_notif_instance.notify_pending_actions.assert_not_awaited()


@pytest.mark.asyncio
async def test_execute_truncates_result_at_50000_chars(
    service, mock_schedule, mock_supabase, mock_agent_executor
):
    """Result content longer than 50000 chars is truncated before storage."""
    long_output = "x" * 60000
    mock_agent_executor.ainvoke = AsyncMock(return_value={"output": long_output})

    patches = _standard_patches()
    with (
        patches["load_agent"] as mock_load,
        patches["get_supabase"] as mock_get_sb,
        patches["wrap_tools"],
        patches["pending_svc"] as mock_pending_cls,
        patches["audit_svc"],
        patches["notification_svc"] as mock_notif_cls,
    ):
        mock_load.return_value = mock_agent_executor
        mock_get_sb.return_value = mock_supabase
        mock_pending_cls.return_value.get_pending_count = AsyncMock(return_value=0)
        mock_notif_cls.return_value.notify_user = AsyncMock()
        mock_notif_cls.return_value.notify_pending_actions = AsyncMock()

        await service.execute(mock_schedule)

    stored_data = mock_supabase.table.return_value.insert.call_args[0][0]
    assert len(stored_data["result_content"]) <= 50000


@pytest.mark.asyncio
async def test_execute_creates_chat_session(service, mock_schedule, mock_agent_executor):
    """Execute should insert a chat_sessions row with channel='scheduled'."""
    # Set up a mock that tracks calls per table
    chat_sessions_insert = MagicMock()
    chat_sessions_insert.execute = AsyncMock(return_value=MagicMock(data=[]))
    chat_sessions_update_chain = MagicMock()
    chat_sessions_update_chain.eq.return_value = chat_sessions_update_chain
    chat_sessions_update_chain.execute = AsyncMock(return_value=MagicMock(data=[]))
    chat_sessions_mock = MagicMock()
    chat_sessions_mock.insert.return_value = chat_sessions_insert
    chat_sessions_mock.update.return_value = chat_sessions_update_chain

    results_insert = MagicMock()
    results_insert.execute = AsyncMock(return_value=MagicMock(data=[{"id": "result-1"}]))
    results_mock = MagicMock()
    results_mock.insert.return_value = results_insert

    supabase_client = MagicMock()

    def table_side_effect(table_name):
        if table_name == "chat_sessions":
            return chat_sessions_mock
        elif table_name == "agent_execution_results":
            return results_mock
        return MagicMock()

    supabase_client.table.side_effect = table_side_effect

    patches = _standard_patches()
    with (
        patches["load_agent"] as mock_load,
        patches["get_supabase"] as mock_get_sb,
        patches["wrap_tools"],
        patches["pending_svc"] as mock_pending_cls,
        patches["audit_svc"],
        patches["notification_svc"] as mock_notif_cls,
    ):
        mock_load.return_value = mock_agent_executor
        mock_get_sb.return_value = supabase_client
        mock_pending_cls.return_value.get_pending_count = AsyncMock(return_value=0)
        mock_notif_cls.return_value.notify_user = AsyncMock()
        mock_notif_cls.return_value.notify_pending_actions = AsyncMock()

        result = await service.execute(mock_schedule)

    assert result["success"] is True

    # Verify chat_sessions insert
    chat_sessions_mock.insert.assert_called_once()
    session_data = chat_sessions_mock.insert.call_args[0][0]
    assert session_data["user_id"] == "user-123"
    assert session_data["channel"] == "scheduled"
    assert session_data["agent_name"] == "assistant"
    assert session_data["is_active"] is True
    assert session_data["session_id"].startswith("scheduled_assistant_")


@pytest.mark.asyncio
async def test_execute_marks_session_inactive_after_completion(service, mock_schedule, mock_agent_executor):
    """After successful execution, the session should be marked is_active=False."""
    chat_sessions_insert = MagicMock()
    chat_sessions_insert.execute = AsyncMock(return_value=MagicMock(data=[]))
    chat_sessions_update_chain = MagicMock()
    chat_sessions_update_chain.eq.return_value = chat_sessions_update_chain
    chat_sessions_update_chain.execute = AsyncMock(return_value=MagicMock(data=[]))
    chat_sessions_mock = MagicMock()
    chat_sessions_mock.insert.return_value = chat_sessions_insert
    chat_sessions_mock.update.return_value = chat_sessions_update_chain

    results_insert = MagicMock()
    results_insert.execute = AsyncMock(return_value=MagicMock(data=[{"id": "result-1"}]))
    results_mock = MagicMock()
    results_mock.insert.return_value = results_insert

    supabase_client = MagicMock()

    def table_side_effect(table_name):
        if table_name == "chat_sessions":
            return chat_sessions_mock
        elif table_name == "agent_execution_results":
            return results_mock
        return MagicMock()

    supabase_client.table.side_effect = table_side_effect

    patches = _standard_patches()
    with (
        patches["load_agent"] as mock_load,
        patches["get_supabase"] as mock_get_sb,
        patches["wrap_tools"],
        patches["pending_svc"] as mock_pending_cls,
        patches["audit_svc"],
        patches["notification_svc"] as mock_notif_cls,
    ):
        mock_load.return_value = mock_agent_executor
        mock_get_sb.return_value = supabase_client
        mock_pending_cls.return_value.get_pending_count = AsyncMock(return_value=0)
        mock_notif_cls.return_value.notify_user = AsyncMock()
        mock_notif_cls.return_value.notify_pending_actions = AsyncMock()

        await service.execute(mock_schedule)

    # Verify session marked inactive
    chat_sessions_mock.update.assert_called_once_with({"is_active": False})
    eq_calls = [call.args for call in chat_sessions_update_chain.eq.call_args_list]
    # session_id should start with "scheduled_assistant_"
    assert len(eq_calls) == 1
    assert eq_calls[0][0] == "session_id"
    assert eq_calls[0][1].startswith("scheduled_assistant_")
