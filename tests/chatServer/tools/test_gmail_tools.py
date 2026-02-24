"""Tests for Gmail tools — metadata search, format, defaults."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from chatServer.tools.gmail_tools import (
    GetGmailTool,
    MetadataGmailSearch,
    SearchGmailTool,
    GmailSearchInput,
)


class TestMetadataGmailSearch:
    """Tests for MetadataGmailSearch._parse_messages (AC-01)."""

    def test_parse_messages_returns_metadata_only(self):
        """Verify _parse_messages uses format=metadata and returns structured data."""
        # Mock the API resource chain
        mock_api = MagicMock()
        mock_get = MagicMock()
        mock_get.execute.return_value = {
            "threadId": "thread-1",
            "snippet": "Hey, just checking in...",
            "payload": {
                "headers": [
                    {"name": "Subject", "value": "Check in"},
                    {"name": "From", "value": "alice@example.com"},
                    {"name": "Date", "value": "Mon, 24 Feb 2026 10:00:00 -0500"},
                ]
            },
        }
        mock_api.users.return_value.messages.return_value.get.return_value = mock_get

        search = MetadataGmailSearch.model_construct(api_resource=mock_api)
        results = search._parse_messages([{"id": "msg-123"}])

        assert len(results) == 1
        result = results[0]
        assert result["id"] == "msg-123"
        assert result["subject"] == "Check in"
        assert result["sender"] == "alice@example.com"
        assert result["snippet"] == "Hey, just checking in..."
        assert result["date"] == "Mon, 24 Feb 2026 10:00:00 -0500"
        assert "body" not in result  # No body in metadata-only search

        # Verify format="metadata" was used
        mock_api.users().messages().get.assert_called_with(
            userId="me",
            id="msg-123",
            format="metadata",
            metadataHeaders=["Subject", "From", "Date"],
        )

    def test_parse_messages_handles_missing_headers(self):
        """Verify graceful handling when headers are missing."""
        mock_api = MagicMock()
        mock_get = MagicMock()
        mock_get.execute.return_value = {
            "threadId": "thread-2",
            "snippet": "",
            "payload": {"headers": []},
        }
        mock_api.users.return_value.messages.return_value.get.return_value = mock_get

        search = MetadataGmailSearch.model_construct(api_resource=mock_api)
        results = search._parse_messages([{"id": "msg-456"}])

        assert results[0]["subject"] == "(no subject)"
        assert results[0]["sender"] == "(unknown)"
        assert results[0]["date"] == ""


class TestGetGmailToolDescription:
    """Test AC-02: get_gmail description mentions full content."""

    def test_description_mentions_full_content(self):
        assert "full email content" in GetGmailTool.model_fields["description"].default


class TestSearchGmailDefaults:
    """Test AC-03: max_results default is 5."""

    def test_default_max_results_is_5(self):
        schema = GmailSearchInput(query="test")
        assert schema.max_results == 5


class TestSearchGmailFormatResults:
    """Test metadata result formatting."""

    def test_format_metadata_results(self):
        tool = SearchGmailTool(
            user_id="test-user",
            agent_name="search_test_runner",
            supabase_url="http://localhost",
            supabase_key="test-key",
        )
        results = [
            {
                "id": "19c90daa1234",
                "subject": "PR #85 merged",
                "sender": "notifications@github.com",
                "date": "Feb 24",
                "snippet": "Your PR was merged",
            }
        ]
        formatted = tool._format_metadata_results(results)
        assert "[19c90daa1234]" in formatted
        assert "PR #85 merged" in formatted
        assert "notifications@github.com" in formatted
        assert "get_gmail" in formatted.lower()

    def test_format_empty_results(self):
        tool = SearchGmailTool(
            user_id="test-user",
            agent_name="search_test_runner",
            supabase_url="http://localhost",
            supabase_key="test-key",
        )
        formatted = tool._format_metadata_results([])
        assert "No messages found" in formatted
