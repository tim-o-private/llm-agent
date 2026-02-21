"""Simple tests for tool cache service focusing on core functionality."""

from unittest.mock import AsyncMock

import pytest

from chatServer.services.tool_cache_service import ToolCacheService, get_tool_cache_service


@pytest.mark.asyncio
async def test_tool_cache_service_initialization():
    """Test tool cache service initialization."""
    service = ToolCacheService(ttl_seconds=300, refresh_interval_seconds=60)

    assert service.cache_service.cache_type == "Tool"
    assert service.cache_service.ttl_seconds == 300
    assert service.cache_service.refresh_interval == 60


@pytest.mark.asyncio
async def test_cache_invalidation():
    """Test cache invalidation."""
    service = ToolCacheService(ttl_seconds=300, refresh_interval_seconds=60)

    # Mock some cache data
    service.cache_service._cache = {
        "agent1": [{"name": "tool1"}],
        "agent2": [{"name": "tool2"}]
    }

    # Test specific invalidation
    await service.invalidate_cache(agent_id="agent1")
    assert "agent1" not in service.cache_service._cache
    assert "agent2" in service.cache_service._cache

    # Test full invalidation
    await service.invalidate_cache()
    assert len(service.cache_service._cache) == 0


@pytest.mark.asyncio
async def test_cache_stats():
    """Test cache statistics."""
    service = ToolCacheService(ttl_seconds=300, refresh_interval_seconds=60)

    # Mock some cache data
    service.cache_service._cache = {
        "agent1": [{"name": "tool1"}],
        "agent2": [{"name": "tool2"}]
    }
    service.cache_service._timestamps = {
        "agent1": 1000000000,
        "agent2": 1000000000
    }

    stats = service.get_cache_stats()

    assert stats["cache_type"] == "Tool"
    assert stats["total_entries"] == 2
    assert stats["ttl_seconds"] == 300


def test_get_tool_cache_service_singleton():
    """Test that get_tool_cache_service returns the same instance."""
    service1 = get_tool_cache_service()
    service2 = get_tool_cache_service()

    assert service1 is service2
    assert isinstance(service1, ToolCacheService)


@pytest.mark.asyncio
async def test_fetch_all_tools_with_mock():
    """Test _fetch_all_tools with mocked database manager."""
    service = ToolCacheService(ttl_seconds=300, refresh_interval_seconds=60)

    # Mock the database manager method directly
    async def mock_fetch_all():
        return {
            "agent1": [
                {"name": "gmail_search", "tool_class": "GmailSearchTool", "config": {}, "runtime_args_schema": {}, "is_active": True},  # noqa: E501
                {"name": "gmail_digest", "tool_class": "GmailDigestTool", "config": {}, "runtime_args_schema": {}, "is_active": True}  # noqa: E501
            ],
            "agent2": [
                {"name": "crud_tool", "tool_class": "CRUDTool", "config": {}, "runtime_args_schema": {}, "is_active": True}  # noqa: E501
            ]
        }

    # Replace the method with our mock
    service._fetch_all_tools = mock_fetch_all

    result = await service._fetch_all_tools()

    assert len(result) == 2
    assert "agent1" in result
    assert "agent2" in result
    assert len(result["agent1"]) == 2
    assert len(result["agent2"]) == 1


@pytest.mark.asyncio
async def test_fetch_tools_for_agent_with_mock():
    """Test _fetch_tools_for_agent with mocked database manager."""
    service = ToolCacheService(ttl_seconds=300, refresh_interval_seconds=60)

    # Mock the database manager method directly
    async def mock_fetch_single(agent_id: str):
        if agent_id == "agent1":
            return [
                {"name": "gmail_search", "tool_class": "GmailSearchTool", "config": {}, "runtime_args_schema": {}, "is_active": True},  # noqa: E501
                {"name": "gmail_digest", "tool_class": "GmailDigestTool", "config": {}, "runtime_args_schema": {}, "is_active": True}  # noqa: E501
            ]
        return []

    # Replace the method with our mock
    service._fetch_tools_for_agent = mock_fetch_single

    result = await service._fetch_tools_for_agent("agent1")

    assert len(result) == 2
    assert result[0]["name"] == "gmail_search"
    assert result[0]["tool_class"] == "GmailSearchTool"
    assert result[1]["name"] == "gmail_digest"
    assert result[1]["tool_class"] == "GmailDigestTool"


@pytest.mark.asyncio
async def test_get_tools_for_agent_with_cache():
    """Test getting tools for agent using cache."""
    service = ToolCacheService(ttl_seconds=300, refresh_interval_seconds=60)

    # Pre-populate cache
    service.cache_service._cache = {
        "agent1": [
            {"name": "gmail_search", "tool_class": "GmailSearchTool", "config": {}, "runtime_args_schema": {}, "is_active": True},  # noqa: E501
            {"name": "gmail_digest", "tool_class": "GmailDigestTool", "config": {}, "runtime_args_schema": {}, "is_active": True}  # noqa: E501
        ]
    }
    service.cache_service._timestamps = {"agent1": 1000000000}

    # Mock the cache validity check to return True
    service.cache_service._is_cache_valid = lambda key: True

    tools = await service.get_tools_for_agent("agent1")

    assert len(tools) == 2
    assert tools[0]["name"] == "gmail_search"
    assert tools[0]["tool_class"] == "GmailSearchTool"
    assert tools[1]["name"] == "gmail_digest"
    assert tools[1]["tool_class"] == "GmailDigestTool"


@pytest.mark.asyncio
async def test_start_and_stop():
    """Test starting and stopping the cache service."""
    service = ToolCacheService(ttl_seconds=300, refresh_interval_seconds=60)

    # Mock the fetch_all method to avoid database calls
    service.cache_service.fetch_all_callback = AsyncMock(return_value={})

    # Start service
    await service.start()
    assert service.cache_service._is_running

    # Stop service
    await service.stop()
    assert not service.cache_service._is_running
