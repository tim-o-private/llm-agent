"""Database connection management."""

import logging
import asyncio
from typing import Optional, AsyncIterator
import psycopg
from psycopg_pool import AsyncConnectionPool
from fastapi import HTTPException

try:
    from ..config.settings import get_settings
except ImportError:
    from chatServer.config.settings import get_settings

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages the database connection pool with auto-initialization."""
    
    def __init__(self):
        self.pool: Optional[AsyncConnectionPool] = None
        self.settings = get_settings()
        self._initialization_lock = asyncio.Lock()
        self._initialization_attempted = False
    
    async def initialize(self) -> None:
        """Initialize the database connection pool."""
        async with self._initialization_lock:
            if self.pool is not None:
                logger.debug("Database connection pool already initialized")
                return
                
            try:
                conn_str = self.settings.database_url
                logger.info(f"Initializing AsyncConnectionPool with: postgresql://{self.settings.db_user}:[REDACTED]@{self.settings.db_host}:{self.settings.db_port}/{self.settings.db_name}?connect_timeout=10")
                
                self.pool = AsyncConnectionPool(
                    conninfo=conn_str, 
                    open=False, 
                    min_size=2, 
                    max_size=10, 
                    check=AsyncConnectionPool.check_connection
                )
                await self.pool.open(wait=True, timeout=30)
                self._initialization_attempted = True
                logger.info("Database connection pool started successfully.")
            except Exception as e:
                logger.critical(f"Failed to initialize database connection pool: {e}", exc_info=True)
                self.pool = None
                self._initialization_attempted = True
                raise
    
    async def ensure_initialized(self) -> None:
        """Ensure the database connection pool is initialized."""
        if self.pool is None and not self._initialization_attempted:
            logger.info("Database pool not initialized, attempting auto-initialization...")
            try:
                await self.initialize()
            except Exception as e:
                logger.error(f"Auto-initialization of database pool failed: {e}")
                raise HTTPException(status_code=503, detail="Database service not available. Failed to initialize connection pool.")
        elif self.pool is None and self._initialization_attempted:
            logger.error("Database pool initialization was attempted but failed")
            raise HTTPException(status_code=503, detail="Database service not available. Pool initialization failed.")
    
    async def close(self) -> None:
        """Close the database connection pool."""
        if self.pool:
            await self.pool.close()
            logger.info("Database connection pool closed.")
            self.pool = None
            self._initialization_attempted = False
    
    async def get_connection(self) -> AsyncIterator[psycopg.AsyncConnection]:
        """Get a database connection from the pool."""
        await self.ensure_initialized()
        
        if self.pool is None:
            logger.error("Database connection pool is not available after initialization attempt.")
            raise HTTPException(status_code=503, detail="Database service not available. Pool not initialized.")
        
        try:
            async with self.pool.connection() as conn:
                logger.debug("DB connection acquired from pool.")
                yield conn
            logger.debug("DB connection released back to pool.")
        except Exception as e:
            logger.error(f"Failed to get DB connection from pool: {e}", exc_info=True)
            raise HTTPException(status_code=503, detail="Failed to acquire database connection.")


# Global database manager instance
_db_manager: Optional[DatabaseManager] = None


def get_database_manager() -> DatabaseManager:
    """Get the global database manager instance."""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
    return _db_manager


# @docs memory-bank/patterns/api-patterns.md#pattern-1-single-database-use-prescribed-connections
# @rules memory-bank/rules/api-rules.json#api-001
async def get_db_connection() -> AsyncIterator[psycopg.AsyncConnection]:
    """FastAPI dependency to get a database connection."""
    db_manager = get_database_manager()
    async for conn in db_manager.get_connection():
        yield conn 