"""Tests for memory prefetch into agent execution (replaces old LTM tests)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.agent_loader_db import _prefetch_memory_notes, _resolve_memory_user_id

# --- _prefetch_memory_notes tests ---


@pytest.mark.asyncio
async def test_prefetch_memory_notes_returns_formatted_lines():
    """_prefetch_memory_notes formats list results as bullet points."""
    mock_client = MagicMock()
    mock_client.base_url = "http://memory:8000"
    mock_client.call_tool = AsyncMock(return_value=[
        {"text": "User prefers morning emails"},
        {"text": "User lives in NYC"},
    ])

    result = await _prefetch_memory_notes(mock_client)

    assert result == "- User prefers morning emails\n- User lives in NYC"
    mock_client.call_tool.assert_called_once_with("retrieve_context", {
        "query": "user context and preferences",
        "memory_type": ["core_identity", "project_context"],
        "limit": 10,
    })


@pytest.mark.asyncio
async def test_prefetch_memory_notes_returns_none_for_no_client():
    """_prefetch_memory_notes returns None when memory_client is None."""
    result = await _prefetch_memory_notes(None)
    assert result is None


@pytest.mark.asyncio
async def test_prefetch_memory_notes_returns_none_for_empty_base_url():
    """_prefetch_memory_notes returns None when base_url is empty."""
    mock_client = MagicMock()
    mock_client.base_url = ""

    result = await _prefetch_memory_notes(mock_client)
    assert result is None


@pytest.mark.asyncio
async def test_prefetch_memory_notes_returns_none_on_error():
    """_prefetch_memory_notes returns None on exception (non-fatal)."""
    mock_client = MagicMock()
    mock_client.base_url = "http://memory:8000"
    mock_client.call_tool = AsyncMock(side_effect=RuntimeError("Connection refused"))

    result = await _prefetch_memory_notes(mock_client)
    assert result is None


@pytest.mark.asyncio
async def test_prefetch_memory_notes_handles_dict_with_memories_key():
    """_prefetch_memory_notes extracts memories from dict response."""
    mock_client = MagicMock()
    mock_client.base_url = "http://memory:8000"
    mock_client.call_tool = AsyncMock(return_value={
        "memories": [{"text": "User prefers dark mode"}, {"text": "Likes coffee"}],
    })

    result = await _prefetch_memory_notes(mock_client)
    assert result == "- User prefers dark mode\n- Likes coffee"


@pytest.mark.asyncio
async def test_prefetch_memory_notes_returns_none_for_empty_list():
    """_prefetch_memory_notes returns None for empty list result."""
    mock_client = MagicMock()
    mock_client.base_url = "http://memory:8000"
    mock_client.call_tool = AsyncMock(return_value=[])

    result = await _prefetch_memory_notes(mock_client)
    assert result is None


# --- _resolve_memory_user_id tests ---


@pytest.mark.asyncio
async def test_resolve_memory_user_id_returns_oauth_format():
    """_resolve_memory_user_id returns google-oauth2|provider_id when found."""
    mock_cursor = MagicMock()
    mock_cursor.fetchone = AsyncMock(return_value=("12345",))
    mock_cursor.execute = AsyncMock()

    mock_conn = MagicMock()
    mock_conn.cursor.return_value.__aenter__ = AsyncMock(return_value=mock_cursor)
    mock_conn.cursor.return_value.__aexit__ = AsyncMock(return_value=False)

    async def mock_get_db():
        yield mock_conn

    with patch("src.core.agent_loader_db.get_db_connection", mock_get_db):
        result = await _resolve_memory_user_id("uuid-123")

    assert result == "google-oauth2|12345"


@pytest.mark.asyncio
async def test_resolve_memory_user_id_falls_back_on_error():
    """_resolve_memory_user_id returns original UUID on error."""
    with patch("src.core.agent_loader_db.get_db_connection", side_effect=Exception("DB down")):
        result = await _resolve_memory_user_id("uuid-123")

    assert result == "uuid-123"
