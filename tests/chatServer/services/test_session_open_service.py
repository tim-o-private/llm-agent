"""Tests for session open service."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from chatServer.services.session_open_service import SessionOpenService

_SVC = "chatServer.services.session_open_service"


def _mock_supabase(has_instructions=False):
    """Build a mock supabase client.

    Only mocks user_agent_prompt_customizations (for _has_instructions).
    _has_memory is patched separately since it now queries min-memory, not Supabase.
    """
    client = MagicMock()

    def table_side_effect(table_name):
        mock_table = MagicMock()

        if table_name == "user_agent_prompt_customizations":
            resp = MagicMock()
            resp.data = {"id": "instr-1"} if has_instructions else None
            mock_table.select.return_value = mock_table
            mock_table.eq.return_value = mock_table
            mock_table.maybe_single.return_value = mock_table
            mock_table.execute = AsyncMock(return_value=resp)

        return mock_table

    client.table = MagicMock(side_effect=table_side_effect)
    return client


def _mock_get_db_connection(last_message_at=None):
    """Return an async generator mock for get_db_connection."""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.execute = AsyncMock()
    mock_cursor.fetchone = AsyncMock(
        return_value=(last_message_at,) if last_message_at else None
    )
    mock_cursor.__aenter__ = AsyncMock(return_value=mock_cursor)
    mock_cursor.__aexit__ = AsyncMock(return_value=False)
    mock_conn.cursor.return_value = mock_cursor

    async def _gen():
        yield mock_conn

    return _gen


_DB_CONN = "chatServer.database.connection.get_db_connection"


def _patch_svc(mock_executor, last_message_at=None, has_memory=False):
    """Return a tuple of context managers for the common service patches."""
    return (
        patch(f"{_SVC}.load_agent_executor_db_async", return_value=mock_executor),
        patch(_DB_CONN, new=_mock_get_db_connection(last_message_at)),
        patch(f"{_SVC}.SessionOpenService._has_memory", new_callable=AsyncMock, return_value=has_memory),
    )


@pytest.mark.asyncio
async def test_new_user_returns_is_new_user_true():
    """New user (no memory, no instructions) -> is_new_user=True, bootstrap trigger."""
    mock_client = _mock_supabase(has_instructions=False)
    service = SessionOpenService(mock_client)
    mock_executor = AsyncMock()
    mock_executor.tools = []
    mock_executor.ainvoke = AsyncMock(return_value={"output": "Hello! I'm your assistant."})
    p_loader, p_db, p_mem = _patch_svc(mock_executor, has_memory=False)

    with p_loader, p_db, p_mem, patch.object(
        service, "_persist_ai_message", new_callable=AsyncMock
    ) as mock_persist:
        result = await service.run(user_id="u1", agent_name="assistant", session_id="s1")

    assert result["is_new_user"] is True
    assert result["silent"] is False
    call_args = mock_executor.ainvoke.call_args[0][0]
    assert "First session" in call_args["input"]
    mock_persist.assert_awaited_once()


@pytest.mark.asyncio
async def test_returning_user_with_memory_not_new():
    """User with min-memory memories -> is_new_user=False (memory alone is sufficient)."""
    mock_client = _mock_supabase(has_instructions=False)
    service = SessionOpenService(mock_client)
    mock_executor = AsyncMock()
    mock_executor.tools = []
    mock_executor.ainvoke = AsyncMock(return_value={"output": "Morning! 2 tasks due."})
    p_loader, p_db, p_mem = _patch_svc(mock_executor, has_memory=True)

    with p_loader, p_db, p_mem, patch.object(
        service, "_persist_ai_message", new_callable=AsyncMock
    ):
        result = await service.run(user_id="u1", agent_name="assistant", session_id="s1")

    assert result["is_new_user"] is False
    call_args = mock_executor.ainvoke.call_args[0][0]
    assert "User returned" in call_args["input"]


@pytest.mark.asyncio
async def test_returning_user_wakeup_silent():
    """Returning user, agent returns 'WAKEUP_SILENT' -> silent=True, no persistence."""
    mock_client = _mock_supabase(has_instructions=True)
    service = SessionOpenService(mock_client)
    mock_executor = AsyncMock()
    mock_executor.tools = []
    mock_executor.ainvoke = AsyncMock(return_value={"output": "WAKEUP_SILENT"})
    p_loader, p_db, p_mem = _patch_svc(mock_executor, has_memory=True)

    with p_loader, p_db, p_mem, patch.object(
        service, "_persist_ai_message", new_callable=AsyncMock
    ) as mock_persist:
        result = await service.run(user_id="u1", agent_name="assistant", session_id="s1")

    assert result["silent"] is True
    assert result["is_new_user"] is False
    mock_persist.assert_not_awaited()


@pytest.mark.asyncio
async def test_returning_user_greeting_persisted():
    """Returning user (has memory, no instructions), agent greets -> persisted."""
    mock_client = _mock_supabase(has_instructions=False)
    service = SessionOpenService(mock_client)
    mock_executor = AsyncMock()
    mock_executor.tools = []
    mock_executor.ainvoke = AsyncMock(return_value={"output": "Morning! 2 tasks due today."})
    p_loader, p_db, p_mem = _patch_svc(mock_executor, has_memory=True)

    with p_loader, p_db, p_mem, patch.object(
        service, "_persist_ai_message", new_callable=AsyncMock
    ) as mock_persist:
        result = await service.run(user_id="u1", agent_name="assistant", session_id="s1")

    assert result["silent"] is False
    assert result["is_new_user"] is False
    assert result["response"] == "Morning! 2 tasks due today."
    mock_persist.assert_awaited_once_with("s1", "Morning! 2 tasks due today.")


@pytest.mark.asyncio
async def test_content_block_list_normalized():
    """Content block list output normalized to string."""
    mock_client = _mock_supabase(has_instructions=True)
    service = SessionOpenService(mock_client)
    mock_executor = AsyncMock()
    mock_executor.tools = []
    mock_executor.ainvoke = AsyncMock(return_value={
        "output": [
            {"type": "text", "text": "Hello "},
            {"type": "text", "text": "world!"},
        ]
    })
    p_loader, p_db, p_mem = _patch_svc(mock_executor, has_memory=True)

    with p_loader, p_db, p_mem, patch.object(
        service, "_persist_ai_message", new_callable=AsyncMock
    ):
        result = await service.run(user_id="u1", agent_name="assistant", session_id="s1")

    assert result["response"] == "Hello world!"


@pytest.mark.asyncio
async def test_deterministic_silence_recent_returning_user():
    """Returning user seen < 5 min ago → silent without invoking agent."""
    ts = datetime.now(timezone.utc)  # just now
    mock_client = _mock_supabase(has_instructions=True)
    service = SessionOpenService(mock_client)
    mock_executor = AsyncMock()
    mock_executor.tools = []
    mock_executor.ainvoke = AsyncMock()  # should NOT be called

    with (
        patch(f"{_SVC}.load_agent_executor_db_async", return_value=mock_executor) as mock_loader,
        patch(_DB_CONN, new=_mock_get_db_connection(ts)),
        patch(f"{_SVC}.SessionOpenService._has_memory", new_callable=AsyncMock, return_value=True),
        patch.object(service, "_persist_ai_message", new_callable=AsyncMock) as mock_persist,
    ):
        result = await service.run(user_id="u1", agent_name="assistant", session_id="s1")

    assert result["silent"] is True
    assert result["is_new_user"] is False
    mock_loader.assert_not_awaited()  # agent never loaded
    mock_executor.ainvoke.assert_not_awaited()  # agent never invoked
    mock_persist.assert_not_awaited()


@pytest.mark.asyncio
async def test_deterministic_silence_skipped_for_new_user():
    """New user is never deterministically silenced, even with recent last_message_at."""
    ts = datetime.now(timezone.utc)  # just now
    mock_client = _mock_supabase(has_instructions=False)
    service = SessionOpenService(mock_client)
    mock_executor = AsyncMock()
    mock_executor.tools = []
    mock_executor.ainvoke = AsyncMock(return_value={"output": "Hello! I'm your assistant."})
    p_loader, p_db, p_mem = _patch_svc(mock_executor, last_message_at=ts, has_memory=False)

    with p_loader, p_db, p_mem, patch.object(
        service, "_persist_ai_message", new_callable=AsyncMock
    ):
        result = await service.run(user_id="u1", agent_name="assistant", session_id="s1")

    assert result["is_new_user"] is True
    assert result["silent"] is False
    mock_executor.ainvoke.assert_awaited_once()


@pytest.mark.asyncio
async def test_agent_loaded_with_session_open_channel():
    """Agent loaded with channel='session_open'."""
    mock_client = _mock_supabase(has_instructions=True)
    service = SessionOpenService(mock_client)
    mock_executor = AsyncMock()
    mock_executor.tools = []
    mock_executor.ainvoke = AsyncMock(return_value={"output": "WAKEUP_SILENT"})

    with (
        patch(f"{_SVC}.load_agent_executor_db_async", return_value=mock_executor) as mock_loader,
        patch(_DB_CONN, new=_mock_get_db_connection()),
        patch(f"{_SVC}.SessionOpenService._has_memory", new_callable=AsyncMock, return_value=True),
        patch.object(service, "_persist_ai_message", new_callable=AsyncMock),
    ):
        await service.run(user_id="u1", agent_name="assistant", session_id="s1")

    mock_loader.assert_awaited_once()
    call_kwargs = mock_loader.call_args[1]
    assert call_kwargs["channel"] == "session_open"


@pytest.mark.asyncio
async def test_last_message_at_passed_to_loader():
    """last_message_at from DB passed through to agent loader."""
    ts = datetime(2026, 2, 22, 10, 0, 0, tzinfo=timezone.utc)
    mock_client = _mock_supabase(has_instructions=True)
    service = SessionOpenService(mock_client)
    mock_executor = AsyncMock()
    mock_executor.tools = []
    mock_executor.ainvoke = AsyncMock(return_value={"output": "WAKEUP_SILENT"})

    with (
        patch(f"{_SVC}.load_agent_executor_db_async", return_value=mock_executor) as mock_loader,
        patch(_DB_CONN, new=_mock_get_db_connection(ts)),
        patch(f"{_SVC}.SessionOpenService._has_memory", new_callable=AsyncMock, return_value=True),
        patch.object(service, "_persist_ai_message", new_callable=AsyncMock),
        patch(f"{_SVC}.BootstrapContextService") as mock_bcs_cls,
    ):
        mock_bcs = AsyncMock()
        mock_bcs.gather = AsyncMock(return_value=MagicMock(render=MagicMock(return_value="Tasks: 2 active")))
        mock_bcs_cls.return_value = mock_bcs
        await service.run(user_id="u1", agent_name="assistant", session_id="s1")

    call_kwargs = mock_loader.call_args[1]
    assert call_kwargs["last_message_at"] == ts


@pytest.mark.asyncio
async def test_returning_user_gets_bootstrap_context():
    """Returning user: BootstrapContextService.gather() called and result passed to loader."""
    mock_client = _mock_supabase(has_instructions=True)
    service = SessionOpenService(mock_client)
    mock_executor = AsyncMock()
    mock_executor.tools = []
    mock_executor.ainvoke = AsyncMock(return_value={"output": "WAKEUP_SILENT"})

    rendered = "Tasks: 2 active task(s)\nReminders: No upcoming reminders.\nEmail: 1 account(s) connected: alice@example.com"  # noqa: E501

    with (
        patch(f"{_SVC}.load_agent_executor_db_async", return_value=mock_executor) as mock_loader,
        patch(_DB_CONN, new=_mock_get_db_connection()),
        patch(f"{_SVC}.SessionOpenService._has_memory", new_callable=AsyncMock, return_value=True),
        patch.object(service, "_persist_ai_message", new_callable=AsyncMock),
        patch(f"{_SVC}.BootstrapContextService") as mock_bcs_cls,
    ):
        mock_ctx = MagicMock()
        mock_ctx.render.return_value = rendered
        mock_bcs = AsyncMock()
        mock_bcs.gather = AsyncMock(return_value=mock_ctx)
        mock_bcs_cls.return_value = mock_bcs

        await service.run(user_id="u1", agent_name="assistant", session_id="s1")

    mock_bcs.gather.assert_awaited_once_with("u1")
    call_kwargs = mock_loader.call_args[1]
    assert call_kwargs["bootstrap_context"] == rendered


@pytest.mark.asyncio
async def test_new_user_skips_bootstrap_context():
    """New user: BootstrapContextService never called, bootstrap_context=None passed to loader."""
    mock_client = _mock_supabase(has_instructions=False)
    service = SessionOpenService(mock_client)
    mock_executor = AsyncMock()
    mock_executor.tools = []
    mock_executor.ainvoke = AsyncMock(return_value={"output": "Hello! I'm your assistant."})
    p_loader, p_db, p_mem = _patch_svc(mock_executor, has_memory=False)

    with p_loader as mock_loader, p_db, p_mem, patch.object(
        service, "_persist_ai_message", new_callable=AsyncMock
    ), patch(f"{_SVC}.BootstrapContextService") as mock_bcs_cls:
        await service.run(user_id="u1", agent_name="assistant", session_id="s1")

    mock_bcs_cls.assert_not_called()
    call_kwargs = mock_loader.call_args[1]
    assert call_kwargs["bootstrap_context"] is None


# --- _has_memory unit tests (min-memory integration) ---


@pytest.mark.asyncio
async def test_empty_output_returns_silent():
    """AC-17: Empty output from executor → silent=True, no persistence."""
    mock_client = _mock_supabase(has_instructions=True)
    service = SessionOpenService(mock_client)
    mock_executor = AsyncMock()
    mock_executor.tools = []
    mock_executor.ainvoke = AsyncMock(return_value={"output": ""})
    p_loader, p_db, p_mem = _patch_svc(mock_executor, has_memory=True)

    with p_loader, p_db, p_mem, patch.object(
        service, "_persist_ai_message", new_callable=AsyncMock
    ) as mock_persist:
        result = await service.run(user_id="u1", agent_name="assistant", session_id="s1")

    assert result["silent"] is True
    assert result["response"] == ""
    mock_persist.assert_not_awaited()


@pytest.mark.asyncio
async def test_no_text_content_output_returns_silent():
    """AC-17: 'No text content in response.' output → silent=True."""
    mock_client = _mock_supabase(has_instructions=True)
    service = SessionOpenService(mock_client)
    mock_executor = AsyncMock()
    mock_executor.tools = []
    mock_executor.ainvoke = AsyncMock(return_value={"output": "No text content in response."})
    p_loader, p_db, p_mem = _patch_svc(mock_executor, has_memory=True)

    with p_loader, p_db, p_mem, patch.object(
        service, "_persist_ai_message", new_callable=AsyncMock
    ) as mock_persist:
        result = await service.run(user_id="u1", agent_name="assistant", session_id="s1")

    assert result["silent"] is True
    mock_persist.assert_not_awaited()


@pytest.mark.asyncio
async def test_llm_error_returns_silent():
    """AC-16: Exception from ainvoke → silent=True, no re-raise."""
    mock_client = _mock_supabase(has_instructions=True)
    service = SessionOpenService(mock_client)
    mock_executor = AsyncMock()
    mock_executor.tools = []
    mock_executor.ainvoke = AsyncMock(side_effect=RuntimeError("rate limit exceeded"))
    p_loader, p_db, p_mem = _patch_svc(mock_executor, has_memory=True)

    with p_loader, p_db, p_mem, patch.object(
        service, "_persist_ai_message", new_callable=AsyncMock
    ) as mock_persist:
        result = await service.run(user_id="u1", agent_name="assistant", session_id="s1")

    assert result["silent"] is True
    assert result["response"] == ""
    mock_persist.assert_not_awaited()


# --- _has_memory unit tests (min-memory integration) ---


@pytest.mark.asyncio
async def test_has_memory_returns_true_for_list_results():
    """_has_memory returns True when min-memory returns non-empty list."""
    mock_client = MagicMock()
    service = SessionOpenService(mock_client)

    with (
        patch("os.getenv", side_effect=lambda k, d="": {"MEMORY_SERVER_URL": "http://mem:8000", "MEMORY_SERVER_BACKEND_KEY": "key"}.get(k, d)),  # noqa: E501
        patch("src.core.agent_loader_db._resolve_memory_user_id", new_callable=AsyncMock, return_value="google-oauth2|123"),  # noqa: E501
        patch("chatServer.services.memory_client.MemoryClient") as mock_mem_cls,
    ):
        mock_mem = MagicMock()
        mock_mem.call_tool = AsyncMock(return_value=[{"id": "m1", "text": "pref"}])
        mock_mem_cls.return_value = mock_mem
        result = await service._has_memory(mock_client, "u1", "assistant")

    assert result is True


@pytest.mark.asyncio
async def test_has_memory_returns_true_for_dict_with_memories():
    """_has_memory returns True when min-memory returns dict with memories key."""
    mock_client = MagicMock()
    service = SessionOpenService(mock_client)

    with (
        patch("os.getenv", side_effect=lambda k, d="": {"MEMORY_SERVER_URL": "http://mem:8000", "MEMORY_SERVER_BACKEND_KEY": "key"}.get(k, d)),  # noqa: E501
        patch("src.core.agent_loader_db._resolve_memory_user_id", new_callable=AsyncMock, return_value="google-oauth2|123"),  # noqa: E501
        patch("chatServer.services.memory_client.MemoryClient") as mock_mem_cls,
    ):
        mock_mem = MagicMock()
        mock_mem.call_tool = AsyncMock(return_value={"memories": [{"text": "pref"}]})
        mock_mem_cls.return_value = mock_mem
        result = await service._has_memory(mock_client, "u1", "assistant")

    assert result is True


@pytest.mark.asyncio
async def test_has_memory_returns_false_for_empty_results():
    """_has_memory returns False when min-memory returns empty list."""
    mock_client = MagicMock()
    service = SessionOpenService(mock_client)

    with (
        patch("os.getenv", side_effect=lambda k, d="": {"MEMORY_SERVER_URL": "http://mem:8000", "MEMORY_SERVER_BACKEND_KEY": "key"}.get(k, d)),  # noqa: E501
        patch("src.core.agent_loader_db._resolve_memory_user_id", new_callable=AsyncMock, return_value="google-oauth2|123"),  # noqa: E501
        patch("chatServer.services.memory_client.MemoryClient") as mock_mem_cls,
    ):
        mock_mem = MagicMock()
        mock_mem.call_tool = AsyncMock(return_value=[])
        mock_mem_cls.return_value = mock_mem
        result = await service._has_memory(mock_client, "u1", "assistant")

    assert result is False


@pytest.mark.asyncio
async def test_has_memory_returns_false_when_env_vars_unset():
    """_has_memory returns False when MEMORY_SERVER_URL is not set."""
    mock_client = MagicMock()
    service = SessionOpenService(mock_client)

    with patch("os.getenv", return_value=""):
        result = await service._has_memory(mock_client, "u1", "assistant")

    assert result is False


@pytest.mark.asyncio
async def test_has_memory_returns_false_on_error():
    """_has_memory returns False (non-fatal) when min-memory is unreachable."""
    mock_client = MagicMock()
    service = SessionOpenService(mock_client)

    with (
        patch("os.getenv", side_effect=lambda k, d="": {"MEMORY_SERVER_URL": "http://mem:8000", "MEMORY_SERVER_BACKEND_KEY": "key"}.get(k, d)),  # noqa: E501
        patch("src.core.agent_loader_db._resolve_memory_user_id", new_callable=AsyncMock, return_value="u1"),  # noqa: E501
        patch("chatServer.services.memory_client.MemoryClient") as mock_mem_cls,
    ):
        mock_mem = MagicMock()
        mock_mem.call_tool = AsyncMock(side_effect=RuntimeError("Connection refused"))
        mock_mem_cls.return_value = mock_mem
        result = await service._has_memory(mock_client, "u1", "assistant")

    assert result is False
