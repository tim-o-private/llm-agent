"""
Tests for the approval tier system.

Tests the core security properties:
1. REQUIRES_APPROVAL tools cannot be overridden to auto
2. AUTO_APPROVE tools always execute immediately
3. USER_CONFIGURABLE tools respect user preferences
4. Unknown tools default to REQUIRES_APPROVAL
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

import sys
sys.path.insert(0, 'chatServer')

from chatServer.security.approval_tiers import (
    ApprovalTier,
    TOOL_APPROVAL_DEFAULTS,
    get_tool_default_tier,
    get_effective_tier,
    set_user_preference,
    requires_approval,
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
        tier, _ = TOOL_APPROVAL_DEFAULTS.get("gmail_search", (None, None))
        assert tier == ApprovalTier.AUTO_APPROVE

        tier, _ = TOOL_APPROVAL_DEFAULTS.get("gmail_get_message", (None, None))
        assert tier == ApprovalTier.AUTO_APPROVE

    def test_gmail_send_requires_approval(self):
        tier, default = TOOL_APPROVAL_DEFAULTS.get("gmail_send_message", (None, None))
        assert tier == ApprovalTier.REQUIRES_APPROVAL
        assert default == ApprovalTier.REQUIRES_APPROVAL

    def test_get_tasks_is_auto_approve(self):
        tier, _ = TOOL_APPROVAL_DEFAULTS.get("get_tasks", (None, None))
        assert tier == ApprovalTier.AUTO_APPROVE

    def test_create_task_is_user_configurable(self):
        tier, _ = TOOL_APPROVAL_DEFAULTS.get("create_task", (None, None))
        assert tier == ApprovalTier.USER_CONFIGURABLE


class TestGetToolDefaultTier:
    def test_known_tool(self):
        tier, default = get_tool_default_tier("gmail_search")
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
        # Chain: table().select().eq().eq().single().execute()
        chain = mock_db.table.return_value.select.return_value.eq.return_value.eq.return_value.single.return_value
        chain.execute = mock_execute
        # Also for upsert chain: table().upsert().execute()
        upsert_execute = AsyncMock(return_value=MagicMock())
        mock_db.table.return_value.upsert.return_value.execute = upsert_execute
        return mock_db

    @pytest.mark.asyncio
    async def test_requires_approval_cannot_be_overridden(self):
        mock_db = self._make_db_mock({"approval_tier": "auto"})

        tier = await get_effective_tier(
            user_id="test-user",
            tool_name="gmail_send_message",
            db_client=mock_db,
        )

        assert tier == ApprovalTier.REQUIRES_APPROVAL

    @pytest.mark.asyncio
    async def test_auto_approve_always_auto(self):
        tier = await get_effective_tier(
            user_id="test-user",
            tool_name="gmail_search",
            db_client=None,
        )

        assert tier == ApprovalTier.AUTO_APPROVE

    @pytest.mark.asyncio
    async def test_user_configurable_with_no_override(self):
        mock_db = self._make_db_mock(None)

        tier = await get_effective_tier(
            user_id="test-user",
            tool_name="create_task",
            db_client=mock_db,
        )

        _, default = get_tool_default_tier("create_task")
        assert tier == default

    @pytest.mark.asyncio
    async def test_user_configurable_with_auto_override(self):
        mock_db = self._make_db_mock({"approval_tier": "auto"})

        tier = await get_effective_tier(
            user_id="test-user",
            tool_name="gmail_archive",
            db_client=mock_db,
        )

        assert tier == ApprovalTier.AUTO_APPROVE

    @pytest.mark.asyncio
    async def test_user_configurable_with_requires_approval_override(self):
        mock_db = self._make_db_mock({"approval_tier": "requires_approval"})

        tier = await get_effective_tier(
            user_id="test-user",
            tool_name="create_task",
            db_client=mock_db,
        )

        assert tier == ApprovalTier.REQUIRES_APPROVAL

    @pytest.mark.asyncio
    async def test_unknown_tool_requires_approval(self):
        tier = await get_effective_tier(
            user_id="test-user",
            tool_name="some_new_dangerous_tool",
            db_client=None,
        )

        assert tier == ApprovalTier.REQUIRES_APPROVAL


class TestSetUserPreference:
    @pytest.mark.asyncio
    async def test_cannot_override_requires_approval(self):
        mock_db = AsyncMock()

        result = await set_user_preference(
            db_client=mock_db,
            user_id="test-user",
            tool_name="gmail_send_message",
            preference="auto",
        )

        assert result is False
        mock_db.table.assert_not_called()

    @pytest.mark.asyncio
    async def test_cannot_set_preference_for_auto_approve(self):
        mock_db = AsyncMock()

        result = await set_user_preference(
            db_client=mock_db,
            user_id="test-user",
            tool_name="gmail_search",
            preference="requires_approval",
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_can_set_preference_for_user_configurable(self):
        mock_db = MagicMock()
        mock_db.table.return_value.upsert.return_value.execute = AsyncMock(return_value=MagicMock())

        result = await set_user_preference(
            db_client=mock_db,
            user_id="test-user",
            tool_name="create_task",
            preference="requires_approval",
        )

        assert result is True
        mock_db.table.assert_called_once_with("user_tool_preferences")

    @pytest.mark.asyncio
    async def test_invalid_preference_rejected(self):
        mock_db = AsyncMock()

        result = await set_user_preference(
            db_client=mock_db,
            user_id="test-user",
            tool_name="create_task",
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
    def test_all_send_operations_require_approval(self):
        dangerous_tools = ["gmail_send_message"]
        for tool_name in dangerous_tools:
            tier, _ = TOOL_APPROVAL_DEFAULTS.get(tool_name, (None, None))
            assert tier == ApprovalTier.REQUIRES_APPROVAL, f"{tool_name} should require approval"

    def test_all_read_operations_are_auto_approve(self):
        read_tools = ["gmail_search", "gmail_get_message", "get_tasks"]
        for tool_name in read_tools:
            tier, _ = TOOL_APPROVAL_DEFAULTS.get(tool_name, (None, None))
            assert tier == ApprovalTier.AUTO_APPROVE, f"{tool_name} should be auto-approve"

    @pytest.mark.asyncio
    async def test_llm_cannot_bypass_approval_system(self):
        tier = await get_effective_tier(
            user_id="victim-user",
            tool_name="gmail_send_message",
            db_client=None,
        )
        assert tier == ApprovalTier.REQUIRES_APPROVAL
