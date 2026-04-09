"""Unit tests for deep_agent_builder.py — build_deep_agent and _build_channel_prompt."""

from __future__ import annotations

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import chatServer.services.deep_agent_builder as mod
from chatServer.services.deep_agent_builder import (
    _agent_cache,
    _agent_locks,
    _build_channel_prompt,
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
    """Second call with same (user_id, agent_name) returns the cached instance."""
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


# ---------------------------------------------------------------------------
# build_deep_agent — create_deep_agent integration (AC-22 backend fallback)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_build_deep_agent_constructs_bwrap_backend():
    """AC-22: BwrapBackend always constructed."""
    agent_config = {
        "id": "agent-id-1",
        "agent_name": "clarity",
        "soul": "Be helpful.",
        "identity": {"name": "Clarity"},
        "prompt_template": None,
        "llm_config": {},
    }
    mock_graph = _make_mock_graph()
    mock_backend = MagicMock()
    with (
        patch("chatServer.services.agent_config_cache_service.get_cached_agent_config", new=AsyncMock(return_value=agent_config)),  # noqa: E501
        patch("src.core.agent_loader_db.load_tools_from_db", return_value=[]),
        patch("src.core.agent_loader_db._fetch_agent_config_from_db_async", new=AsyncMock(return_value=agent_config)),  # noqa: E501
        patch("src.core.agent_loader_db._prefetch_memory_notes", new=AsyncMock(return_value=None)),
        patch("src.core.agent_loader_db._resolve_memory_user_id", new=AsyncMock(return_value="user-1")),
        patch("chatServer.services.tool_cache_service.get_cached_tools_for_agent", new=AsyncMock(return_value=[])),  # noqa: E501
        patch("chatServer.services.user_instructions_cache_service.get_cached_user_instructions", new=AsyncMock(return_value=None)),  # noqa: E501
        patch("chatServer.database.supabase_client.create_user_scoped_client", new=AsyncMock(return_value=MagicMock())),  # noqa: E501
        patch("chatServer.security.tool_wrapper.wrap_tools_with_approval"),
        patch("chatServer.services.audit_service.AuditService", return_value=MagicMock()),
        patch("chatServer.services.pending_actions.PendingActionsService", return_value=MagicMock()),
        patch("chatServer.services.notification_service.NotificationService", return_value=MagicMock()),
        patch("chatServer.security.tool_wrapper.ApprovalContext", return_value=MagicMock()),
        patch("chatServer.sandbox.bwrap_backend.BwrapBackend", return_value=mock_backend),
        patch("chatServer.services.storage_sync.StorageSync"),
        patch.dict(os.environ, {"SUPABASE_URL": "", "SUPABASE_SERVICE_ROLE_KEY": ""}),
        patch("deepagents.create_deep_agent", return_value=mock_graph) as mock_create,
    ):
        agent = await mod.build_deep_agent("user-1", "clarity", "session-1", "web")

    assert agent is mock_graph
    # BwrapBackend is always passed as backend
    call_kwargs = mock_create.call_args.kwargs
    assert call_kwargs.get("backend") is mock_backend


@pytest.mark.asyncio
async def test_build_deep_agent_model_prefixed_with_anthropic():
    """Model from DB is prefixed with 'anthropic:' when no provider prefix present."""
    agent_config = {
        "id": "agent-id-1",
        "agent_name": "clarity",
        "soul": "Be helpful.",
        "identity": {"name": "Clarity"},
        "prompt_template": None,
        "llm_config": {"model": "claude-sonnet-4-20250514"},
    }
    mock_graph = _make_mock_graph()
    with (
        patch("chatServer.services.agent_config_cache_service.get_cached_agent_config", new=AsyncMock(return_value=agent_config)),  # noqa: E501
        patch("src.core.agent_loader_db.load_tools_from_db", return_value=[]),
        patch("src.core.agent_loader_db._fetch_agent_config_from_db_async", new=AsyncMock(return_value=agent_config)),  # noqa: E501
        patch("src.core.agent_loader_db._prefetch_memory_notes", new=AsyncMock(return_value=None)),
        patch("src.core.agent_loader_db._resolve_memory_user_id", new=AsyncMock(return_value="user-1")),
        patch("chatServer.services.tool_cache_service.get_cached_tools_for_agent", new=AsyncMock(return_value=[])),  # noqa: E501
        patch("chatServer.services.user_instructions_cache_service.get_cached_user_instructions", new=AsyncMock(return_value=None)),  # noqa: E501
        patch("chatServer.database.supabase_client.create_user_scoped_client", new=AsyncMock(return_value=MagicMock())),  # noqa: E501
        patch("chatServer.security.tool_wrapper.wrap_tools_with_approval"),
        patch("chatServer.services.audit_service.AuditService", return_value=MagicMock()),
        patch("chatServer.services.pending_actions.PendingActionsService", return_value=MagicMock()),
        patch("chatServer.services.notification_service.NotificationService", return_value=MagicMock()),
        patch("chatServer.security.tool_wrapper.ApprovalContext", return_value=MagicMock()),

        patch("chatServer.sandbox.bwrap_backend.BwrapBackend", return_value=MagicMock()),
        patch("chatServer.services.storage_sync.StorageSync"),
        patch.dict(os.environ, {"SUPABASE_URL": "", "SUPABASE_SERVICE_ROLE_KEY": ""}),
        patch("deepagents.create_deep_agent", return_value=mock_graph) as mock_create,
    ):
        await mod.build_deep_agent("user-1", "clarity", "session-1", "web")

    call_kwargs = mock_create.call_args.kwargs
    assert call_kwargs["model"] == "anthropic:claude-sonnet-4-20250514"


@pytest.mark.asyncio
async def test_build_deep_agent_model_with_existing_prefix_unchanged():
    """Model with existing 'provider:' prefix is not double-prefixed."""
    agent_config = {
        "id": "agent-id-1",
        "agent_name": "clarity",
        "soul": "Be helpful.",
        "identity": {"name": "Clarity"},
        "prompt_template": None,
        "llm_config": {"model": "openai:gpt-4o"},
    }
    mock_graph = _make_mock_graph()
    with (
        patch("chatServer.services.agent_config_cache_service.get_cached_agent_config", new=AsyncMock(return_value=agent_config)),  # noqa: E501
        patch("src.core.agent_loader_db.load_tools_from_db", return_value=[]),
        patch("src.core.agent_loader_db._fetch_agent_config_from_db_async", new=AsyncMock(return_value=agent_config)),  # noqa: E501
        patch("src.core.agent_loader_db._prefetch_memory_notes", new=AsyncMock(return_value=None)),
        patch("src.core.agent_loader_db._resolve_memory_user_id", new=AsyncMock(return_value="user-1")),
        patch("chatServer.services.tool_cache_service.get_cached_tools_for_agent", new=AsyncMock(return_value=[])),  # noqa: E501
        patch("chatServer.services.user_instructions_cache_service.get_cached_user_instructions", new=AsyncMock(return_value=None)),  # noqa: E501
        patch("chatServer.database.supabase_client.create_user_scoped_client", new=AsyncMock(return_value=MagicMock())),  # noqa: E501
        patch("chatServer.security.tool_wrapper.wrap_tools_with_approval"),
        patch("chatServer.services.audit_service.AuditService", return_value=MagicMock()),
        patch("chatServer.services.pending_actions.PendingActionsService", return_value=MagicMock()),
        patch("chatServer.services.notification_service.NotificationService", return_value=MagicMock()),
        patch("chatServer.security.tool_wrapper.ApprovalContext", return_value=MagicMock()),

        patch("chatServer.sandbox.bwrap_backend.BwrapBackend", return_value=MagicMock()),
        patch("chatServer.services.storage_sync.StorageSync"),
        patch.dict(os.environ, {"SUPABASE_URL": "", "SUPABASE_SERVICE_ROLE_KEY": ""}),
        patch("deepagents.create_deep_agent", return_value=mock_graph) as mock_create,
    ):
        await mod.build_deep_agent("user-1", "clarity", "session-1", "web")

    call_kwargs = mock_create.call_args.kwargs
    assert call_kwargs["model"] == "openai:gpt-4o"


@pytest.mark.asyncio
async def test_build_deep_agent_passes_tools_and_backend():
    """create_deep_agent receives tools, BwrapBackend, skills, and system_prompt."""
    agent_config = {
        "id": "agent-id-1",
        "agent_name": "clarity",
        "soul": "Be helpful.",
        "identity": {"name": "Clarity"},
        "prompt_template": None,
        "llm_config": {},
    }
    mock_tool = MagicMock()
    mock_backend = MagicMock()
    mock_graph = _make_mock_graph()
    with (
        patch("chatServer.services.agent_config_cache_service.get_cached_agent_config", new=AsyncMock(return_value=agent_config)),  # noqa: E501
        patch("src.core.agent_loader_db.load_tools_from_db", return_value=[mock_tool]),
        patch("src.core.agent_loader_db._fetch_agent_config_from_db_async", new=AsyncMock(return_value=agent_config)),  # noqa: E501
        patch("src.core.agent_loader_db._prefetch_memory_notes", new=AsyncMock(return_value=None)),
        patch("src.core.agent_loader_db._resolve_memory_user_id", new=AsyncMock(return_value="user-1")),
        patch("chatServer.services.tool_cache_service.get_cached_tools_for_agent", new=AsyncMock(return_value=[])),  # noqa: E501
        patch("chatServer.services.user_instructions_cache_service.get_cached_user_instructions", new=AsyncMock(return_value=None)),  # noqa: E501
        patch("chatServer.database.supabase_client.create_user_scoped_client", new=AsyncMock(return_value=MagicMock())),  # noqa: E501
        patch("chatServer.security.tool_wrapper.wrap_tools_with_approval"),
        patch("chatServer.services.audit_service.AuditService", return_value=MagicMock()),
        patch("chatServer.services.pending_actions.PendingActionsService", return_value=MagicMock()),
        patch("chatServer.services.notification_service.NotificationService", return_value=MagicMock()),
        patch("chatServer.security.tool_wrapper.ApprovalContext", return_value=MagicMock()),
        patch("chatServer.sandbox.bwrap_backend.BwrapBackend", return_value=mock_backend),
        patch("chatServer.services.storage_sync.StorageSync"),
        patch.dict(os.environ, {"SUPABASE_URL": "", "SUPABASE_SERVICE_ROLE_KEY": ""}),
        patch("deepagents.create_deep_agent", return_value=mock_graph) as mock_create,
    ):
        await mod.build_deep_agent("user-1", "clarity", "session-1", "web")

    call_kwargs = mock_create.call_args.kwargs
    assert call_kwargs["tools"] == [mock_tool]
    assert call_kwargs["backend"] is mock_backend
    assert call_kwargs["skills"] == ["/skills/"]
    assert call_kwargs["name"] == "clarity"
    assert "system_prompt" in call_kwargs


# ---------------------------------------------------------------------------
# _build_channel_prompt — AC-05 (runtime-only content)
# ---------------------------------------------------------------------------


def test_channel_prompt_includes_channel_guidance():
    prompt = _build_channel_prompt("web")
    assert "Channel" in prompt


def test_channel_prompt_includes_time():
    prompt = _build_channel_prompt("web")
    assert "Current Time" in prompt


def test_channel_prompt_includes_memory_notes():
    prompt = _build_channel_prompt("web", memory_notes="User likes brevity.")
    assert "User likes brevity." in prompt


def test_channel_prompt_includes_user_instructions():
    prompt = _build_channel_prompt("web", user_instructions="Always reply in bullet points.")
    assert "Always reply in bullet points." in prompt


def test_channel_prompt_excludes_soul_and_identity():
    """AC-05: soul/identity are skills — must NOT appear in the channel-only prompt."""
    prompt = _build_channel_prompt("web")
    assert "Soul" not in prompt
    assert "Identity" not in prompt
    assert "Operating Model" not in prompt


def test_channel_prompt_scheduled_mode():
    prompt = _build_channel_prompt("scheduled")
    assert "automated" in prompt.lower() or "scheduled" in prompt.lower()


def test_channel_prompt_heartbeat_mode():
    prompt = _build_channel_prompt("heartbeat")
    assert "HEARTBEAT_OK" in prompt


def test_channel_prompt_onboarding_when_no_memory_or_instructions():
    prompt = _build_channel_prompt("web", memory_notes=None, user_instructions=None)
    assert "first interaction" in prompt.lower() or "onboarding" in prompt.lower()


def test_channel_prompt_no_onboarding_when_memory_exists():
    prompt = _build_channel_prompt("web", memory_notes="Likes cats.")
    assert "Onboarding" not in prompt


def test_channel_prompt_session_open_new_user():
    prompt = _build_channel_prompt("session_open", memory_notes=None, user_instructions=None)
    assert "Session Open" in prompt
    assert "first time" in prompt.lower()


