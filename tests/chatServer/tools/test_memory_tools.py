"""Tests for SaveMemoryTool and ReadMemoryTool."""

from unittest.mock import MagicMock, patch

import pytest

from chatServer.tools.memory_tools import MAX_NOTES_LENGTH, ReadMemoryTool, SaveMemoryTool


@pytest.fixture
def mock_supabase_client():
    """Create a mock Supabase client with chainable methods."""
    client = MagicMock()
    return client


@pytest.fixture
def save_tool():
    return SaveMemoryTool(
        user_id="user-123",
        agent_name="assistant",
        supabase_url="https://test.supabase.co",
        supabase_key="test-key",
    )


@pytest.fixture
def read_tool():
    return ReadMemoryTool(
        user_id="user-123",
        agent_name="assistant",
        supabase_url="https://test.supabase.co",
        supabase_key="test-key",
    )


def _mock_upsert(client, return_value=None, side_effect=None):
    """Set up mock for upsert chain: table().upsert().execute()."""
    execute = client.table.return_value.upsert.return_value.execute
    if side_effect:
        execute.side_effect = side_effect
    else:
        execute.return_value = return_value or MagicMock(data=[{"id": 1}])


def _mock_select(client, return_value=None, side_effect=None):
    """Set up mock for select chain: table().select().eq().eq().maybe_single().execute()."""
    chain = client.table.return_value.select.return_value
    execute = (
        chain.eq.return_value
        .eq.return_value
        .maybe_single.return_value
        .execute
    )
    if side_effect:
        execute.side_effect = side_effect
    else:
        execute.return_value = return_value or MagicMock(data=None)


class TestSaveMemoryTool:
    @pytest.mark.asyncio
    async def test_save_memory_creates_new_entry(self, save_tool, mock_supabase_client):
        """Test saving memory notes upserts into the table."""
        _mock_upsert(mock_supabase_client)

        with patch.object(save_tool, "_get_client", return_value=mock_supabase_client):
            result = await save_tool._arun(notes="User prefers morning meetings")

        assert "saved successfully" in result
        mock_supabase_client.table.assert_called_once_with("agent_long_term_memory")
        mock_supabase_client.table.return_value.upsert.assert_called_once_with(
            {
                "user_id": "user-123",
                "agent_id": "assistant",
                "notes": "User prefers morning meetings",
            },
            on_conflict="user_id,agent_id",
        )

    @pytest.mark.asyncio
    async def test_save_memory_updates_existing_entry(self, save_tool, mock_supabase_client):
        """Test that upsert updates existing notes (same user_id + agent_id)."""
        _mock_upsert(mock_supabase_client)

        with patch.object(save_tool, "_get_client", return_value=mock_supabase_client):
            result = await save_tool._arun(notes="Updated notes content")

        assert "saved successfully" in result
        call_args = mock_supabase_client.table.return_value.upsert.call_args
        assert call_args[1]["on_conflict"] == "user_id,agent_id"

    @pytest.mark.asyncio
    async def test_save_memory_truncates_long_notes(self, save_tool, mock_supabase_client):
        """Test that notes exceeding MAX_NOTES_LENGTH are truncated."""
        long_notes = "x" * (MAX_NOTES_LENGTH + 500)
        _mock_upsert(mock_supabase_client)

        with patch.object(save_tool, "_get_client", return_value=mock_supabase_client):
            result = await save_tool._arun(notes=long_notes)

        assert "truncated" in result
        call_args = mock_supabase_client.table.return_value.upsert.call_args
        saved_notes = call_args[0][0]["notes"]
        assert len(saved_notes) == MAX_NOTES_LENGTH

    @pytest.mark.asyncio
    async def test_save_memory_handles_db_error(self, save_tool, mock_supabase_client):
        """Test graceful handling of database errors."""
        _mock_upsert(mock_supabase_client, side_effect=Exception("DB connection failed"))

        with patch.object(save_tool, "_get_client", return_value=mock_supabase_client):
            result = await save_tool._arun(notes="Some notes")

        assert "Failed to save" in result
        assert "DB connection failed" in result

    @pytest.mark.asyncio
    async def test_save_memory_scoped_to_user(self, mock_supabase_client):
        """Test that memory is scoped to a specific user_id and agent_name."""
        tool_user_a = SaveMemoryTool(
            user_id="user-A",
            agent_name="assistant",
            supabase_url="https://test.supabase.co",
            supabase_key="test-key",
        )
        tool_user_b = SaveMemoryTool(
            user_id="user-B",
            agent_name="assistant",
            supabase_url="https://test.supabase.co",
            supabase_key="test-key",
        )

        _mock_upsert(mock_supabase_client)

        with patch.object(tool_user_a, "_get_client", return_value=mock_supabase_client):
            await tool_user_a._arun(notes="User A notes")

        call_a = mock_supabase_client.table.return_value.upsert.call_args[0][0]
        assert call_a["user_id"] == "user-A"

        mock_supabase_client.reset_mock()
        _mock_upsert(mock_supabase_client, return_value=MagicMock(data=[{"id": 2}]))

        with patch.object(tool_user_b, "_get_client", return_value=mock_supabase_client):
            await tool_user_b._arun(notes="User B notes")

        call_b = mock_supabase_client.table.return_value.upsert.call_args[0][0]
        assert call_b["user_id"] == "user-B"


