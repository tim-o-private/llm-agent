"""Tests for prompt builder service."""

from chatServer.services.prompt_builder import (
    MAX_INSTRUCTIONS_LENGTH,
    build_agent_prompt,
)


class TestBuildAgentPrompt:
    def test_minimal_prompt_soul_only(self):
        """Soul-only prompt still includes all mandatory sections."""
        result = build_agent_prompt(
            soul="Be helpful.",
            identity=None,
            channel="web",
            user_instructions=None,
        )
        assert "## Soul\nBe helpful." in result
        assert "## Channel" in result
        assert "## Current Time" in result
        assert "## Memory" in result
        assert "## User Instructions" in result
        # Identity section should be absent when identity is None
        assert "## Identity" not in result

    def test_all_sections_populated(self):
        """All sections present when every input is provided."""
        result = build_agent_prompt(
            soul="Be concise.",
            identity={"name": "Jarvis", "description": "a personal assistant", "vibe": "Calm and direct."},
            channel="web",
            user_instructions="Always respond in bullet points.",
            timezone="America/New_York",
            tool_names=["read_memory", "save_memory", "update_instructions"],
        )
        assert "## Identity" in result
        assert "You are Jarvis" in result
        assert "a personal assistant" in result
        assert "Calm and direct." in result
        assert "## Soul\nBe concise." in result
        assert "web" in result
        assert "America/New_York" in result
        assert "Always respond in bullet points." in result
        assert "read_memory, save_memory, update_instructions" in result

    def test_missing_identity_no_identity_section(self):
        """Identity section omitted when identity is None."""
        result = build_agent_prompt(
            soul="Be helpful.",
            identity=None,
            channel="web",
            user_instructions=None,
        )
        assert "## Identity" not in result

    def test_identity_missing_fields_uses_defaults(self):
        """Identity section uses fallback values for missing fields."""
        result = build_agent_prompt(
            soul="Be helpful.",
            identity={"name": None, "description": None, "vibe": None},
            channel="web",
            user_instructions=None,
        )
        assert "You are an AI assistant" in result
        assert "a personal assistant" in result

    def test_identity_partial_fields(self):
        """Identity works with only some fields set."""
        result = build_agent_prompt(
            soul="Be helpful.",
            identity={"name": "Atlas"},
            channel="web",
            user_instructions=None,
        )
        assert "You are Atlas" in result
        assert "a personal assistant" in result

    def test_channel_web(self):
        result = build_agent_prompt(soul="x", identity=None, channel="web", user_instructions=None)
        assert "web app" in result
        assert "Markdown" in result

    def test_channel_telegram(self):
        result = build_agent_prompt(soul="x", identity=None, channel="telegram", user_instructions=None)
        assert "Telegram" in result
        assert "concise" in result

    def test_channel_scheduled(self):
        result = build_agent_prompt(soul="x", identity=None, channel="scheduled", user_instructions=None)
        assert "automated scheduled run" in result
        assert "don't ask follow-up" in result

    def test_channel_unknown_falls_back_to_web(self):
        result = build_agent_prompt(soul="x", identity=None, channel="unknown_channel", user_instructions=None)
        assert "unknown_channel" in result
        assert "Markdown" in result

    def test_current_time_included(self):
        result = build_agent_prompt(soul="x", identity=None, channel="web", user_instructions=None)
        assert "## Current Time" in result
        # Should contain UTC when no timezone given
        assert "UTC" in result

    def test_current_time_with_timezone(self):
        result = build_agent_prompt(
            soul="x", identity=None, channel="web", user_instructions=None, timezone="Europe/London"
        )
        assert "Europe/London" in result

    def test_current_time_with_invalid_timezone_falls_back(self):
        result = build_agent_prompt(
            soul="x", identity=None, channel="web", user_instructions=None, timezone="Invalid/Zone"
        )
        assert "UTC" in result

    def test_memory_section_always_present(self):
        result = build_agent_prompt(soul="x", identity=None, channel="web", user_instructions=None)
        assert "read_memory" in result
        assert "save_memory" in result
        assert "IMPORTANT" in result

    def test_no_user_instructions(self):
        result = build_agent_prompt(soul="x", identity=None, channel="web", user_instructions=None)
        assert "(No custom instructions set.)" in result
        assert "update_instructions" in result

    def test_user_instructions_present(self):
        result = build_agent_prompt(
            soul="x", identity=None, channel="web", user_instructions="Always use bullet points."
        )
        assert "Always use bullet points." in result
        assert "(No custom instructions set.)" not in result

    def test_user_instructions_truncated(self):
        long_instructions = "x" * (MAX_INSTRUCTIONS_LENGTH + 500)
        result = build_agent_prompt(soul="x", identity=None, channel="web", user_instructions=long_instructions)
        assert "truncated" in result

    def test_empty_user_instructions_treated_as_no_instructions(self):
        result = build_agent_prompt(soul="x", identity=None, channel="web", user_instructions="")
        assert "(No custom instructions set.)" in result

    def test_tool_names_listed(self):
        result = build_agent_prompt(
            soul="x",
            identity=None,
            channel="web",
            user_instructions=None,
            tool_names=["tool_a", "tool_b"],
        )
        assert "## Tools" in result
        assert "tool_a, tool_b" in result

    def test_no_tool_names_no_tools_section(self):
        result = build_agent_prompt(soul="x", identity=None, channel="web", user_instructions=None, tool_names=None)
        assert "## Tools" not in result

    def test_empty_tool_names_no_tools_section(self):
        result = build_agent_prompt(soul="x", identity=None, channel="web", user_instructions=None, tool_names=[])
        assert "## Tools" not in result

    def test_empty_soul_uses_default(self):
        result = build_agent_prompt(soul="", identity=None, channel="web", user_instructions=None)
        assert "You are a helpful assistant." in result

    def test_none_soul_uses_default(self):
        result = build_agent_prompt(soul=None, identity=None, channel="web", user_instructions=None)
        assert "You are a helpful assistant." in result

    def test_section_ordering(self):
        """Sections appear in the correct order."""
        result = build_agent_prompt(
            soul="Be helpful.",
            identity={"name": "Test", "description": "test agent", "vibe": "cool"},
            channel="web",
            user_instructions="Some instructions.",
            tool_names=["tool_a"],
        )
        sections = [
            "## Identity", "## Soul", "## Channel", "## Current Time",
            "## Memory", "## User Instructions", "## Tools",
        ]
        positions = [result.index(s) for s in sections]
        assert positions == sorted(positions), "Sections are not in the expected order"

    # --- Heartbeat channel guidance ---

    def test_channel_heartbeat(self):
        """Heartbeat channel includes heartbeat-specific guidance."""
        result = build_agent_prompt(soul="x", identity=None, channel="heartbeat", user_instructions=None)
        assert "automated heartbeat check" in result
        assert "HEARTBEAT_OK" in result

    # --- Onboarding section ---

    def test_onboarding_web_no_memory_no_instructions(self):
        """Onboarding section present on web when memory_notes=None and user_instructions=None."""
        result = build_agent_prompt(
            soul="x", identity=None, channel="web",
            user_instructions=None, memory_notes=None,
        )
        assert "## Onboarding" in result
        assert "first interaction" in result

    def test_onboarding_telegram_no_memory_no_instructions(self):
        """Onboarding section present on telegram when memory and instructions are empty."""
        result = build_agent_prompt(
            soul="x", identity=None, channel="telegram",
            user_instructions=None, memory_notes=None,
        )
        assert "## Onboarding" in result

    def test_no_onboarding_when_memory_exists(self):
        """No onboarding when memory_notes has content."""
        result = build_agent_prompt(
            soul="x", identity=None, channel="web",
            user_instructions=None, memory_notes="User prefers concise answers",
        )
        assert "## Onboarding" not in result

    def test_no_onboarding_when_instructions_exist(self):
        """No onboarding when user_instructions has content."""
        result = build_agent_prompt(
            soul="x", identity=None, channel="web",
            user_instructions="Always use bullet points.",
            memory_notes=None,
        )
        assert "## Onboarding" not in result

    def test_no_onboarding_on_scheduled_channel(self):
        """No onboarding on non-interactive channels even if memory/instructions are empty."""
        result = build_agent_prompt(
            soul="x", identity=None, channel="scheduled",
            user_instructions=None, memory_notes=None,
        )
        assert "## Onboarding" not in result

    def test_no_onboarding_on_heartbeat_channel(self):
        """No onboarding on heartbeat channel."""
        result = build_agent_prompt(
            soul="x", identity=None, channel="heartbeat",
            user_instructions=None, memory_notes=None,
        )
        assert "## Onboarding" not in result

    def test_onboarding_after_tools_section(self):
        """Onboarding section appears after Tools section when both present."""
        result = build_agent_prompt(
            soul="x", identity=None, channel="web",
            user_instructions=None, memory_notes=None,
            tool_names=["tool_a"],
        )
        assert "## Onboarding" in result
        tools_pos = result.index("## Tools")
        onboarding_pos = result.index("## Onboarding")
        assert onboarding_pos > tools_pos
