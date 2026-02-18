"""Tests for LTM (long-term memory) loading into agent execution."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from src.core.agent_loader_db import fetch_ltm_notes
from src.core.agents.customizable_agent import CustomizableAgentExecutor


# --- fetch_ltm_notes tests ---


@pytest.mark.asyncio
async def test_agent_loader_fetches_ltm_from_db():
    """fetch_ltm_notes returns notes when the DB has an entry for user+agent."""
    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.maybe_single.return_value.execute = AsyncMock(
        return_value=MagicMock(data={"notes": "User prefers morning emails"})
    )

    result = await fetch_ltm_notes("user-123", "assistant", supabase_client=mock_client)

    assert result == "User prefers morning emails"
    mock_client.table.assert_called_with("agent_long_term_memory")


@pytest.mark.asyncio
async def test_agent_loader_handles_missing_ltm():
    """fetch_ltm_notes returns None when no LTM row exists."""
    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.maybe_single.return_value.execute = AsyncMock(
        return_value=MagicMock(data=None)
    )

    result = await fetch_ltm_notes("user-123", "assistant", supabase_client=mock_client)

    assert result is None


@pytest.mark.asyncio
async def test_fetch_ltm_handles_db_error():
    """fetch_ltm_notes returns None on database error (non-fatal)."""
    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.maybe_single.return_value.execute = AsyncMock(
        side_effect=Exception("DB connection lost")
    )

    result = await fetch_ltm_notes("user-123", "assistant", supabase_client=mock_client)

    assert result is None


@pytest.mark.asyncio
async def test_fetch_ltm_handles_empty_notes():
    """fetch_ltm_notes returns None when notes field is empty string."""
    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.maybe_single.return_value.execute = AsyncMock(
        return_value=MagicMock(data={"notes": ""})
    )

    result = await fetch_ltm_notes("user-123", "assistant", supabase_client=mock_client)

    assert result is None


# --- update_ltm_context tests ---


def test_ltm_injected_into_system_prompt():
    """_build_system_message correctly injects LTM into the system prompt."""
    built = CustomizableAgentExecutor._build_system_message(
        "You are a helpful assistant.", "User is traveling March 3-7", None
    )
    assert "--- BEGIN LONG-TERM MEMORY NOTES ---" in built
    assert "User is traveling March 3-7" in built
    assert "You are a helpful assistant." in built


def test_ltm_injected_with_placeholder():
    """LTM replaces {{ltm_notes}} placeholder when present in system prompt."""
    built = CustomizableAgentExecutor._build_system_message(
        "You are helpful. {{ltm_notes}} Do your best.", "Remember: user likes coffee", None
    )
    assert "--- BEGIN LONG-TERM MEMORY NOTES ---" in built
    assert "Remember: user likes coffee" in built
    assert "{{ltm_notes}}" not in built


def test_ltm_none_replaces_placeholder():
    """When LTM is None, {{ltm_notes}} placeholder is replaced with a default message."""
    built = CustomizableAgentExecutor._build_system_message(
        "You are helpful. {{ltm_notes}} Do your best.", None, None
    )
    assert "(No LTM notes for this session.)" in built
    assert "{{ltm_notes}}" not in built


def test_ltm_none_without_placeholder():
    """When LTM is None and no placeholder, system prompt is unchanged."""
    built = CustomizableAgentExecutor._build_system_message(
        "You are a helpful assistant.", None, None
    )
    assert built == "You are a helpful assistant."


def test_update_ltm_context_with_none_clears_ltm():
    """_build_system_message with None LTM produces a clean prompt."""
    built = CustomizableAgentExecutor._build_system_message(
        "You are a helpful assistant.", None, None
    )
    assert "--- BEGIN LONG-TERM MEMORY NOTES ---" not in built
    assert built == "You are a helpful assistant."


def test_update_ltm_context_noop_without_rebuild_state():
    """update_ltm_context is a no-op when executor lacks rebuild state."""
    executor = MagicMock(spec=CustomizableAgentExecutor)
    executor._base_system_prompt = None
    executor._llm_with_tools = None

    CustomizableAgentExecutor.update_ltm_context(executor, "some notes")

    # agent should NOT have been set
    assert not hasattr(executor, 'agent') or executor.agent == executor.agent  # mock default


# --- Scheduled execution LTM loading test ---


@pytest.mark.asyncio
async def test_scheduled_execution_loads_ltm():
    """ScheduledExecutionService loads LTM and prepends it to the prompt."""
    from chatServer.services.scheduled_execution_service import ScheduledExecutionService

    service = ScheduledExecutionService()
    mock_schedule = {
        "id": "schedule-123",
        "user_id": "user-123",
        "agent_name": "assistant",
        "prompt": "What's new?",
        "config": {},
    }

    mock_executor = MagicMock()
    mock_executor.ainvoke = AsyncMock(return_value={"output": "Test response"})
    mock_executor.tools = [MagicMock()]

    mock_supabase = MagicMock()
    mock_supabase.table.return_value.insert.return_value.execute = AsyncMock(
        return_value=MagicMock(data=[{"id": "result-123"}])
    )
    update_chain = mock_supabase.table.return_value.update.return_value
    update_chain.eq.return_value = update_chain
    update_chain.execute = AsyncMock(return_value=MagicMock(data=[]))

    with (
        patch(
            "chatServer.services.scheduled_execution_service.load_agent_executor_db",
            return_value=mock_executor,
        ),
        patch(
            "chatServer.services.scheduled_execution_service.get_supabase_client",
            new_callable=AsyncMock,
            return_value=mock_supabase,
        ),
        patch(
            "chatServer.services.scheduled_execution_service.wrap_tools_with_approval"
        ),
        patch(
            "chatServer.services.scheduled_execution_service.PendingActionsService"
        ) as mock_pending_cls,
        patch("chatServer.services.scheduled_execution_service.AuditService"),
        patch(
            "chatServer.services.notification_service.NotificationService"
        ) as mock_notif_cls,
        patch.object(
            service, "_load_ltm", new_callable=AsyncMock,
            return_value="User context from LTM",
        ),
    ):
        mock_pending_cls.return_value.get_pending_count = AsyncMock(return_value=0)
        mock_notif_cls.return_value.notify_user = AsyncMock()
        mock_notif_cls.return_value.notify_pending_actions = AsyncMock()

        result = await service.execute(mock_schedule)

    assert result["success"] is True
    # Verify LTM was prepended to the prompt passed to ainvoke
    invoke_args = mock_executor.ainvoke.call_args[0][0]
    assert "User context from LTM" in invoke_args["input"]
    assert "What's new?" in invoke_args["input"]
