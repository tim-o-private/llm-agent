"""Unit tests for deep_agent_stream.py — real LangGraph v2 event format."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from chatServer.services.conversation_handler import StreamEvent
from chatServer.services.deep_agent_stream import deep_agent_stream_to_sse

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_token(content: str, token_type: str = "ai") -> MagicMock:
    """Build a mock LangChain AIMessageChunk."""
    token = MagicMock()
    token.content = content
    token.type = token_type
    return token


def _make_agent(chunks: list):
    """Build a mock CompiledStateGraph whose astream yields the given v2 chunks."""
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
# Tests — text streaming ("messages" chunks)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_messages_chunk_yields_text_delta():
    """messages chunk with AI token → text_delta SSE line."""
    token = _make_token("Hello")
    chunk = {"type": "messages", "ns": (), "data": (token, {})}
    agent = _make_agent([chunk])

    results = await _collect(deep_agent_stream_to_sse(agent, {"messages": []}))

    # Last item is message_complete; first is text_delta
    assert any("text_delta" in r for r in results)
    assert any("Hello" in r for r in results)


@pytest.mark.asyncio
async def test_empty_token_content_skipped():
    """messages chunk with empty content string is not yielded."""
    token = _make_token("")
    chunk = {"type": "messages", "ns": (), "data": (token, {})}
    agent = _make_agent([chunk])

    results = await _collect(deep_agent_stream_to_sse(agent, {"messages": []}))

    # Only message_complete should be emitted
    assert len(results) == 1
    assert "message_complete" in results[0]


@pytest.mark.asyncio
async def test_multiple_text_chunks_all_yielded():
    """Multiple messages chunks produce multiple text_delta SSE lines."""
    chunks = [
        {"type": "messages", "ns": (), "data": (_make_token("A"), {})},
        {"type": "messages", "ns": (), "data": (_make_token("B"), {})},
        {"type": "messages", "ns": (), "data": (_make_token("C"), {})},
    ]
    agent = _make_agent(chunks)

    results = await _collect(deep_agent_stream_to_sse(agent, {"messages": []}))

    text_deltas = [r for r in results if "text_delta" in r]
    assert len(text_deltas) == 3
    assert any("A" in r for r in text_deltas)
    assert any("B" in r for r in text_deltas)
    assert any("C" in r for r in text_deltas)


# ---------------------------------------------------------------------------
# Tests — tool results ("updates" chunks)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_updates_chunk_tools_node_yields_tool_result():
    """updates chunk with tools node produces tool_result SSE line."""
    tool_msg = MagicMock()
    tool_msg.name = "search_gmail"
    tool_msg.tool_call_id = "call-123"
    tool_msg.content = "3 emails found"

    chunk = {
        "type": "updates",
        "ns": (),
        "data": {"tools": {"messages": [tool_msg]}},
    }
    agent = _make_agent([chunk])

    results = await _collect(deep_agent_stream_to_sse(agent, {"messages": []}))

    tool_results = [r for r in results if "tool_result" in r]
    assert len(tool_results) == 1
    assert "call-123" in tool_results[0]  # tool_call_id is included in SSE payload


@pytest.mark.asyncio
async def test_updates_chunk_non_tools_node_skipped():
    """updates chunk for non-tools nodes (e.g., model_request) produces no tool_result."""
    chunk = {
        "type": "updates",
        "ns": (),
        "data": {"model_request": {"messages": []}},
    }
    agent = _make_agent([chunk])

    results = await _collect(deep_agent_stream_to_sse(agent, {"messages": []}))

    tool_results = [r for r in results if "tool_result" in r]
    assert len(tool_results) == 0


# ---------------------------------------------------------------------------
# Tests — always ends with message_complete
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_empty_stream_yields_only_message_complete():
    """Empty stream → only message_complete."""
    agent = _make_agent([])

    results = await _collect(deep_agent_stream_to_sse(agent, {"messages": []}))

    assert len(results) == 1
    assert "message_complete" in results[0]


@pytest.mark.asyncio
async def test_stream_always_ends_with_message_complete():
    """Regardless of content, last event is always message_complete."""
    chunks = [
        {"type": "messages", "ns": (), "data": (_make_token("Hello"), {})},
    ]
    agent = _make_agent(chunks)

    results = await _collect(deep_agent_stream_to_sse(agent, {"messages": []}))

    assert "message_complete" in results[-1]


# ---------------------------------------------------------------------------
# Tests — unknown chunk types and error handling
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_unknown_chunk_type_skipped():
    """Chunks with unknown type are silently ignored (no crash, no output)."""
    chunk = {"type": "custom", "ns": (), "data": {"some": "event"}}
    agent = _make_agent([chunk])

    results = await _collect(deep_agent_stream_to_sse(agent, {"messages": []}))

    # Only message_complete
    assert len(results) == 1
    assert "message_complete" in results[0]


@pytest.mark.asyncio
async def test_astream_exception_yields_error_sse():
    """If astream raises, an error SSE line is yielded (no message_complete after)."""
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


@pytest.mark.asyncio
async def test_passes_version_v2_to_astream():
    """stream adapter always passes version='v2' to agent.astream."""
    agent = MagicMock()
    captured = {}

    async def _astream(input_data, **kwargs):
        captured["kwargs"] = kwargs
        return
        yield  # noqa: unreachable

    agent.astream = _astream

    await _collect(deep_agent_stream_to_sse(agent, {}))

    assert captured["kwargs"].get("version") == "v2"


@pytest.mark.asyncio
async def test_passes_stream_modes_to_astream():
    """stream adapter passes both 'messages' and 'updates' stream modes."""
    agent = MagicMock()
    captured = {}

    async def _astream(input_data, **kwargs):
        captured["kwargs"] = kwargs
        return
        yield  # noqa: unreachable

    agent.astream = _astream

    await _collect(deep_agent_stream_to_sse(agent, {}))

    modes = captured["kwargs"].get("stream_mode", [])
    assert "messages" in modes
    assert "updates" in modes
