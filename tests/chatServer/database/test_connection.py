"""Unit tests for database connection module."""

import os
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from chatServer.database.connection import DatabaseManager, get_database_manager, get_db_connection


class TestDatabaseManager(unittest.TestCase):
    """Test cases for DatabaseManager class."""

    def setUp(self):
        """Set up test fixtures."""
        # Clear the settings cache before each test
        from chatServer.config.settings import get_settings
        get_settings.cache_clear()

        # Reset the global database manager
        import chatServer.database.connection
        chatServer.database.connection._db_manager = None

    def test_database_manager_initialization(self):
        """Test DatabaseManager initialization."""
        with patch.dict(os.environ, {
            "SUPABASE_DB_USER": "test_user",
            "SUPABASE_DB_PASSWORD": "test_password",
            "SUPABASE_DB_HOST": "test_host"
        }, clear=True):
            db_manager = DatabaseManager()

            self.assertIsNone(db_manager.pool)
            self.assertIsNotNone(db_manager.settings)


class TestDatabaseManagerAsync:
    """Test cases for DatabaseManager async methods."""

    def setup_method(self):
        """Set up test fixtures."""
        # Clear the settings cache before each test
        from chatServer.config.settings import get_settings
        get_settings.cache_clear()

        # Reset the global database manager
        import chatServer.database.connection
        chatServer.database.connection._db_manager = None

    @pytest.mark.asyncio
    async def test_database_manager_initialize_success(self):
        """Test successful database pool initialization."""
        with patch.dict(os.environ, {
            "SUPABASE_DB_USER": "test_user",
            "SUPABASE_DB_PASSWORD": "test_password",
            "SUPABASE_DB_HOST": "test_host"
        }, clear=True):
            with patch('chatServer.database.connection.AsyncConnectionPool') as mock_pool_class:
                mock_pool = AsyncMock()
                mock_pool_class.return_value = mock_pool

                db_manager = DatabaseManager()
                await db_manager.initialize()

                assert db_manager.pool is mock_pool
                mock_pool.open.assert_called_once_with(wait=True, timeout=30)

    @pytest.mark.asyncio
    async def test_database_manager_initialize_failure(self):
        """Test database pool initialization failure."""
        with patch.dict(os.environ, {
            "SUPABASE_DB_USER": "test_user",
            "SUPABASE_DB_PASSWORD": "test_password",
            "SUPABASE_DB_HOST": "test_host"
        }, clear=True):
            with patch('chatServer.database.connection.AsyncConnectionPool', side_effect=Exception("Connection failed")):  # noqa: E501
                db_manager = DatabaseManager()

                with pytest.raises(Exception):
                    await db_manager.initialize()

                assert db_manager.pool is None

    @pytest.mark.asyncio
    async def test_database_manager_close(self):
        """Test database pool closure."""
        with patch.dict(os.environ, {
            "SUPABASE_DB_USER": "test_user",
            "SUPABASE_DB_PASSWORD": "test_password",
            "SUPABASE_DB_HOST": "test_host"
        }, clear=True):
            mock_pool = AsyncMock()

            db_manager = DatabaseManager()
            db_manager.pool = mock_pool

            await db_manager.close()

            mock_pool.close.assert_called_once()
            assert db_manager.pool is None

    @pytest.mark.asyncio
    async def test_database_manager_close_no_pool(self):
        """Test database pool closure when no pool exists."""
        with patch.dict(os.environ, {
            "SUPABASE_DB_USER": "test_user",
            "SUPABASE_DB_PASSWORD": "test_password",
            "SUPABASE_DB_HOST": "test_host"
        }, clear=True):
            db_manager = DatabaseManager()

            # Should not raise an exception
            await db_manager.close()

            assert db_manager.pool is None

    @pytest.mark.asyncio
    async def test_database_manager_get_connection_success(self):
        """Test successful database connection retrieval."""
        with patch.dict(os.environ, {
            "SUPABASE_DB_USER": "test_user",
            "SUPABASE_DB_PASSWORD": "test_password",
            "SUPABASE_DB_HOST": "test_host"
        }, clear=True):
            mock_pool = MagicMock()
            mock_connection = MagicMock()
            mock_pool.connection.return_value.__aenter__.return_value = mock_connection
            mock_pool.connection.return_value.__aexit__.return_value = None

            db_manager = DatabaseManager()
            db_manager.pool = mock_pool

            # Test the async generator
            async for conn in db_manager.get_connection():
                assert conn is mock_connection
                break

    @pytest.mark.asyncio
    async def test_database_manager_get_connection_no_pool(self):
        """Test database connection retrieval when no pool exists."""
        with patch.dict(os.environ, {
            "SUPABASE_DB_USER": "test_user",
            "SUPABASE_DB_PASSWORD": "test_password",
            "SUPABASE_DB_HOST": "test_host"
        }, clear=True):
            db_manager = DatabaseManager()

            with pytest.raises(HTTPException) as exc_info:
                async for conn in db_manager.get_connection():
                    pass

            assert exc_info.value.status_code == 503
            assert "Database service not available" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_database_manager_get_connection_pool_error(self):
        """Test database connection retrieval when pool raises an error."""
        with patch.dict(os.environ, {
            "SUPABASE_DB_USER": "test_user",
            "SUPABASE_DB_PASSWORD": "test_password",
            "SUPABASE_DB_HOST": "test_host"
        }, clear=True):
            mock_pool = MagicMock()
            mock_pool.connection.side_effect = Exception("Pool error")

            db_manager = DatabaseManager()
            db_manager.pool = mock_pool

            with pytest.raises(HTTPException) as exc_info:
                async for conn in db_manager.get_connection():
                    pass

            assert exc_info.value.status_code == 503
            assert "Failed to acquire database connection" in exc_info.value.detail


