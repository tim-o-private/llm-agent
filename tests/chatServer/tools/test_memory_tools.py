"""Tests for memory tools backed by min-memory MCP server."""

from unittest.mock import AsyncMock

import pytest

from chatServer.tools.memory_tools import (
    DeleteMemoryTool,
    FetchMemoryTool,
    GetContextInfoTool,
    LinkMemoriesTool,
    ListEntitiesTool,
    RecallMemoryTool,
    SearchEntitiesTool,
    SearchMemoryTool,
    SetProjectTool,
    StoreMemoryTool,
    UpdateMemoryTool,
)


@pytest.fixture
def mock_memory_client():
    client = AsyncMock()
    client.call_tool = AsyncMock(return_value={"message": "ok"})
    return client


def _make_tool(cls, mock_memory_client):
    return cls(memory_client=mock_memory_client, user_id="user-123", agent_name="search_agent")


@pytest.fixture
def store_tool(mock_memory_client):
    return _make_tool(StoreMemoryTool, mock_memory_client)


@pytest.fixture
def recall_tool(mock_memory_client):
    return _make_tool(RecallMemoryTool, mock_memory_client)


@pytest.fixture
def search_tool(mock_memory_client):
    return _make_tool(SearchMemoryTool, mock_memory_client)


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
        assert "ok" in result

    @pytest.mark.asyncio
    async def test_omits_empty_tags(self, store_tool, mock_memory_client):
        await store_tool._arun(
            text="Test memory", memory_type="episodic", entity="user-123", scope="global",
        )
        call_args = mock_memory_client.call_tool.call_args[0][1]
        assert "tags" not in call_args

    @pytest.mark.asyncio
    async def test_passes_project_and_task_id(self, store_tool, mock_memory_client):
        await store_tool._arun(
            text="Sprint goal", memory_type="project_context", entity="myproj",
            scope="project", project="myproj", task_id="task-1",
        )
        call_args = mock_memory_client.call_tool.call_args[0][1]
        assert call_args["project"] == "myproj"
        assert call_args["task_id"] == "task-1"

    @pytest.mark.asyncio
    async def test_handles_client_error_gracefully(self, store_tool, mock_memory_client):
        mock_memory_client.call_tool.side_effect = RuntimeError("Connection refused")
        result = await store_tool._arun(
            text="Test", memory_type="episodic", entity="user-123", scope="global",
        )
        assert "Failed" in result
        assert "Connection refused" in result


class TestRecallMemoryTool:
    @pytest.mark.asyncio
    async def test_calls_retrieve_context_with_correct_args(self, recall_tool, mock_memory_client):
        await recall_tool._arun(query="coffee preferences", limit=5, memory_type=["core_identity"])

        mock_memory_client.call_tool.assert_called_once_with(
            "retrieve_context",
            {"query": "coffee preferences", "limit": 5, "memory_type": ["core_identity"]},
        )

    @pytest.mark.asyncio
    async def test_default_limit(self, recall_tool, mock_memory_client):
        await recall_tool._arun(query="test")
        call_args = mock_memory_client.call_tool.call_args[0][1]
        assert call_args["limit"] == 10

    @pytest.mark.asyncio
    async def test_passes_scope_and_project(self, recall_tool, mock_memory_client):
        await recall_tool._arun(query="test", scope="project", project="myproj")
        call_args = mock_memory_client.call_tool.call_args[0][1]
        assert call_args["scope"] == "project"
        assert call_args["project"] == "myproj"

    @pytest.mark.asyncio
    async def test_handles_client_error_gracefully(self, recall_tool, mock_memory_client):
        mock_memory_client.call_tool.side_effect = RuntimeError("Timeout")
        result = await recall_tool._arun(query="test")
        assert "Failed" in result


class TestSearchMemoryTool:
    @pytest.mark.asyncio
    async def test_calls_search_with_correct_args(self, search_tool, mock_memory_client):
        await search_tool._arun(query="project deadlines")
        mock_memory_client.call_tool.assert_called_once_with("search", {"query": "project deadlines"})

    @pytest.mark.asyncio
    async def test_handles_client_error_gracefully(self, search_tool, mock_memory_client):
        mock_memory_client.call_tool.side_effect = RuntimeError("Server down")
        result = await search_tool._arun(query="test")
        assert "Failed" in result


class TestFetchMemoryTool:
    @pytest.mark.asyncio
    async def test_calls_fetch(self, mock_memory_client):
        tool = _make_tool(FetchMemoryTool, mock_memory_client)
        await tool._arun(id="mem-abc-123")
        mock_memory_client.call_tool.assert_called_once_with("fetch", {"id": "mem-abc-123"})


