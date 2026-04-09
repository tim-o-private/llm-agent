"""Unit tests for deep_agent_stream.py — LangGraph messages stream format."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from chatServer.services.deep_agent_stream import deep_agent_stream_to_sse

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_token(content: str = "", tool_call_chunks: list | None = None) -> MagicMock:
    """Build a mock LangChain AIMessageChunk."""
    token = MagicMock()
    token.content = content
    token.tool_call_chunks = tool_call_chunks or []
    return token


def _make_agent(chunks: list):
    """Build a mock CompiledStateGraph whose astream yields (token, metadata) tuples."""
    agent = MagicMock()

    async def _fake_astream(input_data, **kwargs):
        for chunk in chunks:
            yield chunk

    agent.astream = _fake_astream
    return agent


async def _collect(gen) -> list[str]:
    """Drain an async generator into a list."""
    results = []
    async for item in gen:
        results.append(item)
    return results


# ---------------------------------------------------------------------------
# Tests — text streaming
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_text_chunk_yields_text_delta():
    """(token, metadata) tuple with text content → text_delta SSE."""
    token = _make_token("Hello")
    agent = _make_agent([(token, {})])

    results = await _collect(deep_agent_stream_to_sse(agent, {"messages": []}))

    assert any("text_delta" in r for r in results)
    assert any("Hello" in r for r in results)


@pytest.mark.asyncio
async def test_empty_content_skipped():
    """Token with empty content string produces no text_delta."""
    token = _make_token("")
    agent = _make_agent([(token, {})])

    results = await _collect(deep_agent_stream_to_sse(agent, {"messages": []}))

    assert len(results) == 1
    assert "message_complete" in results[0]


@pytest.mark.asyncio
async def test_multiple_text_chunks():
    """Multiple tokens produce multiple text_delta SSE lines."""
    chunks = [(_make_token("A"), {}), (_make_token("B"), {}), (_make_token("C"), {})]
    agent = _make_agent(chunks)

    results = await _collect(deep_agent_stream_to_sse(agent, {"messages": []}))

    text_deltas = [r for r in results if "text_delta" in r]
    assert len(text_deltas) == 3


# ---------------------------------------------------------------------------
# Tests — tool calls
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_tool_call_chunk_yields_tool_start():
    """Token with tool_call_chunks produces tool_start SSE."""
    token = _make_token(tool_call_chunks=[{"name": "search_gmail", "id": "call-123"}])
    agent = _make_agent([(token, {})])

    results = await _collect(deep_agent_stream_to_sse(agent, {"messages": []}))

    tool_starts = [r for r in results if "tool_start" in r]
    assert len(tool_starts) == 1
    assert "search_gmail" in tool_starts[0]


# ---------------------------------------------------------------------------
# Tests — message_complete always last
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_empty_stream_yields_message_complete():
    """Empty stream → only message_complete."""
    agent = _make_agent([])

    results = await _collect(deep_agent_stream_to_sse(agent, {"messages": []}))

    assert len(results) == 1
    assert "message_complete" in results[0]


@pytest.mark.asyncio
async def test_stream_always_ends_with_message_complete():
    """Last event is always message_complete."""
    agent = _make_agent([(_make_token("Hi"), {})])

    results = await _collect(deep_agent_stream_to_sse(agent, {"messages": []}))

    assert "message_complete" in results[-1]


# ---------------------------------------------------------------------------
# Tests — error handling
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_astream_exception_yields_error():
    """If astream raises, an error SSE line is yielded."""
    agent = MagicMock()

    async def _broken(input_data, **kwargs):
        raise RuntimeError("stream failed")
        yield  # noqa: RET503 — unreachable, makes it a generator

    agent.astream = _broken

    results = await _collect(deep_agent_stream_to_sse(agent, {"messages": []}))

    assert any("error" in r.lower() for r in results)


@pytest.mark.asyncio
async def test_non_tuple_chunk_skipped():
    """Non-tuple chunks are silently ignored."""
    agent = _make_agent(["unexpected_string", 42, None])

    results = await _collect(deep_agent_stream_to_sse(agent, {"messages": []}))

    assert len(results) == 1
    assert "message_complete" in results[0]


@pytest.mark.asyncio
async def test_passes_stream_mode_messages():
    """Adapter passes stream_mode='messages' to astream."""
    captured = {}
    agent = MagicMock()

    async def _astream(input_data, **kwargs):
        captured.update(kwargs)
        return
        yield  # noqa: RET503

    agent.astream = _astream
    await _collect(deep_agent_stream_to_sse(agent, {}))

    assert captured.get("stream_mode") == "messages"