class TestReadMemoryTool:
    @pytest.mark.asyncio
    async def test_read_memory_returns_notes(self, read_tool, mock_supabase_client):
        """Test reading existing memory notes."""
        mock_result = MagicMock()
        mock_result.data = {"notes": "User prefers morning meetings"}
        _mock_select(mock_supabase_client, return_value=mock_result)

        with patch.object(read_tool, "_get_client", return_value=mock_supabase_client):
            result = await read_tool._arun()

        assert result == "User prefers morning meetings"
        mock_supabase_client.table.assert_called_once_with("agent_long_term_memory")

    @pytest.mark.asyncio
    async def test_read_memory_returns_placeholder_when_empty(self, read_tool, mock_supabase_client):
        """Test that a placeholder is returned when no notes exist."""
        mock_result = MagicMock()
        mock_result.data = None
        _mock_select(mock_supabase_client, return_value=mock_result)

        with patch.object(read_tool, "_get_client", return_value=mock_supabase_client):
            result = await read_tool._arun()

        assert result == "(No memory notes yet.)"

    @pytest.mark.asyncio
    async def test_read_memory_returns_placeholder_for_empty_notes(self, read_tool, mock_supabase_client):
        """Test placeholder returned when notes field is empty string."""
        mock_result = MagicMock()
        mock_result.data = {"notes": ""}
        _mock_select(mock_supabase_client, return_value=mock_result)

        with patch.object(read_tool, "_get_client", return_value=mock_supabase_client):
            result = await read_tool._arun()

        assert result == "(No memory notes yet.)"

    @pytest.mark.asyncio
    async def test_read_memory_handles_db_error(self, read_tool, mock_supabase_client):
        """Test graceful handling of database errors."""
        _mock_select(
            mock_supabase_client,
            side_effect=Exception("DB connection failed"),
        )

        with patch.object(read_tool, "_get_client", return_value=mock_supabase_client):
            result = await read_tool._arun()

        assert "Failed to read" in result
        assert "DB connection failed" in result

    @pytest.mark.asyncio
    async def test_read_memory_filters_by_user_and_agent(self, read_tool, mock_supabase_client):
        """Test that read queries filter by user_id and agent_name."""
        mock_result = MagicMock()
        mock_result.data = {"notes": "test"}
        chain = mock_supabase_client.table.return_value.select.return_value
        chain.eq.return_value.eq.return_value.maybe_single.return_value.execute.return_value = mock_result

        with patch.object(read_tool, "_get_client", return_value=mock_supabase_client):
            await read_tool._arun()

        eq_calls = chain.eq.call_args_list
        assert eq_calls[0] == (("user_id", "user-123"),)
        second_eq = chain.eq.return_value.eq
        second_eq.assert_called_once_with("agent_id", "assistant")
