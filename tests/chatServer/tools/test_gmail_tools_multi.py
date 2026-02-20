"""Tests for multi-account Gmail tools (SPEC-008 FU-3)."""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from chatServer.tools.gmail_tools import (
    GmailDigestTool,
    GmailGetMessageTool,
    GmailSearchTool,
    GmailToolProvider,
)


# --- GmailToolProvider tests ---


@pytest.fixture
def mock_connections():
    """Two Gmail connections for a user."""
    return [
        {
            "connection_id": "conn-1",
            "service_user_email": "work@gmail.com",
            "access_token": "ya29.work",
            "refresh_token": "1//work",
            "expires_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
        },
        {
            "connection_id": "conn-2",
            "service_user_email": "personal@gmail.com",
            "access_token": "ya29.personal",
            "refresh_token": "1//personal",
            "expires_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
        },
    ]


@pytest.mark.asyncio
async def test_get_all_providers_returns_one_per_connection(mock_connections):
    """get_all_providers should return a provider for each connection."""
    with patch.object(GmailToolProvider, "_get_gmail_connections", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_connections

        providers = await GmailToolProvider.get_all_providers("user-1")

    assert len(providers) == 2
    assert providers[0].account_email == "work@gmail.com"
    assert providers[1].account_email == "personal@gmail.com"
    assert providers[0].connection_id == "conn-1"
    assert providers[1].connection_id == "conn-2"


@pytest.mark.asyncio
async def test_get_all_providers_empty_when_no_connections():
    """get_all_providers should return empty list when no connections."""
    with patch.object(GmailToolProvider, "_get_gmail_connections", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = []

        providers = await GmailToolProvider.get_all_providers("user-1")

    assert providers == []


@pytest.mark.asyncio
async def test_get_provider_for_account_finds_match(mock_connections):
    """get_provider_for_account should return the matching provider."""
    with patch.object(GmailToolProvider, "_get_gmail_connections", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_connections

        provider = await GmailToolProvider.get_provider_for_account("user-1", "personal@gmail.com")

    assert provider.account_email == "personal@gmail.com"
    assert provider.connection_id == "conn-2"


@pytest.mark.asyncio
async def test_get_provider_for_account_raises_on_miss(mock_connections):
    """get_provider_for_account should raise ValueError for unknown email."""
    with patch.object(GmailToolProvider, "_get_gmail_connections", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_connections

        with pytest.raises(ValueError, match="No Gmail connection found for unknown@gmail.com"):
            await GmailToolProvider.get_provider_for_account("user-1", "unknown@gmail.com")


@pytest.mark.asyncio
async def test_token_refresh_triggered_when_expired():
    """Credentials should be refreshed when token is near expiry."""
    expired_token_data = {
        "connection_id": "conn-1",
        "service_user_email": "work@gmail.com",
        "access_token": "ya29.expired",
        "refresh_token": "1//refresh",
        "expires_at": (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat(),
    }

    provider = GmailToolProvider("user-1", "conn-1")
    provider._token_data = expired_token_data

    with patch.dict("os.environ", {
        "GOOGLE_CLIENT_ID": "test-client-id",
        "GOOGLE_CLIENT_SECRET": "test-client-secret",
        "SUPABASE_URL": "https://test.supabase.co",
        "SUPABASE_SERVICE_ROLE_KEY": "test-key",
    }):
        with patch("chatServer.tools.gmail_tools.Credentials") as mock_creds_cls:
            mock_creds = MagicMock()
            mock_creds.expired = True
            mock_creds.token = "ya29.refreshed"
            mock_creds.expiry = datetime.now(timezone.utc) + timedelta(hours=1)
            mock_creds.refresh_token = "1//refresh"
            mock_creds_cls.return_value = mock_creds

            with patch("google.auth.transport.requests.Request"):
                with patch.object(provider, "_update_stored_token", new_callable=AsyncMock) as mock_update:
                    creds = await provider._get_google_credentials()

                    mock_creds.refresh.assert_called_once()
                    mock_update.assert_called_once_with(
                        mock_creds.token,
                        mock_creds.expiry,
                    )


@pytest.mark.asyncio
async def test_token_refresh_not_triggered_when_valid():
    """Credentials should NOT be refreshed when token is still valid."""
    valid_token_data = {
        "connection_id": "conn-1",
        "service_user_email": "work@gmail.com",
        "access_token": "ya29.valid",
        "refresh_token": "1//refresh",
        "expires_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
    }

    provider = GmailToolProvider("user-1", "conn-1")
    provider._token_data = valid_token_data

    with patch.dict("os.environ", {
        "GOOGLE_CLIENT_ID": "test-client-id",
        "GOOGLE_CLIENT_SECRET": "test-client-secret",
    }):
        with patch("chatServer.tools.gmail_tools.Credentials") as mock_creds_cls:
            mock_creds = MagicMock()
            mock_creds.expired = False
            mock_creds_cls.return_value = mock_creds

            creds = await provider._get_google_credentials()

            mock_creds.refresh.assert_not_called()


# --- GmailSearchTool tests ---


def _make_search_tool():
    """Create a GmailSearchTool with test config."""
    return GmailSearchTool(
        user_id="user-1",
        agent_name="search_test_runner",
        supabase_url="https://test.supabase.co",
        supabase_key="test-key",
    )


@pytest.mark.asyncio
async def test_search_single_account():
    """Search with account param targets only that account."""
    tool = _make_search_tool()

    mock_provider = AsyncMock()
    mock_provider.account_email = "work@gmail.com"

    with patch.object(GmailToolProvider, "get_provider_for_account", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_provider

        with patch.object(tool, "_search_single", new_callable=AsyncMock) as mock_search:
            mock_search.return_value = "Message 1: Subject line"

            result = await tool._arun(query="is:unread", account="work@gmail.com")

    assert "[work@gmail.com]" in result
    assert "Message 1: Subject line" in result
    mock_get.assert_called_once_with("user-1", "work@gmail.com", "user")


@pytest.mark.asyncio
async def test_search_all_accounts():
    """Search without account param iterates all accounts."""
    tool = _make_search_tool()

    provider1 = AsyncMock()
    provider1.account_email = "work@gmail.com"
    provider2 = AsyncMock()
    provider2.account_email = "personal@gmail.com"

    with patch.object(GmailToolProvider, "get_all_providers", new_callable=AsyncMock) as mock_all:
        mock_all.return_value = [provider1, provider2]

        with patch.object(tool, "_search_single", new_callable=AsyncMock) as mock_search:
            mock_search.side_effect = ["Work result", "Personal result"]

            result = await tool._arun(query="is:unread")

    assert "=== work@gmail.com ===" in result
    assert "Work result" in result
    assert "=== personal@gmail.com ===" in result
    assert "Personal result" in result


@pytest.mark.asyncio
async def test_search_no_accounts_connected():
    """Search with no accounts should return helpful message."""
    tool = _make_search_tool()

    with patch.object(GmailToolProvider, "get_all_providers", new_callable=AsyncMock) as mock_all:
        mock_all.return_value = []

        result = await tool._arun(query="is:unread")

    assert "No Gmail accounts connected" in result


@pytest.mark.asyncio
async def test_search_partial_failure():
    """Search should return results from working accounts even if one fails."""
    tool = _make_search_tool()

    provider1 = AsyncMock()
    provider1.account_email = "work@gmail.com"
    provider2 = AsyncMock()
    provider2.account_email = "broken@gmail.com"

    with patch.object(GmailToolProvider, "get_all_providers", new_callable=AsyncMock) as mock_all:
        mock_all.return_value = [provider1, provider2]

        with patch.object(tool, "_search_single", new_callable=AsyncMock) as mock_search:
            mock_search.side_effect = ["Work result", Exception("Token expired")]

            result = await tool._arun(query="is:unread")

    assert "=== work@gmail.com ===" in result
    assert "Work result" in result
    assert "=== broken@gmail.com (error) ===" in result
    assert "Token expired" in result


# --- GmailGetMessageTool tests ---


def _make_get_message_tool():
    """Create a GmailGetMessageTool with test config."""
    return GmailGetMessageTool(
        user_id="user-1",
        agent_name="search_test_runner",
        supabase_url="https://test.supabase.co",
        supabase_key="test-key",
    )


@pytest.mark.asyncio
async def test_get_message_requires_account():
    """get_message should require account parameter."""
    tool = _make_get_message_tool()
    result = await tool._arun(message_id="msg-123", account="")
    assert "account" in result.lower()
    assert "required" in result.lower()


@pytest.mark.asyncio
async def test_get_message_with_account():
    """get_message should fetch from specified account."""
    tool = _make_get_message_tool()

    mock_provider = AsyncMock()
    mock_provider.account_email = "work@gmail.com"

    mock_gmail_tool = AsyncMock()
    mock_gmail_tool.name = "get_gmail_message"
    mock_gmail_tool.arun.return_value = "Subject: Test\nBody: Hello"
    mock_provider.get_gmail_tools.return_value = [mock_gmail_tool]

    with patch.object(GmailToolProvider, "get_provider_for_account", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_provider

        result = await tool._arun(message_id="msg-123", account="work@gmail.com")

    assert "[work@gmail.com]" in result
    mock_get.assert_called_once_with("user-1", "work@gmail.com", "user")


# --- GmailDigestTool tests ---


def _make_digest_tool():
    """Create a GmailDigestTool with test config."""
    return GmailDigestTool(
        user_id="user-1",
        agent_name="search_test_runner",
        supabase_url="https://test.supabase.co",
        supabase_key="test-key",
    )


@pytest.mark.asyncio
async def test_digest_single_account():
    """Digest with account param targets only that account."""
    tool = _make_digest_tool()

    mock_provider = AsyncMock()
    mock_provider.account_email = "work@gmail.com"

    with patch.object(GmailToolProvider, "get_provider_for_account", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_provider

        with patch.object(tool, "_digest_single", new_callable=AsyncMock) as mock_digest:
            mock_digest.return_value = "3 unread emails"

            result = await tool._arun(account="work@gmail.com")

    assert result == "3 unread emails"


@pytest.mark.asyncio
async def test_digest_all_accounts():
    """Digest without account param aggregates all accounts."""
    tool = _make_digest_tool()

    provider1 = AsyncMock()
    provider1.account_email = "work@gmail.com"
    provider2 = AsyncMock()
    provider2.account_email = "personal@gmail.com"

    with patch.object(GmailToolProvider, "get_all_providers", new_callable=AsyncMock) as mock_all:
        mock_all.return_value = [provider1, provider2]

        with patch.object(tool, "_digest_single", new_callable=AsyncMock) as mock_digest:
            mock_digest.side_effect = ["5 work emails", "2 personal emails"]

            result = await tool._arun()

    assert "=== work@gmail.com ===" in result
    assert "5 work emails" in result
    assert "=== personal@gmail.com ===" in result
    assert "2 personal emails" in result
    assert "2 accounts" in result


@pytest.mark.asyncio
async def test_digest_no_accounts():
    """Digest with no accounts should return helpful message."""
    tool = _make_digest_tool()

    with patch.object(GmailToolProvider, "get_all_providers", new_callable=AsyncMock) as mock_all:
        mock_all.return_value = []

        result = await tool._arun()

    assert "No Gmail accounts connected" in result


@pytest.mark.asyncio
async def test_digest_partial_failure():
    """Digest should include error notes for failing accounts."""
    tool = _make_digest_tool()

    provider1 = AsyncMock()
    provider1.account_email = "work@gmail.com"
    provider2 = AsyncMock()
    provider2.account_email = "broken@gmail.com"

    with patch.object(GmailToolProvider, "get_all_providers", new_callable=AsyncMock) as mock_all:
        mock_all.return_value = [provider1, provider2]

        with patch.object(tool, "_digest_single", new_callable=AsyncMock) as mock_digest:
            mock_digest.side_effect = ["5 work emails", Exception("Auth error")]

            result = await tool._arun()

    assert "=== work@gmail.com ===" in result
    assert "5 work emails" in result
    assert "=== broken@gmail.com (error) ===" in result
    assert "Auth error" in result
