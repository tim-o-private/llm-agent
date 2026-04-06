"""Bridge layer: LangChain BaseTool → Anthropic Messages API format.

Temporary adapter — removed when SPEC-034 (Capability Gateway) ships.
Converts BaseTool schemas to Anthropic tool definitions for the API call,
and dispatches tool calls back to BaseTool._arun().
"""

import logging
from typing import Any, Callable, Coroutine

logger = logging.getLogger(__name__)


class LangChainToolBridge:
    """Converts LangChain BaseTool instances to Anthropic-native tool format."""

    @staticmethod
    def to_anthropic_schema(tool) -> dict:
        """Convert a BaseTool to an Anthropic tool definition.

        Returns dict with name, description, input_schema suitable for
        the Anthropic Messages API tools parameter.
        """
        schema: dict[str, Any] = {"type": "object", "properties": {}}
        if hasattr(tool, "args_schema") and tool.args_schema is not None:
            try:
                schema = tool.args_schema.model_json_schema()
                # Remove Pydantic metadata that Anthropic doesn't need
                schema.pop("title", None)
            except Exception:
                logger.warning(
                    "Failed to generate schema for tool '%s', using empty schema",
                    tool.name,
                )
                schema = {"type": "object", "properties": {}}

        return {
            "name": tool.name,
            "description": tool.description or "",
            "input_schema": schema,
        }

    @staticmethod
    async def execute(tool, args: dict) -> str:
        """Dispatch a tool call to BaseTool._arun().

        Returns the string result. Converts None or empty string to
        "(No output)" since the Anthropic API rejects empty tool results.
        """
        result = await tool._arun(**args)
        if result is None or result == "":
            return "(No output)"
        return str(result)

    @staticmethod
    def convert_tools(
        tools: list,
    ) -> tuple[list[dict], dict[str, Callable[..., Coroutine[Any, Any, str]]]]:
        """Convert a list of BaseTools to Anthropic schemas + executor map.

        Returns:
            (tool_schemas, tool_executors) where tool_schemas is a list of
            Anthropic tool definitions and tool_executors maps tool name
            to an async callable that accepts a dict of arguments.
        """
        schemas = []
        executors: dict[str, Callable[..., Coroutine[Any, Any, str]]] = {}
        for tool in tools:
            schemas.append(LangChainToolBridge.to_anthropic_schema(tool))

            async def _executor(args: dict, _tool=tool) -> str:
                return await LangChainToolBridge.execute(_tool, args)

            executors[tool.name] = _executor
        return schemas, executors
