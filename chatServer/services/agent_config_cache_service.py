"""Agent configuration cache service using TTL cache."""

import logging
from typing import Any, Dict, List, Optional

try:
    from ..database.connection import get_database_manager
    from .infrastructure_error_handler import handle_cache_errors, handle_database_errors
    from .ttl_cache_service import TTLCacheService, register_ttl_cache_service
except ImportError:
    from database.connection import get_database_manager

    from services.infrastructure_error_handler import handle_cache_errors, handle_database_errors
    from services.ttl_cache_service import TTLCacheService, register_ttl_cache_service

logger = logging.getLogger(__name__)


class AgentConfigCacheService:
    """Cache service for agent configurations from the database."""

    def __init__(self, ttl_seconds: int = 600, refresh_interval_seconds: int = 120):
        self.cache_service = TTLCacheService[Dict[str, Any]](
            cache_type="AgentConfig",
            ttl_seconds=ttl_seconds,
            refresh_interval_seconds=refresh_interval_seconds,
            fetch_all_callback=self._fetch_all_agent_configs,
            fetch_single_callback=self._fetch_agent_config,
        )
        register_ttl_cache_service("AgentConfig", self.cache_service)
        logger.info(f"Initialized agent config cache (TTL: {ttl_seconds}s, Refresh: {refresh_interval_seconds}s)")

    async def start(self) -> None:
        await self.cache_service.start()

    async def stop(self) -> None:
        await self.cache_service.stop()

    async def get_agent_config(self, agent_name: str) -> Optional[Dict[str, Any]]:
        """Get agent config by agent_name. Returns the config dict or None."""
        results = await self.cache_service.get(agent_name)
        if results:
            return results[0]
        return None

    @handle_cache_errors("get_cached_agent_config", fallback=lambda: None)
    async def get_cached_agent_config(self, agent_name: str) -> Optional[Dict[str, Any]]:
        """Get agent config from cache with error handling."""
        try:
            all_configs = await self.cache_service.get_data()
            configs = all_configs.get(agent_name, [])
            if configs:
                return configs[0]
            return None
        except AttributeError:
            # get_data not available, fall back to get()
            return await self.get_agent_config(agent_name)
        except Exception as e:
            logger.error(f"Failed to get cached agent config for {agent_name}: {e}")
            raise

    @handle_cache_errors("invalidate_agent_config_cache")
    async def invalidate_cache(self, agent_name: Optional[str] = None) -> None:
        await self.cache_service.invalidate(agent_name)
        logger.info(f"Agent config cache invalidated{f' for {agent_name}' if agent_name else ''}")

    def get_cache_stats(self) -> Dict[str, Any]:
        return self.cache_service.get_cache_stats()

    @handle_database_errors("fetch_all_agent_configs", fallback=lambda: {})
    async def _fetch_all_agent_configs(self) -> Dict[str, List[Dict[str, Any]]]:
        """Fetch all agent configurations, keyed by agent_name."""
        try:
            db_manager = get_database_manager()
            async for conn in db_manager.get_connection():
                async with conn.cursor() as cur:
                    await cur.execute("""
                        SELECT id, agent_name, soul, identity, llm_config,
                               created_at, updated_at
                        FROM agent_configurations
                    """)
                    rows = await cur.fetchall()
                    columns = [desc[0] for desc in cur.description]

                    configs_by_name: Dict[str, List[Dict[str, Any]]] = {}
                    for row in rows:
                        config = dict(zip(columns, row))
                        agent_name = config["agent_name"]
                        configs_by_name[agent_name] = [config]

                    logger.info(f"Fetched {len(configs_by_name)} agent configurations from database")
                    return configs_by_name
        except Exception as e:
            logger.error(f"Failed to fetch all agent configs from database: {e}")
            raise

    @handle_database_errors("fetch_agent_config", fallback=lambda: [])
    async def _fetch_agent_config(self, agent_name: str) -> List[Dict[str, Any]]:
        """Fetch config for a single agent by name."""
        try:
            db_manager = get_database_manager()
            async for conn in db_manager.get_connection():
                async with conn.cursor() as cur:
                    await cur.execute("""
                        SELECT id, agent_name, soul, identity, llm_config,
                               created_at, updated_at
                        FROM agent_configurations
                        WHERE agent_name = %s
                    """, (agent_name,))
                    rows = await cur.fetchall()
                    columns = [desc[0] for desc in cur.description]

                    configs = [dict(zip(columns, row)) for row in rows]
                    logger.debug(f"Fetched config for agent '{agent_name}': {len(configs)} result(s)")
                    return configs
        except Exception as e:
            logger.error(f"Failed to fetch agent config for {agent_name}: {e}")
            raise


# Global instance
_agent_config_cache_service: Optional[AgentConfigCacheService] = None


def get_agent_config_cache_service() -> AgentConfigCacheService:
    global _agent_config_cache_service
    if _agent_config_cache_service is None:
        _agent_config_cache_service = AgentConfigCacheService()
    return _agent_config_cache_service


async def initialize_agent_config_cache() -> None:
    service = get_agent_config_cache_service()
    await service.start()
    logger.info("Agent config cache service initialized and started")


async def shutdown_agent_config_cache() -> None:
    global _agent_config_cache_service
    if _agent_config_cache_service:
        await _agent_config_cache_service.stop()
        logger.info("Agent config cache service stopped")


async def get_cached_agent_config(agent_name: str) -> Optional[Dict[str, Any]]:
    """Convenience function: get cached agent config by name."""
    service = get_agent_config_cache_service()
    return await service.get_agent_config(agent_name)
