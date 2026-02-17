"""Unit tests for Gmail tools."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from chatServer.tools.gmail_tools import (
    GmailDigestInput,
    GmailDigestTool,
    GmailSearchInput,
    GmailSearchTool,
    create_gmail_digest_tool,
    create_gmail_search_tool,
)


# Module-level fixtures that can be shared across test classes
@pytest.fixture
def mock_auth_bridge():
    """Mock authentication bridge."""
    mock_bridge = AsyncMock()
    mock_creds = MagicMock()
    mock_bridge.fetch_or_refresh_gmail_credentials.return_value = mock_creds
    return mock_bridge, mock_creds

@pytest.fixture
def mock_gmail_toolkit():
    """Mock Gmail toolkit."""
    mock_toolkit = MagicMock()
    mock_search_tool = MagicMock()
    mock_search_tool.name = "gmail_search"
    mock_search_tool.run.return_value = "Mock search results"

    mock_get_message_tool = MagicMock()
    mock_get_message_tool.name = "gmail_get_message"
    mock_get_message_tool.run.return_value = "Mock message details"

    mock_toolkit.get_tools.return_value = [mock_search_tool, mock_get_message_tool]
    return mock_toolkit, mock_search_tool, mock_get_message_tool


class TestGmailDigestTool:
    """Test suite for GmailDigestTool."""

    @pytest.fixture
    def gmail_digest_tool(self):
        """Create GmailDigestTool instance."""
        return GmailDigestTool(user_id="test_user_123")

    def test_gmail_digest_tool_initialization(self, gmail_digest_tool):
        """Test Gmail digest tool initialization."""
        assert gmail_digest_tool.name == "gmail_digest"
        assert gmail_digest_tool.user_id == "test_user_123"
        assert "Generate a digest of recent emails" in gmail_digest_tool.description
        assert gmail_digest_tool.args_schema == GmailDigestInput
        assert gmail_digest_tool._gmail_toolkit is None
        assert gmail_digest_tool._auth_bridge is None

    def test_gmail_digest_input_validation(self):
        """Test Gmail digest input validation."""
        # Valid input
        valid_input = GmailDigestInput(hours_back=24, max_threads=10, include_read=False)
        assert valid_input.hours_back == 24
        assert valid_input.max_threads == 10
        assert not valid_input.include_read

        # Test defaults
        default_input = GmailDigestInput()
        assert default_input.hours_back == 24
        assert default_input.max_threads == 20
        assert not default_input.include_read

        # Test validation limits
        with pytest.raises(ValueError):
            GmailDigestInput(hours_back=0)  # Below minimum

        with pytest.raises(ValueError):
            GmailDigestInput(hours_back=200)  # Above maximum

        with pytest.raises(ValueError):
            GmailDigestInput(max_threads=0)  # Below minimum

        with pytest.raises(ValueError):
            GmailDigestInput(max_threads=150)  # Above maximum

    @pytest.mark.asyncio
    async def test_get_auth_bridge(self, gmail_digest_tool):
        """Test auth bridge creation."""
        bridge1 = await gmail_digest_tool._get_auth_bridge()
        bridge2 = await gmail_digest_tool._get_auth_bridge()

        # Should return the same instance (cached)
        assert bridge1 is bridge2
        assert gmail_digest_tool._auth_bridge is not None

    @pytest.mark.asyncio
    async def test_get_gmail_toolkit_success(self, gmail_digest_tool, mock_auth_bridge, mock_gmail_toolkit):
        """Test successful Gmail toolkit initialization."""
        mock_bridge, mock_creds = mock_auth_bridge
        mock_toolkit, _, _ = mock_gmail_toolkit

        with patch.object(gmail_digest_tool, '_get_auth_bridge', return_value=mock_bridge):
            with patch('chatServer.tools.gmail_tools.build_resource_service') as mock_build:
                with patch('chatServer.tools.gmail_tools.GmailToolkit', return_value=mock_toolkit):
                    mock_api_resource = MagicMock()
                    mock_build.return_value = mock_api_resource

                    toolkit = await gmail_digest_tool._get_gmail_toolkit()

                    assert toolkit == mock_toolkit
                    mock_bridge.fetch_or_refresh_gmail_credentials.assert_called_once_with("test_user_123")
                    mock_build.assert_called_once_with(credentials=mock_creds)

    @pytest.mark.asyncio
    async def test_get_gmail_toolkit_no_oauth_connection(self, gmail_digest_tool):
        """Test Gmail toolkit initialization when no OAuth connection exists."""
        mock_bridge = AsyncMock()
        mock_bridge.fetch_or_refresh_gmail_credentials.side_effect = ValueError("No OAuth connection")

        with patch.object(gmail_digest_tool, '_get_auth_bridge', return_value=mock_bridge):
            with pytest.raises(RuntimeError, match="Gmail not connected"):
                await gmail_digest_tool._get_gmail_toolkit()

    @pytest.mark.asyncio
    async def test_get_gmail_toolkit_token_refresh_failure(self, gmail_digest_tool):
        """Test Gmail toolkit initialization when token refresh fails."""
        mock_bridge = AsyncMock()
        mock_bridge.fetch_or_refresh_gmail_credentials.side_effect = RuntimeError("Token refresh failed")

        with patch.object(gmail_digest_tool, '_get_auth_bridge', return_value=mock_bridge):
            with pytest.raises(RuntimeError, match="Gmail connection expired"):
                await gmail_digest_tool._get_gmail_toolkit()

    @pytest.mark.asyncio
    async def test_get_gmail_toolkit_general_error(self, gmail_digest_tool):
        """Test Gmail toolkit initialization with general error."""
        mock_bridge = AsyncMock()
        mock_bridge.fetch_or_refresh_gmail_credentials.side_effect = Exception("Network error")

        with patch.object(gmail_digest_tool, '_get_auth_bridge', return_value=mock_bridge):
            with pytest.raises(RuntimeError, match="Gmail service unavailable"):
                await gmail_digest_tool._get_gmail_toolkit()

    @pytest.mark.asyncio
    async def test_get_gmail_tools(self, gmail_digest_tool, mock_gmail_toolkit):
        """Test Gmail tools retrieval."""
        mock_toolkit, mock_search_tool, mock_get_message_tool = mock_gmail_toolkit

        with patch.object(gmail_digest_tool, '_get_gmail_toolkit', return_value=mock_toolkit):
            tools = await gmail_digest_tool._get_gmail_tools()

            assert tools == [mock_search_tool, mock_get_message_tool]
            assert gmail_digest_tool._gmail_tools is not None

    @pytest.mark.asyncio
    async def test_search_recent_emails(self, gmail_digest_tool, mock_gmail_toolkit):
        """Test recent email search functionality."""
        mock_toolkit, mock_search_tool, _ = mock_gmail_toolkit
        mock_search_tool.run.return_value = "Found 5 recent emails"

        with patch.object(gmail_digest_tool, '_get_gmail_tools', return_value=[mock_search_tool]):
            result = await gmail_digest_tool._search_recent_emails(24, False)

            assert result == "Found 5 recent emails"
            mock_search_tool.run.assert_called_once()

            # Check the query construction
            call_args = mock_search_tool.run.call_args[0][0]
            assert "newer_than:24h" in call_args["query"]
            assert "is:unread" in call_args["query"]

    @pytest.mark.asyncio
    async def test_search_recent_emails_include_read(self, gmail_digest_tool, mock_gmail_toolkit):
        """Test recent email search including read emails."""
        mock_toolkit, mock_search_tool, _ = mock_gmail_toolkit

        with patch.object(gmail_digest_tool, '_get_gmail_tools', return_value=[mock_search_tool]):
            await gmail_digest_tool._search_recent_emails(48, True)

            call_args = mock_search_tool.run.call_args[0][0]
            assert "newer_than:2d" in call_args["query"]
            assert "is:unread" not in call_args["query"]

    @pytest.mark.asyncio
    async def test_search_recent_emails_no_search_tool(self, gmail_digest_tool):
        """Test recent email search when search tool is not available."""
        mock_other_tool = MagicMock()
        mock_other_tool.name = "gmail_send"

        with patch.object(gmail_digest_tool, '_get_gmail_tools', return_value=[mock_other_tool]):
            result = await gmail_digest_tool._search_recent_emails(24, False)

            assert result == "Gmail search tool not available"

    @pytest.mark.asyncio
    async def test_get_message_details(self, gmail_digest_tool, mock_gmail_toolkit):
        """Test message details retrieval."""
        mock_toolkit, _, mock_get_message_tool = mock_gmail_toolkit
        mock_get_message_tool.run.return_value = "Message details"

        with patch.object(gmail_digest_tool, '_get_gmail_tools', return_value=[mock_get_message_tool]):
            result = await gmail_digest_tool._get_message_details(["msg1", "msg2"])

            assert result == ["Message details", "Message details"]
            assert mock_get_message_tool.run.call_count == 2

    @pytest.mark.asyncio
    async def test_get_message_details_no_tool(self, gmail_digest_tool):
        """Test message details retrieval when get message tool is not available."""
        mock_other_tool = MagicMock()
        mock_other_tool.name = "gmail_search"

        with patch.object(gmail_digest_tool, '_get_gmail_tools', return_value=[mock_other_tool]):
            result = await gmail_digest_tool._get_message_details(["msg1"])

            assert result == ["Gmail get message tool not available"]

    def test_generate_digest_summary(self, gmail_digest_tool):
        """Test digest summary generation."""
        email_data = """
        Message ID: 123
        Subject: Test Email 1
        Message ID: 456
        Subject: Test Email 2
        """

        summary = gmail_digest_tool._generate_digest_summary(email_data, 24)

        assert "Email Digest - Last 24 hours" in summary
        assert "Found 2 recent emails" in summary
        assert "Test Email 1" in summary
        assert "Test Email 2" in summary

    def test_run_sync_method(self, gmail_digest_tool):
        """Test synchronous run method (should indicate async needed)."""
        result = gmail_digest_tool._run(hours_back=24, max_threads=10, include_read=False)

        assert "Email digest generation initiated" in result
        assert "test_user_123" in result
        assert "async execution context" in result

    @pytest.mark.asyncio
    async def test_arun_success(self, gmail_digest_tool):
        """Test async run method success."""
        mock_search_results = "Subject: Important Email\nSubject: Meeting Reminder"

        with patch.object(gmail_digest_tool, '_search_recent_emails', return_value=mock_search_results):
            result = await gmail_digest_tool._arun(hours_back=24, max_threads=10, include_read=False)

            assert "Email Digest - Last 24 hours" in result
            assert "Found 2 recent emails" in result

    @pytest.mark.asyncio
    async def test_arun_no_emails(self, gmail_digest_tool):
        """Test async run method when no emails found."""
        with patch.object(gmail_digest_tool, '_search_recent_emails', return_value=""):
            result = await gmail_digest_tool._arun(hours_back=24, max_threads=10, include_read=False)

            assert "No emails found in the last 24 hours" in result

    @pytest.mark.asyncio
    async def test_arun_error(self, gmail_digest_tool):
        """Test async run method with error."""
        with patch.object(gmail_digest_tool, '_search_recent_emails', side_effect=Exception("API Error")):
            result = await gmail_digest_tool._arun(hours_back=24, max_threads=10, include_read=False)

            assert "Failed to generate email digest" in result
            assert "API Error" in result


class TestGmailSearchTool:
    """Test suite for GmailSearchTool."""

    @pytest.fixture
    def gmail_search_tool(self):
        """Create GmailSearchTool instance."""
        return GmailSearchTool(user_id="test_user_123")

    def test_gmail_search_tool_initialization(self, gmail_search_tool):
        """Test Gmail search tool initialization."""
        assert gmail_search_tool.name == "gmail_search"
        assert gmail_search_tool.user_id == "test_user_123"
        assert "Search Gmail messages" in gmail_search_tool.description
        assert gmail_search_tool.args_schema == GmailSearchInput
        assert gmail_search_tool._gmail_toolkit is None
        assert gmail_search_tool._auth_bridge is None

    def test_gmail_search_input_validation(self):
        """Test Gmail search input validation."""
        # Valid input
        valid_input = GmailSearchInput(query="is:unread", max_results=10)
        assert valid_input.query == "is:unread"
        assert valid_input.max_results == 10

        # Test defaults
        default_input = GmailSearchInput(query="test")
        assert default_input.query == "test"
        assert default_input.max_results == 20

        # Test validation limits
        with pytest.raises(ValueError):
            GmailSearchInput(query="test", max_results=0)  # Below minimum

        with pytest.raises(ValueError):
            GmailSearchInput(query="test", max_results=150)  # Above maximum

    @pytest.mark.asyncio
    async def test_get_gmail_toolkit_success(self, gmail_search_tool, mock_auth_bridge, mock_gmail_toolkit):
        """Test successful Gmail toolkit initialization."""
        mock_bridge, mock_creds = mock_auth_bridge
        mock_toolkit, _, _ = mock_gmail_toolkit

        with patch.object(gmail_search_tool, '_get_auth_bridge', return_value=mock_bridge):
            with patch('chatServer.tools.gmail_tools.build_resource_service') as mock_build:
                with patch('chatServer.tools.gmail_tools.GmailToolkit', return_value=mock_toolkit):
                    mock_api_resource = MagicMock()
                    mock_build.return_value = mock_api_resource

                    toolkit = await gmail_search_tool._get_gmail_toolkit()

                    assert toolkit == mock_toolkit
                    mock_bridge.fetch_or_refresh_gmail_credentials.assert_called_once_with("test_user_123")

    def test_run_sync_method(self, gmail_search_tool):
        """Test synchronous run method (should indicate async needed)."""
        result = gmail_search_tool._run(query="is:unread", max_results=10)

        assert "Gmail search initiated" in result
        assert "test_user_123" in result
        assert "is:unread" in result
        assert "async execution context" in result

    @pytest.mark.asyncio
    async def test_arun_success(self, gmail_search_tool, mock_gmail_toolkit):
        """Test async run method success."""
        mock_toolkit, mock_search_tool, _ = mock_gmail_toolkit
        mock_search_tool.run.return_value = "Search results: 5 messages found"

        with patch.object(gmail_search_tool, '_get_gmail_toolkit', return_value=mock_toolkit):
            result = await gmail_search_tool._arun(query="is:unread", max_results=10)

            assert result == "Search results: 5 messages found"
            mock_search_tool.run.assert_called_once_with({
                "query": "is:unread",
                "max_results": 10
            })

    @pytest.mark.asyncio
    async def test_arun_no_search_tool(self, gmail_search_tool):
        """Test async run method when search tool is not available."""
        mock_toolkit = MagicMock()
        mock_other_tool = MagicMock()
        mock_other_tool.name = "gmail_send"
        mock_toolkit.get_tools.return_value = [mock_other_tool]

        with patch.object(gmail_search_tool, '_get_gmail_toolkit', return_value=mock_toolkit):
            result = await gmail_search_tool._arun(query="is:unread", max_results=10)

            assert result == "Gmail search tool not available in toolkit"

    @pytest.mark.asyncio
    async def test_arun_error(self, gmail_search_tool):
        """Test async run method with error."""
        with patch.object(gmail_search_tool, '_get_gmail_toolkit', side_effect=Exception("Auth Error")):
            result = await gmail_search_tool._arun(query="is:unread", max_results=10)

            assert "Failed to search Gmail" in result
            assert "Auth Error" in result


class TestGmailToolFactories:
    """Test suite for Gmail tool factory functions."""

    def test_create_gmail_digest_tool(self):
        """Test Gmail digest tool factory function."""
        tool = create_gmail_digest_tool("user123", name="custom_digest")

        assert isinstance(tool, GmailDigestTool)
        assert tool.user_id == "user123"
        assert tool.name == "custom_digest"

    def test_create_gmail_search_tool(self):
        """Test Gmail search tool factory function."""
        tool = create_gmail_search_tool("user456", name="custom_search")

        assert isinstance(tool, GmailSearchTool)
        assert tool.user_id == "user456"
        assert tool.name == "custom_search"


class TestGmailToolsIntegration:
    """Integration tests for Gmail tools working together."""

    @pytest.mark.asyncio
    async def test_digest_and_search_tool_coordination(self, mock_auth_bridge, mock_gmail_toolkit):
        """Test that digest and search tools can work together."""
        mock_bridge, mock_creds = mock_auth_bridge
        mock_toolkit, mock_search_tool, _ = mock_gmail_toolkit

        digest_tool = GmailDigestTool(user_id="test_user")
        search_tool = GmailSearchTool(user_id="test_user")

        # Mock the same toolkit for both tools
        with patch.object(digest_tool, '_get_auth_bridge', return_value=mock_bridge):
            with patch.object(search_tool, '_get_auth_bridge', return_value=mock_bridge):
                with patch('chatServer.tools.gmail_tools.build_resource_service'):
                    with patch('chatServer.tools.gmail_tools.GmailToolkit', return_value=mock_toolkit):

                        # Both tools should be able to get the same toolkit
                        digest_toolkit = await digest_tool._get_gmail_toolkit()
                        search_toolkit = await search_tool._get_gmail_toolkit()

                        assert digest_toolkit == search_toolkit

                        # Both should call the auth bridge
                        assert mock_bridge.fetch_or_refresh_gmail_credentials.call_count == 2

    @pytest.mark.asyncio
    async def test_error_handling_consistency(self):
        """Test that both tools handle errors consistently."""
        digest_tool = GmailDigestTool(user_id="test_user")
        search_tool = GmailSearchTool(user_id="test_user")

        mock_bridge = AsyncMock()
        mock_bridge.fetch_or_refresh_gmail_credentials.side_effect = ValueError("No OAuth connection")

        with patch.object(digest_tool, '_get_auth_bridge', return_value=mock_bridge):
            with patch.object(search_tool, '_get_auth_bridge', return_value=mock_bridge):

                # Both should raise the same type of error with similar messages
                with pytest.raises(RuntimeError, match="Gmail not connected"):
                    await digest_tool._get_gmail_toolkit()

                with pytest.raises(RuntimeError, match="Gmail not connected"):
                    await search_tool._get_gmail_toolkit()
