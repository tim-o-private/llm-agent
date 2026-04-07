"""Unit tests for deep_agent_stream.py."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from chatServer.services.conversation_handler import StreamEvent
from chatServer.services.deep_agent_stream import deep_agent_stream_to_sse

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_agent(events: list):
    """Build a mock DeepAgentWrapper whose astream yields the given items."""
    agent = MagicMock()

    async def _fake_astream(input_data, **kwargs):
        for ev in events:
            yield ev

    agent.astream = _fake_astream
    return agent


async def _collect(gen) -> list[str]:
    """Drain an async generator into a list."""
    results = []
    async for item in gen:
        results.append(item)
    return results


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_yields_sse_for_envelope_with_event():
    """Dict envelope {"type": ..., "event": StreamEvent} is unwrapped and formatted."""
    event = StreamEvent(type="text_delta", text="Hello")
    agent = _make_agent([{"type": "text_delta", "event": event}])

    results = await _collect(deep_agent_stream_to_sse(agent, {"messages": []}))

    assert len(results) == 1
    assert "data:" in results[0]
    assert "text_delta" in results[0]


@pytest.mark.asyncio
async def test_yields_sse_for_direct_stream_event():
    """Defensive path: bare StreamEvent (no dict envelope) is also formatted."""
    event = StreamEvent(type="message_complete", text="Done")
    agent = _make_agent([event])

    results = await _collect(deep_agent_stream_to_sse(agent, {"messages": []}))

    assert len(results) == 1
    assert "data:" in results[0]


@pytest.mark.asyncio
async def test_multiple_events_all_yielded():
    events = [
        {"type": "text_delta", "event": StreamEvent(type="text_delta", text="A")},
        {"type": "text_delta", "event": StreamEvent(type="text_delta", text="B")},
        {"type": "message_complete", "event": StreamEvent(type="message_complete", text="AB")},
    ]
    agent = _make_agent(events)

    results = await _collect(deep_agent_stream_to_sse(agent, {"messages": []}))

    assert len(results) == 3


@pytest.mark.asyncio
async def test_empty_stream_yields_nothing():
    agent = _make_agent([])

    results = await _collect(deep_agent_stream_to_sse(agent, {"messages": []}))

    assert results == []


@pytest.mark.asyncio
async def test_unknown_envelope_type_skipped():
    """Dict without 'event' key is silently skipped (no crash, no output)."""
    agent = _make_agent([{"type": "unknown", "data": "something"}])

    results = await _collect(deep_agent_stream_to_sse(agent, {"messages": []}))

    assert results == []


@pytest.mark.asyncio
async def test_astream_exception_yields_error_sse():
    """If astream raises, an error SSE line is yielded instead of crashing."""
    agent = MagicMock()

    async def _broken_astream(input_data, **kwargs):
        raise RuntimeError("stream failed")
        yield  # make it a generator  # noqa: unreachable

    agent.astream = _broken_astream

    results = await _collect(deep_agent_stream_to_sse(agent, {"messages": []}))

    assert len(results) == 1
    assert "error" in results[0].lower() or "data:" in results[0]


@pytest.mark.asyncio
async def test_passes_input_data_to_astream():
    """input_data dict is forwarded to agent.astream unchanged."""
    agent = MagicMock()
    captured = {}

    async def _astream(input_data, **kwargs):
        captured["input_data"] = input_data
        return
        yield  # noqa: unreachable

    agent.astream = _astream
    input_data = {"messages": [{"role": "user", "content": "hi"}]}

    await _collect(deep_agent_stream_to_sse(agent, input_data))

    assert captured["input_data"] == input_data
