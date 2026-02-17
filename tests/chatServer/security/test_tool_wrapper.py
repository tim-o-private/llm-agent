"""
Tests for the tool wrapper that enforces approval tiers.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

import sys
sys.path.insert(0, 'chatServer')

from chatServer.security.approval_tiers import ApprovalTier
from chatServer.security.tool_wrapper import (
    ApprovalContext,
    with_approval,
    wrap_tools_with_approval,
    ApprovalRequiredError,
)


class MockTool:
    """Mock LangChain-style tool for testing."""

    def __init__(self, name: str, approval_tier: ApprovalTier = ApprovalTier.AUTO_APPROVE):
        self.name = name
        self.approval_tier = approval_tier
        self._arun_called = False
        self._arun_args = None
        self._arun_kwargs = None
        self._arun_result = "Tool executed successfully"

    async def _arun(self, *args, **kwargs):
        self._arun_called = True
        self._arun_args = args
        self._arun_kwargs = kwargs
        return self._arun_result

    def _run(self, *args, **kwargs):
        return "Sync run"


class TestApprovalContext:
    def test_context_creation(self):
        context = ApprovalContext(
            user_id="test-user",
            session_id="session-123",
            agent_name="test-agent",
        )

        assert context.user_id == "test-user"
        assert context.session_id == "session-123"
        assert context.agent_name == "test-agent"
        assert context.db_client is None
        assert context.pending_actions_service is None
        assert context.audit_service is None


class TestWithApproval:
    @pytest.mark.asyncio
    async def test_auto_approve_executes_immediately(self):
        tool = MockTool(name="get_tasks", approval_tier=ApprovalTier.AUTO_APPROVE)
        context = ApprovalContext(user_id="test-user")

        with patch('chatServer.security.tool_wrapper.get_effective_tier') as mock_tier:
            mock_tier.return_value = ApprovalTier.AUTO_APPROVE
            wrapped_tool = with_approval(tool, context)
            result = await wrapped_tool._arun(status="pending")

        assert tool._arun_called is True
        assert tool._arun_kwargs == {"status": "pending"}
        assert result == "Tool executed successfully"

    @pytest.mark.asyncio
    async def test_requires_approval_queues_action(self):
        tool = MockTool(name="gmail_send_message", approval_tier=ApprovalTier.REQUIRES_APPROVAL)

        mock_pending_service = AsyncMock()
        mock_pending_service.queue_action.return_value = "action-123"

        context = ApprovalContext(
            user_id="test-user",
            pending_actions_service=mock_pending_service,
        )

        with patch('chatServer.security.tool_wrapper.get_effective_tier') as mock_tier:
            mock_tier.return_value = ApprovalTier.REQUIRES_APPROVAL
            wrapped_tool = with_approval(tool, context)
            result = await wrapped_tool._arun(to="test@example.com", subject="Test")

        assert tool._arun_called is False
        mock_pending_service.queue_action.assert_called_once()
        call_kwargs = mock_pending_service.queue_action.call_args[1]
        assert call_kwargs["user_id"] == "test-user"
        assert call_kwargs["tool_name"] == "gmail_send_message"
        assert "queued" in result.lower()
        assert "action-123" in result

    @pytest.mark.asyncio
    async def test_auto_approve_with_audit_logging(self):
        tool = MockTool(name="get_tasks", approval_tier=ApprovalTier.AUTO_APPROVE)
        mock_audit_service = AsyncMock()

        context = ApprovalContext(
            user_id="test-user",
            session_id="session-123",
            agent_name="test-agent",
            audit_service=mock_audit_service,
        )

        with patch('chatServer.security.tool_wrapper.get_effective_tier') as mock_tier:
            mock_tier.return_value = ApprovalTier.AUTO_APPROVE
            wrapped_tool = with_approval(tool, context)
            await wrapped_tool._arun(limit=10)

        mock_audit_service.log_action.assert_called_once()
        call_kwargs = mock_audit_service.log_action.call_args[1]
        assert call_kwargs["user_id"] == "test-user"
        assert call_kwargs["tool_name"] == "get_tasks"
        assert call_kwargs["approval_status"] == "auto_approved"
        assert call_kwargs["execution_status"] == "success"

    @pytest.mark.asyncio
    async def test_auto_approve_logs_errors(self):
        tool = MockTool(name="get_tasks")

        async def failing_arun(*args, **kwargs):
            raise Exception("Database connection failed")

        tool._arun = failing_arun
        mock_audit_service = AsyncMock()

        context = ApprovalContext(
            user_id="test-user",
            audit_service=mock_audit_service,
        )

        with patch('chatServer.security.tool_wrapper.get_effective_tier') as mock_tier:
            mock_tier.return_value = ApprovalTier.AUTO_APPROVE
            wrapped_tool = with_approval(tool, context)

            with pytest.raises(Exception, match="Database connection failed"):
                await wrapped_tool._arun()

        mock_audit_service.log_action.assert_called_once()
        call_kwargs = mock_audit_service.log_action.call_args[1]
        assert call_kwargs["execution_status"] == "error"
        assert "Database connection failed" in call_kwargs["error_message"]

    @pytest.mark.asyncio
    async def test_requires_approval_without_pending_service(self):
        tool = MockTool(name="gmail_send_message")

        context = ApprovalContext(
            user_id="test-user",
            pending_actions_service=None,
        )

        with patch('chatServer.security.tool_wrapper.get_effective_tier') as mock_tier:
            mock_tier.return_value = ApprovalTier.REQUIRES_APPROVAL
            wrapped_tool = with_approval(tool, context)
            result = await wrapped_tool._arun(to="test@example.com")

        assert "error" in result.lower()
        assert tool._arun_called is False


class TestWrapToolsWithApproval:
    @pytest.mark.asyncio
    async def test_wraps_multiple_tools(self):
        tools = [MockTool(name="tool1"), MockTool(name="tool2"), MockTool(name="tool3")]
        context = ApprovalContext(user_id="test-user")

        wrapped = wrap_tools_with_approval(tools, context)

        assert len(wrapped) == 3
        for original, result in zip(tools, wrapped):
            assert original is result


class TestSecurityInvariants:
    @pytest.mark.asyncio
    async def test_wrapper_always_checks_tier_before_executing(self):
        tool = MockTool(name="dangerous_tool")
        context = ApprovalContext(user_id="test-user")

        tier_check_count = 0

        async def counting_get_effective_tier(*args, **kwargs):
            nonlocal tier_check_count
            tier_check_count += 1
            return ApprovalTier.AUTO_APPROVE

        with patch('chatServer.security.tool_wrapper.get_effective_tier', counting_get_effective_tier):
            wrapped_tool = with_approval(tool, context)
            await wrapped_tool._arun()

        assert tier_check_count == 1

    @pytest.mark.asyncio
    async def test_wrapper_cannot_be_bypassed_by_tool_modification(self):
        tool = MockTool(name="gmail_send_message")
        mock_pending_service = AsyncMock()
        mock_pending_service.queue_action.return_value = "action-123"

        context = ApprovalContext(
            user_id="test-user",
            pending_actions_service=mock_pending_service,
        )

        with patch('chatServer.security.tool_wrapper.get_effective_tier') as mock_tier:
            mock_tier.return_value = ApprovalTier.REQUIRES_APPROVAL
            wrapped_tool = with_approval(tool, context)

            # Attacker tries to modify the tool's approval tier after wrapping
            tool.approval_tier = ApprovalTier.AUTO_APPROVE

            result = await wrapped_tool._arun(to="test@example.com")

        assert tool._arun_called is False
        mock_pending_service.queue_action.assert_called_once()
