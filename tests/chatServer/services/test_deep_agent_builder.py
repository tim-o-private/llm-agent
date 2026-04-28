"""Unit tests for deep_agent_builder.py — build_deep_agent and _build_system_prompt."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import chatServer.services.deep_agent_builder as mod
from chatServer.services.deep_agent_builder import (
    _agent_cache,
    _agent_locks,
    _build_system_prompt,
    _collect_tool_guidance,
    _detect_agent_phase,
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

    mock_settings = MagicMock()
    mock_settings.llm_provider = "openai"
    mock_settings.llm_default_model = "kimi-k2.6"
    mock_settings.supabase_url = ""
    mock_settings.supabase_service_key = ""

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
        patch("chatServer.config.settings.get_settings", return_value=mock_settings),
        patch("chatServer.services.storage_sync.StorageSync", return_value=MagicMock(hydrate_user=AsyncMock())),
        patch.dict(os.environ, {"SUPABASE_URL": "", "SUPABASE_SERVICE_ROLE_KEY": "", "SANDBOX_DATA_DIR": "/tmp/test-sandbox"}),  # noqa: E501
        patch.dict("sys.modules", {"langchain_openrouter": MagicMock()}),
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
@pytest.mark.parametrize(
    "provider, model_in, expected",
    [
        ("anthropic", "claude-sonnet-4-5-20250514", "anthropic:claude-sonnet-4-5-20250514"),
        ("anthropic", "anthropic:claude-sonnet-4-5-20250514", "anthropic:claude-sonnet-4-5-20250514"),
    ],
    ids=["anthropic-bare", "anthropic-prefixed"],
)
async def test_build_deep_agent_model_prefix_anthropic(provider, model_in, expected):
    """Anthropic models are prefixed with 'anthropic:' when no prefix present; existing prefixes preserved."""
    config = _make_agent_config()
    config["llm_config"] = {"model": model_in}
    mock_graph = _make_mock_graph()

    mock_settings = MagicMock()
    mock_settings.llm_provider = provider
    mock_settings.llm_default_model = "default-model"
    mock_settings.supabase_url = ""
    mock_settings.supabase_service_key = ""

    patches = _standard_patches(agent_config=config, mock_graph=mock_graph)
    patches[11] = patch("chatServer.config.settings.get_settings", return_value=mock_settings)

    from contextlib import ExitStack
    with ExitStack() as stack:
        cms = [stack.enter_context(p) for p in patches]
        mock_create = cms[-1]
        await mod.build_deep_agent("user-1", "clarity", "session-1", "web")

    call_kwargs = mock_create.call_args.kwargs
    assert call_kwargs["model"] == expected


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "model_in",
    ["gpt-4o", "openai:gpt-4o"],
    ids=["openai-bare", "openai-prefixed"],
)
async def test_build_deep_agent_model_prefix_openai(model_in):
    """OpenAI models are wrapped in a ChatOpenRouter instance with the bare model name."""
    config = _make_agent_config()
    config["llm_config"] = {"model": model_in}
    mock_graph = _make_mock_graph()
    patches = _standard_patches(agent_config=config, mock_graph=mock_graph)

    from contextlib import ExitStack
    with ExitStack() as stack:
        cms = [stack.enter_context(p) for p in patches]
        mock_create = cms[-1]
        await mod.build_deep_agent("user-1", "clarity", "session-1", "web")

    call_kwargs = mock_create.call_args.kwargs
    model_obj = call_kwargs["model"]
    assert not isinstance(model_obj, str)


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


def test_system_prompt_includes_identity():
    prompt = _build_system_prompt(identity={"name": "Clarity", "vibe": "warm"})
    assert "Clarity" in prompt
    assert "warm" in prompt


def test_system_prompt_includes_channel_note():
    prompt = _build_system_prompt(channel="web")
    assert "web app" in prompt.lower() or "markdown" in prompt.lower()


def test_system_prompt_includes_time():
    prompt = _build_system_prompt(channel="web")
    assert "Current time:" in prompt


def test_system_prompt_includes_user_instructions():
    prompt = _build_system_prompt(channel="web", user_instructions="Always reply in bullet points.")
    assert "Always reply in bullet points." in prompt


def test_system_prompt_scheduled_mode():
    prompt = _build_system_prompt(channel="scheduled")
    assert "scheduled" in prompt.lower() or "no one" in prompt.lower()


def test_system_prompt_heartbeat_mode():
    prompt = _build_system_prompt(channel="heartbeat")
    assert "HEARTBEAT_OK" in prompt


def test_system_prompt_session_open_new_user():
    prompt = _build_system_prompt(channel="session_open", user_instructions=None)
    assert "first session" in prompt.lower() or "no prior history" in prompt.lower()


def test_system_prompt_telegram_channel():
    prompt = _build_system_prompt(channel="telegram")
    assert "Telegram" in prompt
    assert "4096" in prompt


def test_system_prompt_includes_tool_guidance_when_provided():
    """When tool_guidance is passed in, it appears in the prompt."""
    guidance = "## Tool Guidance\nTasks: act on them."
    prompt = _build_system_prompt(channel="web", tool_guidance=guidance)
    assert "## Tool Guidance" in prompt
    assert "Tasks: act on them." in prompt


def test_system_prompt_omits_tool_guidance_when_empty():
    """Empty/None tool_guidance means no Tool Guidance section."""
    prompt = _build_system_prompt(channel="web", tool_guidance=None)
    assert "## Tool Guidance" not in prompt
    prompt2 = _build_system_prompt(channel="web", tool_guidance="")
    assert "## Tool Guidance" not in prompt2


def test_system_prompt_session_open_returning_user():
    """Returning-user session_open includes pre-fetched signals and WAKEUP_SILENT protocol."""
    from datetime import timedelta
    lm = datetime.now(timezone.utc) - timedelta(hours=2)
    prompt = _build_system_prompt(
        channel="session_open",
        user_instructions="some instructions",
        last_message_at=lm,
        bootstrap_context="- 1 overdue task: Follow up with Mike",
    )
    assert "2 hour" in prompt
    assert "Follow up with Mike" in prompt
    assert "WAKEUP_SILENT" in prompt


# ---------------------------------------------------------------------------
# _collect_tool_guidance
# ---------------------------------------------------------------------------


class _ToolWithWebSection:
    @classmethod
    def prompt_section(cls, channel):
        if channel == "web":
            return "Tasks: create them when actionable."
        return None


class _ToolWithNoneSection:
    @classmethod
    def prompt_section(cls, channel):
        return None


class _ToolNoPromptSection:
    pass


class _ToolRaises:
    @classmethod
    def prompt_section(cls, channel):
        raise RuntimeError("boom")


class _DupeTool:
    @classmethod
    def prompt_section(cls, channel):
        return "Tasks: create them when actionable."


class TestCollectToolGuidance:
    def test_empty_list_returns_empty_string(self):
        assert _collect_tool_guidance([], "web") == ""

    def test_collects_non_none_strings(self):
        result = _collect_tool_guidance([_ToolWithWebSection()], "web")
        assert "## Tool Guidance" in result
        assert "Tasks: create them when actionable." in result

    def test_skips_tools_without_prompt_section(self):
        result = _collect_tool_guidance([_ToolNoPromptSection(), _ToolWithWebSection()], "web")
        assert "Tasks: create them when actionable." in result

    def test_skips_none_returns(self):
        result = _collect_tool_guidance([_ToolWithNoneSection()], "web")
        assert result == ""

    def test_swallows_exceptions(self):
        result = _collect_tool_guidance([_ToolRaises(), _ToolWithWebSection()], "web")
        assert "Tasks: create them when actionable." in result

    def test_dedupes_identical_strings(self):
        result = _collect_tool_guidance(
            [_ToolWithWebSection(), _DupeTool(), _ToolWithWebSection()],
            "web",
        )
        # The guidance text should appear exactly once in the output.
        assert result.count("Tasks: create them when actionable.") == 1

    def test_honors_channel_routing(self):
        """Tool returns guidance only for 'web' — 'scheduled' yields empty."""
        assert _collect_tool_guidance([_ToolWithWebSection()], "scheduled") == ""

    def test_real_task_tool_guidance_surfaces_executive_function_mandate(self):
        """Regression: the executive-function text in GetTasksTool must reach the prompt."""
        from chatServer.tools.task_tools import GetTasksTool
        # Instantiate with minimum required fields; we never call _arun.
        tool = GetTasksTool(user_id="u1")
        result = _collect_tool_guidance([tool], "web")
        assert "executive function" in result.lower()
        assert "break down" in result.lower() or "concrete steps" in result.lower()


# ---------------------------------------------------------------------------
# Phase detection tests
# ---------------------------------------------------------------------------


class TestDetectAgentPhase:
    """Tests for _detect_agent_phase() — orientation vs. management."""

    def test_empty_seed_is_orientation(self):
        seed = (
            "# Agent Memory\n\n"
            "## Who This Person Is\n"
            "*(Not yet known)*\n\n"
            "## Life Domains\n"
            "*(Work, family, health)*\n\n"
            "## Key People\n"
            "*(Name → relationship)*\n\n"
            "## Active Plans\n"
            "*(Goals the user is working toward)*\n\n"
            "## Open Threads\n"
            "*(Things needing follow-up)*\n\n"
            "## Observations\n"
            "*(Patterns)*\n"
        )
        assert _detect_agent_phase(seed) == "orientation"

    def test_fully_populated_is_management(self):
        content = (
            "# Agent Memory\n\n"
            "## Who This Person Is\n"
            "Tim, runs two businesses. Prefers concise communication.\n\n"
            "## Life Domains\n"
            "Work: Sunday Carpenter, SLVR. Family: two kids, wife.\n\n"
            "## Key People\n"
            "Sarah → wife, manages family calendar\n\n"
            "## Active Plans\n"
            "Goal: grow SLVR subscription revenue. Next step: email campaign.\n\n"
            "## Open Threads\n"
            "Permit renewal due Friday.\n\n"
            "## Observations\n"
            "Responds quickly to business email, ignores newsletters.\n"
        )
        assert _detect_agent_phase(content) == "management"

    def test_partially_populated_below_threshold(self):
        content = (
            "# Agent Memory\n\n"
            "## Who This Person Is\n"
            "Tim, software engineer.\n\n"
            "## Life Domains\n"
            "*(Work, family, health)*\n\n"
            "## Key People\n"
            "*(Name → relationship)*\n\n"
            "## Active Plans\n"
            "*(Goals)*\n\n"
            "## Open Threads\n"
            "Waiting on contractor reply.\n\n"
            "## Observations\n"
            "Prefers prose over bullets.\n"
        )
        # 3 populated (Who, Open Threads, Observations), 3 placeholders
        assert _detect_agent_phase(content) == "orientation"

    def test_at_threshold_is_management(self):
        content = (
            "# Agent Memory\n\n"
            "## Who This Person Is\n"
            "Tim, two businesses.\n\n"
            "## Life Domains\n"
            "Work and family are main domains.\n\n"
            "## Key People\n"
            "*(Name → relationship)*\n\n"
            "## Active Plans\n"
            "Launch email campaign.\n\n"
            "## Open Threads\n"
            "Permit renewal.\n\n"
            "## Observations\n"
            "*(Patterns)*\n"
        )
        # 4 populated (Who, Life Domains, Active Plans, Open Threads)
        assert _detect_agent_phase(content) == "management"

    def test_empty_string_is_orientation(self):
        assert _detect_agent_phase("") == "orientation"

    def test_no_headers_is_orientation(self):
        assert _detect_agent_phase("Some random text") == "orientation"

    def test_old_format_populated_is_management(self):
        """Old-format AGENTS.md with different headers but real content → management."""
        content = (
            "# Agent Memory\n\n"
            "## User Profile\n"
            "Email: user@example.com\n"
            "Active and checking in regularly.\n\n"
            "## Preferences\n"
            "- Prefers prose over bullet points\n"
            "- Wants concise responses\n"
            "- Likes morning check-ins\n\n"
            "## Key Context\n"
            "- Morning routine: 6:45 AM\n"
            "- No active tasks\n"
            "- Wife: Sarah, manages family calendar\n"
            "- Two kids, school pickup at 3pm\n"
            "- Runs Sunday Carpenter and SLVR\n"
            "- Permit renewal due Friday\n"
        )
        assert _detect_agent_phase(content) == "management"

    def test_old_format_sparse_is_orientation(self):
        """Old-format AGENTS.md with very little content → orientation."""
        content = (
            "# Agent Memory\n\n"
            "## User Profile\n"
            "Name unknown.\n\n"
            "## Preferences\n\n"
            "## Key Context\n"
        )
        assert _detect_agent_phase(content) == "orientation"


# ---------------------------------------------------------------------------
# File-based prompt loading tests
# ---------------------------------------------------------------------------


class TestPhaseSkillInjection:
    """Tests for phase-specific skill injection."""

    def test_management_injects_operating_skill(self, tmp_path):
        """Management phase injects operating skill from file."""
        skills_dir = tmp_path / "skills" / "operating"
        skills_dir.mkdir(parents=True)
        (skills_dir / "SKILL.md").write_text(
            "---\nname: operating\n---\n\nConnect before you respond."
        )

        prompt = _build_system_prompt(phase="management", system_dir=tmp_path)
        assert "Connect before you respond" in prompt

    def test_orientation_injects_bootstrapping_skill(self, tmp_path):
        """Orientation phase injects bootstrapping skill from file."""
        skills_dir = tmp_path / "skills" / "bootstrapping"
        skills_dir.mkdir(parents=True)
        (skills_dir / "SKILL.md").write_text(
            "---\nname: bootstrapping\n---\n\nBuild a world model."
        )

        prompt = _build_system_prompt(phase="orientation", system_dir=tmp_path)
        assert "Build a world model" in prompt

    def test_orientation_does_not_include_operating(self, tmp_path):
        """Orientation phase does not inject operating skill."""
        for name in ("bootstrapping", "operating"):
            d = tmp_path / "skills" / name
            d.mkdir(parents=True)
            (d / "SKILL.md").write_text(f"---\nname: {name}\n---\n\n{name} content.")

        prompt = _build_system_prompt(phase="orientation", system_dir=tmp_path)
        assert "bootstrapping content" in prompt
        assert "operating content" not in prompt

    def test_no_skill_injection_without_system_dir(self):
        """Without system_dir, no skills are injected (no crash)."""
        prompt = _build_system_prompt(phase="management", system_dir=None)
        assert prompt  # still produces something

    def test_session_open_new_user(self):
        """New user session_open includes 'first session' marker."""
        prompt = _build_system_prompt(
            channel="session_open", user_instructions=None,
        )
        assert "first session" in prompt.lower() or "no prior history" in prompt.lower()

    def test_session_open_returning_user(self):
        """Returning user session_open includes signals and WAKEUP_SILENT."""
        from datetime import timedelta
        lm = datetime.now(timezone.utc) - timedelta(hours=3)
        prompt = _build_system_prompt(
            channel="session_open",
            user_instructions="yes",
            last_message_at=lm,
            bootstrap_context="2 overdue tasks",
        )
        assert "3 hour" in prompt
        assert "2 overdue tasks" in prompt
        assert "WAKEUP_SILENT" in prompt

    def test_seed_file_reading(self, tmp_path):
        """_read_system_file reads files and strips frontmatter."""
        from chatServer.services.deep_agent_builder import _read_system_file

        path = tmp_path / "test.md"
        path.write_text("---\nname: test\n---\n\nActual content.")
        assert "Actual content." in _read_system_file(path)
        assert "name: test" not in _read_system_file(path)
