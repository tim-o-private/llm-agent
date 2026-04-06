"""ConversationHandler — direct Anthropic Messages API tool-loop.

Replaces LangChain's AgentExecutor with a simple while-loop over the
Anthropic Messages API.  Runs behind a feature flag alongside the
existing ChatService during migration.
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Callable, Optional

import anthropic

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class TokenUsage:
    """Cumulative token usage."""
    input_tokens: int = 0
    output_tokens: int = 0


@dataclass
class ToolCallRecord:
    """Record of a single tool invocation."""
    tool_name: str
    tool_call_id: str
    input: dict
    output: str
    is_error: bool = False


@dataclass
class ConversationResult:
    """Result of a non-streaming conversation run."""
    response_text: str
    new_messages: list[dict] = field(default_factory=list)
    tool_calls: list[ToolCallRecord] = field(default_factory=list)
    token_usage: TokenUsage = field(default_factory=TokenUsage)
    turn_count: int = 0
    stop_reason: str = ""


@dataclass
class StreamEvent:
    """Event yielded during streaming."""
    type: str  # text_delta | tool_start | tool_result | message_complete | error
    text: str = ""
    tool_name: str = ""
    tool_call_id: str = ""
    result: str = ""
    token_usage: Optional[TokenUsage] = None
    message: str = ""


# ---------------------------------------------------------------------------
# dispatch_workflow stub  (AC-28 – AC-30)
# ---------------------------------------------------------------------------

DISPATCH_WORKFLOW_TOOL: dict[str, Any] = {
    "name": "dispatch_workflow",
    "description": (
        "Start a multi-step workflow (email triage, draft reply, etc.). "
        "Not yet available — will be implemented in SPEC-035."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "workflow_name": {"type": "string"},
            "parameters": {"type": "object"},
        },
        "required": ["workflow_name"],
    },
}

DISPATCH_WORKFLOW_RESPONSE = (
    "Workflow dispatch is not yet available. "
    "I'll handle this conversationally instead."
)


# ---------------------------------------------------------------------------
# ConversationHandler
# ---------------------------------------------------------------------------

class ConversationHandler:
    """Direct Anthropic Messages API tool-loop.

    Accepts a system prompt, tool definitions (Anthropic format), and tool
    executors (name → async callable).  Loops until the API returns
    ``stop_reason == "end_turn"`` or *max_turns* is reached.
    """

    def __init__(
        self,
        client: anthropic.AsyncAnthropic,
        model: str,
        system_prompt: str,
        tools: list[dict],
        tool_executors: dict[str, Callable],
        max_turns: int = 25,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        timeout_seconds: float = 120,
    ):
        self.client = client
        self.model = model
        self.system_prompt = system_prompt
        self.tools = tools + [DISPATCH_WORKFLOW_TOOL]
        self.tool_executors: dict[str, Callable] = {
            **tool_executors,
            "dispatch_workflow": _dispatch_workflow_stub,
        }
        self.max_turns = max_turns
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.timeout_seconds = timeout_seconds
        self._cumulative_usage = TokenUsage()

    @property
    def token_usage(self) -> TokenUsage:
        """Cumulative token usage across all runs on this handler."""
        return self._cumulative_usage

    # ------------------------------------------------------------------
    # Non-streaming
    # ------------------------------------------------------------------

    async def run(self, messages: list[dict]) -> ConversationResult:
        """Execute the tool-loop without streaming.

        Returns a *ConversationResult* once the model stops or max_turns
        is reached.  ``result.new_messages`` contains every message added
        during the run (assistant responses, tool results) for persistence.
        """
        start_time = time.monotonic()
        tool_calls: list[ToolCallRecord] = []
        new_messages: list[dict] = []
        turn_count = 0
        usage = TokenUsage()
        working_messages = list(messages)
        response = None

        while turn_count < self.max_turns:
            elapsed = time.monotonic() - start_time
            if elapsed > self.timeout_seconds:
                return self._timeout_result(
                    tool_calls, usage, turn_count, new_messages
                )

            turn_count += 1
            remaining = max(self.timeout_seconds - elapsed, 1)

            try:
                response = await asyncio.wait_for(
                    self.client.messages.create(
                        model=self.model,
                        max_tokens=self.max_tokens,
                        temperature=self.temperature,
                        system=self.system_prompt,
                        tools=self.tools or anthropic.NOT_GIVEN,
                        messages=working_messages,
                    ),
                    timeout=remaining,
                )
            except asyncio.TimeoutError:
                return self._timeout_result(
                    tool_calls, usage, turn_count, new_messages
                )

            self._accum_usage(usage, response.usage)

            logger.info(
                "Turn %d: %d in / %d out, stop_reason=%s",
                turn_count,
                response.usage.input_tokens,
                response.usage.output_tokens,
                response.stop_reason,
            )

            if response.stop_reason == "end_turn":
                final_msg = {
                    "role": "assistant",
                    "content": _extract_text(response.content),
                }
                new_messages.append(final_msg)
                return ConversationResult(
                    response_text=final_msg["content"],
                    new_messages=new_messages,
                    tool_calls=tool_calls,
                    token_usage=usage,
                    turn_count=turn_count,
                    stop_reason="end_turn",
                )

            if response.stop_reason == "tool_use":
                assistant_msg = {
                    "role": "assistant",
                    "content": _content_to_dicts(response.content),
                }
                working_messages.append(assistant_msg)
                new_messages.append(assistant_msg)

                tool_use_blocks = [
                    b for b in response.content if b.type == "tool_use"
                ]

                results = await asyncio.gather(
                    *[self._execute_tool(b) for b in tool_use_blocks],
                )

                tool_result_content: list[dict] = []
                for block, (result_str, is_error) in zip(
                    tool_use_blocks, results
                ):
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

                tool_result_msg = {
                    "role": "user",
                    "content": tool_result_content,
                }
                working_messages.append(tool_result_msg)
                new_messages.append(tool_result_msg)
                continue

            # Unexpected stop_reason — return what we have
            final_msg = {
                "role": "assistant",
                "content": _extract_text(response.content),
            }
            new_messages.append(final_msg)
            return ConversationResult(
                response_text=final_msg["content"],
                new_messages=new_messages,
                tool_calls=tool_calls,
                token_usage=usage,
                turn_count=turn_count,
                stop_reason=response.stop_reason or "unknown",
            )

        # max_turns exhausted
        text = _extract_text(response.content) if response else ""
        if text:
            text += " [Max tool iterations reached]"
        else:
            text = "[Max tool iterations reached]"
        new_messages.append({"role": "assistant", "content": text})
        return ConversationResult(
            response_text=text,
            new_messages=new_messages,
            tool_calls=tool_calls,
            token_usage=usage,
            turn_count=turn_count,
            stop_reason="max_turns",
        )

    # ------------------------------------------------------------------
    # Streaming
    # ------------------------------------------------------------------

    async def run_stream(
        self, messages: list[dict]
    ) -> AsyncIterator[StreamEvent]:
        """Execute the tool-loop with streaming.

        Yields *StreamEvent* objects for text deltas, tool starts/results,
        completion, and errors.
        """
        start_time = time.monotonic()
        usage = TokenUsage()
        working_messages = list(messages)
        turn_count = 0

        while turn_count < self.max_turns:
            elapsed = time.monotonic() - start_time
            if elapsed > self.timeout_seconds:
                yield StreamEvent(type="error", message="Request timed out")
                return

            turn_count += 1

            async with self.client.messages.stream(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                system=self.system_prompt,
                tools=self.tools or anthropic.NOT_GIVEN,
                messages=working_messages,
            ) as stream:
                async for event in stream:
                    if not hasattr(event, "type"):
                        continue
                    if event.type == "content_block_start":
                        block = event.content_block
                        if block.type == "tool_use":
                            yield StreamEvent(
                                type="tool_start",
                                tool_name=block.name,
                                tool_call_id=block.id,
                            )
                    elif event.type == "content_block_delta":
                        delta = event.delta
                        if hasattr(delta, "text"):
                            yield StreamEvent(
                                type="text_delta", text=delta.text
                            )

                final_message = await stream.get_final_message()

            self._accum_usage(usage, final_message.usage)

            if final_message.stop_reason == "end_turn":
                yield StreamEvent(
                    type="message_complete", token_usage=usage
                )
                return

            if final_message.stop_reason == "tool_use":
                working_messages.append({
                    "role": "assistant",
                    "content": _content_to_dicts(final_message.content),
                })

                tool_use_blocks = [
                    b for b in final_message.content if b.type == "tool_use"
                ]
                results = await asyncio.gather(
                    *[self._execute_tool(b) for b in tool_use_blocks],
                )

                tool_result_content: list[dict] = []
                for block, (result_str, is_error) in zip(
                    tool_use_blocks, results
                ):
                    yield StreamEvent(
                        type="tool_result",
                        tool_call_id=block.id,
                        result=result_str,
                    )
                    entry: dict[str, Any] = {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result_str,
                    }
                    if is_error:
                        entry["is_error"] = True
                    tool_result_content.append(entry)

                working_messages.append({
                    "role": "user",
                    "content": tool_result_content,
                })
                continue

            yield StreamEvent(type="message_complete", token_usage=usage)
            return

        yield StreamEvent(
            type="error", message="[Max tool iterations reached]"
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _execute_tool(self, block: Any) -> tuple[str, bool]:
        """Execute a single tool call.  Returns ``(result, is_error)``."""
        executor = self.tool_executors.get(block.name)
        if not executor:
            logger.error("No executor found for tool '%s'", block.name)
            return f"Error: Unknown tool '{block.name}'", True
        try:
            result = await executor(block.input)
            if result is None or result == "":
                result = "(No output)"
            return str(result), False
        except Exception as e:
            logger.error(
                "Tool '%s' execution error: %s", block.name, e, exc_info=True
            )
            return f"Error executing tool: {e}", True

    def _accum_usage(self, usage: TokenUsage, api_usage: Any) -> None:
        usage.input_tokens += api_usage.input_tokens
        usage.output_tokens += api_usage.output_tokens
        self._cumulative_usage.input_tokens += api_usage.input_tokens
        self._cumulative_usage.output_tokens += api_usage.output_tokens

    @staticmethod
    def _timeout_result(
        tool_calls: list[ToolCallRecord],
        usage: TokenUsage,
        turn_count: int,
        new_messages: list[dict] | None = None,
    ) -> ConversationResult:
        timeout_msg = {"role": "assistant", "content": "[Request timed out]"}
        msgs = list(new_messages or [])
        msgs.append(timeout_msg)
        return ConversationResult(
            response_text="[Request timed out]",
            new_messages=msgs,
            tool_calls=tool_calls,
            token_usage=usage,
            turn_count=turn_count,
            stop_reason="timeout",
        )


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------

async def _dispatch_workflow_stub(args: dict) -> str:
    return DISPATCH_WORKFLOW_RESPONSE


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
