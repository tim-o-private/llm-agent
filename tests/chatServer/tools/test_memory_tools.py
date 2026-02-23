"""Tests for memory tools backed by min-memory MCP server."""

from unittest.mock import AsyncMock

import pytest

from chatServer.tools.memory_tools import RecallMemoryTool, SearchMemoryTool, StoreMemoryTool


@pytest.fixture
def mock_memory_client():
    client = AsyncMock()
    client.call_tool = AsyncMock(return_value={"message": "ok"})
    return client


@pytest.fixture
def store_tool(mock_memory_client):
    return StoreMemoryTool(
        memory_client=mock_memory_client,
        user_id="user-123",
        agent_name="search_agent",
    )


@pytest.fixture
def recall_tool(mock_memory_client):
    return RecallMemoryTool(
        memory_client=mock_memory_client,
        user_id="user-123",
        agent_name="search_agent",
    )


@pytest.fixture
def search_tool(mock_memory_client):
    return SearchMemoryTool(
        memory_client=mock_memory_client,
        user_id="user-123",
        agent_name="search_agent",
    )


class TestStoreMemoryTool:
    @pytest.mark.asyncio
    async def test_calls_store_memory_with_correct_args(self, store_tool, mock_memory_client):
        result = await store_tool._arun(
            text="User likes dark roast",
            memory_type="core_identity",
            entity="user-123",
            scope="global",
            tags=["preferences"],
        )

        mock_memory_client.call_tool.assert_called_once_with(
            "store_memory",
            {
                "text": "User likes dark roast",
                "memory_type": "core_identity",
                "entity": "user-123",
                "scope": "global",
                "tags": ["preferences"],
            },
        )
        assert "Memory stored" in result

    @pytest.mark.asyncio
    async def test_omits_empty_tags(self, store_tool, mock_memory_client):
        await store_tool._arun(
            text="Test memory",
            memory_type="episodic",
            entity="user-123",
            scope="global",
        )

        call_args = mock_memory_client.call_tool.call_args[0][1]
        assert "tags" not in call_args

    @pytest.mark.asyncio
    async def test_handles_client_error_gracefully(self, store_tool, mock_memory_client):
        mock_memory_client.call_tool.side_effect = RuntimeError("Connection refused")

        result = await store_tool._arun(
            text="Test",
            memory_type="episodic",
            entity="user-123",
            scope="global",
        )

        assert "Failed to store memory" in result
        assert "Connection refused" in result


class TestRecallMemoryTool:
    @pytest.mark.asyncio
    async def test_calls_retrieve_context_with_correct_args(self, recall_tool, mock_memory_client):
        await recall_tool._arun(query="coffee preferences", limit=5, memory_type=["core_identity"])

        mock_memory_client.call_tool.assert_called_once_with(
            "retrieve_context",
            {
                "query": "coffee preferences",
                "limit": 5,
                "memory_type": ["core_identity"],
            },
        )

    @pytest.mark.asyncio
    async def test_default_limit(self, recall_tool, mock_memory_client):
        await recall_tool._arun(query="test")

        call_args = mock_memory_client.call_tool.call_args[0][1]
        assert call_args["limit"] == 10

    @pytest.mark.asyncio
    async def test_omits_empty_memory_type(self, recall_tool, mock_memory_client):
        await recall_tool._arun(query="test")

        call_args = mock_memory_client.call_tool.call_args[0][1]
        assert "memory_type" not in call_args

    @pytest.mark.asyncio
    async def test_handles_client_error_gracefully(self, recall_tool, mock_memory_client):
        mock_memory_client.call_tool.side_effect = RuntimeError("Timeout")

        result = await recall_tool._arun(query="test")

        assert "Failed to recall memories" in result
        assert "Timeout" in result


class TestSearchMemoryTool:
    @pytest.mark.asyncio
    async def test_calls_search_with_correct_args(self, search_tool, mock_memory_client):
        await search_tool._arun(query="project deadlines")

        mock_memory_client.call_tool.assert_called_once_with(
            "search",
            {"query": "project deadlines"},
        )

    @pytest.mark.asyncio
    async def test_handles_client_error_gracefully(self, search_tool, mock_memory_client):
        mock_memory_client.call_tool.side_effect = RuntimeError("Server down")

        result = await search_tool._arun(query="test")

        assert "Failed to search memories" in result
        assert "Server down" in result


class TestPromptSections:
    def test_store_memory_prompt_for_web_channel(self):
        section = StoreMemoryTool.prompt_section("web")
        assert section is not None
        assert "store_memory" in section
        assert "recall" in section

    def test_store_memory_prompt_for_telegram_channel(self):
        section = StoreMemoryTool.prompt_section("telegram")
        assert section is not None

    def test_store_memory_prompt_none_for_scheduled(self):
        section = StoreMemoryTool.prompt_section("scheduled")
        assert section is None

    def test_recall_prompt_always_none(self):
        assert RecallMemoryTool.prompt_section("web") is None
        assert RecallMemoryTool.prompt_section("scheduled") is None

    def test_search_prompt_always_none(self):
        assert SearchMemoryTool.prompt_section("web") is None
        assert SearchMemoryTool.prompt_section("scheduled") is None
