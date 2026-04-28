"""Tests for multi-account Gmail tools (SPEC-008 FU-3)."""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from chatServer.tools.gmail_rate_limiter import GmailRateLimiter
from chatServer.tools.gmail_tools import (
    GetGmailTool,
    GmailToolProvider,
    SearchGmailTool,
)


@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    """Reset Gmail rate limiter between tests to prevent cross-test pollution."""
    GmailRateLimiter.reset()
    yield
    GmailRateLimiter.reset()


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
async def test_get_credentials_delegates_to_credential_service():
    """GmailToolProvider._get_google_credentials delegates to GoogleCredentialService."""
    mock_creds = MagicMock()
    mock_creds.token = "ya29.valid"

    provider = GmailToolProvider("user-1", "conn-1")

    with patch(
        "chatServer.services.google_credential_service.get_google_credential_service"
    ) as mock_factory:
        mock_service = MagicMock()
        mock_service.get_credentials = AsyncMock(return_value=mock_creds)
        mock_factory.return_value = mock_service

        creds = await provider._get_google_credentials()

    assert creds is mock_creds
    mock_service.get_credentials.assert_awaited_once_with(
        user_id="user-1",
        service_name="gmail",
        connection_id="conn-1",
        scopes=["https://www.googleapis.com/auth/gmail.readonly"],
    )


@pytest.mark.asyncio
async def test_get_credentials_caches_result():
    """Second call returns cached credentials without calling service again."""
    mock_creds = MagicMock()

    provider = GmailToolProvider("user-1", "conn-1")

    with patch(
        "chatServer.services.google_credential_service.get_google_credential_service"
    ) as mock_factory:
        mock_service = MagicMock()
        mock_service.get_credentials = AsyncMock(return_value=mock_creds)
        mock_factory.return_value = mock_service

        creds1 = await provider._get_google_credentials()
        creds2 = await provider._get_google_credentials()

    assert creds1 is creds2
    assert mock_service.get_credentials.await_count == 1


@pytest.mark.asyncio
async def test_get_credentials_propagates_reauth_error():
    """Expired token with no refresh token raises ReauthRequiredError."""
    from chatServer.exceptions import ReauthRequiredError

    provider = GmailToolProvider("user-1", "conn-1")

    with patch(
        "chatServer.services.google_credential_service.get_google_credential_service"
    ) as mock_factory:
        mock_service = MagicMock()
        mock_service.get_credentials = AsyncMock(
            side_effect=ReauthRequiredError("gmail", "Token expired, no refresh token")
        )
        mock_factory.return_value = mock_service

        with pytest.raises(ReauthRequiredError):
            await provider._get_google_credentials()


# --- GmailSearchTool tests ---


def _make_search_tool():
    """Create a SearchGmailTool with test config."""
    return SearchGmailTool(
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
    """Create a GetGmailTool with test config."""
    return GetGmailTool(
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


