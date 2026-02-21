"""Tests for user instructions cache service."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from chatServer.services.user_instructions_cache_service import (
    UserInstructionsCacheService,
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
async def test_user_instructions_cache_initialization():
    """Test cache service initialization."""
    service = UserInstructionsCacheService(ttl_seconds=120, refresh_interval_seconds=60)
    assert service.cache_service.cache_type == "UserInstructions"
    assert service.cache_service.ttl_seconds == 120
    assert service.cache_service.refresh_interval == 60


@pytest.mark.asyncio
async def test_cache_key_format():
    """Test cache key construction."""
    assert UserInstructionsCacheService._make_cache_key("user-1", "assistant") == "user-1:assistant"
    assert UserInstructionsCacheService._make_cache_key("abc", "coach") == "abc:coach"


@pytest.mark.asyncio
async def test_fetch_user_instructions_found(mock_db_manager):
    """Test fetching user instructions when they exist."""
    mock_manager, mock_cursor = mock_db_manager
    mock_cursor.fetchone = AsyncMock(return_value=("Always be concise.",))
    mock_cursor.execute = AsyncMock()

    with patch('chatServer.services.user_instructions_cache_service.get_database_manager', return_value=mock_manager):
        service = UserInstructionsCacheService(ttl_seconds=120, refresh_interval_seconds=60)
        result = await service._fetch_user_instructions("user-1:assistant")

        assert result == ["Always be concise."]
        mock_cursor.execute.assert_called_once()


@pytest.mark.asyncio
async def test_fetch_user_instructions_not_found(mock_db_manager):
    """Test fetching user instructions when none exist."""
    mock_manager, mock_cursor = mock_db_manager
    mock_cursor.fetchone = AsyncMock(return_value=None)
    mock_cursor.execute = AsyncMock()

    with patch('chatServer.services.user_instructions_cache_service.get_database_manager', return_value=mock_manager):
        service = UserInstructionsCacheService(ttl_seconds=120, refresh_interval_seconds=60)
        result = await service._fetch_user_instructions("user-1:assistant")

        assert result == []


@pytest.mark.asyncio
async def test_fetch_user_instructions_null_value(mock_db_manager):
    """Test fetching user instructions when instructions column is NULL."""
    mock_manager, mock_cursor = mock_db_manager
    mock_cursor.fetchone = AsyncMock(return_value=(None,))
    mock_cursor.execute = AsyncMock()

    with patch('chatServer.services.user_instructions_cache_service.get_database_manager', return_value=mock_manager):
        service = UserInstructionsCacheService(ttl_seconds=120, refresh_interval_seconds=60)
        result = await service._fetch_user_instructions("user-1:assistant")

        assert result == []


@pytest.mark.asyncio
async def test_fetch_invalid_cache_key():
    """Test fetching with an invalid cache key format."""
    with patch('chatServer.services.user_instructions_cache_service.get_database_manager'):
        service = UserInstructionsCacheService(ttl_seconds=120, refresh_interval_seconds=60)
        result = await service._fetch_user_instructions("invalid-key-no-colon")
        assert result == []


@pytest.mark.asyncio
async def test_get_user_instructions_via_cache(mock_db_manager):
    """Test getting user instructions through the cache layer."""
    mock_manager, mock_cursor = mock_db_manager
    mock_cursor.fetchone = AsyncMock(return_value=("Be friendly.",))
    mock_cursor.execute = AsyncMock()

    with patch('chatServer.services.user_instructions_cache_service.get_database_manager', return_value=mock_manager):
        service = UserInstructionsCacheService(ttl_seconds=120, refresh_interval_seconds=60)

        # First call: cache miss, fetches from DB
        result = await service.get_user_instructions("user-1", "assistant")
        assert result == "Be friendly."

        # Second call: should hit cache (DB won't be called again for same key)
        result = await service.get_user_instructions("user-1", "assistant")
        assert result == "Be friendly."


@pytest.mark.asyncio
async def test_cache_invalidation():
    """Test cache invalidation."""
    with patch('chatServer.services.user_instructions_cache_service.get_database_manager'):
        service = UserInstructionsCacheService(ttl_seconds=120, refresh_interval_seconds=60)

        service.cache_service._cache = {
            "user-1:assistant": ["Be concise."],
            "user-2:coach": ["Be motivating."],
        }

        await service.invalidate_cache(user_id="user-1", agent_name="assistant")
        assert "user-1:assistant" not in service.cache_service._cache
        assert "user-2:coach" in service.cache_service._cache

        await service.invalidate_cache()
        assert len(service.cache_service._cache) == 0


@pytest.mark.asyncio
async def test_cache_stats():
    """Test cache statistics."""
    with patch('chatServer.services.user_instructions_cache_service.get_database_manager'):
        service = UserInstructionsCacheService(ttl_seconds=120, refresh_interval_seconds=60)
        stats = service.get_cache_stats()
        assert stats["cache_type"] == "UserInstructions"
        assert stats["ttl_seconds"] == 120


@pytest.mark.asyncio
async def test_database_error_handling(mock_db_manager):
    """Test database error handling returns fallback."""
    mock_manager, mock_cursor = mock_db_manager
    mock_cursor.execute = AsyncMock(side_effect=Exception("DB connection failed"))

    with patch('chatServer.services.user_instructions_cache_service.get_database_manager', return_value=mock_manager):
        service = UserInstructionsCacheService(ttl_seconds=120, refresh_interval_seconds=60)
        result = await service._fetch_user_instructions("user-1:assistant")
        assert result == []
