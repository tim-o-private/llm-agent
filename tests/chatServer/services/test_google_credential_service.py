"""Tests for GoogleCredentialService."""

import os
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from google.oauth2.credentials import Credentials

from chatServer.exceptions import ReauthRequiredError
from chatServer.services.google_credential_service import GoogleCredentialService


@pytest.fixture
def service():
    return GoogleCredentialService()


def _token_data(
    access_token="ya29.valid",
    refresh_token="1//refresh",
    expires_at=None,
    connection_id="conn-123",
    service_user_email="user@test.com",
):
    if expires_at is None:
        expires_at = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "expires_at": expires_at,
        "connection_id": connection_id,
        "service_user_email": service_user_email,
    }


def _env_patch():
    return patch.dict(os.environ, {
        "GOOGLE_CLIENT_ID": "test-client-id",
        "GOOGLE_CLIENT_SECRET": "test-client-secret",
    })


class TestGetCredentials:
    @pytest.mark.asyncio
    async def test_returns_valid_credentials(self, service):
        data = _token_data()
        with (
            _env_patch(),
            patch.object(service, "_fetch_token_data", new_callable=AsyncMock, return_value=data),
        ):
            creds = await service.get_credentials("user-1", "gmail")

        assert isinstance(creds, Credentials)
        assert creds.token == "ya29.valid"

    @pytest.mark.asyncio
    async def test_raises_reauth_when_no_access_token(self, service):
        data = _token_data(access_token=None)
        with (
            _env_patch(),
            patch.object(service, "_fetch_token_data", new_callable=AsyncMock, return_value=data),
        ):
            with pytest.raises(ReauthRequiredError, match="No access token"):
                await service.get_credentials("user-1", "gmail")

    @pytest.mark.asyncio
    async def test_raises_reauth_when_expired_no_refresh(self, service):
        expired = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        data = _token_data(refresh_token=None, expires_at=expired)
        with (
            _env_patch(),
            patch.object(service, "_fetch_token_data", new_callable=AsyncMock, return_value=data),
        ):
            with pytest.raises(ReauthRequiredError, match="no refresh token"):
                await service.get_credentials("user-1", "gmail")

    @pytest.mark.asyncio
    async def test_refreshes_expired_token(self, service):
        expired = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        data = _token_data(expires_at=expired)

        with (
            _env_patch(),
            patch.object(service, "_fetch_token_data", new_callable=AsyncMock, return_value=data),
            patch.object(service, "_refresh", new_callable=AsyncMock) as mock_refresh,
        ):
            await service.get_credentials("user-1", "gmail")

        mock_refresh.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_skips_refresh_for_fresh_token(self, service):
        data = _token_data()
        with (
            _env_patch(),
            patch.object(service, "_fetch_token_data", new_callable=AsyncMock, return_value=data),
            patch.object(service, "_refresh", new_callable=AsyncMock) as mock_refresh,
        ):
            await service.get_credentials("user-1", "gmail")

        mock_refresh.assert_not_awaited()


class TestRefresh:
    @pytest.mark.asyncio
    async def test_raises_reauth_on_invalid_grant(self, service):
        creds = MagicMock(spec=Credentials)
        creds.refresh.side_effect = Exception("invalid_grant: Token has been expired or revoked")

        with pytest.raises(ReauthRequiredError, match="Refresh token revoked"):
            await service._refresh(creds, "user-1", "gmail", "conn-1", "user@test.com")

    @pytest.mark.asyncio
    async def test_raises_reauth_on_unauthorized(self, service):
        creds = MagicMock(spec=Credentials)
        creds.refresh.side_effect = Exception("unauthorized: Invalid credentials")

        with pytest.raises(ReauthRequiredError, match="Authentication failed"):
            await service._refresh(creds, "user-1", "gmail", "conn-1", "user@test.com")

    @pytest.mark.asyncio
    async def test_raises_reauth_on_generic_failure(self, service):
        creds = MagicMock(spec=Credentials)
        creds.refresh.side_effect = Exception("network timeout")

        with pytest.raises(ReauthRequiredError, match="Token refresh failed"):
            await service._refresh(creds, "user-1", "gmail", "conn-1", "user@test.com")

    @pytest.mark.asyncio
    async def test_raises_reauth_when_no_new_token(self, service):
        creds = MagicMock(spec=Credentials)
        creds.refresh.return_value = None
        creds.token = None

        with pytest.raises(ReauthRequiredError, match="no access token"):
            await service._refresh(creds, "user-1", "gmail", "conn-1", "user@test.com")

    @pytest.mark.asyncio
    async def test_persists_on_success(self, service):
        creds = MagicMock(spec=Credentials)
        creds.refresh.return_value = None
        creds.token = "ya29.new"
        creds.expiry = datetime.now(timezone.utc) + timedelta(hours=1)

        with patch.object(service, "_persist_refreshed_token", new_callable=AsyncMock) as mock_persist:
            await service._refresh(creds, "user-1", "gmail", "conn-1", "user@test.com")

        mock_persist.assert_awaited_once_with("conn-1", "ya29.new", creds.expiry)


class TestNeedsRefresh:
    def test_fresh_token_does_not_need_refresh(self, service):
        future = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
        creds = MagicMock(spec=Credentials, expired=False)
        assert service._needs_refresh(creds, {"expires_at": future}) is False

    def test_expired_by_timestamp_needs_refresh(self, service):
        past = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        creds = MagicMock(spec=Credentials, expired=False)
        assert service._needs_refresh(creds, {"expires_at": past}) is True

    def test_within_buffer_needs_refresh(self, service):
        soon = (datetime.now(timezone.utc) + timedelta(minutes=2)).isoformat()
        creds = MagicMock(spec=Credentials, expired=False)
        assert service._needs_refresh(creds, {"expires_at": soon}) is True

    def test_credentials_expired_flag_needs_refresh(self, service):
        creds = MagicMock(spec=Credentials, expired=True)
        assert service._needs_refresh(creds, {}) is True

    def test_no_expiry_info_does_not_need_refresh(self, service):
        creds = MagicMock(spec=Credentials, expired=False)
        assert service._needs_refresh(creds, {}) is False
