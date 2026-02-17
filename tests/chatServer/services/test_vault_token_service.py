"""Tests for VaultTokenService."""

import os

# Import the service
import sys
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock

import pytest

sys.path.append(os.path.join(os.path.dirname(__file__), '../../../chatServer'))

from chatServer.services.vault_token_service import VaultTokenService


class TestVaultTokenService:
    """Test cases for VaultTokenService."""

    @pytest.fixture
    def mock_db_connection(self):
        """Mock PostgreSQL async connection."""
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_cursor.execute = AsyncMock()
        mock_cursor.fetchone = AsyncMock()
        mock_cursor.fetchall = AsyncMock()
        mock_cursor.description = []

        # Mock the cursor context manager
        mock_conn.cursor.return_value.__aenter__ = AsyncMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__aexit__ = AsyncMock(return_value=None)

        return mock_conn, mock_cursor

    @pytest.fixture
    def vault_service(self, mock_db_connection):
        """VaultTokenService instance with mocked dependencies."""
        mock_conn, _ = mock_db_connection
        return VaultTokenService(mock_conn)

    @pytest.fixture
    def sample_user_id(self):
        """Sample user ID for testing."""
        return "123e4567-e89b-12d3-a456-426614174000"

    @pytest.fixture
    def sample_tokens(self):
        """Sample OAuth tokens for testing."""
        return {
            'access_token': 'ya29.a0ARrdaM9example_access_token',
            'refresh_token': '1//04example_refresh_token',
            'expires_at': datetime.now() + timedelta(hours=1),
            'scopes': ['https://www.googleapis.com/auth/gmail.readonly'],
            'service_user_id': 'google_user_123',
            'service_user_email': 'user@example.com'
        }

    @pytest.mark.asyncio
    async def test_store_tokens_success(self, vault_service, mock_db_connection, sample_user_id, sample_tokens):
        """Test successful token storage."""
        mock_conn, mock_cursor = mock_db_connection

        # Mock vault secret creation responses
        mock_cursor.fetchone.side_effect = [
            ('access_secret_id_123',),  # Access token secret creation
            ('refresh_secret_id_456',),  # Refresh token secret creation
            (  # Connection upsert result
                'connection_id_789', sample_user_id, 'gmail', 'access_secret_id_123',
                'refresh_secret_id_456', sample_tokens['expires_at'], sample_tokens['scopes'],
                sample_tokens['service_user_id'], sample_tokens['service_user_email'],
                True, datetime.now()
            )
        ]

        # Mock cursor description for the final query
        mock_cursor.description = [
            ('id',), ('user_id',), ('service_name',), ('access_token_secret_id',),
            ('refresh_token_secret_id',), ('token_expires_at',), ('scopes',),
            ('service_user_id',), ('service_user_email',), ('is_active',), ('updated_at',)
        ]

        # Execute test
        result = await vault_service.store_tokens(
            user_id=sample_user_id,
            service_name='gmail',
            access_token=sample_tokens['access_token'],
            refresh_token=sample_tokens['refresh_token'],
            expires_at=sample_tokens['expires_at'],
            scopes=sample_tokens['scopes'],
            service_user_id=sample_tokens['service_user_id'],
            service_user_email=sample_tokens['service_user_email']
        )

        # Verify vault secret creation calls
        assert mock_cursor.execute.call_count == 3  # 2 vault calls + 1 upsert

        # Verify vault calls
        vault_calls = [call for call in mock_cursor.execute.call_args_list
                      if 'vault.create_secret' in str(call)]
        assert len(vault_calls) == 2

        # Verify result
        assert result['id'] == 'connection_id_789'
        assert result['user_id'] == sample_user_id

    @pytest.mark.asyncio
    async def test_store_tokens_without_refresh_token(self, vault_service, mock_db_connection, sample_user_id, sample_tokens):
        """Test token storage without refresh token."""
        mock_conn, mock_cursor = mock_db_connection

        # Mock vault secret creation (only access token)
        mock_cursor.fetchone.side_effect = [
            ('access_secret_id_123',),  # Access token secret creation
            (  # Connection upsert result
                'connection_id_789', sample_user_id, 'gmail', 'access_secret_id_123',
                None, None, [], None, None, True, datetime.now()
            )
        ]

        # Mock cursor description
        mock_cursor.description = [
            ('id',), ('user_id',), ('service_name',), ('access_token_secret_id',),
            ('refresh_token_secret_id',), ('token_expires_at',), ('scopes',),
            ('service_user_id',), ('service_user_email',), ('is_active',), ('updated_at',)
        ]

        # Execute test (no refresh token)
        result = await vault_service.store_tokens(
            user_id=sample_user_id,
            service_name='gmail',
            access_token=sample_tokens['access_token']
        )

        # Verify only 2 calls (1 vault + 1 upsert)
        assert mock_cursor.execute.call_count == 2

        # Verify result has null refresh token secret ID
        assert result['refresh_token_secret_id'] is None
        assert result['id'] == 'connection_id_789'

    @pytest.mark.asyncio
    async def test_store_tokens_vault_failure(self, vault_service, mock_db_connection, sample_user_id, sample_tokens):
        """Test token storage when vault secret creation fails."""
        mock_conn, mock_cursor = mock_db_connection

        # Mock vault failure
        mock_cursor.fetchone.return_value = None  # Failure case

        # Execute test and expect exception
        with pytest.raises(Exception, match="Failed to store OAuth tokens"):
            await vault_service.store_tokens(
                user_id=sample_user_id,
                service_name='gmail',
                access_token=sample_tokens['access_token']
            )

    @pytest.mark.asyncio
    async def test_get_tokens_success(self, vault_service, mock_db_connection, sample_user_id, sample_tokens):
        """Test successful token retrieval."""
        mock_conn, mock_cursor = mock_db_connection

        # Mock token retrieval from view
        mock_cursor.fetchone.return_value = (
            sample_tokens['access_token'],
            sample_tokens['refresh_token'],
            True  # is_active
        )

        # Execute test
        access_token, refresh_token = await vault_service.get_tokens(sample_user_id, 'gmail')

        # Verify database query
        mock_cursor.execute.assert_called_once()
        query_call = mock_cursor.execute.call_args[0][0]
        assert 'user_api_tokens' in query_call
        assert 'access_token, refresh_token, is_active' in query_call

        # Verify results
        assert access_token == sample_tokens['access_token']
        assert refresh_token == sample_tokens['refresh_token']

    @pytest.mark.asyncio
    async def test_get_tokens_no_connection(self, vault_service, mock_db_connection, sample_user_id):
        """Test token retrieval when no connection exists."""
        mock_conn, mock_cursor = mock_db_connection

        # Mock no data found
        mock_cursor.fetchone.return_value = None

        # Execute test and expect ValueError
        with pytest.raises(ValueError, match="No gmail connection found"):
            await vault_service.get_tokens(sample_user_id, 'gmail')

    @pytest.mark.asyncio
    async def test_get_tokens_inactive_connection(self, vault_service, mock_db_connection, sample_user_id, sample_tokens):
        """Test token retrieval when connection is inactive."""
        mock_conn, mock_cursor = mock_db_connection

        # Mock inactive connection
        mock_cursor.fetchone.return_value = (
            sample_tokens['access_token'],
            sample_tokens['refresh_token'],
            False  # is_active = False
        )

        # Execute test and expect ValueError
        with pytest.raises(ValueError, match="gmail connection is inactive"):
            await vault_service.get_tokens(sample_user_id, 'gmail')

    @pytest.mark.asyncio
    async def test_update_access_token_success(self, vault_service, mock_db_connection, sample_user_id):
        """Test successful access token update."""
        mock_conn, mock_cursor = mock_db_connection
        new_token = "ya29.new_access_token"
        new_expires_at = datetime.now() + timedelta(hours=1)

        # Mock connection lookup and vault update
        mock_cursor.fetchone.return_value = ('secret_id_123',)

        # Execute test
        result = await vault_service.update_access_token(
            sample_user_id, 'gmail', new_token, new_expires_at
        )

        # Verify calls were made
        assert mock_cursor.execute.call_count == 3  # lookup + vault update + connection update

        # Verify vault update call
        vault_call = mock_cursor.execute.call_args_list[1]
        assert 'vault.update_secret' in vault_call[0][0]
        assert vault_call[0][1] == ('secret_id_123', new_token)

        assert result is True

    @pytest.mark.asyncio
    async def test_update_access_token_no_connection(self, vault_service, mock_db_connection, sample_user_id):
        """Test access token update when no connection exists."""
        mock_conn, mock_cursor = mock_db_connection

        # Mock no connection found
        mock_cursor.fetchone.return_value = None

        # Execute test
        result = await vault_service.update_access_token(
            sample_user_id, 'gmail', 'new_token'
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_revoke_tokens_success(self, vault_service, mock_db_connection, sample_user_id):
        """Test successful token revocation."""
        mock_conn, mock_cursor = mock_db_connection

        # Mock connection lookup result
        mock_cursor.fetchone.return_value = (
            'access_secret_123',
            'refresh_secret_456'
        )

        # Execute test
        result = await vault_service.revoke_tokens(sample_user_id, 'gmail')

        # Verify calls: lookup + 2 vault deletes + connection delete = 4 calls
        assert mock_cursor.execute.call_count == 4

        # Verify vault secret deletions
        delete_calls = [call for call in mock_cursor.execute.call_args_list
                       if 'DELETE FROM vault.secrets' in str(call)]
        assert len(delete_calls) == 2

        # Verify connection deletion
        connection_delete_calls = [call for call in mock_cursor.execute.call_args_list
                                  if 'DELETE FROM external_api_connections' in str(call)]
        assert len(connection_delete_calls) == 1

        assert result is True

    @pytest.mark.asyncio
    async def test_revoke_tokens_no_connection(self, vault_service, mock_db_connection, sample_user_id):
        """Test token revocation when no connection exists."""
        mock_conn, mock_cursor = mock_db_connection

        # Mock no connection found
        mock_cursor.fetchone.return_value = None

        # Execute test
        result = await vault_service.revoke_tokens(sample_user_id, 'gmail')

        # Should return True (already revoked/doesn't exist)
        assert result is True

    @pytest.mark.asyncio
    async def test_get_connection_info_success(self, vault_service, mock_db_connection, sample_user_id):
        """Test successful connection info retrieval."""
        mock_conn, mock_cursor = mock_db_connection

        expected_info = (
            'connection_123', 'gmail', 'google_user_123', 'user@example.com',
            ['https://www.googleapis.com/auth/gmail.readonly'],
            datetime(2024, 1, 1, 12, 0, 0), True,
            datetime(2024, 1, 1, 10, 0, 0), datetime(2024, 1, 1, 11, 0, 0)
        )

        # Mock database response
        mock_cursor.fetchone.return_value = expected_info
        mock_cursor.description = [
            ('id',), ('service_name',), ('service_user_id',), ('service_user_email',),
            ('scopes',), ('token_expires_at',), ('is_active',), ('created_at',), ('updated_at',)
        ]

        # Execute test
        result = await vault_service.get_connection_info(sample_user_id, 'gmail')

        # Verify query excludes token fields
        query_call = mock_cursor.execute.call_args[0][0]
        assert 'access_token' not in query_call
        assert 'refresh_token' not in query_call
        assert 'id, service_name' in query_call

        assert result['id'] == 'connection_123'
        assert result['service_name'] == 'gmail'

    @pytest.mark.asyncio
    async def test_list_user_connections_success(self, vault_service, mock_db_connection, sample_user_id):
        """Test successful user connections listing."""
        mock_conn, mock_cursor = mock_db_connection

        expected_connections = [
            (
                'connection_1', 'gmail', 'google_user_123', 'user@example.com',
                ['https://www.googleapis.com/auth/gmail.readonly'], None, True,
                datetime(2024, 1, 1, 10, 0, 0), datetime(2024, 1, 1, 11, 0, 0)
            ),
            (
                'connection_2', 'google_calendar', 'google_user_123', 'user@example.com',
                ['https://www.googleapis.com/auth/calendar'], None, True,
                datetime(2024, 1, 1, 10, 0, 0), datetime(2024, 1, 1, 11, 0, 0)
            )
        ]

        # Mock database response
        mock_cursor.fetchall.return_value = expected_connections
        mock_cursor.description = [
            ('id',), ('service_name',), ('service_user_id',), ('service_user_email',),
            ('scopes',), ('token_expires_at',), ('is_active',), ('created_at',), ('updated_at',)
        ]

        # Execute test
        result = await vault_service.list_user_connections(sample_user_id)

        # Verify query filters for active connections
        query_call = mock_cursor.execute.call_args[0][0]
        assert 'is_active = true' in query_call

        assert len(result) == 2
        assert result[0]['service_name'] == 'gmail'
        assert result[1]['service_name'] == 'google_calendar'

    @pytest.mark.asyncio
    async def test_list_user_connections_empty(self, vault_service, mock_db_connection, sample_user_id):
        """Test user connections listing when no connections exist."""
        mock_conn, mock_cursor = mock_db_connection

        # Mock empty response
        mock_cursor.fetchall.return_value = []

        # Execute test
        result = await vault_service.list_user_connections(sample_user_id)

        assert result == []

    @pytest.mark.asyncio
    async def test_check_token_expiry_with_expiration(self, vault_service, mock_db_connection, sample_user_id):
        """Test token expiry check when expiration is set."""
        mock_conn, mock_cursor = mock_db_connection

        expiry_time = datetime(2024, 1, 1, 12, 0, 0)

        # Mock database response
        mock_cursor.fetchone.return_value = (expiry_time,)

        # Execute test
        result = await vault_service.check_token_expiry(sample_user_id, 'gmail')

        # Verify result is the datetime object
        assert isinstance(result, datetime)
        assert result == expiry_time

    @pytest.mark.asyncio
    async def test_check_token_expiry_no_expiration(self, vault_service, mock_db_connection, sample_user_id):
        """Test token expiry check when no expiration is set."""
        mock_conn, mock_cursor = mock_db_connection

        # Mock database response with null expiration
        mock_cursor.fetchone.return_value = (None,)

        # Execute test
        result = await vault_service.check_token_expiry(sample_user_id, 'gmail')

        assert result is None

    @pytest.mark.asyncio
    async def test_check_token_expiry_no_connection(self, vault_service, mock_db_connection, sample_user_id):
        """Test token expiry check when no connection exists."""
        mock_conn, mock_cursor = mock_db_connection

        # Mock no connection found
        mock_cursor.fetchone.return_value = None

        # Execute test
        result = await vault_service.check_token_expiry(sample_user_id, 'gmail')

        assert result is None

    @pytest.mark.asyncio
    async def test_error_handling_database_exception(self, vault_service, mock_db_connection, sample_user_id):
        """Test error handling when database operations fail."""
        mock_conn, mock_cursor = mock_db_connection

        # Mock database exception
        mock_cursor.execute.side_effect = Exception("Database connection failed")

        # Test various methods handle exceptions gracefully
        result = await vault_service.get_connection_info(sample_user_id, 'gmail')
        assert result is None

        result = await vault_service.list_user_connections(sample_user_id)
        assert result == []

        result = await vault_service.check_token_expiry(sample_user_id, 'gmail')
        assert result is None

        result = await vault_service.update_access_token(sample_user_id, 'gmail', 'new_token')
        assert result is False

        result = await vault_service.revoke_tokens(sample_user_id, 'gmail')
        assert result is False
