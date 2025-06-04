"""Tests for InfrastructureErrorHandler."""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
import psycopg
from psycopg.errors import UndefinedColumn, OperationalError

from chatServer.services.infrastructure_error_handler import (
    InfrastructureErrorHandler,
    handle_infrastructure_errors,
    handle_database_errors,
    handle_cache_errors,
    InfrastructureError,
    DatabaseConnectionError,
    CacheServiceError
)

class TestInfrastructureErrorHandler:
    """Test the InfrastructureErrorHandler class."""
    
    @pytest.mark.asyncio
    async def test_handle_database_error_connection_error(self):
        """Test handling of database connection errors."""
        error = OperationalError("Connection failed")
        fallback = Mock(return_value="fallback_result")
        
        with patch('chatServer.database.connection.get_database_manager') as mock_get_db:
            mock_db_manager = AsyncMock()
            mock_get_db.return_value = mock_db_manager
            
            result = await InfrastructureErrorHandler.handle_database_error(
                "test_operation", error, fallback
            )
            
            # Should recreate pool and execute fallback
            mock_db_manager.close.assert_called_once()
            mock_db_manager.initialize.assert_called_once()
            fallback.assert_called_once()
            assert result == "fallback_result"
    
    @pytest.mark.asyncio
    async def test_handle_database_error_schema_mismatch(self):
        """Test handling of database schema mismatch errors."""
        error = UndefinedColumn("column does not exist")
        fallback = Mock(return_value="schema_fallback")
        
        result = await InfrastructureErrorHandler.handle_database_error(
            "test_operation", error, fallback
        )
        
        fallback.assert_called_once()
        assert result == "schema_fallback"
    
    @pytest.mark.asyncio
    async def test_handle_database_error_no_fallback(self):
        """Test handling of database errors without fallback."""
        error = UndefinedColumn("column does not exist")
        
        with pytest.raises(InfrastructureError) as exc_info:
            await InfrastructureErrorHandler.handle_database_error(
                "test_operation", error, None
            )
        
        assert "Database schema mismatch" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_handle_cache_error_with_fallback(self):
        """Test handling of cache errors with fallback."""
        error = Exception("Cache service unavailable")
        fallback = Mock(return_value="cache_fallback")
        
        result = await InfrastructureErrorHandler.handle_cache_error(
            "cache_operation", error, fallback
        )
        
        fallback.assert_called_once()
        assert result == "cache_fallback"
    
    @pytest.mark.asyncio
    async def test_handle_cache_error_no_fallback(self):
        """Test handling of cache errors without fallback."""
        error = Exception("Cache service unavailable")
        
        with pytest.raises(CacheServiceError) as exc_info:
            await InfrastructureErrorHandler.handle_cache_error(
                "cache_operation", error, None
            )
        
        assert "Cache operation failed" in str(exc_info.value)

class TestErrorDecorators:
    """Test the error handling decorators."""
    
    @pytest.mark.asyncio
    async def test_handle_infrastructure_errors_async_function(self):
        """Test decorator on async function."""
        fallback = Mock(return_value="fallback_result")
        
        @handle_infrastructure_errors("test_operation", fallback=fallback)
        async def failing_async_function():
            raise UndefinedColumn("test error")
        
        result = await failing_async_function()
        assert result == "fallback_result"
        fallback.assert_called_once()
    
    def test_handle_infrastructure_errors_sync_function(self):
        """Test decorator on sync function."""
        fallback = Mock(return_value="sync_fallback")
        
        @handle_infrastructure_errors("test_operation", fallback=fallback)
        def failing_sync_function():
            raise Exception("test error")
        
        result = failing_sync_function()
        assert result == "sync_fallback"
        fallback.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_handle_database_errors_decorator(self):
        """Test database-specific error decorator."""
        fallback = Mock(return_value="db_fallback")
        
        @handle_database_errors("fetch_data", fallback=fallback)
        async def failing_db_function():
            raise OperationalError("Database connection failed")
        
        with patch('chatServer.database.connection.get_database_manager') as mock_get_db:
            mock_db_manager = AsyncMock()
            mock_get_db.return_value = mock_db_manager
            
            result = await failing_db_function()
            assert result == "db_fallback"
    
    @pytest.mark.asyncio
    async def test_handle_cache_errors_decorator(self):
        """Test cache-specific error decorator."""
        fallback = Mock(return_value="cache_fallback")
        
        @handle_cache_errors("get_data", fallback=fallback)
        async def failing_cache_function():
            raise Exception("Cache unavailable")
        
        result = await failing_cache_function()
        assert result == "cache_fallback"
        fallback.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_successful_function_no_error_handling(self):
        """Test that successful functions are not affected by decorators."""
        @handle_infrastructure_errors("test_operation")
        async def successful_function():
            return "success"
        
        result = await successful_function()
        assert result == "success"

class TestErrorTypes:
    """Test custom error types."""
    
    def test_infrastructure_error_inheritance(self):
        """Test that custom errors inherit from base classes correctly."""
        assert issubclass(DatabaseConnectionError, InfrastructureError)
        assert issubclass(CacheServiceError, InfrastructureError)
        assert issubclass(InfrastructureError, Exception)
    
    def test_error_messages(self):
        """Test error message formatting."""
        db_error = DatabaseConnectionError("Database connection failed")
        cache_error = CacheServiceError("Cache operation failed")
        
        assert "Database connection failed" in str(db_error)
        assert "Cache operation failed" in str(cache_error) 