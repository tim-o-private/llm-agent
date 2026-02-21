"""Tests for LTM (long-term memory) loading into agent execution."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.core.agent_loader_db import fetch_ltm_notes

# --- fetch_ltm_notes tests (deprecated but still functional) ---


@pytest.mark.asyncio
async def test_agent_loader_fetches_ltm_from_db():
    """fetch_ltm_notes returns notes when the DB has an entry for user+agent."""
    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.maybe_single.return_value.execute = AsyncMock(  # noqa: E501
        return_value=MagicMock(data={"notes": "User prefers morning emails"})
    )

    result = await fetch_ltm_notes("user-123", "assistant", supabase_client=mock_client)

    assert result == "User prefers morning emails"
    mock_client.table.assert_called_with("agent_long_term_memory")


@pytest.mark.asyncio
async def test_agent_loader_handles_missing_ltm():
    """fetch_ltm_notes returns None when no LTM row exists."""
    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.maybe_single.return_value.execute = AsyncMock(  # noqa: E501
        return_value=MagicMock(data=None)
    )

    result = await fetch_ltm_notes("user-123", "assistant", supabase_client=mock_client)

    assert result is None


@pytest.mark.asyncio
async def test_fetch_ltm_handles_db_error():
    """fetch_ltm_notes returns None on database error (non-fatal)."""
    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.maybe_single.return_value.execute = AsyncMock(  # noqa: E501
        side_effect=Exception("DB connection lost")
    )

    result = await fetch_ltm_notes("user-123", "assistant", supabase_client=mock_client)

    assert result is None


@pytest.mark.asyncio
async def test_fetch_ltm_handles_empty_notes():
    """fetch_ltm_notes returns None when notes field is empty string."""
    mock_client = MagicMock()
    mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.maybe_single.return_value.execute = AsyncMock(  # noqa: E501
        return_value=MagicMock(data={"notes": ""})
    )

    result = await fetch_ltm_notes("user-123", "assistant", supabase_client=mock_client)

    assert result is None
