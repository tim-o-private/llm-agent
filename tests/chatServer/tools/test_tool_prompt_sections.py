"""Tests for tool prompt_section() classmethods."""

import pytest

from chatServer.tools.gmail_tools import SearchGmailTool
from chatServer.tools.memory_tools import CreateMemoriesTool
from chatServer.tools.reminder_tools import GetRemindersTool
from chatServer.tools.schedule_tools import GetSchedulesTool
from chatServer.tools.task_tools import GetTasksTool
from chatServer.tools.update_instructions_tool import UpdateInstructionsTool


class TestGetTasksToolPromptSection:
    """Tests for GetTasksTool.prompt_section()."""

    def test_web_returns_string(self):
        """GetTasksTool.prompt_section('web') returns non-None string."""
        result = GetTasksTool.prompt_section("web")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_telegram_returns_string(self):
        """GetTasksTool.prompt_section('telegram') returns non-None string."""
        result = GetTasksTool.prompt_section("telegram")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_heartbeat_returns_string(self):
        """GetTasksTool.prompt_section('heartbeat') returns non-None string."""
        result = GetTasksTool.prompt_section("heartbeat")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_scheduled_returns_none(self):
        """GetTasksTool.prompt_section('scheduled') returns None."""
        result = GetTasksTool.prompt_section("scheduled")
        assert result is None

    def test_web_mentions_actionable(self):
        """GetTasksTool.prompt_section('web') mentions actionable context."""
        result = GetTasksTool.prompt_section("web")
        assert "actionable" in result.lower() or "create_tasks" in result.lower()

    def test_heartbeat_mentions_overdue_or_stale(self):
        """GetTasksTool.prompt_section('heartbeat') mentions overdue or stale."""
        result = GetTasksTool.prompt_section("heartbeat")
        assert "overdue" in result.lower() or "stale" in result.lower()

    def test_web_and_telegram_same(self):
        """GetTasksTool prompt sections for web and telegram are the same."""
        web = GetTasksTool.prompt_section("web")
        telegram = GetTasksTool.prompt_section("telegram")
        assert web == telegram

    def test_unknown_channel_returns_string(self):
        """GetTasksTool.prompt_section() for unknown channel returns a non-None string."""
        result = GetTasksTool.prompt_section("unknown_channel")
        assert result is not None
        assert "get_tasks" in result
        assert "create_tasks" in result


class TestCreateMemoriesToolPromptSection:
    """Tests for CreateMemoriesTool.prompt_section()."""

    def test_web_returns_string(self):
        """CreateMemoriesTool.prompt_section('web') returns non-None string."""
        result = CreateMemoriesTool.prompt_section("web")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_telegram_returns_string(self):
        """CreateMemoriesTool.prompt_section('telegram') returns non-None string."""
        result = CreateMemoriesTool.prompt_section("telegram")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_heartbeat_returns_none(self):
        """CreateMemoriesTool.prompt_section('heartbeat') returns None."""
        result = CreateMemoriesTool.prompt_section("heartbeat")
        assert result is None

    def test_scheduled_returns_none(self):
        """CreateMemoriesTool.prompt_section('scheduled') returns None."""
        result = CreateMemoriesTool.prompt_section("scheduled")
        assert result is None

    def test_web_mentions_structured_recording_and_search(self):
        """CreateMemoriesTool.prompt_section('web') contains recording guide and search_memories."""
        result = CreateMemoriesTool.prompt_section("web")
        assert "core_identity" in result
        assert "search_memories" in result.lower()

    def test_web_and_telegram_same(self):
        """CreateMemoriesTool prompt sections for web and telegram are the same."""
        web = CreateMemoriesTool.prompt_section("web")
        telegram = CreateMemoriesTool.prompt_section("telegram")
        assert web == telegram


class TestSearchGmailToolPromptSection:
    """Tests for SearchGmailTool.prompt_section()."""

    def test_web_returns_string(self):
        """SearchGmailTool.prompt_section('web') returns non-None string."""
        result = SearchGmailTool.prompt_section("web")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_telegram_returns_string(self):
        """SearchGmailTool.prompt_section('telegram') returns non-None string."""
        result = SearchGmailTool.prompt_section("telegram")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_heartbeat_returns_string(self):
        """SearchGmailTool.prompt_section('heartbeat') returns non-None string."""
        result = SearchGmailTool.prompt_section("heartbeat")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_scheduled_returns_none(self):
        """SearchGmailTool.prompt_section('scheduled') returns None."""
        result = SearchGmailTool.prompt_section("scheduled")
        assert result is None

    def test_web_differs_from_heartbeat(self):
        """SearchGmailTool.prompt_section('web') differs from heartbeat."""
        web = SearchGmailTool.prompt_section("web")
        heartbeat = SearchGmailTool.prompt_section("heartbeat")
        assert web != heartbeat

    def test_heartbeat_mentions_unread(self):
        """SearchGmailTool.prompt_section('heartbeat') mentions unread."""
        result = SearchGmailTool.prompt_section("heartbeat")
        assert "unread" in result.lower()

    def test_web_and_telegram_same(self):
        """SearchGmailTool prompt sections for web and telegram are the same."""
        web = SearchGmailTool.prompt_section("web")
        telegram = SearchGmailTool.prompt_section("telegram")
        assert web == telegram


