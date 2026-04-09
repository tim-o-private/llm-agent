"""SSE stream adapter for Deep Agent (CompiledStateGraph).

Maps LangGraph stream events to SSE-framed StreamEvents.

Uses stream_mode="messages" which yields (AIMessageChunk, metadata) tuples.
AIMessageChunk.content is the streamed text; .tool_call_chunks has tool info.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any, AsyncIterator, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# StreamEvent — shared data class for SSE event payloads
# ---------------------------------------------------------------------------


@dataclass
class TokenUsage:
    """Cumulative token usage."""
    input_tokens: int = 0
    output_tokens: int = 0


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


def _format_sse(event: StreamEvent) -> str:
    """Convert a StreamEvent to an SSE data line."""
    payload: dict = {"type": event.type}

    if event.type == "text_delta":
        payload["text"] = event.text
    elif event.type == "tool_start":
        payload["tool_name"] = event.tool_name
        payload["tool_call_id"] = event.tool_call_id
    elif event.type == "tool_result":
        payload["tool_call_id"] = event.tool_call_id
        payload["result"] = event.result
    elif event.type == "message_complete":
        if event.token_usage:
            payload["token_usage"] = {
                "input_tokens": event.token_usage.input_tokens,
                "output_tokens": event.token_usage.output_tokens,
            }
    elif event.type == "error":
        payload["message"] = event.message

    return f"data: {json.dumps(payload)}\n\n"


# ---------------------------------------------------------------------------
# Deep Agent SSE streaming
# ---------------------------------------------------------------------------


async def deep_agent_stream_to_sse(
    agent: Any,
    input_data: dict,
    config: Optional[dict] = None,
) -> AsyncIterator[str]:
    """Yield SSE-formatted strings from a CompiledStateGraph.astream call.

    Handles real LangGraph v2 events:
    - "messages" chunks → text_delta StreamEvents
    - "updates" chunks with "tools" node → tool_result StreamEvents
    - End of stream → message_complete StreamEvent
    """
    try:
        async for chunk in agent.astream(
            input_data,
            config=config,
            stream_mode="messages",
        ):
            # stream_mode="messages" yields (AIMessageChunk, metadata) tuples
            if not isinstance(chunk, tuple) or len(chunk) != 2:
                continue

            token, _metadata = chunk
            content = getattr(token, "content", None)
            tool_calls = getattr(token, "tool_call_chunks", None)

            # Content can be a string OR a list of content blocks
            # Anthropic returns: [{"text": "...", "type": "text", "index": 0}]
            if content:
                if isinstance(content, str):
                    yield _format_sse(StreamEvent(type="text_delta", text=content))
                elif isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "text" and block.get("text"):
                            yield _format_sse(StreamEvent(type="text_delta", text=block["text"]))

            if tool_calls:
                for tc in tool_calls:
                    name = tc.get("name", "") if isinstance(tc, dict) else ""
                    tc_id = tc.get("id", "") if isinstance(tc, dict) else ""
                    if name:
                        yield _format_sse(StreamEvent(
                            type="tool_start",
                            tool_name=name,
                            tool_call_id=tc_id,
                        ))

    except Exception as e:
        logger.exception("deep_agent_stream_to_sse: unexpected error: %s", e)
        yield _format_sse(StreamEvent(type="error", message=str(e)))
        return

    yield _format_sse(StreamEvent(type="message_complete"))