class TestDeleteMemoryTool:
    @pytest.mark.asyncio
    async def test_calls_delete(self, mock_memory_client):
        tool = _make_tool(DeleteMemoryTool, mock_memory_client)
        await tool._arun(memory_id="mem-abc-123")
        mock_memory_client.call_tool.assert_called_once_with("delete_memory", {"memory_id": "mem-abc-123"})


class TestUpdateMemoryTool:
    @pytest.mark.asyncio
    async def test_calls_update_with_text(self, mock_memory_client):
        tool = _make_tool(UpdateMemoryTool, mock_memory_client)
        await tool._arun(memory_id="mem-1", text="updated text")
        mock_memory_client.call_tool.assert_called_once_with(
            "update_memory", {"memory_id": "mem-1", "text": "updated text"},
        )

    @pytest.mark.asyncio
    async def test_calls_update_with_multiple_fields(self, mock_memory_client):
        tool = _make_tool(UpdateMemoryTool, mock_memory_client)
        await tool._arun(memory_id="mem-1", text="new", tags=["a"], priority=5)
        call_args = mock_memory_client.call_tool.call_args[0][1]
        assert call_args["memory_id"] == "mem-1"
        assert call_args["text"] == "new"
        assert call_args["tags"] == ["a"]
        assert call_args["priority"] == 5

    @pytest.mark.asyncio
    async def test_omits_empty_fields(self, mock_memory_client):
        tool = _make_tool(UpdateMemoryTool, mock_memory_client)
        await tool._arun(memory_id="mem-1")
        mock_memory_client.call_tool.assert_called_once_with(
            "update_memory", {"memory_id": "mem-1"},
        )


class TestSetProjectTool:
    @pytest.mark.asyncio
    async def test_calls_set_project(self, mock_memory_client):
        tool = _make_tool(SetProjectTool, mock_memory_client)
        await tool._arun(project="llm-agent")
        mock_memory_client.call_tool.assert_called_once_with("set_project", {"project": "llm-agent"})


class TestLinkMemoriesTool:
    @pytest.mark.asyncio
    async def test_calls_link_memories(self, mock_memory_client):
        tool = _make_tool(LinkMemoriesTool, mock_memory_client)
        await tool._arun(memory_id="a", related_id="b", relation_type="supports")
        mock_memory_client.call_tool.assert_called_once_with(
            "link_memories", {"memory_id": "a", "related_id": "b", "relation_type": "supports"},
        )


class TestListEntitiesTool:
    @pytest.mark.asyncio
    async def test_calls_list_entities(self, mock_memory_client):
        tool = _make_tool(ListEntitiesTool, mock_memory_client)
        await tool._arun(scope="project", project="myproj")
        mock_memory_client.call_tool.assert_called_once_with(
            "list_entities", {"scope": "project", "project": "myproj"},
        )

    @pytest.mark.asyncio
    async def test_omits_empty_filters(self, mock_memory_client):
        tool = _make_tool(ListEntitiesTool, mock_memory_client)
        await tool._arun()
        mock_memory_client.call_tool.assert_called_once_with("list_entities", {})


class TestSearchEntitiesTool:
    @pytest.mark.asyncio
    async def test_calls_search_entities(self, mock_memory_client):
        tool = _make_tool(SearchEntitiesTool, mock_memory_client)
        await tool._arun(query="user", limit=3)
        mock_memory_client.call_tool.assert_called_once_with(
            "search_entities", {"query": "user", "limit": 3},
        )


class TestGetContextInfoTool:
    @pytest.mark.asyncio
    async def test_calls_get_context_info(self, mock_memory_client):
        tool = _make_tool(GetContextInfoTool, mock_memory_client)
        await tool._arun()
        mock_memory_client.call_tool.assert_called_once_with("get_context_info", {})


class TestPromptSections:
    def test_store_memory_prompt_for_web(self):
        section = StoreMemoryTool.prompt_section("web")
        assert section is not None
        assert "store_memory" in section
        assert "recall" in section

    def test_store_memory_prompt_for_telegram(self):
        assert StoreMemoryTool.prompt_section("telegram") is not None

    def test_store_memory_prompt_none_for_scheduled(self):
        assert StoreMemoryTool.prompt_section("scheduled") is None

    def test_other_tools_prompt_always_none(self):
        for cls in (RecallMemoryTool, SearchMemoryTool, FetchMemoryTool, DeleteMemoryTool,
                    UpdateMemoryTool, SetProjectTool, LinkMemoriesTool, ListEntitiesTool,
                    SearchEntitiesTool, GetContextInfoTool):
            assert cls.prompt_section("web") is None
            assert cls.prompt_section("scheduled") is None