class TestGetRemindersToolPromptSection:
    """Tests for GetRemindersTool.prompt_section()."""

    def test_web_returns_string(self):
        """GetRemindersTool.prompt_section('web') returns non-None string."""
        result = GetRemindersTool.prompt_section("web")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_telegram_returns_string(self):
        """GetRemindersTool.prompt_section('telegram') returns non-None string."""
        result = GetRemindersTool.prompt_section("telegram")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_heartbeat_returns_none(self):
        """GetRemindersTool.prompt_section('heartbeat') returns None."""
        result = GetRemindersTool.prompt_section("heartbeat")
        assert result is None

    def test_scheduled_returns_none(self):
        """GetRemindersTool.prompt_section('scheduled') returns None."""
        result = GetRemindersTool.prompt_section("scheduled")
        assert result is None

    def test_web_mentions_create_reminders(self):
        """GetRemindersTool.prompt_section('web') mentions create_reminders."""
        result = GetRemindersTool.prompt_section("web")
        assert "create_reminders" in result.lower()

    def test_web_and_telegram_same(self):
        """GetRemindersTool prompt sections for web and telegram are the same."""
        web = GetRemindersTool.prompt_section("web")
        telegram = GetRemindersTool.prompt_section("telegram")
        assert web == telegram


class TestGetSchedulesToolPromptSection:
    """Tests for GetSchedulesTool.prompt_section()."""

    def test_web_returns_string(self):
        """GetSchedulesTool.prompt_section('web') returns non-None string."""
        result = GetSchedulesTool.prompt_section("web")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_telegram_returns_string(self):
        """GetSchedulesTool.prompt_section('telegram') returns non-None string."""
        result = GetSchedulesTool.prompt_section("telegram")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_heartbeat_returns_none(self):
        """GetSchedulesTool.prompt_section('heartbeat') returns None."""
        result = GetSchedulesTool.prompt_section("heartbeat")
        assert result is None

    def test_scheduled_returns_none(self):
        """GetSchedulesTool.prompt_section('scheduled') returns None."""
        result = GetSchedulesTool.prompt_section("scheduled")
        assert result is None

    def test_web_mentions_create_schedules(self):
        """GetSchedulesTool.prompt_section('web') mentions create_schedules."""
        result = GetSchedulesTool.prompt_section("web")
        assert "create_schedules" in result.lower()

    def test_web_and_telegram_same(self):
        """GetSchedulesTool prompt sections for web and telegram are the same."""
        web = GetSchedulesTool.prompt_section("web")
        telegram = GetSchedulesTool.prompt_section("telegram")
        assert web == telegram


class TestUpdateInstructionsToolPromptSection:
    """Tests for UpdateInstructionsTool.prompt_section()."""

    def test_web_returns_string(self):
        """UpdateInstructionsTool.prompt_section('web') returns non-None string."""
        result = UpdateInstructionsTool.prompt_section("web")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_telegram_returns_string(self):
        """UpdateInstructionsTool.prompt_section('telegram') returns non-None string."""
        result = UpdateInstructionsTool.prompt_section("telegram")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_heartbeat_returns_none(self):
        """UpdateInstructionsTool.prompt_section('heartbeat') returns None."""
        result = UpdateInstructionsTool.prompt_section("heartbeat")
        assert result is None

    def test_scheduled_returns_none(self):
        """UpdateInstructionsTool.prompt_section('scheduled') returns None."""
        result = UpdateInstructionsTool.prompt_section("scheduled")
        assert result is None

    def test_web_mentions_always_or_never(self):
        """UpdateInstructionsTool.prompt_section('web') mentions always or never."""
        result = UpdateInstructionsTool.prompt_section("web")
        assert "always" in result.lower() or "never" in result.lower()

    def test_web_and_telegram_same(self):
        """UpdateInstructionsTool prompt sections for web and telegram are the same."""
        web = UpdateInstructionsTool.prompt_section("web")
        telegram = UpdateInstructionsTool.prompt_section("telegram")
        assert web == telegram


class TestPromptSectionLengthLimits:
    """Tests that all prompt sections respect length limits."""

    @pytest.mark.parametrize("tool_class", [
        GetTasksTool,
        CreateMemoriesTool,
        SearchGmailTool,
        GetRemindersTool,
        GetSchedulesTool,
        UpdateInstructionsTool,
    ])
    @pytest.mark.parametrize("channel", ["web", "telegram", "heartbeat", "scheduled"])
    def test_prompt_section_length_under_600_chars(self, tool_class, channel):
        """All prompt_section() returns do not exceed 600 characters."""
        result = tool_class.prompt_section(channel)
        if result is not None:
            assert len(result) <= 600, (
                f"{tool_class.__name__}.prompt_section('{channel}') "
                f"is {len(result)} chars (max 600)"
            )


class TestPromptSectionConsistency:
    """Tests for consistency across all tool classes."""

    @pytest.mark.parametrize("tool_class", [
        GetTasksTool,
        CreateMemoriesTool,
        SearchGmailTool,
        GetRemindersTool,
        GetSchedulesTool,
        UpdateInstructionsTool,
    ])
    def test_prompt_section_returns_str_or_none(self, tool_class):
        """All tool classes have prompt_section() that returns str or None."""
        assert hasattr(tool_class, "prompt_section")
        assert callable(tool_class.prompt_section)
        for channel in ["web", "telegram", "heartbeat", "scheduled"]:
            result = tool_class.prompt_section(channel)
            assert result is None or isinstance(result, str), (
                f"{tool_class.__name__}.prompt_section('{channel}') "
                f"returned {type(result).__name__} instead of str or None"
            )
