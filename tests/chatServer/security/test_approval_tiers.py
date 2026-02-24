"""
Tests for the approval tier system.

Tests the core security properties:
1. REQUIRES_APPROVAL tools cannot be overridden to auto
2. AUTO_APPROVE tools always execute immediately
3. USER_CONFIGURABLE tools respect user preferences
4. Unknown tools default to REQUIRES_APPROVAL
"""

import sys
from unittest.mock import AsyncMock, MagicMock

import pytest

sys.path.insert(0, 'chatServer')

from chatServer.security.approval_tiers import (
    TOOL_APPROVAL_DEFAULTS,
    ApprovalTier,
    get_effective_tier,
    get_tool_default_tier,
    requires_approval,
    set_user_preference,
)


class TestApprovalTierEnum:
    def test_enum_values(self):
        assert ApprovalTier.AUTO_APPROVE.value == "auto"
        assert ApprovalTier.REQUIRES_APPROVAL.value == "requires_approval"
        assert ApprovalTier.USER_CONFIGURABLE.value == "user_configurable"

    def test_enum_members(self):
        assert len(ApprovalTier) == 3


class TestToolApprovalDefaults:
    def test_gmail_read_tools_are_auto_approve(self):
        tier, _ = TOOL_APPROVAL_DEFAULTS.get("search_gmail", (None, None))
        assert tier == ApprovalTier.AUTO_APPROVE

        tier, _ = TOOL_APPROVAL_DEFAULTS.get("get_gmail", (None, None))
        assert tier == ApprovalTier.AUTO_APPROVE

    def test_get_tasks_is_auto_approve(self):
        tier, _ = TOOL_APPROVAL_DEFAULTS.get("get_tasks", (None, None))
        assert tier == ApprovalTier.AUTO_APPROVE

    def test_create_tasks_is_user_configurable(self):
        tier, _ = TOOL_APPROVAL_DEFAULTS.get("create_tasks", (None, None))
        assert tier == ApprovalTier.USER_CONFIGURABLE

    def test_delete_tools_require_approval_by_default(self):
        for tool_name in ("delete_tasks", "delete_reminders", "delete_schedules"):
            tier, default = TOOL_APPROVAL_DEFAULTS.get(tool_name, (None, None))
            assert tier == ApprovalTier.USER_CONFIGURABLE, f"{tool_name} should be user_configurable"
            assert default == ApprovalTier.REQUIRES_APPROVAL, f"{tool_name} default should be requires_approval"

    def test_memory_tools_are_auto_approve(self):
        memory_tools = [
            "create_memories", "search_memories", "get_memories",
            "update_memories", "delete_memories", "set_project",
            "link_memories", "get_entities", "search_entities", "get_context",
        ]
        for tool_name in memory_tools:
            tier, _ = TOOL_APPROVAL_DEFAULTS.get(tool_name, (None, None))
            assert tier == ApprovalTier.AUTO_APPROVE, f"{tool_name} should be auto-approve"

    def test_update_instructions_requires_approval_by_default(self):
        tier, default = TOOL_APPROVAL_DEFAULTS.get("update_instructions", (None, None))
        assert tier == ApprovalTier.USER_CONFIGURABLE
        assert default == ApprovalTier.REQUIRES_APPROVAL


class TestGetToolDefaultTier:
    def test_known_tool(self):
        tier, default = get_tool_default_tier("search_gmail")
        assert tier == ApprovalTier.AUTO_APPROVE

    def test_unknown_tool_defaults_to_requires_approval(self):
        tier, default = get_tool_default_tier("unknown_dangerous_tool")
        assert tier == ApprovalTier.REQUIRES_APPROVAL
        assert default == ApprovalTier.REQUIRES_APPROVAL


