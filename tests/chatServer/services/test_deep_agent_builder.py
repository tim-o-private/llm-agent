"""Unit tests for deep_agent_builder.py — build_deep_agent and _build_system_prompt."""

from __future__ import annotations

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import chatServer.services.deep_agent_builder as mod
from chatServer.services.deep_agent_builder import (
    _agent_cache,
    _agent_locks,
    _build_system_prompt,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def clear_agent_cache():
    """Clear the module-level TTLCache before every test."""
    _agent_cache.clear()
    _agent_locks.clear()
    yield
    _agent_cache.clear()
    _agent_locks.clear()


def _make_mock_graph():
    """Return a mock CompiledStateGraph."""
    graph = MagicMock()
    graph.ainvoke = AsyncMock(return_value={"messages": []})

    async def _fake_astream(input_data, **kwargs):
        yield {"type": "messages", "ns": (), "data": (MagicMock(content="hi"), {})}

    graph.astream = _fake_astream
    return graph


def _make_agent_config():
    """Return a file-based agent config dict matching AgentConfigLoader.load() output."""
    return {
        "agent_name": "clarity",
        "soul": "Be helpful.",
        "identity": {"name": "Clarity"},
        "llm_config": {"model": "claude-sonnet-4-20250514"},
        "tools": [],
        "subagents": [
            {
                "name": "researcher",
                "description": "Research a topic.",
                "system_prompt": "You are a research assistant.",
            },
        ],
    }


def _standard_patches(agent_config=None, mock_graph=None, mock_backend=None, tools=None):
    """Return a list of context managers for the standard mock stack."""
    if agent_config is None:
        agent_config = _make_agent_config()
    if mock_graph is None:
        mock_graph = _make_mock_graph()
    if mock_backend is None:
        mock_backend = MagicMock()

    mock_loader = MagicMock()
    mock_loader.load.return_value = agent_config

    patches = [
        patch("chatServer.services.agent_config_loader.get_agent_config_loader", return_value=mock_loader),
        patch("src.core.agent_loader_db.load_tools_from_db", return_value=tools or []),
        patch("src.core.agent_loader_db._resolve_memory_user_id", new=AsyncMock(return_value="user-1")),
        patch("chatServer.services.user_instructions_cache_service.get_cached_user_instructions", new=AsyncMock(return_value=None)),  # noqa: E501
        patch("chatServer.database.supabase_client.create_user_scoped_client", new=AsyncMock(return_value=MagicMock())),
        patch("chatServer.security.tool_wrapper.wrap_tools_with_approval"),
        patch("chatServer.services.audit_service.AuditService", return_value=MagicMock()),
        patch("chatServer.services.pending_actions.PendingActionsService", return_value=MagicMock()),
        patch("chatServer.services.notification_service.NotificationService", return_value=MagicMock()),
        patch("chatServer.security.tool_wrapper.ApprovalContext", return_value=MagicMock()),
        patch.object(mod, "_create_backend", return_value=mock_backend),
        patch("chatServer.services.storage_sync.StorageSync"),
        patch.dict(os.environ, {"SUPABASE_URL": "", "SUPABASE_SERVICE_ROLE_KEY": ""}),
        patch("deepagents.create_deep_agent", return_value=mock_graph),
    ]
    return patches


# ---------------------------------------------------------------------------
# build_deep_agent — caching behavior
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_build_deep_agent_returns_agent():
    """Happy path: build_deep_agent returns a graph with ainvoke/astream."""
    mock_graph = _make_mock_graph()
    with patch.object(mod, "_build_agent", new_callable=AsyncMock, return_value=mock_graph):
        agent = await mod.build_deep_agent("user-1", "clarity", "session-1")

    assert hasattr(agent, "ainvoke")
    assert hasattr(agent, "astream")


@pytest.mark.asyncio
async def test_build_deep_agent_caches():
    """Second call with same (user_id, agent_name, channel) returns the cached instance."""
    mock_graph = _make_mock_graph()
    with patch.object(mod, "_build_agent", new_callable=AsyncMock, return_value=mock_graph) as mock_build:
        agent1 = await mod.build_deep_agent("user-1", "clarity", "session-1")
        agent2 = await mod.build_deep_agent("user-1", "clarity", "session-2")

    assert agent1 is agent2
    mock_build.assert_awaited_once()  # built only once


@pytest.mark.asyncio
async def test_build_deep_agent_different_users_not_cached():
    """Different user_id → different agents, both built."""
    graph1 = _make_mock_graph()
    graph2 = _make_mock_graph()
    with patch.object(
        mod,
        "_build_agent",
        new_callable=AsyncMock,
        side_effect=[graph1, graph2],
    ) as mock_build:
        agent1 = await mod.build_deep_agent("user-1", "clarity", "session-1")
        agent2 = await mod.build_deep_agent("user-2", "clarity", "session-2")

    assert agent1 is not agent2
    assert mock_build.await_count == 2


@pytest.mark.asyncio
async def test_build_deep_agent_different_channels_not_cached():
    """Different channel → different agents (system_prompt varies by channel)."""
    graph1 = _make_mock_graph()
    graph2 = _make_mock_graph()
    with patch.object(
        mod,
        "_build_agent",
        new_callable=AsyncMock,
        side_effect=[graph1, graph2],
    ) as mock_build:
        agent1 = await mod.build_deep_agent("user-1", "clarity", "s1", "web")
        agent2 = await mod.build_deep_agent("user-1", "clarity", "s2", "telegram")

    assert agent1 is not agent2
    assert mock_build.await_count == 2


# ---------------------------------------------------------------------------
# build_deep_agent — create_deep_agent integration
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_build_deep_agent_constructs_backend():
    """Backend always constructed via _create_backend."""
    mock_graph = _make_mock_graph()
    mock_backend = MagicMock()
    patches = _standard_patches(mock_graph=mock_graph, mock_backend=mock_backend)

    from contextlib import ExitStack
    with ExitStack() as stack:
        cms = [stack.enter_context(p) for p in patches]
        mock_create = cms[-1]  # deepagents.create_deep_agent
        agent = await mod.build_deep_agent("user-1", "clarity", "session-1", "web")

    assert agent is mock_graph
    call_kwargs = mock_create.call_args.kwargs
    assert call_kwargs.get("backend") is mock_backend


@pytest.mark.asyncio
async def test_build_deep_agent_model_prefixed_with_anthropic():
    """Model from config is prefixed with 'anthropic:' when no provider prefix present."""
    config = _make_agent_config()
    config["llm_config"] = {"model": "claude-sonnet-4-20250514"}
    mock_graph = _make_mock_graph()
    patches = _standard_patches(agent_config=config, mock_graph=mock_graph)

    from contextlib import ExitStack
    with ExitStack() as stack:
        cms = [stack.enter_context(p) for p in patches]
        mock_create = cms[-1]
        await mod.build_deep_agent("user-1", "clarity", "session-1", "web")

    call_kwargs = mock_create.call_args.kwargs
    assert call_kwargs["model"] == "anthropic:claude-sonnet-4-20250514"


@pytest.mark.asyncio
async def test_build_deep_agent_model_with_existing_prefix_unchanged():
    """Model with existing 'provider:' prefix is not double-prefixed."""
    config = _make_agent_config()
    config["llm_config"] = {"model": "openai:gpt-4o"}
    mock_graph = _make_mock_graph()
    patches = _standard_patches(agent_config=config, mock_graph=mock_graph)

    from contextlib import ExitStack
    with ExitStack() as stack:
        cms = [stack.enter_context(p) for p in patches]
        mock_create = cms[-1]
        await mod.build_deep_agent("user-1", "clarity", "session-1", "web")

    call_kwargs = mock_create.call_args.kwargs
    assert call_kwargs["model"] == "openai:gpt-4o"


@pytest.mark.asyncio
async def test_build_deep_agent_passes_tools_backend_skills_memory():
    """create_deep_agent receives tools, backend, skills, memory, and system_prompt."""
    mock_tool = MagicMock()
    mock_backend = MagicMock()
    mock_graph = _make_mock_graph()
    patches = _standard_patches(mock_graph=mock_graph, mock_backend=mock_backend, tools=[mock_tool])

    from contextlib import ExitStack
    with ExitStack() as stack:
        cms = [stack.enter_context(p) for p in patches]
        mock_create = cms[-1]
        await mod.build_deep_agent("user-1", "clarity", "session-1", "web")

    call_kwargs = mock_create.call_args.kwargs
    assert call_kwargs["tools"] == [mock_tool]
    assert call_kwargs["backend"] is mock_backend
    assert call_kwargs["skills"] == ["/system/skills/", "/user/skills/"]
    assert call_kwargs["memory"] == ["/user/memory/AGENTS.md"]
    assert call_kwargs["name"] == "clarity"
    assert "system_prompt" in call_kwargs
    # Subagents from file config
    subagents = call_kwargs.get("subagents")
    assert subagents is not None
    assert len(subagents) == 1
    assert subagents[0]["name"] == "researcher"


# ---------------------------------------------------------------------------
# _build_system_prompt — always-present identity + runtime context
# ---------------------------------------------------------------------------


def test_system_prompt_includes_soul():
    prompt = _build_system_prompt(soul="Be deeply helpful.")
    assert "Be deeply helpful." in prompt
    assert "Soul" in prompt


def test_system_prompt_includes_identity():
    prompt = _build_system_prompt(identity={"name": "Clarity", "vibe": "warm"})
    assert "Clarity" in prompt
    assert "warm" in prompt


def test_system_prompt_includes_channel():
    prompt = _build_system_prompt(channel="web")
    assert "Channel" in prompt


def test_system_prompt_includes_time():
    prompt = _build_system_prompt(channel="web")
    assert "Current Time" in prompt


def test_system_prompt_includes_user_instructions():
    prompt = _build_system_prompt(channel="web", user_instructions="Always reply in bullet points.")
    assert "Always reply in bullet points." in prompt


def test_system_prompt_scheduled_mode():
    prompt = _build_system_prompt(channel="scheduled")
    assert "automated" in prompt.lower() or "scheduled" in prompt.lower()


def test_system_prompt_heartbeat_mode():
    prompt = _build_system_prompt(channel="heartbeat")
    assert "HEARTBEAT_OK" in prompt


def test_system_prompt_session_open_new_user():
    prompt = _build_system_prompt(channel="session_open", user_instructions=None)
    assert "Session Open" in prompt
    assert "first time" in prompt.lower()


def test_system_prompt_telegram_channel():
    prompt = _build_system_prompt(channel="telegram")
    assert "Telegram" in prompt
    assert "4096" in prompt
