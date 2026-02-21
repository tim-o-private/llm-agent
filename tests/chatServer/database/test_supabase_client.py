"""Unit tests for Supabase client module."""

import os
import unittest
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from chatServer.database.supabase_client import SupabaseManager, get_supabase_client, get_supabase_manager


class TestSupabaseManager(unittest.TestCase):
    """Test cases for SupabaseManager class."""

    def setUp(self):
        """Set up test fixtures."""
        # Clear the settings cache before each test
        from chatServer.config.settings import get_settings
        get_settings.cache_clear()

        # Reset the global Supabase manager
        import chatServer.database.supabase_client
        chatServer.database.supabase_client._supabase_manager = None

    def test_supabase_manager_initialization(self):
        """Test SupabaseManager initialization."""
        with patch.dict(os.environ, {
            "SUPABASE_URL": "https://test.supabase.co",
            "SUPABASE_SERVICE_ROLE_KEY": "test_service_key"
        }, clear=True):
            supabase_manager = SupabaseManager()

            self.assertIsNone(supabase_manager.client)
            self.assertIsNotNone(supabase_manager.settings)

    def test_supabase_manager_get_client_success(self):
        """Test successful client retrieval."""
        from supabase import AsyncClient

        mock_client = MagicMock(spec=AsyncClient)
        supabase_manager = SupabaseManager()
        supabase_manager.client = mock_client

        result = supabase_manager.get_client()

        self.assertIs(result, mock_client)

    def test_supabase_manager_get_client_no_client(self):
        """Test client retrieval when no client exists."""
        supabase_manager = SupabaseManager()

        with self.assertRaises(HTTPException) as context:
            supabase_manager.get_client()

        self.assertEqual(context.exception.status_code, 503)
        self.assertIn("Supabase client not available", context.exception.detail)


class TestSupabaseManagerAsync:
    """Test cases for SupabaseManager async methods."""

    def setup_method(self):
        """Set up test fixtures."""
        # Clear the settings cache before each test
        from chatServer.config.settings import get_settings
        get_settings.cache_clear()

        # Reset the global Supabase manager
        import chatServer.database.supabase_client
        chatServer.database.supabase_client._supabase_manager = None

    @pytest.mark.asyncio
    async def test_supabase_manager_initialize_success(self):
        """Test successful Supabase client initialization."""
        from supabase import AsyncClient

        with patch.dict(os.environ, {
            "SUPABASE_URL": "https://test.supabase.co",
            "SUPABASE_SERVICE_ROLE_KEY": "test_service_key"
        }, clear=True):
            mock_client = MagicMock(spec=AsyncClient)

            with patch('chatServer.database.supabase_client.acreate_client', return_value=mock_client) as mock_create:
                supabase_manager = SupabaseManager()
                await supabase_manager.initialize()

                assert supabase_manager.client is mock_client
                mock_create.assert_called_once_with("https://test.supabase.co", "test_service_key")

    @pytest.mark.asyncio
    async def test_supabase_manager_initialize_missing_url(self):
        """Test Supabase client initialization with missing URL."""
        with patch.dict(os.environ, {
            "SUPABASE_SERVICE_ROLE_KEY": "test_service_key"
        }, clear=True):
            supabase_manager = SupabaseManager()
            await supabase_manager.initialize()

            assert supabase_manager.client is None

    @pytest.mark.asyncio
    async def test_supabase_manager_initialize_missing_key(self):
        """Test Supabase client initialization with missing service key."""
        with patch.dict(os.environ, {
            "SUPABASE_URL": "https://test.supabase.co"
        }, clear=True):
            supabase_manager = SupabaseManager()
            await supabase_manager.initialize()

            assert supabase_manager.client is None

    @pytest.mark.asyncio
    async def test_supabase_manager_initialize_wrong_client_type(self):
        """Test Supabase client initialization with wrong client type."""
        with patch.dict(os.environ, {
            "SUPABASE_URL": "https://test.supabase.co",
            "SUPABASE_SERVICE_ROLE_KEY": "test_service_key"
        }, clear=True):
            mock_wrong_client = MagicMock()  # Not an AsyncClient

            with patch('chatServer.database.supabase_client.acreate_client', return_value=mock_wrong_client):
                supabase_manager = SupabaseManager()
                await supabase_manager.initialize()

                assert supabase_manager.client is None

    @pytest.mark.asyncio
    async def test_supabase_manager_initialize_exception(self):
        """Test Supabase client initialization with exception."""
        with patch.dict(os.environ, {
            "SUPABASE_URL": "https://test.supabase.co",
            "SUPABASE_SERVICE_ROLE_KEY": "test_service_key"
        }, clear=True):
            with patch('chatServer.database.supabase_client.acreate_client', side_effect=Exception("Connection failed")):  # noqa: E501
                supabase_manager = SupabaseManager()
                await supabase_manager.initialize()

                assert supabase_manager.client is None


class TestGetSupabaseManager(unittest.TestCase):
    """Test cases for get_supabase_manager function."""

    def setUp(self):
        """Reset the global Supabase manager before each test."""
        import chatServer.database.supabase_client
        chatServer.database.supabase_client._supabase_manager = None

    def test_get_supabase_manager_creates_instance(self):
        """Test that get_supabase_manager creates a SupabaseManager instance."""
        with patch.dict(os.environ, {
            "SUPABASE_URL": "https://test.supabase.co",
            "SUPABASE_SERVICE_ROLE_KEY": "test_service_key"
        }, clear=True):
            manager = get_supabase_manager()

            self.assertIsInstance(manager, SupabaseManager)

    def test_get_supabase_manager_singleton(self):
        """Test that get_supabase_manager returns the same instance (singleton pattern)."""
        with patch.dict(os.environ, {
            "SUPABASE_URL": "https://test.supabase.co",
            "SUPABASE_SERVICE_ROLE_KEY": "test_service_key"
        }, clear=True):
            manager1 = get_supabase_manager()
            manager2 = get_supabase_manager()

            self.assertIs(manager1, manager2)


class TestGetSupabaseClientAsync:
    """Test cases for get_supabase_client function."""

    def setup_method(self):
        """Reset the global Supabase manager before each test."""
        import chatServer.database.supabase_client
        chatServer.database.supabase_client._supabase_manager = None

    @pytest.mark.asyncio
    async def test_get_supabase_client_success(self):
        """Test successful client retrieval through dependency."""
        from supabase import AsyncClient

        mock_client = MagicMock(spec=AsyncClient)

        with patch('chatServer.database.supabase_client.get_supabase_manager') as mock_get_manager:
            mock_manager = MagicMock()
            mock_manager.get_client.return_value = mock_client
            mock_get_manager.return_value = mock_manager

            result = await get_supabase_client()

            assert result is mock_client
            mock_get_manager.assert_called_once()
            mock_manager.get_client.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_supabase_client_manager_raises_exception(self):
        """Test client retrieval when manager raises an exception."""
        with patch('chatServer.database.supabase_client.get_supabase_manager') as mock_get_manager:
            mock_manager = MagicMock()
            mock_manager.get_client.side_effect = HTTPException(status_code=503, detail="Client not available")
            mock_get_manager.return_value = mock_manager

            with pytest.raises(HTTPException) as exc_info:
                await get_supabase_client()

            assert exc_info.value.status_code == 503
            assert exc_info.value.detail == "Client not available"


if __name__ == '__main__':
    unittest.main()
