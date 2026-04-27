"""Unit tests for VaultToLangChainCredentialAdapter (thin wrapper over GoogleCredentialService)."""

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from google.oauth2.credentials import Credentials

from chatServer.exceptions import ReauthRequiredError
from chatServer.services.langchain_auth_bridge import (
    VaultToLangChainCredentialAdapter,
    create_auth_bridge,
)


def _mock_credentials():
    creds = MagicMock(spec=Credentials)
    creds.token = "ya29.valid"
    creds.refresh_token = "1//refresh"
    creds.token_uri = "https://oauth2.googleapis.com/token"
    creds.client_id = "test-id"
    creds.client_secret = "test-secret"
    creds.scopes = ["https://www.googleapis.com/auth/gmail.readonly"]
    return creds


class TestVaultToLangChainCredentialAdapter:
    @pytest.mark.asyncio
    async def test_create_google_credentials_delegates(self):
        adapter = VaultToLangChainCredentialAdapter()
        mock_creds = _mock_credentials()

        with patch(
            "chatServer.services.langchain_auth_bridge.get_google_credential_service"
        ) as mock_factory:
            mock_service = MagicMock()
            mock_service.get_credentials = AsyncMock(return_value=mock_creds)
            mock_factory.return_value = mock_service

            result = await adapter.create_google_credentials("user-1", "gmail")

        assert result is mock_creds
        mock_service.get_credentials.assert_awaited_once_with(
            user_id="user-1",
            service_name="gmail",
            scopes=["https://www.googleapis.com/auth/gmail.readonly"],
        )

    @pytest.mark.asyncio
    async def test_create_google_credentials_custom_scopes(self):
        adapter = VaultToLangChainCredentialAdapter()
        mock_creds = _mock_credentials()
        custom_scopes = ["https://www.googleapis.com/auth/gmail.compose"]

        with patch(
            "chatServer.services.langchain_auth_bridge.get_google_credential_service"
        ) as mock_factory:
            mock_service = MagicMock()
            mock_service.get_credentials = AsyncMock(return_value=mock_creds)
            mock_factory.return_value = mock_service

            result = await adapter.create_google_credentials("user-1", "gmail", scopes=custom_scopes)

        assert result is mock_creds
        mock_service.get_credentials.assert_awaited_once_with(
            user_id="user-1",
            service_name="gmail",
            scopes=custom_scopes,
        )

    @pytest.mark.asyncio
    async def test_create_google_credentials_propagates_reauth_error(self):
        adapter = VaultToLangChainCredentialAdapter()

        with patch(
            "chatServer.services.langchain_auth_bridge.get_google_credential_service"
        ) as mock_factory:
            mock_service = MagicMock()
            mock_service.get_credentials = AsyncMock(
                side_effect=ReauthRequiredError("gmail", "Token expired")
            )
            mock_factory.return_value = mock_service

            with pytest.raises(ReauthRequiredError, match="Token expired"):
                await adapter.create_google_credentials("user-1", "gmail")

    @pytest.mark.asyncio
    async def test_fetch_or_refresh_gmail(self):
        adapter = VaultToLangChainCredentialAdapter()
        mock_creds = _mock_credentials()

        with patch(
            "chatServer.services.langchain_auth_bridge.get_google_credential_service"
        ) as mock_factory:
            mock_service = MagicMock()
            mock_service.get_credentials = AsyncMock(return_value=mock_creds)
            mock_factory.return_value = mock_service

            result = await adapter.fetch_or_refresh_gmail_credentials("user-1")

        assert result is mock_creds

    @pytest.mark.asyncio
    async def test_fetch_or_refresh_calendar(self):
        adapter = VaultToLangChainCredentialAdapter()
        mock_creds = _mock_credentials()

        with patch(
            "chatServer.services.langchain_auth_bridge.get_google_credential_service"
        ) as mock_factory:
            mock_service = MagicMock()
            mock_service.get_credentials = AsyncMock(return_value=mock_creds)
            mock_factory.return_value = mock_service

            result = await adapter.fetch_or_refresh_calendar_credentials("user-1")

        assert result is mock_creds
        mock_service.get_credentials.assert_awaited_once_with(
            user_id="user-1",
            service_name="google_calendar",
            scopes=["https://www.googleapis.com/auth/calendar.readonly"],
        )

    @pytest.mark.asyncio
    async def test_create_temp_credential_files(self):
        adapter = VaultToLangChainCredentialAdapter()
        mock_creds = _mock_credentials()

        with patch(
            "chatServer.services.langchain_auth_bridge.get_google_credential_service"
        ) as mock_factory:
            mock_service = MagicMock()
            mock_service.get_credentials = AsyncMock(return_value=mock_creds)
            mock_factory.return_value = mock_service

            token_file, secrets_file = await adapter.create_temp_credential_files("user-1")

        assert os.path.exists(token_file)
        assert os.path.exists(secrets_file)
        assert len(adapter._temp_files) == 2

        adapter.cleanup_temp_files()
        assert not os.path.exists(token_file)
        assert not os.path.exists(secrets_file)

    @pytest.mark.asyncio
    async def test_factory_function(self):
        adapter = await create_auth_bridge()
        assert isinstance(adapter, VaultToLangChainCredentialAdapter)

    @pytest.mark.asyncio
    async def test_factory_with_db_connection(self):
        mock_conn = AsyncMock()
        adapter = await create_auth_bridge(mock_conn)
        assert adapter.db_connection is mock_conn
