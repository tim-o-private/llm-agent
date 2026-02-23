"""Tests for tool prompt_section() classmethods."""

import pytest

from chatServer.tools.email_digest_tool import EmailDigestTool
from chatServer.tools.gmail_tools import GmailSearchTool
from chatServer.tools.memory_tools import StoreMemoryTool
from chatServer.tools.reminder_tools import CreateReminderTool
from chatServer.tools.schedule_tools import CreateScheduleTool
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
        assert "actionable" in result.lower() or "create_task" in result.lower()

    def test_heartbeat_mentions_overdue_or_stale(self):
        """GetTasksTool.prompt_section('heartbeat') mentions overdue or stale."""
        result = GetTasksTool.prompt_section("heartbeat")
        assert "overdue" in result.lower() or "stale" in result.lower()

    def test_web_and_telegram_same(self):
        """GetTasksTool prompt sections for web and telegram are the same."""
        web = GetTasksTool.prompt_section("web")
        telegram = GetTasksTool.prompt_section("telegram")
        assert web == telegram

    def test_unknown_channel_returns_web_default(self):
        """GetTasksTool.prompt_section() for unknown channel returns web default."""
        result = GetTasksTool.prompt_section("unknown_channel")
        web_result = GetTasksTool.prompt_section("web")
        assert result == web_result


class TestStoreMemoryToolPromptSection:
    """Tests for StoreMemoryTool.prompt_section()."""

    def test_web_returns_string(self):
        """StoreMemoryTool.prompt_section('web') returns non-None string."""
        result = StoreMemoryTool.prompt_section("web")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_telegram_returns_string(self):
        """StoreMemoryTool.prompt_section('telegram') returns non-None string."""
        result = StoreMemoryTool.prompt_section("telegram")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_heartbeat_returns_none(self):
        """StoreMemoryTool.prompt_section('heartbeat') returns None."""
        result = StoreMemoryTool.prompt_section("heartbeat")
        assert result is None

    def test_scheduled_returns_none(self):
        """StoreMemoryTool.prompt_section('scheduled') returns None."""
        result = StoreMemoryTool.prompt_section("scheduled")
        assert result is None

    def test_web_mentions_store_and_recall(self):
        """StoreMemoryTool.prompt_section('web') mentions store_memory and recall."""
        result = StoreMemoryTool.prompt_section("web")
        assert "store_memory" in result.lower()
        assert "recall" in result.lower()

    def test_web_and_telegram_same(self):
        """StoreMemoryTool prompt sections for web and telegram are the same."""
        web = StoreMemoryTool.prompt_section("web")
        telegram = StoreMemoryTool.prompt_section("telegram")
        assert web == telegram


class TestGmailSearchToolPromptSection:
    """Tests for GmailSearchTool.prompt_section()."""

    def test_web_returns_string(self):
        """GmailSearchTool.prompt_section('web') returns non-None string."""
        result = GmailSearchTool.prompt_section("web")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_telegram_returns_string(self):
        """GmailSearchTool.prompt_section('telegram') returns non-None string."""
        result = GmailSearchTool.prompt_section("telegram")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_heartbeat_returns_string(self):
        """GmailSearchTool.prompt_section('heartbeat') returns non-None string."""
        result = GmailSearchTool.prompt_section("heartbeat")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_scheduled_returns_none(self):
        """GmailSearchTool.prompt_section('scheduled') returns None."""
        result = GmailSearchTool.prompt_section("scheduled")
        assert result is None

    def test_web_differs_from_heartbeat(self):
        """GmailSearchTool.prompt_section('web') differs from heartbeat."""
        web = GmailSearchTool.prompt_section("web")
        heartbeat = GmailSearchTool.prompt_section("heartbeat")
        assert web != heartbeat

    def test_heartbeat_mentions_unread(self):
        """GmailSearchTool.prompt_section('heartbeat') mentions unread."""
        result = GmailSearchTool.prompt_section("heartbeat")
        assert "unread" in result.lower()

    def test_web_and_telegram_same(self):
        """GmailSearchTool prompt sections for web and telegram are the same."""
        web = GmailSearchTool.prompt_section("web")
        telegram = GmailSearchTool.prompt_section("telegram")
        assert web == telegram


