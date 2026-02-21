"""Tests for agent config cache service."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from chatServer.services.agent_config_cache_service import (
    AgentConfigCacheService,
)


@pytest.fixture
def mock_db_manager():
    """Mock database manager for testing."""
    mock_manager = MagicMock()
    mock_conn = MagicMock()
    mock_cursor = MagicMock()

    async def mock_get_connection():
        yield mock_conn

    mock_cursor_cm = MagicMock()
    mock_cursor_cm.__aenter__ = AsyncMock(return_value=mock_cursor)
    mock_cursor_cm.__aexit__ = AsyncMock(return_value=None)

    mock_manager.get_connection = mock_get_connection
    mock_conn.cursor.return_value = mock_cursor_cm

    return mock_manager, mock_cursor


@pytest.mark.asyncio
async def test_agent_config_cache_initialization():
    """Test cache service initialization."""
    service = AgentConfigCacheService(ttl_seconds=600, refresh_interval_seconds=120)
    assert service.cache_service.cache_type == "AgentConfig"
    assert service.cache_service.ttl_seconds == 600
    assert service.cache_service.refresh_interval == 120


@pytest.mark.asyncio
async def test_fetch_all_agent_configs(mock_db_manager):
    """Test fetching all agent configs grouped by name."""
    mock_manager, mock_cursor = mock_db_manager

    mock_cursor.description = [
        ("id",), ("agent_name",), ("soul",), ("identity",),
        ("llm_config",), ("created_at",), ("updated_at",),
    ]
    mock_cursor.fetchall = AsyncMock(return_value=[
        ("uuid-1", "assistant", "Be helpful", None, {"model": "claude"}, None, None),
        ("uuid-2", "coach", "Be motivating", None, {"model": "claude"}, None, None),
    ])
    mock_cursor.execute = AsyncMock()

    with patch('chatServer.services.agent_config_cache_service.get_database_manager', return_value=mock_manager):
        service = AgentConfigCacheService(ttl_seconds=600, refresh_interval_seconds=120)
        result = await service._fetch_all_agent_configs()

        assert len(result) == 2
        assert "assistant" in result
        assert "coach" in result
        assert result["assistant"][0]["id"] == "uuid-1"
        assert result["assistant"][0]["soul"] == "Be helpful"
        assert result["coach"][0]["id"] == "uuid-2"


@pytest.mark.asyncio
async def test_fetch_single_agent_config(mock_db_manager):
    """Test fetching a single agent config."""
    mock_manager, mock_cursor = mock_db_manager

    mock_cursor.description = [
        ("id",), ("agent_name",), ("soul",), ("identity",),
        ("llm_config",), ("created_at",), ("updated_at",),
    ]
    mock_cursor.fetchall = AsyncMock(return_value=[
        ("uuid-1", "assistant", "Be helpful", None, {"model": "claude"}, None, None),
    ])
    mock_cursor.execute = AsyncMock()

    with patch('chatServer.services.agent_config_cache_service.get_database_manager', return_value=mock_manager):
        service = AgentConfigCacheService(ttl_seconds=600, refresh_interval_seconds=120)
        result = await service._fetch_agent_config("assistant")

        assert len(result) == 1
        assert result[0]["agent_name"] == "assistant"
        assert result[0]["id"] == "uuid-1"


@pytest.mark.asyncio
async def test_get_agent_config_from_cache(mock_db_manager):
    """Test getting agent config from warmed cache."""
    mock_manager, mock_cursor = mock_db_manager

    mock_cursor.description = [
        ("id",), ("agent_name",), ("soul",), ("identity",),
        ("llm_config",), ("created_at",), ("updated_at",),
    ]
    mock_cursor.fetchall = AsyncMock(return_value=[
        ("uuid-1", "assistant", "Be helpful", None, {"model": "claude"}, None, None),
    ])
    mock_cursor.execute = AsyncMock()

    with patch('chatServer.services.agent_config_cache_service.get_database_manager', return_value=mock_manager):
        service = AgentConfigCacheService(ttl_seconds=600, refresh_interval_seconds=120)
        await service.start()

        config = await service.get_agent_config("assistant")
        assert config is not None
        assert config["agent_name"] == "assistant"
        assert config["id"] == "uuid-1"

        # Non-existent agent: reset mock to return empty before the call
        mock_cursor.fetchall = AsyncMock(return_value=[])
        config = await service.get_agent_config("nonexistent")
        assert config is None

        await service.stop()


@pytest.mark.asyncio
async def test_cache_invalidation():
    """Test cache invalidation."""
    with patch('chatServer.services.agent_config_cache_service.get_database_manager'):
        service = AgentConfigCacheService(ttl_seconds=600, refresh_interval_seconds=120)

        service.cache_service._cache = {
            "assistant": [{"id": "uuid-1", "agent_name": "assistant"}],
            "coach": [{"id": "uuid-2", "agent_name": "coach"}],
        }

        await service.invalidate_cache("assistant")
        assert "assistant" not in service.cache_service._cache
        assert "coach" in service.cache_service._cache

        await service.invalidate_cache()
        assert len(service.cache_service._cache) == 0


@pytest.mark.asyncio
async def test_cache_stats():
    """Test cache statistics."""
    with patch('chatServer.services.agent_config_cache_service.get_database_manager'):
        service = AgentConfigCacheService(ttl_seconds=600, refresh_interval_seconds=120)
        stats = service.get_cache_stats()
        assert stats["cache_type"] == "AgentConfig"
        assert stats["ttl_seconds"] == 600


@pytest.mark.asyncio
async def test_database_error_handling(mock_db_manager):
    """Test database error handling returns fallback."""
    mock_manager, mock_cursor = mock_db_manager
    mock_cursor.execute = AsyncMock(side_effect=Exception("DB connection failed"))

    with patch('chatServer.services.agent_config_cache_service.get_database_manager', return_value=mock_manager):
        service = AgentConfigCacheService(ttl_seconds=600, refresh_interval_seconds=120)

        result = await service._fetch_all_agent_configs()
        assert result == {}

        result = await service._fetch_agent_config("assistant")
        assert result == []