class TestGetEffectiveTier:
    @staticmethod
    def _make_db_mock(execute_data=None):
        """Create a mock Supabase client with sync chain and async execute."""
        mock_db = MagicMock()
        mock_execute = AsyncMock(return_value=MagicMock(data=execute_data))
        chain = mock_db.table.return_value.select.return_value.eq.return_value.eq.return_value.single.return_value
        chain.execute = mock_execute
        upsert_execute = AsyncMock(return_value=MagicMock())
        mock_db.table.return_value.upsert.return_value.execute = upsert_execute
        return mock_db

    @pytest.mark.asyncio
    async def test_auto_approve_always_auto(self):
        tier = await get_effective_tier(
            user_id="search_test_user",
            tool_name="search_gmail",
            db_client=None,
        )
        assert tier == ApprovalTier.AUTO_APPROVE

    @pytest.mark.asyncio
    async def test_user_configurable_with_no_override(self):
        mock_db = self._make_db_mock(None)

        tier = await get_effective_tier(
            user_id="search_test_user",
            tool_name="create_tasks",
            db_client=mock_db,
        )

        _, default = get_tool_default_tier("create_tasks")
        assert tier == default

    @pytest.mark.asyncio
    async def test_user_configurable_with_auto_override(self):
        mock_db = self._make_db_mock({"approval_tier": "auto"})

        tier = await get_effective_tier(
            user_id="search_test_user",
            tool_name="create_tasks",
            db_client=mock_db,
        )

        assert tier == ApprovalTier.AUTO_APPROVE

    @pytest.mark.asyncio
    async def test_user_configurable_with_requires_approval_override(self):
        mock_db = self._make_db_mock({"approval_tier": "requires_approval"})

        tier = await get_effective_tier(
            user_id="search_test_user",
            tool_name="create_tasks",
            db_client=mock_db,
        )

        assert tier == ApprovalTier.REQUIRES_APPROVAL

    @pytest.mark.asyncio
    async def test_unknown_tool_requires_approval(self):
        tier = await get_effective_tier(
            user_id="search_test_user",
            tool_name="some_new_dangerous_tool",
            db_client=None,
        )
        assert tier == ApprovalTier.REQUIRES_APPROVAL


class TestSetUserPreference:
    @pytest.mark.asyncio
    async def test_cannot_set_preference_for_auto_approve(self):
        mock_db = AsyncMock()

        result = await set_user_preference(
            db_client=mock_db,
            user_id="search_test_user",
            tool_name="search_gmail",
            preference="requires_approval",
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_can_set_preference_for_user_configurable(self):
        mock_db = MagicMock()
        mock_db.table.return_value.upsert.return_value.execute = AsyncMock(return_value=MagicMock())

        result = await set_user_preference(
            db_client=mock_db,
            user_id="search_test_user",
            tool_name="create_tasks",
            preference="requires_approval",
        )

        assert result is True
        mock_db.table.assert_called_once_with("user_tool_preferences")

    @pytest.mark.asyncio
    async def test_invalid_preference_rejected(self):
        mock_db = AsyncMock()

        result = await set_user_preference(
            db_client=mock_db,
            user_id="search_test_user",
            tool_name="create_tasks",
            preference="invalid_value",
        )

        assert result is False


class TestRequiresApprovalHelper:
    def test_requires_approval_tier(self):
        assert requires_approval(ApprovalTier.REQUIRES_APPROVAL) is True

    def test_auto_approve_tier(self):
        assert requires_approval(ApprovalTier.AUTO_APPROVE) is False

    def test_user_configurable_tier(self):
        assert requires_approval(ApprovalTier.USER_CONFIGURABLE) is False


class TestSecurityInvariants:
    def test_all_read_operations_are_auto_approve(self):
        read_tools = ["search_gmail", "get_gmail", "get_tasks", "get_reminders", "get_schedules"]
        for tool_name in read_tools:
            tier, _ = TOOL_APPROVAL_DEFAULTS.get(tool_name, (None, None))
            assert tier == ApprovalTier.AUTO_APPROVE, f"{tool_name} should be auto-approve"

    @pytest.mark.asyncio
    async def test_unknown_tool_cannot_bypass_approval(self):
        tier = await get_effective_tier(
            user_id="search_test_user",
            tool_name="dangerous_unknown_tool",
            db_client=None,
        )
        assert tier == ApprovalTier.REQUIRES_APPROVAL
