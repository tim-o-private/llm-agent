"""Supabase client management."""

import asyncio
import logging
from typing import Optional

from fastapi import Depends, HTTPException

from supabase import AsyncClient, acreate_client

from ..config.settings import get_settings
from ..dependencies.auth import get_current_user
from .scoped_client import SystemClient, UserScopedClient

logger = logging.getLogger(__name__)


class SupabaseManager:
    """Manages the Supabase async client with auto-initialization."""

    def __init__(self):
        self.client: Optional[AsyncClient] = None
        self.settings = get_settings()
        self._initialization_lock = asyncio.Lock()
        self._initialization_attempted = False

    async def initialize(self) -> None:
        """Initialize the Supabase async client."""
        async with self._initialization_lock:
            if self.client is not None:
                logger.debug("Supabase client already initialized")
                return

            if not self.settings.supabase_url or not self.settings.supabase_service_key:
                logger.warning("Supabase async client not initialized due to missing URL or Key.")
                self._initialization_attempted = True
                return

            try:
                logger.info(f"Attempting to initialize Supabase async client with URL: {self.settings.supabase_url}")
                client_instance = await acreate_client(self.settings.supabase_url, self.settings.supabase_service_key)

                if isinstance(client_instance, AsyncClient):
                    self.client = client_instance
                    self._initialization_attempted = True
                    logger.info("Supabase AsyncClient initialized successfully.")
                else:
                    logger.error(
                        f"Supabase client initialized but is not AsyncClient. Type: {type(client_instance)}"
                    )
                    self.client = None
                    self._initialization_attempted = True
            except Exception as e:
                logger.error(f"Error initializing Supabase async client: {e}", exc_info=True)
                self.client = None
                self._initialization_attempted = True

    async def ensure_initialized(self) -> None:
        """Ensure the Supabase client is initialized, auto-initializing if needed."""
        if self.client is None and not self._initialization_attempted:
            logger.info("Supabase client not initialized, attempting auto-initialization...")
            await self.initialize()
        elif self.client is None and self._initialization_attempted:
            logger.error("Supabase client initialization was attempted but failed")
            raise HTTPException(status_code=503, detail="Supabase client not available. Initialization failed.")

    def get_client(self) -> AsyncClient:
        """Get the Supabase client."""
        if self.client is None:
            logger.error("Supabase client not available. Check server startup logs.")
            raise HTTPException(status_code=503, detail="Supabase client not available. Check server startup logs.")
        return self.client


# Global Supabase manager instance
_supabase_manager: Optional[SupabaseManager] = None


def get_supabase_manager() -> SupabaseManager:
    """Get the global Supabase manager instance."""
    global _supabase_manager
    if _supabase_manager is None:
        _supabase_manager = SupabaseManager()
    return _supabase_manager


async def get_supabase_client() -> AsyncClient:
    """FastAPI dependency to get the raw Supabase client.

    Prefer get_user_scoped_client() for user-facing code or
    get_system_client() for background services.
    """
    supabase_manager = get_supabase_manager()
    if isinstance(supabase_manager, SupabaseManager):
        await supabase_manager.ensure_initialized()
    return supabase_manager.get_client()


async def get_user_scoped_client(
    user_id: str = Depends(get_current_user),
    client: AsyncClient = Depends(get_supabase_client),
) -> UserScopedClient:
    """FastAPI dependency for user-facing endpoints. Auto-scopes all queries."""
    return UserScopedClient(client, user_id)


async def get_system_client(
    client: AsyncClient = Depends(get_supabase_client),
) -> SystemClient:
    """FastAPI dependency for background services only. No user scoping."""
    return SystemClient(client)
