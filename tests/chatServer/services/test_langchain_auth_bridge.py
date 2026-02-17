"""Unit tests for VaultToLangChainCredentialAdapter."""

import os
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from chatServer.services.langchain_auth_bridge import VaultToLangChainCredentialAdapter


class TestVaultToLangChainCredentialAdapter:
    """Test suite for VaultToLangChainCredentialAdapter."""

    @pytest.fixture
    def mock_db_connection(self):
        """Mock database connection and cursor."""
        mock_conn = AsyncMock()
        mock_cursor = AsyncMock()

        # Set up the async context manager for cursor properly
        mock_cursor_context = AsyncMock()
        mock_cursor_context.__aenter__ = AsyncMock(return_value=mock_cursor)
        mock_cursor_context.__aexit__ = AsyncMock(return_value=None)

        # IMPORTANT: cursor() should be a regular method, not async
        # It returns an async context manager, but the method itself is sync
        mock_conn.cursor = MagicMock(return_value=mock_cursor_context)

        return mock_conn, mock_cursor

    @pytest.fixture
    def adapter(self, mock_db_connection):
        """Create adapter instance with mock database connection."""
        mock_conn, _ = mock_db_connection

        # Pass the mock connection directly to the adapter constructor
        # This bypasses the get_db_connection() complexity entirely
        adapter = VaultToLangChainCredentialAdapter(db_connection=mock_conn)
        return adapter

    @pytest.fixture
    def sample_tokens(self):
        """Sample OAuth tokens for testing."""
        return {
            'access_token': 'ya29.test_access_token',
            'refresh_token': 'refresh_token_123',
            'expires_at': datetime.now() + timedelta(hours=1)
        }

    @pytest.fixture
    def mock_env_vars(self):
        """Mock environment variables for Google OAuth."""
        with patch.dict(os.environ, {
            'GOOGLE_CLIENT_ID': 'test_client_id',
            'GOOGLE_CLIENT_SECRET': 'test_client_secret'
        }):
            yield

    @pytest.mark.asyncio
    async def test_get_tokens_from_vault_success(self, adapter, mock_db_connection, sample_tokens):
        """Test successful token retrieval from vault."""
        mock_conn, mock_cursor = mock_db_connection

        # Mock database responses
        mock_cursor.fetchone.side_effect = [
            ('secret_id_1', 'secret_id_2', True),  # Connection query
            (sample_tokens['access_token'],),       # Access token query
            (sample_tokens['refresh_token'],)       # Refresh token query
        ]

        # Remove the conflicting patch - let the fixture handle it
        access_token, refresh_token = await adapter._get_tokens_from_vault('user123', 'gmail')

        assert access_token == sample_tokens['access_token']
        assert refresh_token == sample_tokens['refresh_token']

        # Verify database queries
        assert mock_cursor.execute.call_count == 3

    @pytest.mark.asyncio
    async def test_get_tokens_from_vault_no_connection(self, adapter, mock_db_connection):
        """Test token retrieval when no connection exists."""
        mock_conn, mock_cursor = mock_db_connection
        mock_cursor.fetchone.return_value = None

        with pytest.raises(ValueError, match="No gmail connection found for user user123"):
            await adapter._get_tokens_from_vault('user123', 'gmail')

    @pytest.mark.asyncio
    async def test_get_tokens_from_vault_inactive_connection(self, adapter, mock_db_connection):
        """Test token retrieval when connection is inactive."""
        mock_conn, mock_cursor = mock_db_connection
        mock_cursor.fetchone.return_value = ('secret_id_1', 'secret_id_2', False)  # is_active = False

        with pytest.raises(ValueError, match="gmail connection is inactive for user user123"):
            await adapter._get_tokens_from_vault('user123', 'gmail')

    @pytest.mark.asyncio
    async def test_get_tokens_from_vault_no_access_token(self, adapter, mock_db_connection):
        """Test token retrieval when access token is missing."""
        mock_conn, mock_cursor = mock_db_connection
        mock_cursor.fetchone.side_effect = [
            ('secret_id_1', 'secret_id_2', True),  # Connection query
            (None,)  # Access token query returns None
        ]

        with pytest.raises(RuntimeError, match="Failed to decrypt access token"):
            await adapter._get_tokens_from_vault('user123', 'gmail')

    @pytest.mark.asyncio
    async def test_create_google_credentials_success(self, adapter, mock_db_connection, sample_tokens, mock_env_vars):
        """Test successful Google credentials creation."""
        mock_conn, mock_cursor = mock_db_connection

        # Mock database responses for valid, non-expired tokens
        mock_cursor.fetchone.side_effect = [
            ('secret_id_1', 'secret_id_2', True),  # Connection query
            (sample_tokens['access_token'],),       # Access token query
            (sample_tokens['refresh_token'],)       # Refresh token query
        ]

        with patch('chatServer.services.langchain_auth_bridge.Credentials') as mock_creds_class:
            mock_creds = MagicMock()
            mock_creds.expired = False
            mock_creds_class.return_value = mock_creds

            credentials = await adapter.create_google_credentials('user123', 'gmail')

            assert credentials == mock_creds
            mock_creds_class.assert_called_once_with(
                token=sample_tokens['access_token'],
                refresh_token=sample_tokens['refresh_token'],
                token_uri="https://oauth2.googleapis.com/token",
                client_id='test_client_id',
                client_secret='test_client_secret',
                scopes=['https://www.googleapis.com/auth/gmail.readonly']
            )

    @pytest.mark.asyncio
    async def test_create_google_credentials_no_oauth_connection(self, adapter, mock_db_connection):
        """Test credentials creation when no OAuth connection exists."""
        mock_conn, mock_cursor = mock_db_connection
        mock_cursor.fetchone.return_value = None

        with pytest.raises(ValueError, match="No OAuth connection found"):
            await adapter.create_google_credentials('user123', 'gmail')

    @pytest.mark.asyncio
    async def test_create_google_credentials_missing_env_vars(self, adapter, mock_db_connection, sample_tokens):
        """Test credentials creation when environment variables are missing."""
        mock_conn, mock_cursor = mock_db_connection
        mock_cursor.fetchone.side_effect = [
            ('secret_id_1', 'secret_id_2', True),
            (sample_tokens['access_token'],),
            (sample_tokens['refresh_token'],)
        ]

        # Explicitly clear env vars (load_dotenv from other tests may have set them)
        env_overrides = {k: '' for k in ('GOOGLE_CLIENT_ID', 'GOOGLE_CLIENT_SECRET') if k in os.environ}
        with patch.dict(os.environ, env_overrides, clear=False):
            for k in ('GOOGLE_CLIENT_ID', 'GOOGLE_CLIENT_SECRET'):
                os.environ.pop(k, None)
            with pytest.raises(RuntimeError, match="Google OAuth configuration missing"):
                await adapter.create_google_credentials('user123', 'gmail')

    @pytest.mark.asyncio
    async def test_create_google_credentials_expired_with_refresh(self, adapter, mock_db_connection, sample_tokens, mock_env_vars):
        """Test credentials creation with expired token that gets refreshed."""
        mock_conn, mock_cursor = mock_db_connection
        mock_cursor.fetchone.side_effect = [
            ('secret_id_1', 'secret_id_2', True),
            (sample_tokens['access_token'],),
            (sample_tokens['refresh_token'],)
        ]

        with patch('chatServer.services.langchain_auth_bridge.Credentials') as mock_creds_class:
            mock_creds = MagicMock()
            mock_creds.expired = True
            mock_creds.refresh_token = sample_tokens['refresh_token']
            mock_creds.token = 'new_access_token'
            mock_creds.expiry = datetime.now() + timedelta(hours=1)
            mock_creds_class.return_value = mock_creds

            with patch.object(adapter, '_refresh_credentials') as mock_refresh:
                credentials = await adapter.create_google_credentials('user123', 'gmail')

                assert credentials == mock_creds
                mock_refresh.assert_called_once_with('user123', 'gmail', mock_creds)

    @pytest.mark.asyncio
    async def test_create_google_credentials_expired_no_refresh(self, adapter, mock_db_connection, sample_tokens, mock_env_vars):
        """Test credentials creation with expired token and no refresh token."""
        mock_conn, mock_cursor = mock_db_connection
        mock_cursor.fetchone.side_effect = [
            ('secret_id_1', 'secret_id_2', True),
            (sample_tokens['access_token'],),
            (None,)  # No refresh token
        ]

        with patch('chatServer.services.langchain_auth_bridge.Credentials') as mock_creds_class:
            mock_creds = MagicMock()
            mock_creds.expired = True
            mock_creds.refresh_token = None
            mock_creds_class.return_value = mock_creds

            with pytest.raises(RuntimeError, match="Access token expired and no refresh token available"):
                await adapter.create_google_credentials('user123', 'gmail')

    @pytest.mark.asyncio
    async def test_refresh_credentials_success(self, adapter, mock_db_connection, sample_tokens):
        """Test successful credential refresh."""
        mock_conn, mock_cursor = mock_db_connection

        # Mock successful vault update
        mock_cursor.fetchone.return_value = ('secret_id_1',)

        mock_creds = MagicMock()
        mock_creds.token = 'new_access_token'
        mock_creds.expiry = datetime.now() + timedelta(hours=1)

        with patch('google.auth.transport.requests.Request') as mock_request:
            with patch('asyncio.get_event_loop') as mock_loop:
                # Mock the executor to actually call the function
                async def mock_executor(executor, func):
                    func()  # Actually call the refresh function
                    return None

                mock_loop.return_value.run_in_executor = mock_executor

                await adapter._refresh_credentials('user123', 'gmail', mock_creds)

                # Verify that refresh was called
                mock_creds.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_refresh_credentials_invalid_grant(self, adapter, mock_db_connection):
        """Test credential refresh with invalid grant error."""
        mock_conn, mock_cursor = mock_db_connection
        mock_creds = MagicMock()

        with patch('google.auth.transport.requests.Request'):
            with patch('asyncio.get_event_loop') as mock_loop:
                mock_executor = AsyncMock()
                mock_executor.side_effect = Exception("invalid_grant: Token has been expired or revoked")
                mock_loop.return_value.run_in_executor = mock_executor

                with pytest.raises(RuntimeError, match="Refresh token is invalid or expired"):
                    await adapter._refresh_credentials('user123', 'gmail', mock_creds)

    @pytest.mark.asyncio
    async def test_refresh_credentials_unauthorized(self, adapter, mock_db_connection):
        """Test credential refresh with unauthorized error."""
        mock_conn, mock_cursor = mock_db_connection
        mock_creds = MagicMock()

        with patch('google.auth.transport.requests.Request'):
            with patch('asyncio.get_event_loop') as mock_loop:
                mock_executor = AsyncMock()
                mock_executor.side_effect = Exception("unauthorized: Invalid credentials")
                mock_loop.return_value.run_in_executor = mock_executor

                with pytest.raises(RuntimeError, match="Authentication failed during token refresh"):
                    await adapter._refresh_credentials('user123', 'gmail', mock_creds)

    @pytest.mark.asyncio
    async def test_fetch_or_refresh_gmail_credentials(self, adapter):
        """Test Gmail-specific credentials convenience method."""
        with patch.object(adapter, 'create_google_credentials') as mock_create:
            mock_creds = MagicMock()
            mock_create.return_value = mock_creds

            result = await adapter.fetch_or_refresh_gmail_credentials('user123')

            assert result == mock_creds
            mock_create.assert_called_once_with(
                user_id='user123',
                service_name='gmail',
                scopes=['https://www.googleapis.com/auth/gmail.readonly']
            )

    @pytest.mark.asyncio
    async def test_fetch_or_refresh_calendar_credentials(self, adapter):
        """Test Calendar-specific credentials convenience method."""
        with patch.object(adapter, 'create_google_credentials') as mock_create:
            mock_creds = MagicMock()
            mock_create.return_value = mock_creds

            result = await adapter.fetch_or_refresh_calendar_credentials('user123')

            assert result == mock_creds
            mock_create.assert_called_once_with(
                user_id='user123',
                service_name='google_calendar',
                scopes=['https://www.googleapis.com/auth/calendar.readonly']
            )

    @pytest.mark.asyncio
    async def test_create_temp_credential_files(self, adapter, sample_tokens, mock_env_vars):
        """Test temporary credential file creation."""
        with patch.object(adapter, 'create_google_credentials') as mock_create:
            mock_creds = MagicMock()
            mock_creds.token = sample_tokens['access_token']
            mock_creds.refresh_token = sample_tokens['refresh_token']
            mock_creds.token_uri = "https://oauth2.googleapis.com/token"
            mock_creds.client_id = 'test_client_id'
            mock_creds.client_secret = 'test_client_secret'
            mock_creds.scopes = ['https://www.googleapis.com/auth/gmail.readonly']
            mock_create.return_value = mock_creds

            with patch('tempfile.NamedTemporaryFile') as mock_temp:
                mock_file = MagicMock()
                mock_file.name = '/tmp/test_file.json'
                mock_temp.return_value.__enter__.return_value = mock_file

                token_file, secrets_file = await adapter.create_temp_credential_files('user123', 'gmail')

                assert token_file == '/tmp/test_file.json'
                assert secrets_file == '/tmp/test_file.json'
                assert len(adapter._temp_files) == 2

    def test_cleanup_temp_files(self, adapter):
        """Test temporary file cleanup."""
        # Create a fresh adapter instance for this test
        adapter = VaultToLangChainCredentialAdapter()

        # Add some fake temp files
        adapter._temp_files = ['/tmp/fake1.json', '/tmp/fake2.json']

        with patch('os.path.exists', return_value=True):
            with patch('os.unlink') as mock_unlink:
                adapter.cleanup_temp_files()

                assert mock_unlink.call_count == 2
                assert len(adapter._temp_files) == 0

    @pytest.mark.asyncio
    async def test_update_access_token_in_vault_success(self, adapter, mock_db_connection):
        """Test successful access token update in vault."""
        mock_conn, mock_cursor = mock_db_connection
        mock_cursor.fetchone.return_value = ('secret_id_1',)

        expires_at = datetime.now() + timedelta(hours=1)
        await adapter._update_access_token_in_vault('user123', 'gmail', 'new_token', expires_at)

        # Verify vault update and connection update calls
        # 1. SELECT access_token_secret_id FROM external_api_connections
        # 2. SELECT vault.update_secret(...)
        # 3. UPDATE external_api_connections SET token_expires_at (when expires_at provided)
        assert mock_cursor.execute.call_count == 3

    @pytest.mark.asyncio
    async def test_update_access_token_in_vault_no_connection(self, adapter, mock_db_connection):
        """Test access token update when connection doesn't exist."""
        mock_conn, mock_cursor = mock_db_connection
        mock_cursor.fetchone.return_value = None

        with pytest.raises(RuntimeError, match="No connection found"):
            await adapter._update_access_token_in_vault('user123', 'gmail', 'new_token')


@pytest.mark.asyncio
async def test_create_auth_bridge():
    """Test auth bridge factory function."""
    from chatServer.services.langchain_auth_bridge import create_auth_bridge

    bridge = await create_auth_bridge()
    assert isinstance(bridge, VaultToLangChainCredentialAdapter)
    assert bridge.db_connection is None

    # Test with provided connection
    mock_conn = AsyncMock()
    bridge_with_conn = await create_auth_bridge(mock_conn)
    assert bridge_with_conn.db_connection == mock_conn
