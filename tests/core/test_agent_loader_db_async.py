"""Tests for async agent loader (load_agent_executor_db_async)."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# We need to patch at the source modules since load_agent_executor_db_async
# uses local imports from chatServer.services.*


def _make_mock_executor():
    """Create a mock agent executor."""
    mock_executor = MagicMock()
    mock_executor.ainvoke = AsyncMock()
    mock_executor.memory = None
    return mock_executor


MOCK_AGENT_CONFIG = {
    "id": "uuid-1",
    "agent_name": "assistant",
    "soul": "Be helpful",
    "identity": {"name": "Assistant", "description": "a helpful assistant", "vibe": "friendly"},
    "llm_config": {"model": "claude-sonnet-4-20250514"},
}

ENV_VARS = {"SUPABASE_URL": "https://test.supabase.co", "SUPABASE_SERVICE_ROLE_KEY": "test-key"}


@pytest.mark.asyncio
async def test_load_agent_executor_db_async_cache_hit():
    """Test async loader with all caches warm."""
    mock_tools_data = [
        {"name": "read_memory", "type": "ReadMemoryTool", "description": "Read memory", "config": {}, "is_active": True},  # noqa: E501
    ]

    mock_executor = _make_mock_executor()

    with (
        patch.dict("os.environ", ENV_VARS),
        patch("chatServer.services.agent_config_cache_service.get_cached_agent_config", new_callable=AsyncMock, return_value=MOCK_AGENT_CONFIG) as mock_config,  # noqa: E501, F841
        patch("chatServer.services.tool_cache_service.get_cached_tools_for_agent", new_callable=AsyncMock, return_value=mock_tools_data),  # noqa: E501
        patch("chatServer.services.user_instructions_cache_service.get_cached_user_instructions", new_callable=AsyncMock, return_value="Be concise"),  # noqa: E501
        patch("core.agent_loader_db.load_tools_from_db", return_value=[type("MockTool", (), {"name": "read_memory"})()]),  # noqa: E501
        patch("core.agent_loader_db.CustomizableAgentExecutor") as mock_executor_class,
    ):
        mock_executor_class.from_agent_config.return_value = mock_executor

        # Re-import to pick up fresh local imports
        from core.agent_loader_db import load_agent_executor_db_async

        result = await load_agent_executor_db_async(
            agent_name="assistant",
            user_id="user-1",
            session_id="session-1",
        )

        assert result is mock_executor
        mock_executor_class.from_agent_config.assert_called_once()


@pytest.mark.asyncio
async def test_load_agent_executor_db_async_config_cache_miss():
    """Test async loader falls back to DB when config cache misses."""
    mock_executor = _make_mock_executor()

    with (
        patch.dict("os.environ", ENV_VARS),
        patch("chatServer.services.agent_config_cache_service.get_cached_agent_config", new_callable=AsyncMock, return_value=None),  # noqa: E501
        patch("core.agent_loader_db._fetch_agent_config_from_db_async", new_callable=AsyncMock, return_value=MOCK_AGENT_CONFIG),  # noqa: E501
        patch("chatServer.services.tool_cache_service.get_cached_tools_for_agent", new_callable=AsyncMock, return_value=[]),  # noqa: E501
        patch("chatServer.services.user_instructions_cache_service.get_cached_user_instructions", new_callable=AsyncMock, return_value=None),  # noqa: E501
        patch("core.agent_loader_db.load_tools_from_db", return_value=[]),
        patch("core.agent_loader_db.CustomizableAgentExecutor") as mock_executor_class,
    ):
        mock_executor_class.from_agent_config.return_value = mock_executor

        from core.agent_loader_db import load_agent_executor_db_async

        result = await load_agent_executor_db_async(
            agent_name="assistant",
            user_id="user-1",
            session_id="session-1",
        )

        assert result is mock_executor


@pytest.mark.asyncio
async def test_load_agent_executor_db_async_agent_not_found():
    """Test async loader raises ValueError when agent not found."""
    with (
        patch.dict("os.environ", ENV_VARS),
        patch("chatServer.services.agent_config_cache_service.get_cached_agent_config", new_callable=AsyncMock, return_value=None),  # noqa: E501
        patch("core.agent_loader_db._fetch_agent_config_from_db_async", new_callable=AsyncMock, return_value=None),
    ):
        from core.agent_loader_db import load_agent_executor_db_async

        with pytest.raises(ValueError, match="not found"):
            await load_agent_executor_db_async(
                agent_name="nonexistent",
                user_id="user-1",
                session_id="session-1",
            )


@pytest.mark.asyncio
async def test_load_agent_executor_db_async_missing_env():
    """Test async loader raises ValueError when env vars missing."""
    with patch.dict("os.environ", {}, clear=True):
        from core.agent_loader_db import load_agent_executor_db_async

        with pytest.raises(ValueError, match="Supabase URL and Service Key"):
            await load_agent_executor_db_async(
                agent_name="assistant",
                user_id="user-1",
                session_id="session-1",
            )


@pytest.mark.asyncio
async def test_load_agent_executor_db_async_parallelizes_fetch():
    """Test that tools and instructions are fetched in parallel via asyncio.gather."""
    call_order = []

    async def mock_get_tools(agent_id):
        call_order.append("tools_start")
        await asyncio.sleep(0.01)
        call_order.append("tools_end")
        return []

    async def mock_get_instructions(user_id, agent_name):
        call_order.append("instructions_start")
        await asyncio.sleep(0.01)
        call_order.append("instructions_end")
        return None

    mock_executor = _make_mock_executor()

    with (
        patch.dict("os.environ", ENV_VARS),
        patch("chatServer.services.agent_config_cache_service.get_cached_agent_config", new_callable=AsyncMock, return_value=MOCK_AGENT_CONFIG),  # noqa: E501
        patch("chatServer.services.tool_cache_service.get_cached_tools_for_agent", side_effect=mock_get_tools),
        patch("chatServer.services.user_instructions_cache_service.get_cached_user_instructions", side_effect=mock_get_instructions),  # noqa: E501
        patch("core.agent_loader_db.load_tools_from_db", return_value=[]),
        patch("core.agent_loader_db.CustomizableAgentExecutor") as mock_executor_class,
    ):
        mock_executor_class.from_agent_config.return_value = mock_executor

        from core.agent_loader_db import load_agent_executor_db_async

        await load_agent_executor_db_async(
            agent_name="assistant",
            user_id="user-1",
            session_id="session-1",
        )

        # Both should start before either ends (parallel execution)
        assert "tools_start" in call_order
        assert "instructions_start" in call_order
        tools_start_idx = call_order.index("tools_start")
        instructions_start_idx = call_order.index("instructions_start")
        tools_end_idx = call_order.index("tools_end")
        instructions_end_idx = call_order.index("instructions_end")
        assert tools_start_idx < tools_end_idx
        assert instructions_start_idx < instructions_end_idx


@pytest.mark.asyncio
async def test_token_budget_warning_logged(caplog):
    """AC-20: Very long assembled prompt (>200K chars) triggers a WARNING log."""
    import logging

    mock_tools_data = [
        {"name": "read_memory", "type": "ReadMemoryTool", "description": "Read memory", "config": {}, "is_active": True},  # noqa: E501
    ]

    mock_executor = _make_mock_executor()

    # Build a prompt string >200K chars (50K tokens * 4 chars/token)
    huge_soul = "x" * 210_000

    big_config = {**MOCK_AGENT_CONFIG, "soul": huge_soul}

    with (
        patch.dict("os.environ", ENV_VARS),
        patch("chatServer.services.agent_config_cache_service.get_cached_agent_config", new_callable=AsyncMock, return_value=big_config),  # noqa: E501
        patch("chatServer.services.tool_cache_service.get_cached_tools_for_agent", new_callable=AsyncMock, return_value=mock_tools_data),  # noqa: E501
        patch("chatServer.services.user_instructions_cache_service.get_cached_user_instructions", new_callable=AsyncMock, return_value=""),  # noqa: E501
        patch("core.agent_loader_db.load_tools_from_db", return_value=[]),
        patch("core.agent_loader_db.CustomizableAgentExecutor") as mock_executor_class,
        patch("chatServer.services.prompt_builder.build_agent_prompt", return_value="x" * 210_000),
        caplog.at_level(logging.WARNING, logger="core.agent_loader_db"),
    ):
        mock_executor_class.from_agent_config.return_value = mock_executor

        from core.agent_loader_db import load_agent_executor_db_async

        await load_agent_executor_db_async(
            agent_name="assistant",
            user_id="user-1",
            session_id="session-1",
        )

    assert any("Token budget warning" in r.message for r in caplog.records)
