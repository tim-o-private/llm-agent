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
            # stream_mode="messages" yields (message_chunk, metadata) tuples
            if isinstance(chunk, tuple) and len(chunk) == 2:
                token, _metadata = chunk
                # AIMessageChunk has content (text) and tool_call_chunks
                content = getattr(token, "content", None)
                tool_calls = getattr(token, "tool_call_chunks", None)

                if content and isinstance(content, str):
                    yield _format_sse(StreamEvent(type="text_delta", text=content))

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
            else:
                logger.debug("stream chunk (unexpected type): %s %s", type(chunk).__name__, repr(chunk)[:200])

    except Exception as e:
        logger.exception("deep_agent_stream_to_sse: unexpected error: %s", e)
        yield _format_sse(StreamEvent(type="error", message=str(e)))
        return

    yield _format_sse(StreamEvent(type="message_complete"))
