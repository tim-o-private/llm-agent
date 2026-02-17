"""Tests for tool cache service."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from chatServer.services.tool_cache_service import ToolCacheService, get_tool_cache_service


@pytest.fixture
def mock_db_manager():
    """Mock database manager for testing."""
    mock_manager = MagicMock()
    mock_conn = MagicMock()
    mock_cursor = MagicMock()

    # Mock the async context managers properly
    async def mock_get_connection():
        yield mock_conn

    async def mock_cursor_context():
        yield mock_cursor

    mock_manager.get_connection = mock_get_connection
    mock_conn.cursor = mock_cursor_context

    return mock_manager, mock_cursor


@pytest.mark.asyncio
async def test_tool_cache_service_initialization():
    """Test tool cache service initialization."""
    service = ToolCacheService(ttl_seconds=300, refresh_interval_seconds=60)

    assert service.cache_service.cache_type == "Tool"
    assert service.cache_service.ttl_seconds == 300
    assert service.cache_service.refresh_interval == 60


@pytest.mark.asyncio
async def test_get_tools_for_agent(mock_db_manager):
    """Test getting tools for a specific agent."""
    mock_manager, mock_cursor = mock_db_manager

    # Mock database response
    mock_cursor.fetchall = AsyncMock(return_value=[
        ("agent1", "gmail_search", "Search Gmail", "GmailSearchTool", {"query": "test"}, {"query": {"type": "str"}}, True),
        ("agent1", "gmail_digest", "Gmail Digest", "GmailDigestTool", {"hours": 24}, {"hours": {"type": "int"}}, True)
    ])
    mock_cursor.execute = AsyncMock()

    with patch('chatServer.services.tool_cache_service.get_database_manager', return_value=mock_manager):
        service = ToolCacheService(ttl_seconds=300, refresh_interval_seconds=60)
        await service.start()

        # Get tools for agent
        tools = await service.get_tools_for_agent("agent1")

        assert len(tools) == 2
        assert tools[0]["name"] == "gmail_search"
        assert tools[0]["tool_class"] == "GmailSearchTool"
        assert tools[1]["name"] == "gmail_digest"
        assert tools[1]["tool_class"] == "GmailDigestTool"

        await service.stop()


@pytest.mark.asyncio
async def test_fetch_all_tools(mock_db_manager):
    """Test fetching all tools grouped by agent."""
    mock_manager, mock_cursor = mock_db_manager

    # Mock database response with multiple agents
    mock_cursor.fetchall = AsyncMock(return_value=[
        ("agent1", "gmail_search", "Search Gmail", "GmailSearchTool", {"query": "test"}, {"query": {"type": "str"}}, True),
        ("agent1", "gmail_digest", "Gmail Digest", "GmailDigestTool", {"hours": 24}, {"hours": {"type": "int"}}, True),
        ("agent2", "crud_tool", "CRUD Tool", "CRUDTool", {"table": "tasks"}, {"data": {"type": "dict"}}, True)
    ])
    mock_cursor.execute = AsyncMock()

    with patch('chatServer.services.tool_cache_service.get_database_manager', return_value=mock_manager):
        service = ToolCacheService(ttl_seconds=300, refresh_interval_seconds=60)

        # Test the internal fetch method
        result = await service._fetch_all_tools()

        assert len(result) == 2
        assert "agent1" in result
        assert "agent2" in result
        assert len(result["agent1"]) == 2
        assert len(result["agent2"]) == 1

        # Check tool structure
        agent1_tools = result["agent1"]
        assert agent1_tools[0]["name"] == "gmail_search"
        assert agent1_tools[0]["tool_class"] == "GmailSearchTool"
        assert agent1_tools[1]["name"] == "gmail_digest"
        assert agent1_tools[1]["tool_class"] == "GmailDigestTool"


@pytest.mark.asyncio
async def test_fetch_tools_for_agent(mock_db_manager):
    """Test fetching tools for a specific agent."""
    mock_manager, mock_cursor = mock_db_manager

    # Mock database response for specific agent
    mock_cursor.fetchall = AsyncMock(return_value=[
        ("gmail_search", "Search Gmail", "GmailSearchTool", {"query": "test"}, {"query": {"type": "str"}}, True),
        ("gmail_digest", "Gmail Digest", "GmailDigestTool", {"hours": 24}, {"hours": {"type": "int"}}, True)
    ])
    mock_cursor.execute = AsyncMock()

    with patch('chatServer.services.tool_cache_service.get_database_manager', return_value=mock_manager):
        service = ToolCacheService(ttl_seconds=300, refresh_interval_seconds=60)

        # Test the internal fetch method
        result = await service._fetch_tools_for_agent("agent1")

        assert len(result) == 2
        assert result[0]["name"] == "gmail_search"
        assert result[0]["tool_class"] == "GmailSearchTool"
        assert result[1]["name"] == "gmail_digest"
        assert result[1]["tool_class"] == "GmailDigestTool"


@pytest.mark.asyncio
async def test_cache_invalidation():
    """Test cache invalidation."""
    with patch('chatServer.services.tool_cache_service.get_database_manager'):
        service = ToolCacheService(ttl_seconds=300, refresh_interval_seconds=60)

        # Mock some cache data
        service.cache_service._cache = {
            "agent1": [{"name": "tool1"}],
            "agent2": [{"name": "tool2"}]
        }

        # Test specific invalidation
        await service.invalidate_cache("agent1")
        assert "agent1" not in service.cache_service._cache
        assert "agent2" in service.cache_service._cache

        # Test full invalidation
        await service.invalidate_cache()
        assert len(service.cache_service._cache) == 0


@pytest.mark.asyncio
async def test_cache_warming():
    """Test cache warming."""
    mock_manager = MagicMock()
    mock_conn = MagicMock()
    mock_cursor = MagicMock()

    # Setup async context managers properly
    async def mock_get_connection():
        yield mock_conn

    async def mock_cursor_context():
        yield mock_cursor

    mock_manager.get_connection = mock_get_connection
    mock_conn.cursor = mock_cursor_context

    # Mock database responses for different agents
    call_count = 0
    async def mock_fetchall():
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return [("tool1", "Tool 1", "TestTool", {}, {}, True)]
        elif call_count == 2:
            return [("tool2", "Tool 2", "TestTool", {}, {}, True)]
        return []

    mock_cursor.fetchall = mock_fetchall
    mock_cursor.execute = AsyncMock()

    with patch('chatServer.services.tool_cache_service.get_database_manager', return_value=mock_manager):
        service = ToolCacheService(ttl_seconds=300, refresh_interval_seconds=60)

        # Warm cache for specific agents
        await service.warm_cache(["agent1", "agent2"])

        # Verify cache was warmed
        assert "agent1" in service.cache_service._cache
        assert "agent2" in service.cache_service._cache


@pytest.mark.asyncio
async def test_cache_stats():
    """Test cache statistics."""
    with patch('chatServer.services.tool_cache_service.get_database_manager'):
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


@pytest.mark.asyncio
async def test_database_error_handling(mock_db_manager):
    """Test database error handling."""
    mock_manager, mock_cursor = mock_db_manager

    # Mock database error
    mock_cursor.execute = AsyncMock(side_effect=Exception("Database connection failed"))

    with patch('chatServer.services.tool_cache_service.get_database_manager', return_value=mock_manager):
        service = ToolCacheService(ttl_seconds=300, refresh_interval_seconds=60)

        # Should handle error gracefully
        result = await service._fetch_all_tools()
        assert result == {}

        result = await service._fetch_tools_for_agent("agent1")
        assert result == []


def test_get_tool_cache_service_singleton():
    """Test that get_tool_cache_service returns the same instance."""
    service1 = get_tool_cache_service()
    service2 = get_tool_cache_service()

    assert service1 is service2
    assert isinstance(service1, ToolCacheService)
