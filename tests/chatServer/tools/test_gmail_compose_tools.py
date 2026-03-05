"""Tests for Gmail compose tools — SPEC-029 AC-04 to AC-24."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from chatServer.security.approval_tiers import ApprovalTier, TOOL_APPROVAL_DEFAULTS
from chatServer.tools.gmail_compose_tools import (
    COMPOSE_SCOPE,
    DraftEmailReplyTool,
    SendEmailReplyTool,
)


# --- Fixtures ---

@pytest.fixture
def tool_kwargs():
    """Common kwargs for tool instantiation."""
    return {
        "user_id": "test-user-123",
        "agent_name": "assistant",
        "supabase_url": "https://test.supabase.co",
        "supabase_key": "test-key",
    }


@pytest.fixture
def draft_tool(tool_kwargs):
    return DraftEmailReplyTool(**tool_kwargs)


@pytest.fixture
def send_tool(tool_kwargs):
    return SendEmailReplyTool(**tool_kwargs)


def _mock_connection(account="user@test.com", scopes=None):
    """Create a mock Gmail connection dict."""
    return {
        "connection_id": "conn-123",
        "service_user_email": account,
        "scopes": scopes or [
            "https://www.googleapis.com/auth/gmail.readonly",
            COMPOSE_SCOPE,
            "openid",
            "https://www.googleapis.com/auth/userinfo.email",
        ],
        "access_token": "test-token",
        "refresh_token": "test-refresh",
    }


# --- DraftEmailReplyTool tests ---

class TestDraftEmailReplyTool:

    @pytest.mark.asyncio
    async def test_happy_path_returns_structured_context(self, draft_tool):
        """AC-04: Returns original email + writing style as structured context."""
        mock_conn = _mock_connection()

        with patch(
            "chatServer.tools.gmail_tools.GmailToolProvider._get_gmail_connections",
            new_callable=AsyncMock,
            return_value=[mock_conn],
        ), patch(
            "chatServer.tools.gmail_tools.GmailToolProvider.get_provider_for_account",
            new_callable=AsyncMock,
        ) as mock_get_provider, patch.object(
            draft_tool, "_get_writing_style", new_callable=AsyncMock, return_value="Casual, direct, uses em-dashes"
        ), patch(
            "chatServer.tools.gmail_rate_limiter.GmailRateLimiter.check_and_increment",
            return_value=None,
        ):
            mock_provider = MagicMock()
            mock_get_tool = MagicMock()
            mock_get_tool.arun = AsyncMock(return_value="Subject: Meeting\nFrom: mike@test.com\nHi there...")
            mock_provider.get_gmail_tools = AsyncMock(return_value=[mock_get_tool])
            mock_get_tool.name = "get_message"
            mock_get_provider.return_value = mock_provider

            result = await draft_tool._arun(message_id="msg-123", account="user@test.com")

            ctx = json.loads(result)
            assert "original_email" in ctx
            assert ctx["writing_style"] == "Casual, direct, uses em-dashes"
            assert ctx["account"] == "user@test.com"
            assert ctx["message_id"] == "msg-123"

    @pytest.mark.asyncio
    async def test_no_writing_style_returns_neutral_note(self, draft_tool):
        """AC-05: When no writing style exists, includes a neutral tone note."""
        mock_conn = _mock_connection()

        with patch(
            "chatServer.tools.gmail_tools.GmailToolProvider._get_gmail_connections",
            new_callable=AsyncMock,
            return_value=[mock_conn],
        ), patch(
            "chatServer.tools.gmail_tools.GmailToolProvider.get_provider_for_account",
            new_callable=AsyncMock,
        ) as mock_get_provider, patch.object(
            draft_tool, "_get_writing_style", new_callable=AsyncMock, return_value=None
        ), patch(
            "chatServer.tools.gmail_rate_limiter.GmailRateLimiter.check_and_increment",
            return_value=None,
        ):
            mock_provider = MagicMock()
            mock_get_tool = MagicMock()
            mock_get_tool.arun = AsyncMock(return_value="Subject: Test\nBody here")
            mock_provider.get_gmail_tools = AsyncMock(return_value=[mock_get_tool])
            mock_get_tool.name = "get_message"
            mock_get_provider.return_value = mock_provider

            result = await draft_tool._arun(message_id="msg-123", account="user@test.com")

            ctx = json.loads(result)
            assert "writing_style_note" in ctx
            assert "neutral tone" in ctx["writing_style_note"]

    @pytest.mark.asyncio
    async def test_no_gmail_connection(self, draft_tool):
        """AC-23: When no Gmail connection exists, returns helpful error."""
        with patch(
            "chatServer.tools.gmail_tools.GmailToolProvider._get_gmail_connections",
            new_callable=AsyncMock,
            return_value=[],
        ):
            result = await draft_tool._arun(message_id="msg-123", account="user@test.com")

            assert "No Gmail connection found" in result

    @pytest.mark.asyncio
    async def test_missing_compose_scope_returns_reauth(self, draft_tool):
        """AC-02, AC-23: Missing compose scope returns re-auth message."""
        mock_conn = _mock_connection(scopes=["https://www.googleapis.com/auth/gmail.readonly"])

        with patch(
            "chatServer.tools.gmail_tools.GmailToolProvider._get_gmail_connections",
            new_callable=AsyncMock,
            return_value=[mock_conn],
        ):
            result = await draft_tool._arun(message_id="msg-123", account="user@test.com")

            assert "send permission" in result
            assert "Settings > Integrations" in result

    @pytest.mark.asyncio
    async def test_instructions_passed_through(self, draft_tool):
        """AC-04: User instructions are included in context."""
        mock_conn = _mock_connection()

        with patch(
            "chatServer.tools.gmail_tools.GmailToolProvider._get_gmail_connections",
            new_callable=AsyncMock,
            return_value=[mock_conn],
        ), patch(
            "chatServer.tools.gmail_tools.GmailToolProvider.get_provider_for_account",
            new_callable=AsyncMock,
        ) as mock_get_provider, patch.object(
            draft_tool, "_get_writing_style", new_callable=AsyncMock, return_value=None
        ), patch(
            "chatServer.tools.gmail_rate_limiter.GmailRateLimiter.check_and_increment",
            return_value=None,
        ):
            mock_provider = MagicMock()
            mock_get_tool = MagicMock()
            mock_get_tool.arun = AsyncMock(return_value="Email content")
            mock_provider.get_gmail_tools = AsyncMock(return_value=[mock_get_tool])
            mock_get_tool.name = "get_message"
            mock_get_provider.return_value = mock_provider

            result = await draft_tool._arun(
                message_id="msg-123",
                account="user@test.com",
                instructions="tell them I agree but need more time",
            )

            ctx = json.loads(result)
            assert ctx["user_instructions"] == "tell them I agree but need more time"

    def test_approval_tier_auto_approve(self):
        """AC-06: draft_email_reply has AUTO_APPROVE tier."""
        tier, _ = TOOL_APPROVAL_DEFAULTS["draft_email_reply"]
        assert tier == ApprovalTier.AUTO_APPROVE

    def test_prompt_section_returns_guidance(self):
        """AC-15: prompt_section returns behavioral guidance for web/telegram."""
        section = DraftEmailReplyTool.prompt_section("web")
        assert section is not None
        assert "draft_email_reply" in section
        assert "send_email_reply" in section
        assert "revise" in section.lower()

    def test_prompt_section_none_for_other_channels(self):
        """prompt_section returns None for non-interactive channels."""
        assert DraftEmailReplyTool.prompt_section("heartbeat") is None
        assert DraftEmailReplyTool.prompt_section("scheduled") is None


# --- SendEmailReplyTool tests ---

class TestSendEmailReplyTool:

    def test_approval_tier_requires_approval(self):
        """AC-09: send_email_reply has REQUIRES_APPROVAL tier."""
        tier, _ = TOOL_APPROVAL_DEFAULTS["send_email_reply"]
        assert tier == ApprovalTier.REQUIRES_APPROVAL

    @pytest.mark.asyncio
    async def test_happy_path_sends_email(self, send_tool):
        """AC-08, AC-10: Successful send returns confirmation."""
        mock_conn = _mock_connection()

        with patch(
            "chatServer.tools.gmail_tools.GmailToolProvider._get_gmail_connections",
            new_callable=AsyncMock,
            return_value=[mock_conn],
        ), patch(
            "chatServer.tools.gmail_tools.GmailToolProvider.get_provider_for_account",
            new_callable=AsyncMock,
        ) as mock_get_provider, patch(
            "chatServer.tools.gmail_compose_tools._get_gmail_compose_service",
        ) as mock_compose_cls:
            mock_provider = MagicMock()
            mock_provider._get_google_credentials = AsyncMock(return_value=MagicMock())
            mock_get_provider.return_value = mock_provider

            # _get_gmail_compose_service() returns the class,
            # then class(credentials) returns the instance
            mock_compose_class = MagicMock()
            mock_compose_instance = MagicMock()
            mock_compose_instance.send_reply.return_value = {
                "message_id": "sent-456",
                "thread_id": "thread-abc",
                "to": "mike@example.com",
                "subject": "Re: Timeline",
            }
            mock_compose_class.return_value = mock_compose_instance
            mock_compose_cls.return_value = mock_compose_class

            result = await send_tool._arun(
                message_id="msg-123",
                account="user@test.com",
                body="Sounds good!",
            )

            assert "Email sent successfully" in result
            assert "mike@example.com" in result
            assert "Re: Timeline" in result

    @pytest.mark.asyncio
    async def test_missing_compose_scope(self, send_tool):
        """AC-24: Missing compose scope returns re-auth message."""
        mock_conn = _mock_connection(scopes=["https://www.googleapis.com/auth/gmail.readonly"])

        with patch(
            "chatServer.tools.gmail_tools.GmailToolProvider._get_gmail_connections",
            new_callable=AsyncMock,
            return_value=[mock_conn],
        ):
            result = await send_tool._arun(
                message_id="msg-123",
                account="user@test.com",
                body="Hello",
            )

            assert "send permission" in result

    @pytest.mark.asyncio
    async def test_gmail_api_error(self, send_tool):
        """AC-24: Gmail API errors are returned gracefully."""
        mock_conn = _mock_connection()

        with patch(
            "chatServer.tools.gmail_tools.GmailToolProvider._get_gmail_connections",
            new_callable=AsyncMock,
            return_value=[mock_conn],
        ), patch(
            "chatServer.tools.gmail_tools.GmailToolProvider.get_provider_for_account",
            new_callable=AsyncMock,
        ) as mock_get_provider, patch(
            "chatServer.tools.gmail_compose_tools._get_gmail_compose_service",
        ) as mock_compose_cls:
            mock_provider = MagicMock()
            mock_provider._get_google_credentials = AsyncMock(return_value=MagicMock())
            mock_get_provider.return_value = mock_provider

            mock_compose_class = MagicMock()
            mock_compose_instance = MagicMock()
            mock_compose_instance.send_reply.side_effect = Exception("Gmail API quota exceeded")
            mock_compose_class.return_value = mock_compose_instance
            mock_compose_cls.return_value = mock_compose_class

            result = await send_tool._arun(
                message_id="msg-123",
                account="user@test.com",
                body="Hello",
            )

            assert "Failed to send email reply" in result
            assert "quota" in result.lower()

    @pytest.mark.asyncio
    async def test_get_approval_context(self, send_tool):
        """AC-09a: get_approval_context populates original_subject and original_sender."""
        with patch(
            "chatServer.tools.gmail_tools.GmailToolProvider.get_provider_for_account",
            new_callable=AsyncMock,
        ) as mock_get_provider, patch(
            "googleapiclient.discovery.build",
        ) as mock_build:
            mock_provider = MagicMock()
            mock_provider._get_google_credentials = AsyncMock(return_value=MagicMock())
            mock_get_provider.return_value = mock_provider

            mock_service = MagicMock()
            mock_service.users().messages().get().execute.return_value = {
                "payload": {
                    "headers": [
                        {"name": "Subject", "value": "Renovation Timeline"},
                        {"name": "From", "value": "mike@example.com"},
                    ]
                }
            }
            mock_build.return_value = mock_service

            ctx = await send_tool.get_approval_context(
                message_id="msg-123",
                account="user@test.com",
                body="Hello",
            )

            assert ctx["original_subject"] == "Renovation Timeline"
            assert ctx["original_sender"] == "mike@example.com"

    @pytest.mark.asyncio
    async def test_get_approval_context_handles_error(self, send_tool):
        """AC-09a: get_approval_context returns empty dict on failure."""
        with patch(
            "chatServer.tools.gmail_tools.GmailToolProvider.get_provider_for_account",
            new_callable=AsyncMock,
            side_effect=Exception("Connection failed"),
        ):
            ctx = await send_tool.get_approval_context(
                message_id="msg-123",
                account="user@test.com",
                body="Hello",
            )

            assert ctx == {}

    def test_prompt_section_none(self):
        """SendEmailReplyTool.prompt_section returns None (guidance is on DraftEmailReplyTool)."""
        assert SendEmailReplyTool.prompt_section("web") is None
