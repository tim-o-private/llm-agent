"""Tests for session open service."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from chatServer.services.session_open_service import SessionOpenService

_SVC = "chatServer.services.session_open_service"


@pytest.fixture
def service():
    return SessionOpenService()


def _mock_supabase(has_memory=False, has_instructions=False, last_message_at=None):
    """Build a mock supabase client with chained query responses.

    The real supabase client is a sync object (table/select/eq are sync,
    execute is async). We use MagicMock for sync parts and AsyncMock for execute.
    """
    client = MagicMock()

    def table_side_effect(table_name):
        mock_table = MagicMock()

        if table_name == "agent_long_term_memory":
            resp = MagicMock()
            resp.data = {"id": "mem-1"} if has_memory else None
            mock_table.select.return_value = mock_table
            mock_table.eq.return_value = mock_table
            mock_table.maybe_single.return_value = mock_table
            mock_table.execute = AsyncMock(return_value=resp)
        elif table_name == "user_agent_prompt_customizations":
            resp = MagicMock()
            resp.data = {"id": "instr-1"} if has_instructions else None
            mock_table.select.return_value = mock_table
            mock_table.eq.return_value = mock_table
            mock_table.maybe_single.return_value = mock_table
            mock_table.execute = AsyncMock(return_value=resp)
        elif table_name == "chat_message_history":
            resp = MagicMock()
            if last_message_at:
                resp.data = [{"created_at": last_message_at.isoformat()}]
            else:
                resp.data = []
            mock_table.select.return_value = mock_table
            mock_table.eq.return_value = mock_table
            mock_table.order.return_value = mock_table
            mock_table.limit.return_value = mock_table
            mock_table.execute = AsyncMock(return_value=resp)

        return mock_table

    client.table = MagicMock(side_effect=table_side_effect)
    return client


def _patch_svc(mock_client, mock_executor):
    """Return a tuple of context managers for the common service patches."""
    return (
        patch(f"{_SVC}.get_supabase_client", new_callable=AsyncMock, return_value=mock_client),
        patch(f"{_SVC}.load_agent_executor_db_async", return_value=mock_executor),
    )


@pytest.mark.asyncio
async def test_new_user_returns_is_new_user_true(service):
    """New user -> is_new_user=True, silent=False, bootstrap trigger used."""
    mock_client = _mock_supabase(has_memory=False, has_instructions=False)
    mock_executor = AsyncMock()
    mock_executor.tools = []
    mock_executor.ainvoke = AsyncMock(return_value={"output": "Hello! I'm Clarity."})
    p_client, p_loader = _patch_svc(mock_client, mock_executor)

    with p_client, p_loader, patch.object(
        service, "_persist_ai_message", new_callable=AsyncMock
    ) as mock_persist:
        result = await service.run(user_id="u1", agent_name="clarity", session_id="s1")

    assert result["is_new_user"] is True
    assert result["silent"] is False
    call_args = mock_executor.ainvoke.call_args[0][0]
    assert "First session" in call_args["input"]
    mock_persist.assert_awaited_once()


@pytest.mark.asyncio
async def test_returning_user_wakeup_silent(service):
    """Returning user, agent returns 'WAKEUP_SILENT' -> silent=True, no persistence."""
    mock_client = _mock_supabase(has_memory=True, has_instructions=True)
    mock_executor = AsyncMock()
    mock_executor.tools = []
    mock_executor.ainvoke = AsyncMock(return_value={"output": "WAKEUP_SILENT"})
    p_client, p_loader = _patch_svc(mock_client, mock_executor)

    with p_client, p_loader, patch.object(
        service, "_persist_ai_message", new_callable=AsyncMock
    ) as mock_persist:
        result = await service.run(user_id="u1", agent_name="clarity", session_id="s1")

    assert result["silent"] is True
    assert result["is_new_user"] is False
    mock_persist.assert_not_awaited()


@pytest.mark.asyncio
async def test_returning_user_greeting_persisted(service):
    """Returning user, agent returns greeting -> silent=False, AI message persisted."""
    mock_client = _mock_supabase(has_memory=True, has_instructions=False)
    mock_executor = AsyncMock()
    mock_executor.tools = []
    mock_executor.ainvoke = AsyncMock(return_value={"output": "Morning! 2 tasks due today."})
    p_client, p_loader = _patch_svc(mock_client, mock_executor)

    with p_client, p_loader, patch.object(
        service, "_persist_ai_message", new_callable=AsyncMock
    ) as mock_persist:
        result = await service.run(user_id="u1", agent_name="clarity", session_id="s1")

    assert result["silent"] is False
    assert result["response"] == "Morning! 2 tasks due today."
    mock_persist.assert_awaited_once_with("s1", "Morning! 2 tasks due today.")


@pytest.mark.asyncio
async def test_content_block_list_normalized(service):
    """Content block list output normalized to string."""
    mock_client = _mock_supabase(has_memory=True, has_instructions=True)
    mock_executor = AsyncMock()
    mock_executor.tools = []
    mock_executor.ainvoke = AsyncMock(return_value={
        "output": [
            {"type": "text", "text": "Hello "},
            {"type": "text", "text": "world!"},
        ]
    })
    p_client, p_loader = _patch_svc(mock_client, mock_executor)

    with p_client, p_loader, patch.object(
        service, "_persist_ai_message", new_callable=AsyncMock
    ):
        result = await service.run(user_id="u1", agent_name="clarity", session_id="s1")

    assert result["response"] == "Hello world!"


@pytest.mark.asyncio
async def test_agent_loaded_with_session_open_channel(service):
    """Agent loaded with channel='session_open'."""
    mock_client = _mock_supabase(has_memory=True, has_instructions=True)
    mock_executor = AsyncMock()
    mock_executor.tools = []
    mock_executor.ainvoke = AsyncMock(return_value={"output": "WAKEUP_SILENT"})

    with (
        patch(f"{_SVC}.get_supabase_client", new_callable=AsyncMock, return_value=mock_client),
        patch(f"{_SVC}.load_agent_executor_db_async", return_value=mock_executor) as mock_loader,
        patch.object(service, "_persist_ai_message", new_callable=AsyncMock),
    ):
        await service.run(user_id="u1", agent_name="clarity", session_id="s1")

    mock_loader.assert_awaited_once()
    call_kwargs = mock_loader.call_args[1]
    assert call_kwargs["channel"] == "session_open"


@pytest.mark.asyncio
async def test_last_message_at_passed_to_loader(service):
    """last_message_at from DB passed through to agent loader."""
    ts = datetime(2026, 2, 22, 10, 0, 0, tzinfo=timezone.utc)
    mock_client = _mock_supabase(has_memory=True, has_instructions=True, last_message_at=ts)
    mock_executor = AsyncMock()
    mock_executor.tools = []
    mock_executor.ainvoke = AsyncMock(return_value={"output": "WAKEUP_SILENT"})

    with (
        patch(f"{_SVC}.get_supabase_client", new_callable=AsyncMock, return_value=mock_client),
        patch(f"{_SVC}.load_agent_executor_db_async", return_value=mock_executor) as mock_loader,
        patch.object(service, "_persist_ai_message", new_callable=AsyncMock),
    ):
        await service.run(user_id="u1", agent_name="clarity", session_id="s1")

    call_kwargs = mock_loader.call_args[1]
    assert call_kwargs["last_message_at"] == ts
