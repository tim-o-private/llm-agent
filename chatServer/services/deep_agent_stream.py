"""SSE stream adapter for Deep Agent (CompiledStateGraph).

Maps LangGraph stream events to SSE-framed StreamEvents.

Uses stream_mode="messages" which yields (AIMessageChunk, metadata) tuples.
AIMessageChunk.content is the streamed text; .tool_call_chunks has tool info.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, AsyncIterator, Optional

from chatServer.services.conversation_handler import StreamEvent

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


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
    from .sse_stream import _format_sse

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
