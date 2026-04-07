"""SSE stream adapter for DeepAgentWrapper.

Thin shim that formats DeepAgentWrapper.astream output as SSE-framed strings.
DeepAgentWrapper.astream already yields StreamEvent-bearing dicts (same payload
as ConversationHandler.run_stream), so we reuse _format_sse from sse_stream.py.

TODO SPEC-043: when langchain 1.x migration lands and real deepagents events
are available, update the event-extraction logic here to handle the v2 envelope.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, AsyncIterator

if TYPE_CHECKING:
    from .deep_agent_builder import DeepAgentWrapper

logger = logging.getLogger(__name__)


async def deep_agent_stream_to_sse(
    agent: "DeepAgentWrapper",
    input_data: dict,
) -> AsyncIterator[str]:
    """Yield SSE-formatted strings from a DeepAgentWrapper.astream call.

    DeepAgentWrapper.astream yields ``{"type": ..., "event": StreamEvent}``
    dicts.  We unwrap the StreamEvent and pass it to _format_sse so the wire
    format is identical to the existing ConversationHandler SSE path.
    """
    from .conversation_handler import StreamEvent
    from .sse_stream import _format_sse

    try:
        async for envelope in agent.astream(input_data):
            if isinstance(envelope, dict) and "event" in envelope:
                inner = envelope["event"]
                if isinstance(inner, StreamEvent):
                    yield _format_sse(inner)
            elif isinstance(envelope, StreamEvent):
                # Defensive: handle direct StreamEvent in case wrapper changes
                yield _format_sse(envelope)
    except Exception as e:
        logger.exception("deep_agent_stream_to_sse: unexpected error: %s", e)
        error_event = StreamEvent(type="error", message=str(e))
        yield _format_sse(error_event)
