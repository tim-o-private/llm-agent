"""Supabase client management."""

import logging
from typing import Optional
from supabase import acreate_client, AsyncClient
from fastapi import HTTPException

try:
    from ..config.settings import get_settings
except ImportError:
    from chatServer.config.settings import get_settings

logger = logging.getLogger(__name__)


class SupabaseManager:
    """Manages the Supabase async client."""
    
    def __init__(self):
        self.client: Optional[AsyncClient] = None
        self.settings = get_settings()
    
    async def initialize(self) -> None:
        """Initialize the Supabase async client."""
        if not self.settings.supabase_url or not self.settings.supabase_service_key:
            logger.warning("Supabase async client not initialized due to missing URL or Key.")
            return
        
        try:
            logger.info(f"Attempting to initialize Supabase async client with URL: {self.settings.supabase_url}")
            client_instance = await acreate_client(self.settings.supabase_url, self.settings.supabase_service_key)
            
            if isinstance(client_instance, AsyncClient):
                self.client = client_instance
                logger.info("Supabase AsyncClient initialized successfully.")
            else:
                logger.error(f"Supabase client initialized but is not an AsyncClient. Type: {type(client_instance)}")
                self.client = None
        except Exception as e:
            logger.error(f"Error initializing Supabase async client: {e}", exc_info=True)
            self.client = None
    
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
    """FastAPI dependency to get the Supabase client."""
    supabase_manager = get_supabase_manager()
    return supabase_manager.get_client() 