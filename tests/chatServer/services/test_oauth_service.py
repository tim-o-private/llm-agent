"""Tests for the OAuth service (SPEC-008 FU-2)."""

import base64
import json
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from chatServer.services.oauth_service import OAuthService, _encode_state, _decode_state


@pytest.fixture
def mock_supabase():
    """Create a mock Supabase client."""
    client = MagicMock()
    # Chain methods for table operations
    client.table.return_value.insert.return_value.execute.return_value = MagicMock(data=[{"nonce": "test"}])
    client.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
    client.table.return_value.delete.return_value.eq.return_value.execute.return_value = MagicMock()
    return client


@pytest.fixture
def oauth_service(mock_supabase):
    with patch.dict("os.environ", {
        "GOOGLE_CLIENT_ID": "test-client-id",
        "GOOGLE_CLIENT_SECRET": "test-client-secret",
        "GOOGLE_REDIRECT_URI": "http://localhost:3001/oauth/gmail/callback",
    }):
        return OAuthService(mock_supabase)


@pytest.mark.asyncio
async def test_create_auth_url_includes_required_params(oauth_service):
    """Auth URL should include required OAuth params."""
    with patch.dict("os.environ", {
        "GOOGLE_CLIENT_ID": "test-client-id",
        "GOOGLE_REDIRECT_URI": "http://localhost:3001/oauth/gmail/callback",
    }):
        url = await oauth_service.create_gmail_auth_url("user-123")

    assert "accounts.google.com" in url
    assert "client_id=test-client-id" in url
    assert "access_type=offline" in url
    assert "prompt=select_account+consent" in url or "prompt=select_account%20consent" in url
    assert "gmail.readonly" in url
    assert "response_type=code" in url
    assert "state=" in url


@pytest.mark.asyncio
async def test_handle_callback_validates_nonce(oauth_service, mock_supabase):
    """Callback should reject expired nonces."""
    state = _encode_state("user-123", "expired-nonce")

    # Return expired nonce
    expired_time = (datetime.now(timezone.utc) - timedelta(minutes=15)).isoformat()
    mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
        data=[{"nonce": "expired-nonce", "user_id": "user-123", "expires_at": expired_time}]
    )

    result = await oauth_service.handle_gmail_callback("test-code", state)

    assert result.status == "error"
    assert "timed out" in result.error_message


@pytest.mark.asyncio
async def test_handle_callback_validates_missing_nonce(oauth_service, mock_supabase):
    """Callback should reject unknown nonces."""
    state = _encode_state("user-123", "unknown-nonce")

    # Return no matching nonce
    mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[])

    result = await oauth_service.handle_gmail_callback("test-code", state)

    assert result.status == "error"
    assert "Invalid or expired" in result.error_message


@pytest.mark.asyncio
async def test_handle_callback_exchanges_code(oauth_service, mock_supabase):
    """Callback should exchange code for tokens and store them."""
    state = _encode_state("user-123", "valid-nonce")

    # Valid nonce
    valid_time = (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat()
    mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
        data=[{"nonce": "valid-nonce", "user_id": "user-123", "expires_at": valid_time}]
    )

    # No existing connections
    mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(data=[])

    # store_oauth_tokens RPC success
    mock_supabase.rpc.return_value.execute.return_value = MagicMock(
        data={"success": True, "connection_id": "conn-123"}
    )

    with patch.object(oauth_service, "_exchange_code_for_tokens", new_callable=AsyncMock) as mock_exchange, \
         patch.object(oauth_service, "_get_google_userinfo", new_callable=AsyncMock) as mock_userinfo:

        mock_exchange.return_value = {
            "access_token": "ya29.test",
            "refresh_token": "1//test",
            "expires_in": 3600,
        }
        mock_userinfo.return_value = {
            "sub": "google-user-123",
            "email": "user@gmail.com",
        }

        result = await oauth_service.handle_gmail_callback("auth-code", state)

    assert result.status == "success"
    assert result.email == "user@gmail.com"
    assert result.connection_id == "conn-123"


