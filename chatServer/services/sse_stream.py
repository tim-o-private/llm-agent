"""SSE stream formatter for ConversationHandler streaming output.

Wraps the ConversationHandler's streaming events into Server-Sent Events
format for the ``/api/chat`` endpoint.
"""

import json
import logging
from typing import AsyncIterator

from .conversation_handler import ConversationHandler, StreamEvent

logger = logging.getLogger(__name__)


async def sse_stream(
    handler: ConversationHandler,
    messages: list[dict],
) -> AsyncIterator[str]:
    """Wrap handler streaming output as SSE lines.

    Each yielded string is a complete SSE ``data:`` line with trailing
    newlines, ready for ``StreamingResponse(media_type="text/event-stream")``.

    Event types:
    - ``text_delta``       — incremental text chunk
    - ``tool_start``       — tool invocation began
    - ``tool_result``      — tool invocation completed
    - ``message_complete`` — conversation turn finished
    - ``error``            — something went wrong
    """
    try:
        async for event in handler.run_stream(messages):
            yield _format_sse(event)
    except Exception as e:
        logger.error("SSE stream error: %s", e, exc_info=True)
        yield _format_sse(
            StreamEvent(type="error", message=str(e))
        )


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
