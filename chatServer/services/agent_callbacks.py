"""LangGraph callback handler for logging agent tool calls.

Deep Agents middleware tools (ls, read_file, edit_file, etc.) execute inside
the LangGraph graph and are invisible to the chatServer. This callback handler
surfaces tool invocations in the application logs.
"""

import logging
from typing import Any
from uuid import UUID

from langchain_core.callbacks import BaseCallbackHandler

logger = logging.getLogger(__name__)


class ToolCallLogger(BaseCallbackHandler):
    """Logs tool start/end events at INFO level."""

    def on_tool_start(
        self,
        serialized: dict[str, Any],
        input_str: str,
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        **kwargs: Any,
    ) -> None:
        tool_name = serialized.get("name", "unknown")
        # Truncate long inputs (e.g., file contents)
        preview = input_str[:200] if len(input_str) > 200 else input_str
        logger.info("Tool call: %s — %s", tool_name, preview)

    def on_tool_end(
        self,
        output: str,
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        **kwargs: Any,
    ) -> None:
        # Log output length only — full output is too noisy
        output_str = str(output)
        logger.debug("Tool result: %d chars", len(output_str))


# Shared singleton — reuse across invocations
tool_call_logger = ToolCallLogger()