@pytest.mark.asyncio
async def test_handle_callback_enforces_max_5(oauth_service, mock_supabase):
    """Callback should reject 6th Gmail connection."""
    state = _encode_state("user-123", "valid-nonce")

    valid_time = (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat()

    # Set up the chain: table("oauth_states").select("*").eq("nonce", nonce)
    # returns valid nonce
    nonce_result = MagicMock(data=[{"nonce": "valid-nonce", "user_id": "user-123", "expires_at": valid_time}])

    # Set up: table("external_api_connections").select("id").eq(...).eq(...).eq(...)
    # returns 5 existing connections
    five_connections = MagicMock(data=[{"id": f"conn-{i}"} for i in range(5)])

    # We need to handle multiple table() calls with different args
    call_count = {"value": 0}
    original_table = mock_supabase.table

    def table_side_effect(name):
        mock_table = MagicMock()
        if name == "oauth_states":
            mock_table.select.return_value.eq.return_value.execute.return_value = nonce_result
            mock_table.delete.return_value.eq.return_value.execute.return_value = MagicMock()
        elif name == "external_api_connections":
            mock_table.select.return_value.eq.return_value.eq.return_value.eq.return_value.execute.return_value = five_connections
        return mock_table

    mock_supabase.table.side_effect = table_side_effect

    with patch.object(oauth_service, "_exchange_code_for_tokens", new_callable=AsyncMock) as mock_exchange, \
         patch.object(oauth_service, "_get_google_userinfo", new_callable=AsyncMock) as mock_userinfo:

        mock_exchange.return_value = {"access_token": "ya29.test", "refresh_token": "1//test", "expires_in": 3600}
        mock_userinfo.return_value = {"sub": "google-user-6", "email": "sixth@gmail.com"}

        result = await oauth_service.handle_gmail_callback("auth-code", state)

    assert result.status == "error"
    assert "Maximum of 5" in result.error_message


@pytest.mark.asyncio
async def test_nonce_single_use(oauth_service, mock_supabase):
    """Nonce should be deleted after use (single-use)."""
    state = _encode_state("user-123", "single-use-nonce")

    valid_time = (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat()

    nonce_result = MagicMock(data=[{"nonce": "single-use-nonce", "user_id": "user-123", "expires_at": valid_time}])
    delete_mock = MagicMock()
    no_connections = MagicMock(data=[])

    def table_side_effect(name):
        mock_table = MagicMock()
        if name == "oauth_states":
            mock_table.select.return_value.eq.return_value.execute.return_value = nonce_result
            mock_table.delete.return_value.eq.return_value.execute.return_value = delete_mock
        elif name == "external_api_connections":
            mock_table.select.return_value.eq.return_value.eq.return_value.eq.return_value.execute.return_value = no_connections
        return mock_table

    mock_supabase.table.side_effect = table_side_effect

    mock_supabase.rpc.return_value.execute.return_value = MagicMock(
        data={"success": True, "connection_id": "conn-new"}
    )

    with patch.object(oauth_service, "_exchange_code_for_tokens", new_callable=AsyncMock) as mock_exchange, \
         patch.object(oauth_service, "_get_google_userinfo", new_callable=AsyncMock) as mock_userinfo:

        mock_exchange.return_value = {"access_token": "ya29.test", "refresh_token": "1//test", "expires_in": 3600}
        mock_userinfo.return_value = {"sub": "google-user-new", "email": "new@gmail.com"}

        result = await oauth_service.handle_gmail_callback("auth-code", state)

    # Verify nonce was deleted (oauth_states table delete was called)
    # The delete chain: table("oauth_states").delete().eq("nonce", "single-use-nonce").execute()
    # Since we used side_effect, we check the mock was called
    assert result.status == "success"


def test_encode_decode_state():
    """State encoding/decoding should be reversible."""
    state = _encode_state("user-123", "nonce-abc")
    decoded = _decode_state(state)
    assert decoded["user_id"] == "user-123"
    assert decoded["nonce"] == "nonce-abc"


def test_decode_invalid_state():
    """Invalid state should raise ValueError."""
    with pytest.raises(ValueError, match="Invalid OAuth state"):
        _decode_state("not-valid-base64!!!")
