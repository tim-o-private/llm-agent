"""Tool cache service using TTL cache for tool configurations."""

import logging
from typing import Any, Dict, List, Optional

# Import with fallback for relative vs absolute imports
try:
    # Try relative imports first (when imported as a module)
    from ..database.connection import get_database_manager
    from .infrastructure_error_handler import handle_cache_errors, handle_database_errors
    from .ttl_cache_service import TTLCacheService, get_ttl_cache_service, register_ttl_cache_service
except ImportError:
    # Fall back to absolute imports (when run directly)
    from database.connection import get_database_manager

    from services.infrastructure_error_handler import handle_cache_errors, handle_database_errors
    from services.ttl_cache_service import TTLCacheService, register_ttl_cache_service

logger = logging.getLogger(__name__)


class ToolCacheService:
    """Tool cache service using TTL cache for tool configurations."""

    def __init__(self, ttl_seconds: int = 300, refresh_interval_seconds: int = 60):
        """
        Initialize tool cache service.

        Args:
            ttl_seconds: Time-to-live for cache entries in seconds
            refresh_interval_seconds: How often to check for updates
        """
        self.cache_service = TTLCacheService[Dict[str, Any]](
            cache_type="Tool",
            ttl_seconds=ttl_seconds,
            refresh_interval_seconds=refresh_interval_seconds,
            fetch_all_callback=self._fetch_all_tools,
            fetch_single_callback=self._fetch_tools_for_agent
        )

        # Register the cache service globally
        register_ttl_cache_service("Tool", self.cache_service)

        logger.info(f"Initialized tool cache service (TTL: {ttl_seconds}s, Refresh: {refresh_interval_seconds}s)")

    async def start(self) -> None:
        """Start the tool cache service."""
        await self.cache_service.start()

    async def stop(self) -> None:
        """Stop the tool cache service."""
        await self.cache_service.stop()

    async def get_tools_for_agent(self, agent_id: str) -> List[Dict[str, Any]]:
        """
        Get tools for a specific agent.

        Args:
            agent_id: Agent ID to get tools for

        Returns:
            List of tool configurations
        """
        return await self.cache_service.get(agent_id)

    @handle_cache_errors("get_cached_tools_for_agent", fallback=lambda: [])
    async def get_cached_tools_for_agent(self, agent_id: str) -> List[Dict[str, Any]]:
        """
        Get tools for a specific agent from cache.

        Args:
            agent_id: Agent ID to get tools for

        Returns:
            List of tool configurations for the agent
        """
        try:
            all_tools = await self.cache_service.get_data()
            return all_tools.get(agent_id, [])
        except Exception as e:
            logger.error(f"Failed to get cached tools for agent {agent_id}: {e}")
            # Error handler will manage this and apply fallback
            raise

    @handle_cache_errors("invalidate_cache")
    async def invalidate_cache(self, agent_id: Optional[str] = None) -> None:
        """Invalidate the tool cache.

        Args:
            agent_id: Specific agent to invalidate, or None for all
        """
        try:
            await self.cache_service.invalidate(agent_id)
            logger.info(f"Tool cache invalidated{f' for agent {agent_id}' if agent_id else ''}")
        except Exception as e:
            logger.error(f"Failed to invalidate tool cache: {e}")
            raise

    @handle_cache_errors("warm_cache")
    async def warm_cache(self, agent_ids: Optional[List[str]] = None) -> None:
        """Warm the tool cache by fetching fresh data.

        Args:
            agent_ids: List of agent IDs to warm, or None for all
        """
        try:
            await self.cache_service.warm_cache(agent_ids or [])
            logger.info("Tool cache warmed")
        except Exception as e:
            logger.error(f"Failed to warm tool cache: {e}")
            raise

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return self.cache_service.get_cache_stats()

    @handle_database_errors("fetch_all_tools", fallback=lambda: {})
    async def _fetch_all_tools(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Fetch all tools grouped by agent_id.

        Returns:
            Dictionary mapping agent_id to list of tool configurations
        """
        try:
            db_manager = get_database_manager()

            async for conn in db_manager.get_connection():
                async with conn.cursor() as cur:
                    # Fetch all agent-tool relationships with tool details
                    await cur.execute("""
                        SELECT
                            at.agent_id,
                            t.name as tool_name,
                            t.description,
                            t.type,
                            t.config,
                            t.is_active
                        FROM agent_tools at
                        JOIN tools t ON at.tool_id = t.id
                        WHERE at.is_active = true
                        AND at.is_deleted = false
                        AND t.is_active = true
                        AND t.is_deleted = false
                    """)

                    rows = await cur.fetchall()

                    # Group tools by agent_id
                    tools_by_agent = {}
                    for row in rows:
                        agent_id = str(row[0])
                        tool_config = {
                            "name": row[1],
                            "description": row[2],
                            "type": row[3],
                            "config": row[4],
                            "is_active": row[5]
                        }

                        if agent_id not in tools_by_agent:
                            tools_by_agent[agent_id] = []
                        tools_by_agent[agent_id].append(tool_config)

                    logger.info(f"Fetched tools for {len(tools_by_agent)} agents from database")
                    return tools_by_agent

        except Exception as e:
            logger.error(f"Failed to fetch all tools from database: {e}")
            # Error handler will manage this and apply fallback
            raise

    @handle_database_errors("fetch_tools_for_agent", fallback=lambda: [])
    async def _fetch_tools_for_agent(self, agent_id: str) -> List[Dict[str, Any]]:
        """
        Fetch tools for a specific agent.

        Args:
            agent_id: The agent ID to fetch tools for

        Returns:
            List of tool configurations for the agent
        """
        try:
            db_manager = get_database_manager()

            async for conn in db_manager.get_connection():
                async with conn.cursor() as cur:
                    await cur.execute("""
                        SELECT
                            t.name as tool_name,
                            t.description,
                            t.type,
                            t.config,
                            t.is_active
                        FROM agent_tools at
                        JOIN tools t ON at.tool_id = t.id
                        WHERE at.agent_id = %s
                        AND at.is_active = true
                        AND at.is_deleted = false
                        AND t.is_active = true
                        AND t.is_deleted = false
                    """, (agent_id,))

                    rows = await cur.fetchall()

                    tools = []
                    for row in rows:
                        tool_config = {
                            "name": row[0],
                            "description": row[1],
                            "type": row[2],
                            "config": row[3],
                            "is_active": row[4]
                        }
                        tools.append(tool_config)

                    logger.debug(f"Fetched {len(tools)} tools for agent {agent_id}")
                    return tools

        except Exception as e:
            logger.error(f"Failed to fetch tools for agent {agent_id}: {e}")
            # Error handler will manage this and apply fallback
            raise


# Global tool cache service instance
_tool_cache_service: Optional[ToolCacheService] = None


def get_tool_cache_service() -> ToolCacheService:
    """Get the global tool cache service instance."""
    global _tool_cache_service
    if _tool_cache_service is None:
        _tool_cache_service = ToolCacheService()
    return _tool_cache_service


async def initialize_tool_cache() -> None:
    """Initialize and start the tool cache service."""
    service = get_tool_cache_service()
    await service.start()
    logger.info("Tool cache service initialized and started")


async def shutdown_tool_cache() -> None:
    """Shutdown the tool cache service."""
    global _tool_cache_service
    if _tool_cache_service:
        await _tool_cache_service.stop()
        logger.info("Tool cache service stopped")


# Convenience function for getting tools (for backward compatibility)
async def get_cached_tools_for_agent(agent_id: str) -> List[Dict[str, Any]]:
    """
    Get cached tools for an agent.

    Args:
        agent_id: Agent ID to get tools for

    Returns:
        List of tool configurations
    """
    service = get_tool_cache_service()
    return await service.get_cached_tools_for_agent(agent_id)
