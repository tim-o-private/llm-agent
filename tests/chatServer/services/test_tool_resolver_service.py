"""Tests for ToolResolverService."""

from typing import Type
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from chatServer.services.tool_resolver_service import (
    ToolResolverService,
    resolve_tools_for_agent,
)


class DummyInput(BaseModel):
    query: str = Field(default="", description="Query string")


class DummyTool(BaseTool):
    name: str = "dummy_tool"
    description: str = "A dummy tool"
    args_schema: Type[BaseModel] = DummyInput

    def _run(self, query: str = "") -> str:
        return f"result: {query}"

    async def _arun(self, query: str = "") -> str:
        return f"result: {query}"


@pytest.fixture
def mock_db_manager():
    """Mock database manager with async generator connection and cursor context manager."""
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


def _mock_settings():
    s = MagicMock()
    s.supabase_url = "https://test.supabase.co"
    s.supabase_service_key = "test-service-key"
    return s


class TestToolResolverService:
    """Tests for ToolResolverService.resolve_for_agent."""

    async def test_resolve_for_agent_success(self, mock_db_manager):
        """Mock DB query returning tool rows and load_tools_from_db returning BaseTool instances."""
        mock_manager, mock_cursor = mock_db_manager

        mock_cursor.fetchall = AsyncMock(return_value=[
            ("dummy_tool", "A dummy tool", "DummyToolType", {"key": "val"}, "granted"),
        ])
        mock_cursor.execute = AsyncMock()

        dummy_tool = DummyTool()

        with (
            patch("chatServer.database.connection.get_database_manager", return_value=mock_manager),
            patch("chatServer.config.settings.get_settings", return_value=_mock_settings()),
            patch("src.core.agent_loader_db.load_tools_from_db", return_value=[dummy_tool]),
        ):
            service = ToolResolverService()
            tool_schemas, tool_executors, instantiated_tools = await service.resolve_for_agent("user-1", "test-agent")

        assert len(tool_schemas) == 1
        assert len(tool_executors) == 1
        assert len(instantiated_tools) == 1
        assert instantiated_tools[0] is dummy_tool

    async def test_resolve_for_agent_empty_tools(self, mock_db_manager):
        """Mock DB query returning no tools, verify empty lists/dicts returned."""
        mock_manager, mock_cursor = mock_db_manager

        mock_cursor.fetchall = AsyncMock(return_value=[])
        mock_cursor.execute = AsyncMock()

        with patch("chatServer.database.connection.get_database_manager", return_value=mock_manager):
            service = ToolResolverService()
            tool_schemas, tool_executors, instantiated_tools = await service.resolve_for_agent("user-1", "test-agent")

        assert tool_schemas == []
        assert tool_executors == {}
        assert instantiated_tools == []

    async def test_resolve_for_agent_db_failure(self, mock_db_manager, caplog):
        """Mock DB query raising an exception, verify graceful handling."""
        mock_manager, _ = mock_db_manager

        async def failing_connection():
            raise RuntimeError("DB connection failed")
            yield MagicMock()  # makes this an async generator

        mock_manager.get_connection = failing_connection

        with patch("chatServer.database.connection.get_database_manager", return_value=mock_manager):
            service = ToolResolverService()
            tool_schemas, tool_executors, instantiated_tools = await service.resolve_for_agent("user-1", "test-agent")

        assert tool_schemas == []
        assert tool_executors == {}
        assert instantiated_tools == []
        assert "DB connection failed" in caplog.text

    async def test_tool_schemas_format(self, mock_db_manager):
        """Verify returned tool_schemas are in Anthropic format."""
        mock_manager, mock_cursor = mock_db_manager

        mock_cursor.fetchall = AsyncMock(return_value=[
            ("dummy_tool", "A dummy tool", "DummyToolType", {}, "granted"),
        ])
        mock_cursor.execute = AsyncMock()

        dummy_tool = DummyTool()

        with (
            patch("chatServer.database.connection.get_database_manager", return_value=mock_manager),
            patch("chatServer.config.settings.get_settings", return_value=_mock_settings()),
            patch("src.core.agent_loader_db.load_tools_from_db", return_value=[dummy_tool]),
        ):
            service = ToolResolverService()
            tool_schemas, _, _ = await service.resolve_for_agent("user-1", "test-agent")

        assert len(tool_schemas) == 1
        schema = tool_schemas[0]
        assert schema["name"] == "dummy_tool"
        assert schema["description"] == "A dummy tool"
        assert "input_schema" in schema
        assert schema["input_schema"]["type"] == "object"
        assert "properties" in schema["input_schema"]
        assert "required" in schema["input_schema"]

    async def test_tool_executors_callable(self, mock_db_manager):
        """Verify tool_executors are async callables that invoke tool._arun."""
        mock_manager, mock_cursor = mock_db_manager

        mock_cursor.fetchall = AsyncMock(return_value=[
            ("dummy_tool", "A dummy tool", "DummyToolType", {}, "granted"),
        ])
        mock_cursor.execute = AsyncMock()

        dummy_tool = DummyTool()
        dummy_tool._arun = AsyncMock(return_value="mocked result")

        with (
            patch("chatServer.database.connection.get_database_manager", return_value=mock_manager),
            patch("chatServer.config.settings.get_settings", return_value=_mock_settings()),
            patch("src.core.agent_loader_db.load_tools_from_db", return_value=[dummy_tool]),
        ):
            service = ToolResolverService()
            _, tool_executors, _ = await service.resolve_for_agent("user-1", "test-agent")

        assert "dummy_tool" in tool_executors
        executor = tool_executors["dummy_tool"]
        assert callable(executor)

        result = await executor({"query": "hello"})
        assert result == "mocked result"
        dummy_tool._arun.assert_awaited_once_with(query="hello")

    async def test_resolve_tools_for_agent_convenience(self, mock_db_manager):
        """Verify the convenience function works."""
        mock_manager, mock_cursor = mock_db_manager

        mock_cursor.fetchall = AsyncMock(return_value=[
            ("dummy_tool", "A dummy tool", "DummyToolType", {}, "granted"),
        ])
        mock_cursor.execute = AsyncMock()

        dummy_tool = DummyTool()

        with (
            patch("chatServer.database.connection.get_database_manager", return_value=mock_manager),
            patch("chatServer.config.settings.get_settings", return_value=_mock_settings()),
            patch("src.core.agent_loader_db.load_tools_from_db", return_value=[dummy_tool]),
        ):
            tool_schemas, tool_executors, instantiated_tools = await resolve_tools_for_agent("user-1", "test-agent")

        assert len(tool_schemas) == 1
        assert len(tool_executors) == 1
        assert len(instantiated_tools) == 1
