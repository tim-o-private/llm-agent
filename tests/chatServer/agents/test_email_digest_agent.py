"""Tests for Email Digest Agent (deprecated class)."""

from unittest.mock import AsyncMock, patch

import pytest

from chatServer.agents.email_digest_agent import EmailDigestAgent, create_email_digest_agent


class TestEmailDigestAgent:
    """Test cases for the deprecated EmailDigestAgent wrapper."""

    @pytest.fixture
    def email_agent(self):
        """Create Email Digest Agent instance."""
        return EmailDigestAgent(
            user_id="test_user_123",
            session_id="test_session_456",
        )

    def test_agent_initialization(self, email_agent):
        """Test agent initialization sets basic attributes."""
        assert email_agent.user_id == "test_user_123"
        assert email_agent.session_id == "test_session_456"
        assert email_agent.agent_name == "email_digest_agent"

    def test_agent_initialization_optional_config_loader(self):
        """Test agent initialization with optional config_loader (backward compat)."""
        agent = EmailDigestAgent(
            user_id="user1",
            session_id="session1",
            config_loader="ignored_value",
        )
        assert agent.user_id == "user1"

    def test_get_agent_info(self, email_agent):
        """Test getting agent information."""
        info = email_agent.get_agent_info()

        assert info["agent_name"] == "email_digest_agent"
        assert info["user_id"] == "test_user_123"
        assert info["session_id"] == "test_session_456"
        assert info["status"] == "deprecated"

    @pytest.mark.asyncio
    async def test_generate_digest_success(self, email_agent):
        """Test successful email digest generation delegates to EmailDigestService."""
        mock_service = AsyncMock()
        mock_service.generate_digest.return_value = {
            "success": True,
            "digest": "Email digest: 5 new emails found...",
        }

        with patch(
            "chatServer.agents.email_digest_agent.EmailDigestService",
            return_value=mock_service,
        ):
            result = await email_agent.generate_digest(hours_back=24, include_read=False)

        assert "Email digest: 5 new emails found..." in result
        mock_service.generate_digest.assert_called_once_with(hours_back=24, include_read=False)

    @pytest.mark.asyncio
    async def test_generate_digest_failure(self, email_agent):
        """Test email digest generation failure returns error message."""
        with patch(
            "chatServer.agents.email_digest_agent.EmailDigestService",
            side_effect=Exception("Service init failed"),
        ):
            result = await email_agent.generate_digest()

        assert "Failed to generate email digest" in result

    @pytest.mark.asyncio
    async def test_search_emails_success(self, email_agent):
        """Test successful email search delegates to EmailDigestService."""
        mock_service = AsyncMock()
        mock_service.generate_digest.return_value = {
            "success": True,
            "digest": "Found 3 emails matching your search...",
        }

        with patch(
            "chatServer.agents.email_digest_agent.EmailDigestService",
            return_value=mock_service,
        ):
            result = await email_agent.search_emails(query="from:test@example.com", max_results=10)

        assert "Found 3 emails matching" in result
        mock_service.generate_digest.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_emails_failure(self, email_agent):
        """Test email search failure returns error message."""
        with patch(
            "chatServer.agents.email_digest_agent.EmailDigestService",
            side_effect=Exception("Search failed"),
        ):
            result = await email_agent.search_emails("test query")

        assert "Failed to search emails" in result

    @pytest.mark.asyncio
    async def test_generate_digest_service_error_result(self, email_agent):
        """Test generate_digest when service returns unsuccessful result."""
        mock_service = AsyncMock()
        mock_service.generate_digest.return_value = {
            "success": False,
            "digest": "Error: No Gmail connection found",
        }

        with patch(
            "chatServer.agents.email_digest_agent.EmailDigestService",
            return_value=mock_service,
        ):
            result = await email_agent.generate_digest()

        assert "Error: No Gmail connection found" in result


class TestCreateEmailDigestAgent:
    """Test the deprecated factory function."""

    @pytest.mark.asyncio
    async def test_create_agent_with_session_id(self):
        """Test factory creates agent with provided session_id."""
        agent = await create_email_digest_agent(user_id="user1", session_id="session1")
        assert agent.user_id == "user1"
        assert agent.session_id == "session1"

    @pytest.mark.asyncio
    async def test_create_agent_generates_session_id(self):
        """Test factory generates session_id when not provided."""
        agent = await create_email_digest_agent(user_id="user1")
        assert agent.user_id == "user1"
        assert agent.session_id.startswith("email_digest_user1_")
