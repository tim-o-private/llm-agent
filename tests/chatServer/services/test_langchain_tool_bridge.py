"""Tests for LangChainToolBridge — BaseTool → Anthropic format conversion."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import BaseModel, Field

from chatServer.services.langchain_tool_bridge import LangChainToolBridge

# ---------------------------------------------------------------------------
# Fixtures — fake BaseTool-like objects
# ---------------------------------------------------------------------------

class SearchSchema(BaseModel):
    query: str = Field(description="Search query")
    max_results: int = Field(default=10, description="Max results")


def _make_tool(name="test_tool", description="A test tool", args_schema=None):
    """Create a mock BaseTool-like object."""
    tool = MagicMock()
    tool.name = name
    tool.description = description
    tool.args_schema = args_schema
    tool._arun = AsyncMock(return_value="tool result")
    return tool


# ---------------------------------------------------------------------------
# Schema conversion tests  (AC-05)
# ---------------------------------------------------------------------------

class TestToAnthropicSchema:
    def test_basic_schema_conversion(self):
        tool = _make_tool(
            name="search_gmail",
            description="Search Gmail inbox",
            args_schema=SearchSchema,
        )
        schema = LangChainToolBridge.to_anthropic_schema(tool)

        assert schema["name"] == "search_gmail"
        assert schema["description"] == "Search Gmail inbox"
        assert schema["input_schema"]["type"] == "object"
        assert "query" in schema["input_schema"]["properties"]
        assert "max_results" in schema["input_schema"]["properties"]
        # Pydantic title should be stripped
        assert "title" not in schema["input_schema"]

    def test_schema_without_args_schema(self):
        tool = _make_tool(name="no_args_tool", args_schema=None)
        schema = LangChainToolBridge.to_anthropic_schema(tool)

        assert schema["name"] == "no_args_tool"
        assert schema["input_schema"] == {
            "type": "object",
            "properties": {},
        }

    def test_schema_with_broken_args_schema(self):
        """If model_json_schema() fails, fallback to empty schema."""
        tool = _make_tool(name="broken_tool")
        broken_schema = MagicMock()
        broken_schema.model_json_schema = MagicMock(
            side_effect=Exception("schema error")
        )
        tool.args_schema = broken_schema

        schema = LangChainToolBridge.to_anthropic_schema(tool)
        assert schema["input_schema"] == {
            "type": "object",
            "properties": {},
        }

    def test_schema_with_empty_description(self):
        tool = _make_tool(name="t", description=None)
        schema = LangChainToolBridge.to_anthropic_schema(tool)
        assert schema["description"] == ""


# ---------------------------------------------------------------------------
# Tool dispatch tests  (AC-05)
# ---------------------------------------------------------------------------

class TestExecute:
    @pytest.mark.asyncio
    async def test_dispatch_calls_arun(self):
        tool = _make_tool()
        tool._arun = AsyncMock(return_value="found 3 emails")

        result = await LangChainToolBridge.execute(
            tool, {"query": "invoice"}
        )
        assert result == "found 3 emails"
        tool._arun.assert_awaited_once_with(query="invoice")

    @pytest.mark.asyncio
    async def test_dispatch_none_result(self):
        tool = _make_tool()
        tool._arun = AsyncMock(return_value=None)

        result = await LangChainToolBridge.execute(tool, {})
        assert result == "(No output)"

    @pytest.mark.asyncio
    async def test_dispatch_empty_string_result(self):
        tool = _make_tool()
        tool._arun = AsyncMock(return_value="")

        result = await LangChainToolBridge.execute(tool, {})
        assert result == "(No output)"

    @pytest.mark.asyncio
    async def test_dispatch_non_string_result(self):
        tool = _make_tool()
        tool._arun = AsyncMock(return_value=42)

        result = await LangChainToolBridge.execute(tool, {})
        assert result == "42"

    @pytest.mark.asyncio
    async def test_dispatch_propagates_error(self):
        tool = _make_tool()
        tool._arun = AsyncMock(side_effect=ValueError("boom"))

        with pytest.raises(ValueError, match="boom"):
            await LangChainToolBridge.execute(tool, {})


# ---------------------------------------------------------------------------
# convert_tools tests
# ---------------------------------------------------------------------------

class TestConvertTools:
    def test_convert_tools_returns_schemas_and_executors(self):
        t1 = _make_tool(name="tool_a", description="Tool A")
        t2 = _make_tool(name="tool_b", description="Tool B")

        schemas, executors = LangChainToolBridge.convert_tools([t1, t2])

        assert len(schemas) == 2
        assert schemas[0]["name"] == "tool_a"
        assert schemas[1]["name"] == "tool_b"
        assert "tool_a" in executors
        assert "tool_b" in executors

    @pytest.mark.asyncio
    async def test_executors_dispatch_to_correct_tool(self):
        t1 = _make_tool(name="tool_a")
        t1._arun = AsyncMock(return_value="result_a")
        t2 = _make_tool(name="tool_b")
        t2._arun = AsyncMock(return_value="result_b")

        _, executors = LangChainToolBridge.convert_tools([t1, t2])

        assert await executors["tool_a"]({"x": 1}) == "result_a"
        assert await executors["tool_b"]({"y": 2}) == "result_b"
        t1._arun.assert_awaited_once_with(x=1)
        t2._arun.assert_awaited_once_with(y=2)

    def test_convert_empty_tools(self):
        schemas, executors = LangChainToolBridge.convert_tools([])
        assert schemas == []
        assert executors == {}
