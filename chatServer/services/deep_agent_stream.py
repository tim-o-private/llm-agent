"""SSE stream adapter for Deep Agent (CompiledStateGraph).

Maps real LangGraph v2 stream events to SSE-framed StreamEvents.

v2 chunk format (version="v2"):
    {
        "type": "messages" | "updates" | "custom",
        "ns": tuple,   # () for main agent
        "data": ...,   # mode-specific payload
    }

"messages" data: (token, metadata) — token.content is the streamed text
"updates"  data: dict of node_name → state updates (tool results in "tools" node)
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
            stream_mode=["messages", "updates"],
            version="v2",
        ):
            chunk_type = chunk.get("type") if isinstance(chunk, dict) else None
            data = chunk.get("data") if isinstance(chunk, dict) else None

            if chunk_type == "messages":
                # data is a tuple (token, metadata)
                if isinstance(data, tuple) and len(data) == 2:
                    token, _metadata = data
                    content = getattr(token, "content", None)
                    if content and isinstance(content, str):
                        yield _format_sse(StreamEvent(type="text_delta", text=content))

            elif chunk_type == "updates":
                # data is a dict of node_name → state updates
                if isinstance(data, dict):
                    for node_name, node_output in data.items():
                        if node_name == "tools" and isinstance(node_output, dict):
                            for msg in node_output.get("messages", []):
                                tool_name = getattr(msg, "name", "") or ""
                                tool_call_id = getattr(msg, "tool_call_id", "") or ""
                                content = getattr(msg, "content", "") or ""
                                if tool_name or tool_call_id:
                                    yield _format_sse(StreamEvent(
                                        type="tool_result",
                                        tool_name=tool_name,
                                        tool_call_id=tool_call_id,
                                        result=str(content),
                                    ))

    except Exception as e:
        logger.exception("deep_agent_stream_to_sse: unexpected error: %s", e)
        yield _format_sse(StreamEvent(type="error", message=str(e)))
        return

    yield _format_sse(StreamEvent(type="message_complete"))
