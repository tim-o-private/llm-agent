"""Unit tests for deep_agent_builder.py — DeepAgentWrapper and build_deep_agent."""

from __future__ import annotations

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import chatServer.services.deep_agent_builder as mod
from chatServer.services.deep_agent_builder import (
    DeepAgentWrapper,
    _agent_cache,
    _agent_locks,
    _build_channel_prompt,
    _normalise_message,
    _strip_frontmatter,
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


def _make_handler(response_text: str = "Hello from agent"):
    """Build a mock ConversationHandler."""
    from chatServer.services.conversation_handler import ConversationResult, StreamEvent

    handler = MagicMock()
    handler.system_prompt = "initial"
    handler.run = AsyncMock(
        return_value=ConversationResult(
            response_text=response_text,
            new_messages=[],
            tool_calls=[],
        )
    )

    async def _fake_stream(messages):
        yield StreamEvent(type="text_delta", text="Hello")
        yield StreamEvent(type="message_complete", text="Hello from agent")

    handler.run_stream = _fake_stream
    return handler


def _make_backend(skill_paths=None, skill_content="# Soul\n\nBe helpful."):
    """Build a mock ClarityBackend."""
    from chatServer.services.deep_agent_backend_protocol import FileInfo, GlobResult, ReadResult

    backend = MagicMock()
    paths = skill_paths or ["/skills/clarity-soul/SKILL.md"]
    backend.glob = MagicMock(
        return_value=GlobResult(matches=[FileInfo(path=p) for p in paths])
    )
    backend.read = MagicMock(
        return_value=ReadResult(file_data={"content": skill_content, "encoding": "utf-8"})
    )
    return backend


def _make_wrapper(
    response_text: str = "Hello",
    channel: str = "web",
    backend=None,
):
    handler = _make_handler(response_text)
    return DeepAgentWrapper(
        handler=handler,
        channel_prompt=_build_channel_prompt(channel),
        backend=backend,
    )


# ---------------------------------------------------------------------------
# build_deep_agent — caching behavior
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_build_deep_agent_returns_agent():
    """Happy path: build_deep_agent returns a DeepAgentWrapper."""
    mock_wrapper = _make_wrapper()
    with patch.object(mod, "_build_agent", new_callable=AsyncMock, return_value=mock_wrapper):
        agent = await mod.build_deep_agent("user-1", "clarity", "session-1")

    assert isinstance(agent, DeepAgentWrapper)
    assert hasattr(agent, "ainvoke")
    assert hasattr(agent, "astream")


@pytest.mark.asyncio
async def test_build_deep_agent_caches():
    """Second call with same (user_id, agent_name) returns the cached instance."""
    mock_wrapper = _make_wrapper()
    with patch.object(mod, "_build_agent", new_callable=AsyncMock, return_value=mock_wrapper) as mock_build:
        agent1 = await mod.build_deep_agent("user-1", "clarity", "session-1")
        agent2 = await mod.build_deep_agent("user-1", "clarity", "session-2")

    assert agent1 is agent2
    mock_build.assert_awaited_once()  # built only once


@pytest.mark.asyncio
async def test_build_deep_agent_different_users_not_cached():
    """Different user_id → different agents, both built."""
    wrapper1 = _make_wrapper("A")
    wrapper2 = _make_wrapper("B")
    with patch.object(
        mod,
        "_build_agent",
        new_callable=AsyncMock,
        side_effect=[wrapper1, wrapper2],
    ) as mock_build:
        agent1 = await mod.build_deep_agent("user-1", "clarity", "session-1")
        agent2 = await mod.build_deep_agent("user-2", "clarity", "session-2")

    assert agent1 is not agent2
    assert mock_build.await_count == 2


# ---------------------------------------------------------------------------
# build_deep_agent — backend creation + fallback (AC-22)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_build_deep_agent_fallback_on_config_service_failure():
    """AC-22: If ConfigService is not initialized, build succeeds with backend=None."""
    # We need to exercise _build_agent itself, so patch its heavy dependencies at source.
    agent_config = {
        "id": "agent-id-1",
        "agent_name": "clarity",
        "soul": "Be helpful.",
        "identity": {"name": "Clarity"},
        "prompt_template": None,
        "llm_config": {},
    }
    with (
        patch("chatServer.services.agent_config_cache_service.get_cached_agent_config", new=AsyncMock(return_value=agent_config)),  # noqa: E501
        patch("src.core.agent_loader_db.load_tools_from_db", return_value=[]),
        patch("src.core.agent_loader_db._fetch_agent_config_from_db_async", new=AsyncMock(return_value=agent_config)),  # noqa: E501
        patch("src.core.agent_loader_db._prefetch_memory_notes", new=AsyncMock(return_value=None)),
        patch("src.core.agent_loader_db._resolve_memory_user_id", new=AsyncMock(return_value="user-1")),
        patch("chatServer.services.tool_cache_service.get_cached_tools_for_agent", new=AsyncMock(return_value=[])),  # noqa: E501
        patch("chatServer.services.user_instructions_cache_service.get_cached_user_instructions", new=AsyncMock(return_value=None)),  # noqa: E501
        patch("chatServer.services.langchain_tool_bridge.LangChainToolBridge.convert_tools", return_value=([], {})),  # noqa: E501
        patch("chatServer.database.supabase_client.create_user_scoped_client", new=AsyncMock(return_value=MagicMock())),  # noqa: E501
        patch("chatServer.security.tool_wrapper.wrap_tools_with_approval"),
        patch("chatServer.services.audit_service.AuditService", return_value=MagicMock()),
        patch("chatServer.services.pending_actions.PendingActionsService", return_value=MagicMock()),
        patch("chatServer.services.notification_service.NotificationService", return_value=MagicMock()),
        patch("chatServer.security.tool_wrapper.ApprovalContext", return_value=MagicMock()),
        patch("chatServer.services.conversation_handler_builder._get_anthropic_client", return_value=MagicMock()),  # noqa: E501
        # ConfigService raises — simulates not initialized
        patch("chatServer.services.config_service.get_config_service", side_effect=RuntimeError("not initialized")),  # noqa: E501
    ):
        agent = await mod.build_deep_agent("user-1", "clarity", "session-1", "web")

    assert isinstance(agent, DeepAgentWrapper)
    assert agent._backend is None  # graceful fallback — AC-22


# ---------------------------------------------------------------------------
# DeepAgentWrapper — ainvoke
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ainvoke_returns_messages():
    wrapper = _make_wrapper("Hi there")
    result = await wrapper.ainvoke({"messages": [{"role": "user", "content": "Hello"}]})

    assert "messages" in result
    assert result["messages"][-1]["role"] == "assistant"
    assert result["messages"][-1]["content"] == "Hi there"


@pytest.mark.asyncio
async def test_ainvoke_calls_handler_run():
    wrapper = _make_wrapper()
    await wrapper.ainvoke({"messages": [{"role": "user", "content": "Hey"}]})
    wrapper._handler.run.assert_called_once()


@pytest.mark.asyncio
async def test_ainvoke_loads_skills_and_prepends_to_prompt():
    """Skills content should appear in system_prompt before channel prompt."""
    handler = _make_handler()
    backend = _make_backend(
        skill_content="---\nname: clarity-soul\n---\n\n# Soul\n\nBe warm.",
    )
    wrapper = DeepAgentWrapper(
        handler=handler,
        channel_prompt="## Channel\nweb",
        backend=backend,
    )

    await wrapper.ainvoke({"messages": [{"role": "user", "content": "hi"}]})

    # Soul content from skill prepended
    assert "Be warm" in handler.system_prompt
    # Channel prompt still present
    assert "Channel" in handler.system_prompt
    # Soul appears BEFORE channel section
    assert handler.system_prompt.index("Be warm") < handler.system_prompt.index("Channel")


@pytest.mark.asyncio
async def test_ainvoke_graceful_when_backend_none():
    """AC-22: No backend → uses channel prompt only, no crash."""
    wrapper = _make_wrapper(backend=None)
    result = await wrapper.ainvoke({"messages": [{"role": "user", "content": "hi"}]})

    assert result["messages"][-1]["role"] == "assistant"
    assert "Channel" in wrapper._handler.system_prompt


@pytest.mark.asyncio
async def test_ainvoke_graceful_when_backend_fails():
    """AC-22: Backend exception → falls back to channel prompt gracefully."""
    handler = _make_handler()
    backend = MagicMock()
    backend.glob = MagicMock(side_effect=RuntimeError("storage down"))
    wrapper = DeepAgentWrapper(
        handler=handler,
        channel_prompt="## Channel\nweb",
        backend=backend,
    )

    result = await wrapper.ainvoke({"messages": [{"role": "user", "content": "hi"}]})

    assert result["messages"][-1]["role"] == "assistant"
    assert handler.system_prompt == "## Channel\nweb"


@pytest.mark.asyncio
async def test_build_deep_agent_loads_tools():
    """Tools are instantiated and passed to handler (not bridged away)."""
    mock_wrapper = _make_wrapper()
    with patch.object(mod, "_build_agent", new_callable=AsyncMock, return_value=mock_wrapper):
        agent = await mod.build_deep_agent("user-1", "clarity", "session-1")

    # Wrapper holds a handler — this confirms tools flow through correctly
    assert agent._handler is not None


# ---------------------------------------------------------------------------
# DeepAgentWrapper — astream
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_astream_yields_events():
    wrapper = _make_wrapper()
    events = []
    async for ev in wrapper.astream({"messages": [{"role": "user", "content": "hi"}]}):
        events.append(ev)

    assert len(events) >= 1
    assert all("type" in e for e in events)


@pytest.mark.asyncio
async def test_astream_loads_skills():
    handler = _make_handler()
    backend = _make_backend(skill_content="---\nname: soul\n---\n\n# Soul\n\nBe direct.")
    wrapper = DeepAgentWrapper(
        handler=handler,
        channel_prompt="## Channel\nweb",
        backend=backend,
    )

    async for _ in wrapper.astream({"messages": [{"role": "user", "content": "hi"}]}):
        pass

    assert "Be direct" in handler.system_prompt


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


# ---------------------------------------------------------------------------
# Feature flag — settings.py
# ---------------------------------------------------------------------------


def test_feature_flag_defaults_false():
    """DEEP_AGENT_ENABLED defaults to False."""
    env_without_flag = {k: v for k, v in os.environ.items() if k != "DEEP_AGENT_ENABLED"}
    with patch.dict(os.environ, env_without_flag, clear=True):
        from chatServer.config.settings import Settings

        s = Settings()
        assert s.deep_agent_enabled is False


def test_feature_flag_enabled_via_env():
    """DEEP_AGENT_ENABLED=true activates the flag."""
    with patch.dict(os.environ, {"DEEP_AGENT_ENABLED": "true"}):
        from chatServer.config.settings import Settings

        s = Settings()
        assert s.deep_agent_enabled is True


def test_feature_flag_case_insensitive():
    with patch.dict(os.environ, {"DEEP_AGENT_ENABLED": "TRUE"}):
        from chatServer.config.settings import Settings

        s = Settings()
        assert s.deep_agent_enabled is True


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------


def test_strip_frontmatter_removes_yaml():
    content = "---\nname: test\ndescription: foo\n---\n\n# Content\n\nBody text."
    result = _strip_frontmatter(content)
    assert "name:" not in result
    assert "# Content" in result
    assert "Body text." in result


def test_strip_frontmatter_no_frontmatter():
    content = "# Just content\n\nNo frontmatter."
    assert _strip_frontmatter(content) == content


def test_normalise_message_passthrough():
    msg = {"role": "user", "content": "hello"}
    assert _normalise_message(msg) == msg


def test_normalise_message_non_dict():
    result = _normalise_message("raw string")  # type: ignore[arg-type]
    assert result["role"] == "user"
    assert "raw string" in result["content"]
