"""Generic TTL cache service with periodic refresh and auto-creation capabilities."""

import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, Dict, Generic, List, Optional, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar('T')


class TTLCacheService(Generic[T]):
    """Generic TTL cache service with periodic refresh and fallback creation."""

    def __init__(
        self,
        cache_type: str,
        ttl_seconds: int = 300,  # 5 minutes default
        refresh_interval_seconds: int = 60,  # Check for updates every minute
        fetch_all_callback: Optional[Callable[[], Awaitable[Dict[str, List[T]]]]] = None,
        fetch_single_callback: Optional[Callable[[str], Awaitable[List[T]]]] = None
    ):
        """
        Initialize TTL cache service.

        Args:
            cache_type: Type identifier for logging (e.g., "Tool", "Agent", "Config")
            ttl_seconds: Time-to-live for cache entries in seconds
            refresh_interval_seconds: How often to check for updates
            fetch_all_callback: Async function to fetch all data as {key: [items]}
            fetch_single_callback: Async function to fetch data for single key
        """
        self.cache_type = cache_type
        self.ttl_seconds = ttl_seconds
        self.refresh_interval = refresh_interval_seconds
        self.fetch_all_callback = fetch_all_callback
        self.fetch_single_callback = fetch_single_callback

        # Cache storage
        self._cache: Dict[str, List[T]] = {}
        self._timestamps: Dict[str, float] = {}
        self._last_refresh_check: float = 0

        # Synchronization
        self._lock = asyncio.Lock()
        self._refresh_task: Optional[asyncio.Task] = None
        self._is_running = False

        logger.info(f"Initialized {cache_type} TTL cache (TTL: {ttl_seconds}s, Refresh: {refresh_interval_seconds}s)")

    async def start(self) -> None:
        """Start the cache service with periodic refresh."""
        if self._is_running:
            logger.debug(f"{self.cache_type} cache already running")
            return

        self._is_running = True
        logger.info(f"Starting {self.cache_type} cache service")

        # Initial cache population
        await self._populate_cache()

        # Start periodic refresh task
        self._refresh_task = asyncio.create_task(self._periodic_refresh())
        logger.info(f"{self.cache_type} cache service started successfully")

    async def stop(self) -> None:
        """Stop the cache service."""
        if not self._is_running:
            return

        self._is_running = False
        logger.info(f"Stopping {self.cache_type} cache service")

        if self._refresh_task:
            self._refresh_task.cancel()
            try:
                await self._refresh_task
            except asyncio.CancelledError:
                pass

        logger.info(f"{self.cache_type} cache service stopped")

    async def get(self, key: str) -> List[T]:
        """
        Get items for key with cache-first approach.

        Args:
            key: Cache key to retrieve

        Returns:
            List of cached items, empty list if not found
        """
        # Check if cache is valid for this key
        if self._is_cache_valid(key):
            logger.debug(f"{self.cache_type} cache hit for key: {key}")
            return self._cache[key].copy()  # Return copy to prevent external modification

        # Cache miss - try to fetch single item if callback available
        if self.fetch_single_callback:
            logger.debug(f"{self.cache_type} cache miss for key: {key}, fetching from source")
            try:
                items = await self.fetch_single_callback(key)
                await self._update_cache_entry(key, items)
                return items.copy()
            except Exception as e:
                logger.error(f"Failed to fetch {self.cache_type} data for key {key}: {e}")
                return []

        # No single fetch callback or it failed - check if cache is completely empty
        if not self._cache:
            logger.warning(f"{self.cache_type} cache is empty, attempting to populate")
            await self._populate_cache()

            # Try again after population
            if self._is_cache_valid(key):
                return self._cache[key].copy()

        logger.debug(f"{self.cache_type} cache miss for key: {key}, returning empty list")
        return []

    async def invalidate(self, key: Optional[str] = None) -> None:
        """
        Invalidate cache entries.

        Args:
            key: Specific key to invalidate, or None to invalidate all
        """
        async with self._lock:
            if key is None:
                logger.info(f"Invalidating entire {self.cache_type} cache")
                self._cache.clear()
                self._timestamps.clear()
            else:
                logger.info(f"Invalidating {self.cache_type} cache for key: {key}")
                self._cache.pop(key, None)
                self._timestamps.pop(key, None)

    async def warm_cache(self, keys: List[str]) -> None:
        """
        Pre-warm cache for specific keys.

        Args:
            keys: List of keys to pre-warm
        """
        if not self.fetch_single_callback:
            logger.warning(f"Cannot warm {self.cache_type} cache: no single fetch callback configured")
            return

        logger.info(f"Warming {self.cache_type} cache for {len(keys)} keys")

        for key in keys:
            if not self._is_cache_valid(key):
                try:
                    items = await self.fetch_single_callback(key)
                    await self._update_cache_entry(key, items)
                    logger.debug(f"Warmed {self.cache_type} cache for key: {key}")
                except Exception as e:
                    logger.error(f"Failed to warm {self.cache_type} cache for key {key}: {e}")

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        now = time.time()
        valid_entries = sum(1 for key in self._cache.keys() if self._is_cache_valid(key))

        return {
            "cache_type": self.cache_type,
            "total_entries": len(self._cache),
            "valid_entries": valid_entries,
            "expired_entries": len(self._cache) - valid_entries,
            "ttl_seconds": self.ttl_seconds,
            "refresh_interval_seconds": self.refresh_interval,
            "last_refresh_check": datetime.fromtimestamp(self._last_refresh_check, tz=timezone.utc).isoformat() if self._last_refresh_check else None,
            "is_running": self._is_running
        }

    def _is_cache_valid(self, key: str) -> bool:
        """Check if cache entry is valid (exists and not expired)."""
        if key not in self._cache:
            return False

        timestamp = self._timestamps.get(key, 0)
        return (time.time() - timestamp) < self.ttl_seconds

    async def _update_cache_entry(self, key: str, items: List[T]) -> None:
        """Update cache entry with new data."""
        async with self._lock:
            self._cache[key] = items
            self._timestamps[key] = time.time()
            logger.debug(f"Updated {self.cache_type} cache for key: {key} ({len(items)} items)")

    async def _populate_cache(self) -> None:
        """Populate cache using fetch_all_callback."""
        if not self.fetch_all_callback:
            logger.warning(f"Cannot populate {self.cache_type} cache: no fetch_all callback configured")
            return

        try:
            logger.info(f"Populating {self.cache_type} cache from source")
            all_data = await self.fetch_all_callback()

            async with self._lock:
                current_time = time.time()
                for key, items in all_data.items():
                    self._cache[key] = items
                    self._timestamps[key] = current_time

                logger.info(f"Populated {self.cache_type} cache with {len(all_data)} entries")

        except Exception as e:
            logger.error(f"Failed to populate {self.cache_type} cache: {e}", exc_info=True)

    async def _periodic_refresh(self) -> None:
        """Periodic task to check for cache updates."""
        logger.info(f"Started periodic refresh for {self.cache_type} cache")

        while self._is_running:
            try:
                await asyncio.sleep(self.refresh_interval)

                if not self._is_running:
                    break

                # Check if it's time to refresh
                now = time.time()
                if (now - self._last_refresh_check) >= self.refresh_interval:
                    await self._check_for_updates()
                    self._last_refresh_check = now

            except asyncio.CancelledError:
                logger.info(f"Periodic refresh cancelled for {self.cache_type} cache")
                break
            except Exception as e:
                logger.error(f"Error in periodic refresh for {self.cache_type} cache: {e}", exc_info=True)
                # Continue running despite errors
                await asyncio.sleep(5)  # Brief pause before retrying

    async def _check_for_updates(self) -> None:
        """Check for updates and refresh cache if needed."""
        if not self.fetch_all_callback:
            return

        try:
            logger.debug(f"Checking for {self.cache_type} cache updates")

            # Fetch fresh data
            fresh_data = await self.fetch_all_callback()

            # Compare with current cache and update if different
            updates_made = False
            async with self._lock:
                current_time = time.time()

                for key, fresh_items in fresh_data.items():
                    # Update if key doesn't exist or data has changed
                    if key not in self._cache or self._cache[key] != fresh_items:
                        self._cache[key] = fresh_items
                        self._timestamps[key] = current_time
                        updates_made = True
                        logger.debug(f"Updated {self.cache_type} cache for key: {key}")

                # Remove keys that no longer exist in source
                keys_to_remove = set(self._cache.keys()) - set(fresh_data.keys())
                for key in keys_to_remove:
                    del self._cache[key]
                    del self._timestamps[key]
                    updates_made = True
                    logger.debug(f"Removed {self.cache_type} cache for key: {key}")

            if updates_made:
                logger.info(f"Updated {self.cache_type} cache with fresh data")
            else:
                logger.debug(f"No updates needed for {self.cache_type} cache")

        except Exception as e:
            logger.error(f"Failed to check for {self.cache_type} cache updates: {e}", exc_info=True)


# Global cache instances
_cache_instances: Dict[str, TTLCacheService] = {}


def get_ttl_cache_service(cache_type: str) -> Optional[TTLCacheService]:
    """Get a TTL cache service instance by type."""
    return _cache_instances.get(cache_type)


def register_ttl_cache_service(cache_type: str, service: TTLCacheService) -> None:
    """Register a TTL cache service instance."""
    _cache_instances[cache_type] = service
    logger.info(f"Registered TTL cache service for type: {cache_type}")


async def start_all_cache_services() -> None:
    """Start all registered cache services."""
    logger.info(f"Starting {len(_cache_instances)} TTL cache services")
    for cache_type, service in _cache_instances.items():
        try:
            await service.start()
        except Exception as e:
            logger.error(f"Failed to start {cache_type} cache service: {e}")


async def stop_all_cache_services() -> None:
    """Stop all registered cache services."""
    logger.info(f"Stopping {len(_cache_instances)} TTL cache services")
    for cache_type, service in _cache_instances.items():
        try:
            await service.stop()
        except Exception as e:
            logger.error(f"Failed to stop {cache_type} cache service: {e}")
