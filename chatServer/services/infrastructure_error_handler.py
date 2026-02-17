"""Infrastructure error handling service with decorator-based error management."""

import asyncio
import logging
from functools import wraps
from typing import Any, Callable, Optional, TypeVar

import psycopg
from psycopg.errors import OperationalError, UndefinedColumn

logger = logging.getLogger(__name__)

# Type variable for generic function return types
T = TypeVar('T')

class InfrastructureError(Exception):
    """Base exception for infrastructure-related errors."""
    pass

class DatabaseConnectionError(InfrastructureError):
    """Raised when database connection issues occur."""
    pass

class CacheServiceError(InfrastructureError):
    """Raised when cache service operations fail."""
    pass

class InfrastructureErrorHandler:
    """Centralized error handler for infrastructure operations."""

    @staticmethod
    async def handle_database_error(
        operation: str,
        error: Exception,
        fallback: Optional[Callable] = None
    ) -> Any:
        """
        Handle database-related errors with appropriate fallback strategies.

        Args:
            operation: Name of the operation that failed
            error: The exception that occurred
            fallback: Optional fallback function to execute

        Returns:
            Result of fallback function if provided, otherwise raises InfrastructureError

        Raises:
            DatabaseConnectionError: For connection-related issues
            InfrastructureError: For other database errors
        """
        logger.error(f"Database operation '{operation}' failed: {error}")

        if isinstance(error, (psycopg.OperationalError, OperationalError)):
            # Connection pool issues - trigger pool recreation if possible
            logger.warning(f"Database connection issue detected in operation '{operation}', attempting recovery")

            try:
                # Try to get database manager and recreate pool
                from chatServer.database.connection import get_database_manager
                db_manager = get_database_manager()
                await db_manager.close()
                await db_manager.initialize()
                logger.info(f"Database pool recreated after error in operation '{operation}'")

                if fallback:
                    logger.info(f"Executing fallback for operation '{operation}' after pool recreation")
                    return await fallback() if asyncio.iscoroutinefunction(fallback) else fallback()

            except Exception as recovery_error:
                logger.error(f"Failed to recover from database error in operation '{operation}': {recovery_error}")
                raise DatabaseConnectionError(f"Database connection failed for operation '{operation}' and recovery failed: {recovery_error}")

            raise DatabaseConnectionError(f"Database connection failed for operation '{operation}': {error}")

        elif isinstance(error, UndefinedColumn):
            # Schema mismatch - log and provide helpful error
            logger.error(f"Database schema mismatch in operation '{operation}': {error}")
            if fallback:
                logger.info(f"Executing fallback for operation '{operation}' due to schema mismatch")
                return await fallback() if asyncio.iscoroutinefunction(fallback) else fallback()
            raise InfrastructureError(f"Database schema mismatch in operation '{operation}': {error}")

        elif hasattr(error, '__module__') and 'supabase' in str(error.__module__):
            # Supabase client errors (generic check since ClientError import varies)
            logger.error(f"Supabase client error in operation '{operation}': {error}")
            if fallback:
                logger.info(f"Executing fallback for operation '{operation}' due to Supabase error")
                return await fallback() if asyncio.iscoroutinefunction(fallback) else fallback()
            raise InfrastructureError(f"Supabase operation failed for '{operation}': {error}")

        else:
            # Generic database error
            logger.error(f"Unexpected database error in operation '{operation}': {error}")
            if fallback:
                logger.info(f"Executing fallback for operation '{operation}' due to unexpected error")
                return await fallback() if asyncio.iscoroutinefunction(fallback) else fallback()
            raise InfrastructureError(f"Database operation failed for '{operation}': {error}")

    @staticmethod
    async def handle_cache_error(
        operation: str,
        error: Exception,
        fallback: Optional[Callable] = None
    ) -> Any:
        """
        Handle cache-related errors with appropriate fallback strategies.

        Args:
            operation: Name of the cache operation that failed
            error: The exception that occurred
            fallback: Optional fallback function to execute

        Returns:
            Result of fallback function if provided, otherwise raises CacheServiceError
        """
        logger.error(f"Cache operation '{operation}' failed: {error}")

        if fallback:
            logger.info(f"Executing fallback for cache operation '{operation}'")
            return await fallback() if asyncio.iscoroutinefunction(fallback) else fallback()

        raise CacheServiceError(f"Cache operation failed for '{operation}': {error}")

    @staticmethod
    async def handle_error(
        operation: str,
        error: Exception,
        fallback: Optional[Callable] = None
    ) -> Any:
        """
        Generic error handler that routes to specific handlers based on error type.

        Args:
            operation: Name of the operation that failed
            error: The exception that occurred
            fallback: Optional fallback function to execute

        Returns:
            Result of appropriate error handler
        """
        if isinstance(error, psycopg.Error) or (hasattr(error, '__module__') and 'supabase' in str(error.__module__)):
            return await InfrastructureErrorHandler.handle_database_error(operation, error, fallback)
        elif "cache" in operation.lower():
            return await InfrastructureErrorHandler.handle_cache_error(operation, error, fallback)
        else:
            logger.error(f"Unhandled infrastructure error in operation '{operation}': {error}")
            if fallback:
                logger.info(f"Executing fallback for operation '{operation}'")
                return await fallback() if asyncio.iscoroutinefunction(fallback) else fallback()
            raise InfrastructureError(f"Infrastructure operation failed for '{operation}': {error}")

def handle_infrastructure_errors(operation_name: str, fallback: Optional[Callable] = None):
    """
    Decorator for handling infrastructure errors with consistent patterns.

    Args:
        operation_name: Name of the operation for logging and error context
        fallback: Optional fallback function to execute on error

    Returns:
        Decorated function with error handling

    Example:
        @handle_infrastructure_errors("tool_loading", fallback=lambda: [])
        async def load_tools_from_cache(agent_id: str):
            # Implementation that might fail
            pass
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        if asyncio.iscoroutinefunction(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs) -> T:
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    logger.debug(f"Error in {operation_name}: {e}, applying error handler")
                    return await InfrastructureErrorHandler.handle_error(operation_name, e, fallback)
            return async_wrapper
        else:
            @wraps(func)
            def sync_wrapper(*args, **kwargs) -> T:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    logger.debug(f"Error in {operation_name}: {e}, applying error handler")
                    # For sync functions, we need to handle async fallbacks properly
                    if fallback and asyncio.iscoroutinefunction(fallback):
                        # If fallback is async but function is sync, we need to run it in event loop
                        try:
                            loop = asyncio.get_event_loop()
                            return loop.run_until_complete(
                                InfrastructureErrorHandler.handle_error(operation_name, e, fallback)
                            )
                        except RuntimeError:
                            # No event loop running, create one
                            return asyncio.run(
                                InfrastructureErrorHandler.handle_error(operation_name, e, fallback)
                            )
                    else:
                        # Sync fallback or no fallback
                        return asyncio.run(
                            InfrastructureErrorHandler.handle_error(operation_name, e, fallback)
                        )
            return sync_wrapper
    return decorator

# Convenience decorators for common operations
def handle_database_errors(operation_name: str, fallback: Optional[Callable] = None):
    """Decorator specifically for database operations."""
    return handle_infrastructure_errors(f"database_{operation_name}", fallback)

def handle_cache_errors(operation_name: str, fallback: Optional[Callable] = None):
    """Decorator specifically for cache operations."""
    return handle_infrastructure_errors(f"cache_{operation_name}", fallback)

def handle_agent_loading_errors(fallback: Optional[Callable] = None):
    """Decorator specifically for agent loading operations."""
    return handle_infrastructure_errors("agent_loading", fallback)
