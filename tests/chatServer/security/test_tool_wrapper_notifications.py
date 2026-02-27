"""
Tests for approval flow notification integration in tool_wrapper.
"""

import sys
from unittest.mock import AsyncMock, patch

import pytest

sys.path.insert(0, 'chatServer')

from chatServer.security.approval_tiers import ApprovalTier
from chatServer.security.tool_wrapper import (
    ApprovalContext,
    with_approval,
)


class MockTool:
    """Mock LangChain-style tool for testing."""

    def __init__(self, name: str):
        self.name = name
        self._arun_called = False
        self._arun_result = "Tool executed successfully"

    async def _arun(self, *args, **kwargs):
        self._arun_called = True
        return self._arun_result

    def _run(self, *args, **kwargs):
        return "Sync run"


class TestToolWrapperNotifications:
    @pytest.mark.asyncio
    async def test_tool_wrapper_creates_notification_and_action(self):
        """Both queue_action and notify_user are called when approval required."""
        tool = MockTool(name="gmail_send_message")

        mock_pending_service = AsyncMock()
        mock_pending_service.queue_action.return_value = "action-456"

        mock_notification_service = AsyncMock()
        mock_notification_service.notify_user.return_value = "notif-789"

        context = ApprovalContext(
            user_id="test-user",
            session_id="session-1",
            agent_name="assistant",
            pending_actions_service=mock_pending_service,
            notification_service=mock_notification_service,
        )

        with patch('chatServer.security.tool_wrapper.get_effective_tier') as mock_tier:
            mock_tier.return_value = ApprovalTier.REQUIRES_APPROVAL
            wrapped_tool = with_approval(tool, context)
            result = await wrapped_tool._arun(to="user@example.com", subject="Hello")

        mock_pending_service.queue_action.assert_called_once()
        mock_notification_service.notify_user.assert_called_once()

        notify_kwargs = mock_notification_service.notify_user.call_args[1]
        assert notify_kwargs["user_id"] == "test-user"
        assert notify_kwargs["type"] == "notify"
        assert notify_kwargs["requires_approval"] is True
        assert notify_kwargs["pending_action_id"] == "action-456"
        assert "gmail_send_message" in notify_kwargs["title"]

        assert "approval" in result.lower()
        assert tool._arun_called is False

    @pytest.mark.asyncio
    async def test_tool_wrapper_soft_message(self):
        """Return message does NOT contain 'STOP' or 'Do NOT retry'."""
        tool = MockTool(name="gmail_send_message")

        mock_pending_service = AsyncMock()
        mock_pending_service.queue_action.return_value = "action-111"

        context = ApprovalContext(
            user_id="test-user",
            pending_actions_service=mock_pending_service,
        )

        with patch('chatServer.security.tool_wrapper.get_effective_tier') as mock_tier:
            mock_tier.return_value = ApprovalTier.REQUIRES_APPROVAL
            wrapped_tool = with_approval(tool, context)
            result = await wrapped_tool._arun()

        assert "STOP" not in result
        assert "Do NOT retry" not in result
        assert "approval" in result.lower()

    @pytest.mark.asyncio
    async def test_tool_wrapper_notification_failure_nonfatal(self):
        """Notification failure is non-fatal: action still queued, soft message returned."""
        tool = MockTool(name="gmail_send_message")

        mock_pending_service = AsyncMock()
        mock_pending_service.queue_action.return_value = "action-222"

        mock_notification_service = AsyncMock()
        mock_notification_service.notify_user.side_effect = Exception("DB unavailable")

        context = ApprovalContext(
            user_id="test-user",
            pending_actions_service=mock_pending_service,
            notification_service=mock_notification_service,
        )

        with patch('chatServer.security.tool_wrapper.get_effective_tier') as mock_tier:
            mock_tier.return_value = ApprovalTier.REQUIRES_APPROVAL
            wrapped_tool = with_approval(tool, context)
            result = await wrapped_tool._arun()

        mock_pending_service.queue_action.assert_called_once()
        assert "approval" in result.lower()
        assert "STOP" not in result
        assert tool._arun_called is False

    @pytest.mark.asyncio
    async def test_tool_wrapper_no_notification_service_graceful(self):
        """notification_service=None: still queues action, returns soft message."""
        tool = MockTool(name="gmail_send_message")

        mock_pending_service = AsyncMock()
        mock_pending_service.queue_action.return_value = "action-333"

        context = ApprovalContext(
            user_id="test-user",
            pending_actions_service=mock_pending_service,
            notification_service=None,
        )

        with patch('chatServer.security.tool_wrapper.get_effective_tier') as mock_tier:
            mock_tier.return_value = ApprovalTier.REQUIRES_APPROVAL
            wrapped_tool = with_approval(tool, context)
            result = await wrapped_tool._arun()

        mock_pending_service.queue_action.assert_called_once()
        assert "approval" in result.lower()
        assert "STOP" not in result
        assert tool._arun_called is False


class TestApproveRejectNotifications:
    @pytest.mark.asyncio
    async def test_approve_creates_followup_notification(self):
        """Approve endpoint creates a silent follow-up notification."""
        from chatServer.routers.actions import approve_action

        mock_db = AsyncMock()

        mock_pending_service = AsyncMock()
        mock_action = AsyncMock()
        mock_action.tool_name = "gmail_send_message"
        mock_pending_service.get_action.return_value = mock_action

        mock_result = AsyncMock()
        mock_result.success = True
        mock_result.result = "Done"
        mock_result.error = None
        mock_pending_service.approve_action.return_value = mock_result

        mock_notification_service = AsyncMock()
        mock_notification_service.notify_user.return_value = "notif-abc"

        with (
            patch('chatServer.routers.actions._build_pending_actions_service', return_value=mock_pending_service),
            patch('chatServer.routers.actions._build_notification_service', return_value=mock_notification_service),
        ):
            response = await approve_action(
                action_id="action-xyz",
                user_id="test-user",
                db=mock_db,
            )

        mock_notification_service.notify_user.assert_called_once()
        notify_kwargs = mock_notification_service.notify_user.call_args[1]
        assert notify_kwargs["type"] == "silent"
        assert notify_kwargs["category"] == "agent_result"
        assert "gmail_send_message" in notify_kwargs["title"]
        assert response.success is True

    @pytest.mark.asyncio
    async def test_reject_creates_followup_notification(self):
        """Reject endpoint creates a silent follow-up notification."""
        from chatServer.routers.actions import ActionRejectionRequest, reject_action

        mock_db = AsyncMock()

        mock_pending_service = AsyncMock()
        mock_action = AsyncMock()
        mock_action.tool_name = "gmail_send_message"
        mock_pending_service.get_action.return_value = mock_action
        mock_pending_service.reject_action.return_value = True

        mock_notification_service = AsyncMock()
        mock_notification_service.notify_user.return_value = "notif-def"

        with (
            patch('chatServer.routers.actions._build_pending_actions_service', return_value=mock_pending_service),
            patch('chatServer.routers.actions._build_notification_service', return_value=mock_notification_service),
        ):
            response = await reject_action(
                action_id="action-xyz",
                request=ActionRejectionRequest(reason="Not needed"),
                user_id="test-user",
                db=mock_db,
            )

        mock_notification_service.notify_user.assert_called_once()
        notify_kwargs = mock_notification_service.notify_user.call_args[1]
        assert notify_kwargs["type"] == "silent"
        assert notify_kwargs["category"] == "agent_result"
        assert "gmail_send_message" in notify_kwargs["title"]
        assert "Not needed" in notify_kwargs["body"]
        assert response.success is True
