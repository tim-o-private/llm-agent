"""Background task service for managing scheduled tasks."""

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Tuple, Any

try:
    from ..config.constants import SESSION_INSTANCE_TTL_SECONDS, SCHEDULED_TASK_INTERVAL_SECONDS
    from ..database.connection import get_database_manager
except ImportError:
    from chatServer.config.constants import SESSION_INSTANCE_TTL_SECONDS, SCHEDULED_TASK_INTERVAL_SECONDS
    from chatServer.database.connection import get_database_manager

logger = logging.getLogger(__name__)


class BackgroundTaskService:
    """Service for managing background tasks like session cleanup and cache eviction."""
    
    def __init__(self):
        self.deactivate_task: Optional[asyncio.Task] = None
        self.evict_task: Optional[asyncio.Task] = None
        self._agent_executor_cache: Optional[Dict[Tuple[str, str], Any]] = None
    
    def set_agent_executor_cache(self, cache: Dict[Tuple[str, str], Any]) -> None:
        """Set the agent executor cache reference for eviction tasks."""
        self._agent_executor_cache = cache
    
    async def deactivate_stale_chat_session_instances(self) -> None:
        """Periodically deactivates stale chat session instances."""
        while True:
            await asyncio.sleep(SCHEDULED_TASK_INTERVAL_SECONDS)
            logger.debug("Running task: deactivate_stale_chat_session_instances")
            
            db_manager = get_database_manager()
            if db_manager.pool is None:
                logger.warning("db_pool not available, skipping deactivation task cycle.")
                continue
            
            try:
                async with db_manager.pool.connection() as conn:
                    async with conn.cursor() as cur:
                        threshold_time = datetime.now(timezone.utc) - timedelta(seconds=SESSION_INSTANCE_TTL_SECONDS)
                        await cur.execute(
                            """UPDATE chat_sessions 
                               SET is_active = false, updated_at = %s 
                               WHERE is_active = true AND updated_at < %s""",
                            (datetime.now(timezone.utc), threshold_time)
                        )
                        if cur.rowcount > 0:
                            logger.info(f"Deactivated {cur.rowcount} stale chat session instances.")
            except Exception as e:
                logger.error(f"Error in deactivate_stale_chat_session_instances: {e}", exc_info=True)
    
    async def evict_inactive_executors(self) -> None:
        """Periodically evicts agent executors if no active session instances exist for them."""
        while True:
            await asyncio.sleep(SCHEDULED_TASK_INTERVAL_SECONDS + 30)  # Stagger slightly from the other task
            logger.debug("Running task: evict_inactive_executors")
            
            db_manager = get_database_manager()
            if db_manager.pool is None or self._agent_executor_cache is None:
                logger.warning("db_pool or agent_executor_cache not available, skipping eviction task cycle.")
                continue

            keys_to_evict = []
            # Create a copy of keys to iterate over as cache might be modified
            current_cache_keys = list(self._agent_executor_cache.keys())

            for user_id, agent_name in current_cache_keys:
                try:
                    async with db_manager.pool.connection() as conn:
                        async with conn.cursor() as cur:
                            await cur.execute(
                                """SELECT 1 FROM chat_sessions 
                                   WHERE user_id = %s AND agent_name = %s AND is_active = true LIMIT 1""",
                                (user_id, agent_name)
                            )
                            active_session_exists = await cur.fetchone()
                            if not active_session_exists:
                                keys_to_evict.append((user_id, agent_name))
                except Exception as e:
                    logger.error(f"Error checking active sessions for ({user_id}, {agent_name}): {e}", exc_info=True)
            
            for key in keys_to_evict:
                if key in self._agent_executor_cache:
                    del self._agent_executor_cache[key]
                    logger.info(f"Evicted agent executor for {key} due to no active sessions.")
    
    def start_background_tasks(self) -> None:
        """Start all background tasks."""
        self.deactivate_task = asyncio.create_task(self.deactivate_stale_chat_session_instances())
        self.evict_task = asyncio.create_task(self.evict_inactive_executors())
        logger.info("Background tasks for session and cache cleanup started.")
    
    async def stop_background_tasks(self) -> None:
        """Stop all background tasks gracefully."""
        if self.deactivate_task:
            self.deactivate_task.cancel()
            logger.info("Deactivate stale sessions task cancelling...")
            try:
                await self.deactivate_task
            except asyncio.CancelledError:
                logger.info("Deactivate stale sessions task successfully cancelled.")
        
        if self.evict_task:
            self.evict_task.cancel()
            logger.info("Evict inactive executors task cancelling...")
            try:
                await self.evict_task
            except asyncio.CancelledError:
                logger.info("Evict inactive executors task successfully cancelled.")


# Global instance for use in main.py
_background_task_service: Optional[BackgroundTaskService] = None


def get_background_task_service() -> BackgroundTaskService:
    """Get the global background task service instance."""
    global _background_task_service
    if _background_task_service is None:
        _background_task_service = BackgroundTaskService()
    return _background_task_service 