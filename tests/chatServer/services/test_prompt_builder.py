"""Tests for prompt builder service."""

from unittest.mock import Mock

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
        assert "## User Instructions" in result
        # Identity section should be absent when identity is None
        assert "## Identity" not in result
        # Memory section is gone (replaced with What You Know)
        assert "## Memory" not in result

    def test_all_sections_populated(self):
        """All sections present when every input is provided."""
        # Create mock tools
        tool1 = Mock()
        tool1.name = "read_memory"
        tool2 = Mock()
        tool2.name = "save_memory"
        tool3 = Mock()
        tool3.name = "update_instructions"

        result = build_agent_prompt(
            soul="Be concise.",
            identity={"name": "Jarvis", "description": "a personal assistant", "vibe": "Calm and direct."},
            channel="web",
            user_instructions="Always respond in bullet points.",
            timezone="America/New_York",
            tools=[tool1, tool2, tool3],
        )
        assert "## Identity" in result
        assert "You are Jarvis" in result
        assert "a personal assistant" in result
        assert "Calm and direct." in result
        assert "## Soul\nBe concise." in result
        assert "web" in result
        assert "America/New_York" in result
        assert "Always respond in bullet points." in result

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
        assert "Don't ask follow-up questions" in result

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

    def test_no_tools_no_tool_guidance_section(self):
        result = build_agent_prompt(soul="x", identity=None, channel="web", user_instructions=None, tools=None)
        assert "## Tool Guidance" not in result

    def test_empty_tools_no_tool_guidance_section(self):
        result = build_agent_prompt(soul="x", identity=None, channel="web", user_instructions=None, tools=[])
        assert "## Tool Guidance" not in result
        assert "Available tools:" not in result

    def test_tools_with_prompt_section_collected(self):
        """Tools with prompt_section() classmethod are collected."""
        tool = Mock()
        tool_cls = Mock()
        tool_cls.prompt_section = Mock(return_value="Use this tool when needed.")
        type(tool).__name__ = "MockTool"
        type(tool).prompt_section = classmethod(lambda cls, ch: "Use this tool when needed.")

        # Create a real mock that tracks type(tool)
        class MockToolClass:
            @classmethod
            def prompt_section(cls, channel):
                return "Use this tool when needed."

        tool = MockToolClass()
        result = build_agent_prompt(
            soul="x", identity=None, channel="web", user_instructions=None,
            tools=[tool],
        )
        assert "## Tool Guidance" in result
        assert "Use this tool when needed." in result

    def test_tools_without_prompt_section_ignored(self):
        """Tools without prompt_section() don't crash the builder."""
        tool = Mock(spec=[])  # No methods
        result = build_agent_prompt(
            soul="x", identity=None, channel="web", user_instructions=None,
            tools=[tool],
        )
        # Should not crash and should not add guidance section if no tools produce guidance
        assert "## Tool Guidance" not in result

    def test_tools_prompt_section_returns_none_omitted(self):
        """Tools that return None from prompt_section() are omitted."""
        class MockTool:
            @classmethod
            def prompt_section(cls, channel):
                return None

        tool = MockTool()
        result = build_agent_prompt(
            soul="x", identity=None, channel="web", user_instructions=None,
            tools=[tool],
        )
        assert "## Tool Guidance" not in result

    def test_tool_deduplication_by_class(self):
        """Two instances of the same class produce only one guidance line."""
        class MockTool:
            @classmethod
            def prompt_section(cls, channel):
                return "Use this tool."

        tool1 = MockTool()
        tool2 = MockTool()
        result = build_agent_prompt(
            soul="x", identity=None, channel="web", user_instructions=None,
            tools=[tool1, tool2],
        )
        assert "## Tool Guidance" in result
        # Count occurrences of the guidance line - should appear only once
        assert result.count("Use this tool.") == 1

    def test_tools_no_available_tools_string(self):
        """The old 'Available tools:' string should never appear."""
        result = build_agent_prompt(
            soul="x", identity=None, channel="web", user_instructions=None,
            tools=[],
        )
        assert "Available tools:" not in result

    def test_empty_soul_uses_default(self):
        result = build_agent_prompt(soul="", identity=None, channel="web", user_instructions=None)
        assert "You are a helpful assistant." in result

    def test_none_soul_uses_default(self):
        result = build_agent_prompt(soul=None, identity=None, channel="web", user_instructions=None)
        assert "You are a helpful assistant." in result

    def test_section_ordering(self):
        """Sections appear in the correct order."""
        class MockTool:
            @classmethod
            def prompt_section(cls, channel):
                return "Tool guidance"

        result = build_agent_prompt(
            soul="Be helpful.",
            identity={"name": "Test", "description": "test agent", "vibe": "cool"},
            channel="web",
            user_instructions="Some instructions.",
            tools=[MockTool()],
        )
        sections = [
            "## Identity", "## Soul", "## Channel", "## Current Time",
            "## User Instructions", "## Tool Guidance",
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

    def test_onboarding_after_tool_guidance_section(self):
        """Onboarding section appears after Tool Guidance section when both present."""
        class MockTool:
            @classmethod
            def prompt_section(cls, channel):
                return "Tool guidance"

        result = build_agent_prompt(
            soul="x", identity=None, channel="web",
            user_instructions=None, memory_notes=None,
            tools=[MockTool()],
        )
        assert "## Onboarding" in result
        guidance_pos = result.index("## Tool Guidance")
        onboarding_pos = result.index("## Onboarding")
        assert onboarding_pos > guidance_pos

    # --- What You Know (pre-loaded memory) ---

    def test_memory_notes_creates_what_you_know_section(self):
        """build_agent_prompt(memory_notes='...') produces ## What You Know section."""
        result = build_agent_prompt(
            soul="x", identity=None, channel="web",
            user_instructions=None, memory_notes="user likes cats"
        )
        assert "## What You Know" in result
        assert "user likes cats" in result
        assert "These are your accumulated notes about this user:" in result

    def test_memory_notes_none_no_what_you_know(self):
        """build_agent_prompt(memory_notes=None) does NOT produce ## What You Know."""
        result = build_agent_prompt(
            soul="x", identity=None, channel="web",
            user_instructions=None, memory_notes=None
        )
        assert "## What You Know" not in result

    def test_memory_notes_empty_no_what_you_know(self):
        """build_agent_prompt(memory_notes='') does NOT produce ## What You Know."""
        result = build_agent_prompt(
            soul="x", identity=None, channel="web",
            user_instructions=None, memory_notes=""
        )
        assert "## What You Know" not in result

    def test_onboarding_with_memory_notes(self):
        """Onboarding not triggered when memory_notes is present."""
        result = build_agent_prompt(
            soul="x", identity=None, channel="web",
            user_instructions=None, memory_notes="notes"
        )
        assert "## Onboarding" not in result
        assert "## What You Know" in result

    def test_onboarding_with_empty_memory_no_instructions_web(self):
        """Onboarding triggered on web when memory_notes=None and user_instructions=None."""
        result = build_agent_prompt(
            soul="x", identity=None, channel="web",
            user_instructions=None, memory_notes=None
        )
        assert "## Onboarding" in result
        assert "## What You Know" not in result

    def test_memory_section_constant_removed(self):
        """MEMORY_SECTION constant no longer exists on the module."""
        from chatServer.services import prompt_builder
        assert not hasattr(prompt_builder, "MEMORY_SECTION")

    def test_memory_notes_truncated_at_4000(self):
        """Memory notes truncated at 4000 characters."""
        long_notes = "a" * 4500 + "MARKER_NOT_IN_TRUNCATED"
        result = build_agent_prompt(
            soul="x", identity=None, channel="web",
            user_instructions=None, memory_notes=long_notes
        )
        # First 4000 chars should be present
        assert "a" * 4000 in result
        # Marker after position 4000 should not appear
        assert "MARKER_NOT_IN_TRUNCATED" not in result

    def test_tool_guidance_comes_from_tools_not_memory_section(self):
        """Memory tool guidance comes from Tool Guidance section, not hardcoded."""
        result = build_agent_prompt(
            soul="x", identity=None, channel="web",
            user_instructions=None, memory_notes=None
        )
        # Old MEMORY_SECTION had "read_memory" and "save_memory" strings
        # But they should no longer appear in a hardcoded memory section
        # (they may appear from Tool Guidance if tools are provided)
        assert "## Memory" not in result
        # The old memory section guidance should be gone
        assert "IMPORTANT: Before answering any question" not in result

    # --- Channel Guidance (FU-4) ---

    def test_channel_guidance_heartbeat_contains_heartbeat_ok(self):
        """CHANNEL_GUIDANCE['heartbeat'] contains 'HEARTBEAT_OK'."""
        from chatServer.services.prompt_builder import CHANNEL_GUIDANCE
        assert "HEARTBEAT_OK" in CHANNEL_GUIDANCE["heartbeat"]

    def test_channel_guidance_heartbeat_contains_use_tools(self):
        """CHANNEL_GUIDANCE['heartbeat'] contains 'Use tools'."""
        from chatServer.services.prompt_builder import CHANNEL_GUIDANCE
        assert "Use tools" in CHANNEL_GUIDANCE["heartbeat"]

    def test_channel_guidance_scheduled_contains_notification(self):
        """CHANNEL_GUIDANCE['scheduled'] contains 'notification'."""
        from chatServer.services.prompt_builder import CHANNEL_GUIDANCE
        assert "notification" in CHANNEL_GUIDANCE["scheduled"]

    def test_channel_guidance_scheduled_contains_dont_ask_follow_up(self):
        """CHANNEL_GUIDANCE['scheduled'] contains 'Don't ask follow-up questions'."""
        from chatServer.services.prompt_builder import CHANNEL_GUIDANCE
        assert "Don't ask follow-up questions" in CHANNEL_GUIDANCE["scheduled"]

    def test_channel_guidance_web_contains_interactive(self):
        """CHANNEL_GUIDANCE['web'] contains 'interactive'."""
        from chatServer.services.prompt_builder import CHANNEL_GUIDANCE
        assert "interactive" in CHANNEL_GUIDANCE["web"]

    def test_channel_guidance_telegram_contains_4096(self):
        """CHANNEL_GUIDANCE['telegram'] contains '4096'."""
        from chatServer.services.prompt_builder import CHANNEL_GUIDANCE
        assert "4096" in CHANNEL_GUIDANCE["telegram"]