class TestCreateReminderToolPromptSection:
    """Tests for CreateReminderTool.prompt_section()."""

    def test_web_returns_string(self):
        """CreateReminderTool.prompt_section('web') returns non-None string."""
        result = CreateReminderTool.prompt_section("web")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_telegram_returns_string(self):
        """CreateReminderTool.prompt_section('telegram') returns non-None string."""
        result = CreateReminderTool.prompt_section("telegram")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_heartbeat_returns_none(self):
        """CreateReminderTool.prompt_section('heartbeat') returns None."""
        result = CreateReminderTool.prompt_section("heartbeat")
        assert result is None

    def test_scheduled_returns_none(self):
        """CreateReminderTool.prompt_section('scheduled') returns None."""
        result = CreateReminderTool.prompt_section("scheduled")
        assert result is None

    def test_web_mentions_create_reminder(self):
        """CreateReminderTool.prompt_section('web') mentions create_reminder."""
        result = CreateReminderTool.prompt_section("web")
        assert "create_reminder" in result.lower()

    def test_web_and_telegram_same(self):
        """CreateReminderTool prompt sections for web and telegram are the same."""
        web = CreateReminderTool.prompt_section("web")
        telegram = CreateReminderTool.prompt_section("telegram")
        assert web == telegram


class TestCreateScheduleToolPromptSection:
    """Tests for CreateScheduleTool.prompt_section()."""

    def test_web_returns_string(self):
        """CreateScheduleTool.prompt_section('web') returns non-None string."""
        result = CreateScheduleTool.prompt_section("web")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_telegram_returns_string(self):
        """CreateScheduleTool.prompt_section('telegram') returns non-None string."""
        result = CreateScheduleTool.prompt_section("telegram")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_heartbeat_returns_none(self):
        """CreateScheduleTool.prompt_section('heartbeat') returns None."""
        result = CreateScheduleTool.prompt_section("heartbeat")
        assert result is None

    def test_scheduled_returns_none(self):
        """CreateScheduleTool.prompt_section('scheduled') returns None."""
        result = CreateScheduleTool.prompt_section("scheduled")
        assert result is None

    def test_web_mentions_create_schedule(self):
        """CreateScheduleTool.prompt_section('web') mentions create_schedule."""
        result = CreateScheduleTool.prompt_section("web")
        assert "create_schedule" in result.lower()

    def test_web_and_telegram_same(self):
        """CreateScheduleTool prompt sections for web and telegram are the same."""
        web = CreateScheduleTool.prompt_section("web")
        telegram = CreateScheduleTool.prompt_section("telegram")
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


class TestEmailDigestToolPromptSection:
    """Tests for EmailDigestTool.prompt_section()."""

    def test_web_returns_string(self):
        """EmailDigestTool.prompt_section('web') returns non-None string."""
        result = EmailDigestTool.prompt_section("web")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_telegram_returns_string(self):
        """EmailDigestTool.prompt_section('telegram') returns non-None string."""
        result = EmailDigestTool.prompt_section("telegram")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_scheduled_returns_string(self):
        """EmailDigestTool.prompt_section('scheduled') returns non-None string."""
        result = EmailDigestTool.prompt_section("scheduled")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_heartbeat_returns_none(self):
        """EmailDigestTool.prompt_section('heartbeat') returns None."""
        result = EmailDigestTool.prompt_section("heartbeat")
        assert result is None

    def test_scheduled_mentions_notification(self):
        """EmailDigestTool.prompt_section('scheduled') mentions notification."""
        result = EmailDigestTool.prompt_section("scheduled")
        assert "notification" in result.lower()

    def test_web_and_telegram_same(self):
        """EmailDigestTool prompt sections for web and telegram are the same."""
        web = EmailDigestTool.prompt_section("web")
        telegram = EmailDigestTool.prompt_section("telegram")
        assert web == telegram


class TestPromptSectionLengthLimits:
    """Tests that all prompt sections respect length limits."""

    @pytest.mark.parametrize("tool_class", [
        GetTasksTool,
        StoreMemoryTool,
        GmailSearchTool,
        CreateReminderTool,
        CreateScheduleTool,
        UpdateInstructionsTool,
        EmailDigestTool,
    ])
    @pytest.mark.parametrize("channel", ["web", "telegram", "heartbeat", "scheduled"])
    def test_prompt_section_length_under_300_chars(self, tool_class, channel):
        """All prompt_section() returns do not exceed 300 characters."""
        result = tool_class.prompt_section(channel)
        if result is not None:
            assert len(result) <= 300, (
                f"{tool_class.__name__}.prompt_section('{channel}') "
                f"is {len(result)} chars (max 300)"
            )


class TestPromptSectionConsistency:
    """Tests for consistency across all tool classes."""

    @pytest.mark.parametrize("tool_class", [
        GetTasksTool,
        StoreMemoryTool,
        GmailSearchTool,
        CreateReminderTool,
        CreateScheduleTool,
        UpdateInstructionsTool,
        EmailDigestTool,
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
