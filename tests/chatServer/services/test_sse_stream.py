"""Tests for SSE stream formatter.

Covers AC-11 (event format) and AC-12 (StreamingResponse integration).
"""

import json

import pytest

from chatServer.services.conversation_handler import StreamEvent, TokenUsage
from chatServer.services.sse_stream import _format_sse, sse_stream


class TestFormatSSE:
    def test_text_delta(self):
        event = StreamEvent(type="text_delta", text="Hello")
        line = _format_sse(event)
        assert line.startswith("data: ")
        assert line.endswith("\n\n")
        payload = json.loads(line[len("data: "):])
        assert payload == {"type": "text_delta", "text": "Hello"}

    def test_tool_start(self):
        event = StreamEvent(
            type="tool_start",
            tool_name="search_gmail",
            tool_call_id="toolu_01",
        )
        payload = json.loads(_format_sse(event)[len("data: "):])
        assert payload["type"] == "tool_start"
        assert payload["tool_name"] == "search_gmail"
        assert payload["tool_call_id"] == "toolu_01"

    def test_tool_result(self):
        event = StreamEvent(
            type="tool_result",
            tool_call_id="toolu_01",
            result="Found 3 emails",
        )
        payload = json.loads(_format_sse(event)[len("data: "):])
        assert payload["type"] == "tool_result"
        assert payload["tool_call_id"] == "toolu_01"
        assert payload["result"] == "Found 3 emails"

    def test_message_complete(self):
        event = StreamEvent(
            type="message_complete",
            token_usage=TokenUsage(input_tokens=100, output_tokens=50),
        )
        payload = json.loads(_format_sse(event)[len("data: "):])
        assert payload["type"] == "message_complete"
        assert payload["token_usage"] == {
            "input_tokens": 100,
            "output_tokens": 50,
        }

    def test_message_complete_no_usage(self):
        event = StreamEvent(type="message_complete")
        payload = json.loads(_format_sse(event)[len("data: "):])
        assert payload == {"type": "message_complete"}

    def test_error(self):
        event = StreamEvent(type="error", message="Rate limited")
        payload = json.loads(_format_sse(event)[len("data: "):])
        assert payload == {"type": "error", "message": "Rate limited"}


class TestSSEStream:
    @pytest.mark.asyncio
    async def test_streams_events(self):
        """Verify sse_stream yields formatted SSE lines."""
        from unittest.mock import MagicMock

        mock_handler = MagicMock()

        async def mock_run_stream(messages):
            yield StreamEvent(type="text_delta", text="Hi")
            yield StreamEvent(
                type="message_complete",
                token_usage=TokenUsage(100, 50),
            )

        mock_handler.run_stream = mock_run_stream

        lines = []
        async for line in sse_stream(mock_handler, []):
            lines.append(line)

        assert len(lines) == 2
        assert '"text_delta"' in lines[0]
        assert '"message_complete"' in lines[1]

    @pytest.mark.asyncio
    async def test_handles_stream_error(self):
        """Errors during streaming yield an error event."""
        from unittest.mock import MagicMock

        mock_handler = MagicMock()

        async def failing_stream(messages):
            yield StreamEvent(type="text_delta", text="start")
            raise RuntimeError("API failure")

        mock_handler.run_stream = failing_stream

        lines = []
        async for line in sse_stream(mock_handler, []):
            lines.append(line)

        assert len(lines) == 2
        error_payload = json.loads(lines[1][len("data: "):])
        assert error_payload["type"] == "error"
        assert "API failure" in error_payload["message"]
