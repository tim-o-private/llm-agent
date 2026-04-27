"""AnthropicEngine — execute workflow steps via Anthropic Messages API.

Same tool-loop pattern as ConversationHandler but scoped to a single
workflow step. Tool calls go through LangChainToolBridge (temporary —
will be replaced by CapabilityGateway in SPEC-034).
"""

import asyncio
import logging
from typing import Any, Callable, Coroutine, Optional

import anthropic

from .models import EngineResult, TokenUsage, ToolCallRecord

logger = logging.getLogger(__name__)

_DEFAULT_MODEL = "claude-sonnet-4-5-20250514"
_DEFAULT_MAX_TOKENS = 4096
_DEFAULT_TEMPERATURE = 0.5
_MAX_TOOL_ITERATIONS = 15


class AnthropicEngine:
    """Execute workflow steps via Anthropic Messages API tool-loop.

    Constructed with a shared Anthropic client and tool infrastructure.
    Each call to run() executes one workflow step: sends a prompt, loops
    on tool calls until end_turn or max iterations.
    """

    def __init__(
        self,
        client: anthropic.AsyncAnthropic,
        tool_schemas: list[dict],
        tool_executors: dict[str, Callable[..., Coroutine[Any, Any, str]]],
        user_id: str = "",
    ):
        self._client = client
        self._all_tool_schemas = tool_schemas
        self._all_tool_executors = tool_executors
        self._user_id = user_id

    async def run(
        self,
        prompt: str,
        tools: list[str],
        system_prompt: Optional[str] = None,
        model: str = _DEFAULT_MODEL,
        max_tokens: int = _DEFAULT_MAX_TOKENS,
        temperature: float = _DEFAULT_TEMPERATURE,
    ) -> EngineResult:
        """Execute a single workflow step.

        Args:
            prompt: The step prompt (assembled by the graph node).
            tools: Tool names available to this step.
            system_prompt: Optional system prompt override.
            model: Model to use for this step.
            max_tokens: Max tokens for API call.
            temperature: Temperature for API call.

        Returns:
            EngineResult with output text, tool calls, and token usage.
        """
        # Filter tool schemas to only the tools this step is allowed
        step_schemas = [
            s for s in self._all_tool_schemas if s["name"] in tools
        ]

        messages: list[dict] = [{"role": "user", "content": prompt}]
        total_usage = TokenUsage()
        tool_calls: list[ToolCallRecord] = []

        for iteration in range(_MAX_TOOL_ITERATIONS):
            try:
                response = await self._client.messages.create(
                    model=model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    system=system_prompt or "",
                    messages=messages,
                    tools=step_schemas if step_schemas else anthropic.NOT_GIVEN,
                )
            except anthropic.APIStatusError as e:
                logger.error(
                    "Anthropic API error in workflow step: %d, user=%s",
                    e.status_code, self._user_id,
                )
                return EngineResult(
                    output=f"[API error: {e.status_code}]",
                    tool_calls=tool_calls,
                    token_usage=total_usage,
                )

            total_usage.input_tokens += response.usage.input_tokens
            total_usage.output_tokens += response.usage.output_tokens

            logger.debug(
                "Step iteration %d: %d in / %d out, stop=%s",
                iteration + 1,
                response.usage.input_tokens,
                response.usage.output_tokens,
                response.stop_reason,
            )

            if response.stop_reason == "end_turn":
                output = _extract_text(response.content)
                return EngineResult(
                    output=output,
                    tool_calls=tool_calls,
                    token_usage=total_usage,
                )

            if response.stop_reason == "tool_use":
                # Append assistant message
                messages.append({
                    "role": "assistant",
                    "content": _content_to_dicts(response.content),
                })

                # Execute tool calls
                tool_use_blocks = [
                    b for b in response.content if b.type == "tool_use"
                ]
                results = await asyncio.gather(
                    *[self._execute_tool(b) for b in tool_use_blocks],
                )

                tool_result_content: list[dict] = []
                for block, (result_str, is_error) in zip(tool_use_blocks, results):
                    tool_calls.append(ToolCallRecord(
                        tool_name=block.name,
                        tool_call_id=block.id,
                        input=block.input,
                        output=result_str,
                        is_error=is_error,
                    ))
                    entry: dict[str, Any] = {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result_str,
                    }
                    if is_error:
                        entry["is_error"] = True
                    tool_result_content.append(entry)

                messages.append({
                    "role": "user",
                    "content": tool_result_content,
                })
                continue

            # Unexpected stop reason
            output = _extract_text(response.content)
            return EngineResult(
                output=output or f"[Unexpected stop: {response.stop_reason}]",
                tool_calls=tool_calls,
                token_usage=total_usage,
            )

        return EngineResult(
            output="[Max tool iterations reached]",
            tool_calls=tool_calls,
            token_usage=total_usage,
        )

    async def _execute_tool(self, block: Any) -> tuple[str, bool]:
        """Execute a single tool call. Returns (result, is_error)."""
        executor = self._all_tool_executors.get(block.name)
        if not executor:
            logger.error("No executor for tool '%s'", block.name)
            return f"Error: Unknown tool '{block.name}'", True
        try:
            result = await executor(block.input)
            if result is None or result == "":
                result = "(No output)"
            return str(result), False
        except Exception as e:
            logger.error("Tool '%s' error: %s", block.name, e, exc_info=True)
            return f"Error executing tool: {e}", True


def _extract_text(content: list) -> str:
    """Extract text from Anthropic response content blocks."""
    return "".join(
        block.text for block in content if hasattr(block, "text")
    )


def _content_to_dicts(content: list) -> list[dict]:
    """Convert Anthropic SDK content blocks to plain dicts."""
    result: list[dict] = []
    for block in content:
        if block.type == "text":
            result.append({"type": "text", "text": block.text})
        elif block.type == "tool_use":
            result.append({
                "type": "tool_use",
                "id": block.id,
                "name": block.name,
                "input": block.input,
            })
    return result


def create_engine(
    client: Any,
    tool_schemas: list[dict],
    tool_executors: dict[str, Callable[..., Coroutine[Any, Any, str]]],
    user_id: str = "",
):
    """Factory that returns AnthropicEngine or OpenAIEngine based on client type."""
    from chatServer.services.llm_client import is_openai_client

    if is_openai_client(client):
        from .openai_engine import OpenAIEngine
        return OpenAIEngine(client, tool_schemas, tool_executors, user_id)
    return AnthropicEngine(client, tool_schemas, tool_executors, user_id)