class TestGetDatabaseManager(unittest.TestCase):
    """Test cases for get_database_manager function."""

    def setUp(self):
        """Reset the global database manager before each test."""
        import chatServer.database.connection
        chatServer.database.connection._db_manager = None

    def test_get_database_manager_creates_instance(self):
        """Test that get_database_manager creates a DatabaseManager instance."""
        with patch.dict(os.environ, {
            "SUPABASE_DB_USER": "test_user",
            "SUPABASE_DB_PASSWORD": "test_password",
            "SUPABASE_DB_HOST": "test_host"
        }, clear=True):
            manager = get_database_manager()

            self.assertIsInstance(manager, DatabaseManager)

    def test_get_database_manager_singleton(self):
        """Test that get_database_manager returns the same instance (singleton pattern)."""
        with patch.dict(os.environ, {
            "SUPABASE_DB_USER": "test_user",
            "SUPABASE_DB_PASSWORD": "test_password",
            "SUPABASE_DB_HOST": "test_host"
        }, clear=True):
            manager1 = get_database_manager()
            manager2 = get_database_manager()

            self.assertIs(manager1, manager2)


class TestGetDbConnectionAsync:
    """Test cases for get_db_connection function."""

    def setup_method(self):
        """Reset the global database manager before each test."""
        import chatServer.database.connection
        chatServer.database.connection._db_manager = None

    @pytest.mark.asyncio
    async def test_get_db_connection_delegates_to_manager(self):
        """Test that get_db_connection delegates to the database manager."""
        with patch.dict(os.environ, {
            "SUPABASE_DB_USER": "test_user",
            "SUPABASE_DB_PASSWORD": "test_password",
            "SUPABASE_DB_HOST": "test_host"
        }, clear=True):
            mock_connection = MagicMock()

            with patch('chatServer.database.connection.get_database_manager') as mock_get_manager:
                mock_manager = MagicMock()
                mock_manager.get_connection.return_value.__aiter__.return_value = [mock_connection]
                mock_get_manager.return_value = mock_manager

                # Test the async generator
                async for conn in get_db_connection():
                    assert conn is mock_connection
                    break

                mock_get_manager.assert_called_once()
                mock_manager.get_connection.assert_called_once()


if __name__ == '__main__':
    unittest.main()
