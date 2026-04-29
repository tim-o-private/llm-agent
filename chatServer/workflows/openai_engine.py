"""OpenAIEngine — execute workflow steps via OpenAI Chat Completions API.

Mirrors the tool-loop pattern in AnthropicEngine but uses the OpenAI SDK.
Supports any OpenAI-compatible endpoint (e.g. OpenCode Go).
"""

import asyncio
import json
import logging
from typing import Any, Callable, Coroutine, Optional

from .models import EngineResult, TokenUsage, ToolCallRecord

logger = logging.getLogger(__name__)

_DEFAULT_MODEL = "kimi-k2.6"
_DEFAULT_MAX_TOKENS = 8192
_DEFAULT_TEMPERATURE = 0.5
_MAX_TOOL_ITERATIONS = 15


def _openai_tools(step_schemas: list[dict]) -> list[dict]:
    """Convert Anthropic-style tool schemas to OpenAI function format."""
    result: list[dict] = []
    for schema in step_schemas:
        fn: dict = {
            "type": "function",
            "function": {
                "name": schema["name"],
                "description": schema.get("description", ""),
                "parameters": schema.get("input_schema", schema.get("parameters", {})),
            },
        }
        result.append(fn)
    return result


class OpenAIEngine:
    """Execute workflow steps via OpenAI Chat Completions API tool-loop."""

    def __init__(
        self,
        client: Any,
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
        step_schemas = [
            s for s in self._all_tool_schemas if s["name"] in tools
        ]

        messages: list[dict] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        total_usage = TokenUsage()
        tool_calls: list[ToolCallRecord] = []
        openai_tools = _openai_tools(step_schemas) if step_schemas else None

        for iteration in range(_MAX_TOOL_ITERATIONS):
            try:
                response = await self._client.chat.completions.create(
                    model=model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    messages=messages,
                    tools=openai_tools,
                    tool_choice="auto" if openai_tools else None,
                )
            except Exception as e:
                status = getattr(e, "status_code", None) or getattr(e, "code", "unknown")
                logger.error(
                    "OpenAI API error in workflow step: %s, user=%s",
                    status, self._user_id,
                )
                return EngineResult(
                    output=f"[API error: {status}]",
                    tool_calls=tool_calls,
                    token_usage=total_usage,
                )

            choice = response.choices[0]
            message = choice.message

            total_usage.input_tokens += response.usage.prompt_tokens if response.usage else 0
            total_usage.output_tokens += response.usage.completion_tokens if response.usage else 0

            finish_reason = choice.finish_reason
            logger.debug(
                "Step iteration %d: %d in / %d out, finish=%s",
                iteration + 1,
                total_usage.input_tokens,
                total_usage.output_tokens,
                finish_reason,
            )

            if finish_reason in ("stop", "length"):
                output = message.content or ""
                return EngineResult(
                    output=output,
                    tool_calls=tool_calls,
                    token_usage=total_usage,
                )

            if finish_reason == "tool_calls" and message.tool_calls:
                assistant_msg: dict[str, Any] = {
                    "role": "assistant",
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments,
                            },
                        }
                        for tc in message.tool_calls
                    ],
                }
                if message.content:
                    assistant_msg["content"] = message.content
                messages.append(assistant_msg)

                tool_results = await asyncio.gather(
                    *[self._execute_tool(tc) for tc in message.tool_calls]
                )

                for tc, (result_str, is_error) in zip(message.tool_calls, tool_results):
                    try:
                        input_data = json.loads(tc.function.arguments)
                    except json.JSONDecodeError:
                        input_data = {"raw": tc.function.arguments}

                    tool_calls.append(ToolCallRecord(
                        tool_name=tc.function.name,
                        tool_call_id=tc.id,
                        input=input_data,
                        output=result_str,
                        is_error=is_error,
                    ))
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": result_str,
                    })
                continue

            output = message.content or f"[Unexpected finish: {finish_reason}]"
            return EngineResult(
                output=output,
                tool_calls=tool_calls,
                token_usage=total_usage,
            )

        return EngineResult(
            output="[Max tool iterations reached]",
            tool_calls=tool_calls,
            token_usage=total_usage,
        )

    async def _execute_tool(self, tc: Any) -> tuple[str, bool]:
        """Execute a single tool call. Returns (result, is_error)."""
        name = tc.function.name
        executor = self._all_tool_executors.get(name)
        if not executor:
            logger.error("No executor for tool '%s'", name)
            return f"Error: Unknown tool '{name}'", True
        try:
            try:
                input_data = json.loads(tc.function.arguments)
            except json.JSONDecodeError:
                input_data = {"raw": tc.function.arguments}
            result = await executor(input_data)
            if result is None or result == "":
                result = "(No output)"
            return str(result), False
        except Exception as e:
            logger.error("Tool '%s' error: %s", name, e, exc_info=True)
            return f"Error executing tool: {e}", True
