"""Tests for UpdateInstructionsTool."""

from unittest.mock import MagicMock, patch

import pytest

from chatServer.tools.update_instructions_tool import MAX_INSTRUCTIONS_LENGTH, UpdateInstructionsTool


@pytest.fixture
def mock_supabase_client():
    """Create a mock Supabase client with chainable methods."""
    return MagicMock()


@pytest.fixture
def tool():
    return UpdateInstructionsTool(
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


class TestUpdateInstructionsTool:
    @pytest.mark.asyncio
    async def test_upsert_creates_new_instructions(self, tool, mock_supabase_client):
        """First write creates a new row."""
        _mock_upsert(mock_supabase_client)

        with patch.object(tool, "_get_client", return_value=mock_supabase_client):
            result = await tool._arun(instructions="Always respond in bullet points.")

        assert "updated successfully" in result
        mock_supabase_client.table.assert_called_once_with("user_agent_prompt_customizations")
        mock_supabase_client.table.return_value.upsert.assert_called_once_with(
            {
                "user_id": "user-123",
                "agent_name": "assistant",
                "instructions": "Always respond in bullet points.",
            },
            on_conflict="user_id,agent_name",
        )

    @pytest.mark.asyncio
    async def test_upsert_replaces_existing_instructions(self, tool, mock_supabase_client):
        """Second write replaces existing instructions."""
        _mock_upsert(mock_supabase_client)

        with patch.object(tool, "_get_client", return_value=mock_supabase_client):
            result = await tool._arun(instructions="New instructions replacing old ones.")

        assert "updated successfully" in result
        call_args = mock_supabase_client.table.return_value.upsert.call_args
        assert call_args[1]["on_conflict"] == "user_id,agent_name"

    @pytest.mark.asyncio
    async def test_empty_string_clears_instructions(self, tool, mock_supabase_client):
        """Empty string clears custom instructions."""
        _mock_upsert(mock_supabase_client)

        with patch.object(tool, "_get_client", return_value=mock_supabase_client):
            result = await tool._arun(instructions="")

        assert "cleared" in result
        call_args = mock_supabase_client.table.return_value.upsert.call_args
        assert call_args[0][0]["instructions"] == ""

    @pytest.mark.asyncio
    async def test_truncates_long_instructions(self, tool, mock_supabase_client):
        """Instructions exceeding MAX_INSTRUCTIONS_LENGTH are truncated."""
        long_instructions = "x" * (MAX_INSTRUCTIONS_LENGTH + 500)
        _mock_upsert(mock_supabase_client)

        with patch.object(tool, "_get_client", return_value=mock_supabase_client):
            result = await tool._arun(instructions=long_instructions)

        assert "truncated" in result
        call_args = mock_supabase_client.table.return_value.upsert.call_args
        saved = call_args[0][0]["instructions"]
        assert len(saved) == MAX_INSTRUCTIONS_LENGTH

    @pytest.mark.asyncio
    async def test_scoped_to_user_and_agent(self, mock_supabase_client):
        """Instructions are scoped to specific user_id and agent_name."""
        tool_a = UpdateInstructionsTool(
            user_id="user-A",
            agent_name="assistant",
            supabase_url="https://test.supabase.co",
            supabase_key="test-key",
        )
        tool_b = UpdateInstructionsTool(
            user_id="user-B",
            agent_name="assistant",
            supabase_url="https://test.supabase.co",
            supabase_key="test-key",
        )

        _mock_upsert(mock_supabase_client)

        with patch.object(tool_a, "_get_client", return_value=mock_supabase_client):
            await tool_a._arun(instructions="User A prefs")

        call_a = mock_supabase_client.table.return_value.upsert.call_args[0][0]
        assert call_a["user_id"] == "user-A"

        mock_supabase_client.reset_mock()
        _mock_upsert(mock_supabase_client)

        with patch.object(tool_b, "_get_client", return_value=mock_supabase_client):
            await tool_b._arun(instructions="User B prefs")

        call_b = mock_supabase_client.table.return_value.upsert.call_args[0][0]
        assert call_b["user_id"] == "user-B"

    @pytest.mark.asyncio
    async def test_handles_db_error(self, tool, mock_supabase_client):
        """Graceful handling of database errors."""
        _mock_upsert(mock_supabase_client, side_effect=Exception("DB connection failed"))

        with patch.object(tool, "_get_client", return_value=mock_supabase_client):
            result = await tool._arun(instructions="Some instructions")

        assert "Failed to update" in result
        assert "DB connection failed" in result

    def test_sync_run_returns_message(self, tool):
        """Synchronous _run returns a message directing to async."""
        result = tool._run(instructions="test")
        assert "async" in result.lower() or "_arun" in result
