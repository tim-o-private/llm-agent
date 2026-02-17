"""Tests for VaultTokenService."""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from chatServer.services.vault_token_service import VaultTokenService


class TestVaultTokenService:
    """Test cases for VaultTokenService."""

    @pytest.fixture
    def mock_db_connection(self):
        """Mock PostgreSQL async connection with async cursor context manager."""
        mock_conn = MagicMock()
        mock_cursor = AsyncMock()

        # Mock the async cursor context manager
        mock_cursor_cm = MagicMock()
        mock_cursor_cm.__aenter__ = AsyncMock(return_value=mock_cursor)
        mock_cursor_cm.__aexit__ = AsyncMock(return_value=None)
        mock_conn.cursor.return_value = mock_cursor_cm

        # Mock commit and rollback as async
        mock_conn.commit = AsyncMock()
        mock_conn.rollback = AsyncMock()

        return mock_conn, mock_cursor

    @pytest.fixture
    def vault_service(self, mock_db_connection):
        """VaultTokenService instance with mocked dependencies."""
        mock_conn, _ = mock_db_connection
        return VaultTokenService(mock_conn)

    @pytest.fixture
    def sample_user_id(self):
        return "123e4567-e89b-12d3-a456-426614174000"

    @pytest.fixture
    def sample_tokens(self):
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
        """Test successful token storage via RPC."""
        _, mock_cursor = mock_db_connection

        # First fetchone: RPC result (JSON dict), second: connection record
        mock_cursor.fetchone.side_effect = [
            ({'success': True, 'connection_id': 'conn-123'},),  # RPC returns JSON
            ('conn-123', sample_user_id, 'gmail', 'secret-1', 'secret-2',
             sample_tokens['expires_at'], sample_tokens['scopes'],
             sample_tokens['service_user_id'], sample_tokens['service_user_email'],
             True, datetime.now()),
        ]
        mock_cursor.description = [
            ('id',), ('user_id',), ('service_name',), ('access_token_secret_id',),
            ('refresh_token_secret_id',), ('token_expires_at',), ('scopes',),
            ('service_user_id',), ('service_user_email',), ('is_active',), ('updated_at',)
        ]

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

        assert result['id'] == 'conn-123'
        assert result['user_id'] == sample_user_id

    @pytest.mark.asyncio
    async def test_store_tokens_rpc_failure(self, vault_service, mock_db_connection, sample_user_id, sample_tokens):
        """Test token storage when RPC returns no result."""
        _, mock_cursor = mock_db_connection
        mock_cursor.fetchone.return_value = None

        with pytest.raises(Exception, match="Failed to store OAuth tokens"):
            await vault_service.store_tokens(
                user_id=sample_user_id,
                service_name='gmail',
                access_token=sample_tokens['access_token']
            )

    @pytest.mark.asyncio
    async def test_get_tokens_success(self, vault_service, mock_db_connection, sample_user_id, sample_tokens):
        """Test successful token retrieval via RPC."""
        _, mock_cursor = mock_db_connection

        # RPC returns JSON with access_token and refresh_token
        mock_cursor.fetchone.return_value = (
            {'access_token': sample_tokens['access_token'], 'refresh_token': sample_tokens['refresh_token']},
        )

        access_token, refresh_token = await vault_service.get_tokens(sample_user_id, 'gmail')

        assert access_token == sample_tokens['access_token']
        assert refresh_token == sample_tokens['refresh_token']

    @pytest.mark.asyncio
    async def test_get_tokens_no_connection(self, vault_service, mock_db_connection, sample_user_id):
        """Test token retrieval when no connection exists."""
        _, mock_cursor = mock_db_connection
        mock_cursor.fetchone.return_value = None

        with pytest.raises(ValueError, match="No OAuth connection found"):
            await vault_service.get_tokens(sample_user_id, 'gmail')

    @pytest.mark.asyncio
    async def test_get_tokens_scheduler_context(self, mock_db_connection, sample_user_id, sample_tokens):
        """Test token retrieval uses scheduler RPC in scheduler context."""
        mock_conn, mock_cursor = mock_db_connection
        service = VaultTokenService(mock_conn, context="scheduler")

        mock_cursor.fetchone.return_value = (
            {'access_token': sample_tokens['access_token'], 'refresh_token': None},
        )

        access_token, refresh_token = await service.get_tokens(sample_user_id, 'gmail')

        # Verify the scheduler-specific RPC was called
        call_sql = mock_cursor.execute.call_args[0][0]
        assert 'get_oauth_tokens_for_scheduler' in call_sql

    @pytest.mark.asyncio
    async def test_update_access_token_success(self, vault_service, mock_db_connection, sample_user_id):
        """Test successful access token update."""
        _, mock_cursor = mock_db_connection
        new_token = "ya29.new_access_token"
        new_expires_at = datetime.now() + timedelta(hours=1)

        mock_cursor.fetchone.return_value = ('secret_id_123',)

        result = await vault_service.update_access_token(
            sample_user_id, 'gmail', new_token, new_expires_at
        )

        assert result is True
        # lookup + vault update + connection update = 3 calls
        assert mock_cursor.execute.call_count == 3

    @pytest.mark.asyncio
    async def test_update_access_token_no_connection(self, vault_service, mock_db_connection, sample_user_id):
        """Test access token update when no connection exists."""
        _, mock_cursor = mock_db_connection
        mock_cursor.fetchone.return_value = None

        result = await vault_service.update_access_token(
            sample_user_id, 'gmail', 'new_token'
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_revoke_tokens_success(self, vault_service, mock_db_connection, sample_user_id):
        """Test successful token revocation via RPC."""
        _, mock_cursor = mock_db_connection
        mock_cursor.fetchone.return_value = ({'success': True},)

        result = await vault_service.revoke_tokens(sample_user_id, 'gmail')

        assert result is True

    @pytest.mark.asyncio
    async def test_revoke_tokens_failure(self, vault_service, mock_db_connection, sample_user_id):
        """Test token revocation when RPC fails."""
        _, mock_cursor = mock_db_connection
        mock_cursor.fetchone.return_value = None

        result = await vault_service.revoke_tokens(sample_user_id, 'gmail')

        assert result is False

    @pytest.mark.asyncio
    async def test_get_connection_info_success(self, vault_service, mock_db_connection, sample_user_id):
        """Test successful connection info retrieval."""
        _, mock_cursor = mock_db_connection

        expected_info = (
            'connection_123', 'gmail', 'google_user_123', 'user@example.com',
            ['https://www.googleapis.com/auth/gmail.readonly'],
            datetime(2024, 1, 1, 12, 0, 0), True,
            datetime(2024, 1, 1, 10, 0, 0), datetime(2024, 1, 1, 11, 0, 0)
        )

        mock_cursor.fetchone.return_value = expected_info
        mock_cursor.description = [
            ('id',), ('service_name',), ('service_user_id',), ('service_user_email',),
            ('scopes',), ('token_expires_at',), ('is_active',), ('created_at',), ('updated_at',)
        ]

        result = await vault_service.get_connection_info(sample_user_id, 'gmail')

        assert result['id'] == 'connection_123'
        assert result['service_name'] == 'gmail'

    @pytest.mark.asyncio
    async def test_list_user_connections_success(self, vault_service, mock_db_connection, sample_user_id):
        """Test successful user connections listing."""
        _, mock_cursor = mock_db_connection

        expected_connections = [
            ('conn_1', 'gmail', 'google_user_123', 'user@example.com',
             ['https://www.googleapis.com/auth/gmail.readonly'], None, True,
             datetime(2024, 1, 1, 10, 0, 0), datetime(2024, 1, 1, 11, 0, 0)),
            ('conn_2', 'google_calendar', 'google_user_123', 'user@example.com',
             ['https://www.googleapis.com/auth/calendar'], None, True,
             datetime(2024, 1, 1, 10, 0, 0), datetime(2024, 1, 1, 11, 0, 0))
        ]

        mock_cursor.fetchall.return_value = expected_connections
        mock_cursor.description = [
            ('id',), ('service_name',), ('service_user_id',), ('service_user_email',),
            ('scopes',), ('token_expires_at',), ('is_active',), ('created_at',), ('updated_at',)
        ]

        result = await vault_service.list_user_connections(sample_user_id)

        assert len(result) == 2
        assert result[0]['service_name'] == 'gmail'
        assert result[1]['service_name'] == 'google_calendar'

    @pytest.mark.asyncio
    async def test_list_user_connections_empty(self, vault_service, mock_db_connection, sample_user_id):
        """Test user connections listing when no connections exist."""
        _, mock_cursor = mock_db_connection
        mock_cursor.fetchall.return_value = []

        result = await vault_service.list_user_connections(sample_user_id)

        assert result == []

    @pytest.mark.asyncio
    async def test_check_token_expiry_with_expiration(self, vault_service, mock_db_connection, sample_user_id):
        """Test token expiry check when expiration is set."""
        _, mock_cursor = mock_db_connection
        expiry_time = datetime(2024, 1, 1, 12, 0, 0)
        mock_cursor.fetchone.return_value = (expiry_time,)

        result = await vault_service.check_token_expiry(sample_user_id, 'gmail')

        assert isinstance(result, datetime)
        assert result == expiry_time

    @pytest.mark.asyncio
    async def test_check_token_expiry_no_expiration(self, vault_service, mock_db_connection, sample_user_id):
        """Test token expiry check when no expiration is set."""
        _, mock_cursor = mock_db_connection
        mock_cursor.fetchone.return_value = (None,)

        result = await vault_service.check_token_expiry(sample_user_id, 'gmail')

        assert result is None

    @pytest.mark.asyncio
    async def test_check_token_expiry_no_connection(self, vault_service, mock_db_connection, sample_user_id):
        """Test token expiry check when no connection exists."""
        _, mock_cursor = mock_db_connection
        mock_cursor.fetchone.return_value = None

        result = await vault_service.check_token_expiry(sample_user_id, 'gmail')

        assert result is None

    @pytest.mark.asyncio
    async def test_error_handling_database_exception(self, vault_service, mock_db_connection, sample_user_id):
        """Test error handling when database operations fail."""
        _, mock_cursor = mock_db_connection
        mock_cursor.execute.side_effect = Exception("Database connection failed")

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

    def test_invalid_context_raises(self, mock_db_connection):
        """Test that invalid context raises ValueError."""
        mock_conn, _ = mock_db_connection
        with pytest.raises(ValueError, match="Invalid context"):
            VaultTokenService(mock_conn, context="invalid")
