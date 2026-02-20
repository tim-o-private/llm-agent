"""User instructions cache service using TTL cache."""

import logging
from typing import Any, Dict, List, Optional

from ..database.connection import get_database_manager
from .infrastructure_error_handler import handle_cache_errors, handle_database_errors
from .ttl_cache_service import TTLCacheService, register_ttl_cache_service

logger = logging.getLogger(__name__)


class UserInstructionsCacheService:
    """Cache service for user agent prompt customizations.

    Cache key format: "{user_id}:{agent_name}"
    Stores the instructions text (or empty list if no instructions found).
    Short TTL (120s) so user edits propagate quickly.
    No fetch_all_callback — too many user/agent combinations.
    """

    def __init__(self, ttl_seconds: int = 120, refresh_interval_seconds: int = 60):
        self.cache_service = TTLCacheService[str](
            cache_type="UserInstructions",
            ttl_seconds=ttl_seconds,
            refresh_interval_seconds=refresh_interval_seconds,
            fetch_all_callback=None,  # No bulk fetch — too many combinations
            fetch_single_callback=self._fetch_user_instructions,
        )
        register_ttl_cache_service("UserInstructions", self.cache_service)
        logger.info(f"Initialized user instructions cache service (TTL: {ttl_seconds}s)")

    async def start(self) -> None:
        await self.cache_service.start()

    async def stop(self) -> None:
        await self.cache_service.stop()

    @staticmethod
    def _make_cache_key(user_id: str, agent_name: str) -> str:
        return f"{user_id}:{agent_name}"

    async def get_user_instructions(self, user_id: str, agent_name: str) -> Optional[str]:
        """Get cached user instructions. Returns instructions text or None."""
        cache_key = self._make_cache_key(user_id, agent_name)
        results = await self.cache_service.get(cache_key)
        if results:
            return results[0]
        return None

    @handle_cache_errors("invalidate_user_instructions_cache")
    async def invalidate_cache(self, user_id: Optional[str] = None, agent_name: Optional[str] = None) -> None:
        if user_id and agent_name:
            cache_key = self._make_cache_key(user_id, agent_name)
            await self.cache_service.invalidate(cache_key)
        else:
            await self.cache_service.invalidate()
        logger.info("User instructions cache invalidated")

    def get_cache_stats(self) -> Dict[str, Any]:
        return self.cache_service.get_cache_stats()

    @handle_database_errors("fetch_user_instructions", fallback=lambda: [])
    async def _fetch_user_instructions(self, cache_key: str) -> List[str]:
        """Fetch instructions for a user_id:agent_name pair."""
        try:
            parts = cache_key.split(":", 1)
            if len(parts) != 2:
                logger.error(f"Invalid cache key format: {cache_key}")
                return []

            user_id, agent_name = parts

            db_manager = get_database_manager()
            async for conn in db_manager.get_connection():
                async with conn.cursor() as cur:
                    await cur.execute("""
                        SELECT instructions
                        FROM user_agent_prompt_customizations
                        WHERE user_id = %s AND agent_name = %s
                    """, (user_id, agent_name))
                    row = await cur.fetchone()

                    if row and row[0]:
                        logger.debug(f"Fetched user instructions for {user_id}/{agent_name}")
                        return [row[0]]

                    logger.debug(f"No user instructions found for {user_id}/{agent_name}")
                    return []
        except Exception as e:
            logger.error(f"Failed to fetch user instructions for {cache_key}: {e}")
            raise


# Global instance
_user_instructions_cache_service: Optional[UserInstructionsCacheService] = None


def get_user_instructions_cache_service() -> UserInstructionsCacheService:
    global _user_instructions_cache_service
    if _user_instructions_cache_service is None:
        _user_instructions_cache_service = UserInstructionsCacheService()
    return _user_instructions_cache_service


async def initialize_user_instructions_cache() -> None:
    service = get_user_instructions_cache_service()
    await service.start()
    logger.info("User instructions cache service initialized and started")


async def shutdown_user_instructions_cache() -> None:
    global _user_instructions_cache_service
    if _user_instructions_cache_service:
        await _user_instructions_cache_service.stop()
        logger.info("User instructions cache service stopped")


async def get_cached_user_instructions(user_id: str, agent_name: str) -> Optional[str]:
    """Convenience function: get cached user instructions."""
    service = get_user_instructions_cache_service()
    return await service.get_user_instructions(user_id, agent_name)
