"""Tests for TTL cache service."""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock
from typing import Dict, List

from chatServer.services.ttl_cache_service import TTLCacheService


@pytest.fixture
def mock_fetch_all():
    """Mock fetch_all_callback that returns test data."""
    async def fetch_all() -> Dict[str, List[Dict]]:
        return {
            "agent1": [{"name": "tool1", "type": "test"}],
            "agent2": [{"name": "tool2", "type": "test"}, {"name": "tool3", "type": "test"}]
        }
    return fetch_all


@pytest.fixture
def mock_fetch_single():
    """Mock fetch_single_callback that returns test data for a specific key."""
    async def fetch_single(key: str) -> List[Dict]:
        data = {
            "agent1": [{"name": "tool1", "type": "test"}],
            "agent2": [{"name": "tool2", "type": "test"}, {"name": "tool3", "type": "test"}]
        }
        return data.get(key, [])
    return fetch_single


@pytest.mark.asyncio
async def test_cache_initialization():
    """Test cache service initialization."""
    cache = TTLCacheService[Dict](
        cache_type="Test",
        ttl_seconds=300,
        refresh_interval_seconds=60
    )
    
    assert cache.cache_type == "Test"
    assert cache.ttl_seconds == 300
    assert cache.refresh_interval == 60
    assert not cache._is_running


@pytest.mark.asyncio
async def test_cache_start_and_stop():
    """Test cache service start and stop."""
    cache = TTLCacheService[Dict](
        cache_type="Test",
        ttl_seconds=300,
        refresh_interval_seconds=60,
        fetch_all_callback=AsyncMock(return_value={})
    )
    
    # Start cache
    await cache.start()
    assert cache._is_running
    
    # Stop cache
    await cache.stop()
    assert not cache._is_running


@pytest.mark.asyncio
async def test_cache_population(mock_fetch_all):
    """Test cache population on startup."""
    cache = TTLCacheService[Dict](
        cache_type="Test",
        ttl_seconds=300,
        refresh_interval_seconds=60,
        fetch_all_callback=mock_fetch_all
    )
    
    await cache.start()
    
    # Check cache was populated
    assert len(cache._cache) == 2
    assert "agent1" in cache._cache
    assert "agent2" in cache._cache
    assert len(cache._cache["agent1"]) == 1
    assert len(cache._cache["agent2"]) == 2
    
    await cache.stop()


@pytest.mark.asyncio
async def test_cache_get_hit(mock_fetch_all):
    """Test cache hit scenario."""
    cache = TTLCacheService[Dict](
        cache_type="Test",
        ttl_seconds=300,
        refresh_interval_seconds=60,
        fetch_all_callback=mock_fetch_all
    )
    
    await cache.start()
    
    # Get data from cache (should be a hit)
    result = await cache.get("agent1")
    assert len(result) == 1
    assert result[0]["name"] == "tool1"
    
    await cache.stop()


@pytest.mark.asyncio
async def test_cache_get_miss_with_single_fetch(mock_fetch_all, mock_fetch_single):
    """Test cache miss with single fetch callback."""
    cache = TTLCacheService[Dict](
        cache_type="Test",
        ttl_seconds=300,
        refresh_interval_seconds=60,
        fetch_all_callback=mock_fetch_all,
        fetch_single_callback=mock_fetch_single
    )
    
    await cache.start()
    
    # Clear cache to simulate miss
    await cache.invalidate()
    
    # Get data (should trigger single fetch)
    result = await cache.get("agent1")
    assert len(result) == 1
    assert result[0]["name"] == "tool1"
    
    await cache.stop()


@pytest.mark.asyncio
async def test_cache_get_miss_without_single_fetch(mock_fetch_all):
    """Test cache miss without single fetch callback."""
    cache = TTLCacheService[Dict](
        cache_type="Test",
        ttl_seconds=300,
        refresh_interval_seconds=60,
        fetch_all_callback=mock_fetch_all
    )
    
    await cache.start()
    
    # Clear cache to simulate miss
    await cache.invalidate()
    
    # Get data for non-existent key (should return empty list)
    result = await cache.get("nonexistent")
    assert result == []
    
    await cache.stop()


@pytest.mark.asyncio
async def test_cache_invalidation(mock_fetch_all):
    """Test cache invalidation."""
    cache = TTLCacheService[Dict](
        cache_type="Test",
        ttl_seconds=300,
        refresh_interval_seconds=60,
        fetch_all_callback=mock_fetch_all
    )
    
    await cache.start()
    
    # Verify cache has data
    assert len(cache._cache) == 2
    
    # Invalidate specific key
    await cache.invalidate("agent1")
    assert "agent1" not in cache._cache
    assert "agent2" in cache._cache
    
    # Invalidate all
    await cache.invalidate()
    assert len(cache._cache) == 0
    
    await cache.stop()


@pytest.mark.asyncio
async def test_cache_warm_cache(mock_fetch_single):
    """Test cache warming."""
    cache = TTLCacheService[Dict](
        cache_type="Test",
        ttl_seconds=300,
        refresh_interval_seconds=60,
        fetch_single_callback=mock_fetch_single
    )
    
    await cache.start()
    
    # Warm cache for specific keys
    await cache.warm_cache(["agent1", "agent2"])
    
    # Verify cache was warmed
    assert len(cache._cache) == 2
    assert "agent1" in cache._cache
    assert "agent2" in cache._cache
    
    await cache.stop()


@pytest.mark.asyncio
async def test_cache_stats(mock_fetch_all):
    """Test cache statistics."""
    cache = TTLCacheService[Dict](
        cache_type="Test",
        ttl_seconds=300,
        refresh_interval_seconds=60,
        fetch_all_callback=mock_fetch_all
    )
    
    await cache.start()
    
    stats = cache.get_cache_stats()
    assert stats["cache_type"] == "Test"
    assert stats["total_entries"] == 2
    assert stats["valid_entries"] == 2
    assert stats["expired_entries"] == 0
    assert stats["ttl_seconds"] == 300
    assert stats["is_running"] is True
    
    await cache.stop()


@pytest.mark.asyncio
async def test_cache_ttl_expiration():
    """Test TTL expiration."""
    cache = TTLCacheService[Dict](
        cache_type="Test",
        ttl_seconds=0.1,  # Very short TTL for testing
        refresh_interval_seconds=60
    )
    
    # Manually add data to cache
    await cache._update_cache_entry("test_key", [{"name": "test"}])
    
    # Verify data is there
    assert cache._is_cache_valid("test_key")
    
    # Wait for TTL to expire
    await asyncio.sleep(0.2)
    
    # Verify data is expired
    assert not cache._is_cache_valid("test_key")


@pytest.mark.asyncio
async def test_cache_error_handling():
    """Test cache error handling."""
    # Mock that raises exception
    async def failing_fetch_all():
        raise Exception("Database error")
    
    cache = TTLCacheService[Dict](
        cache_type="Test",
        ttl_seconds=300,
        refresh_interval_seconds=60,
        fetch_all_callback=failing_fetch_all
    )
    
    # Start should not fail even if fetch fails
    await cache.start()
    
    # Cache should be empty due to failed fetch
    assert len(cache._cache) == 0
    
    await cache.stop()


@pytest.mark.asyncio
async def test_cache_without_callbacks():
    """Test cache behavior without callbacks."""
    cache = TTLCacheService[Dict](
        cache_type="Test",
        ttl_seconds=300,
        refresh_interval_seconds=60
    )
    
    await cache.start()
    
    # Get should return empty list when no callbacks are configured
    result = await cache.get("any_key")
    assert result == []
    
    await cache.stop() 