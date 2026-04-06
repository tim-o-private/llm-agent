"""Tests for ConversationHandler — Anthropic Messages API tool-loop.

Covers AC-01 (loop), AC-02 (AsyncAnthropic), AC-03 (tool dispatch),
AC-04 (streaming/non-streaming), AC-08 (token tracking), AC-09 (config),
AC-24 (tool errors), AC-25 (max_turns), AC-28–30 (dispatch_workflow stub).
"""

import asyncio
from dataclasses import dataclass
from unittest.mock import AsyncMock, MagicMock

import anthropic
import pytest

from chatServer.services.conversation_handler import (
    DISPATCH_WORKFLOW_RESPONSE,
    DISPATCH_WORKFLOW_TOOL,
    ConversationHandler,
    _content_to_dicts,
    _extract_text,
)

# ---------------------------------------------------------------------------
# Helpers — mock Anthropic API responses
# ---------------------------------------------------------------------------

@dataclass
class MockUsage:
    input_tokens: int = 100
    output_tokens: int = 50


@dataclass
class MockTextBlock:
    type: str = "text"
    text: str = "Hello!"


@dataclass
class MockToolUseBlock:
    type: str = "tool_use"
    id: str = "toolu_01"
    name: str = "search_gmail"
    input: dict = None

    def __post_init__(self):
        if self.input is None:
            self.input = {"query": "test"}


@dataclass
class MockResponse:
    content: list = None
    stop_reason: str = "end_turn"
    usage: MockUsage = None

    def __post_init__(self):
        if self.content is None:
            self.content = [MockTextBlock()]
        if self.usage is None:
            self.usage = MockUsage()


def _make_handler(
    mock_client=None,
    tools=None,
    tool_executors=None,
    max_turns=25,
    max_tokens=4096,
    temperature=0.7,
    timeout_seconds=120,
):
    """Create a ConversationHandler with a mocked Anthropic client."""
    if mock_client is None:
        mock_client = MagicMock()
        mock_client.messages = MagicMock()
        mock_client.messages.create = AsyncMock(
            return_value=MockResponse()
        )
    return ConversationHandler(
        client=mock_client,
        model="claude-sonnet-4-20250514",
        system_prompt="You are a test assistant.",
        tools=tools or [],
        tool_executors=tool_executors or {},
        max_turns=max_turns,
        max_tokens=max_tokens,
        temperature=temperature,
        timeout_seconds=timeout_seconds,
    )


# ---------------------------------------------------------------------------
# Non-streaming tests  (AC-01, AC-02, AC-03)
# ---------------------------------------------------------------------------

class TestRunBasic:
    @pytest.mark.asyncio
    async def test_simple_end_turn(self):
        """AC-01: Loop stops on end_turn."""
        handler = _make_handler()
        result = await handler.run([
            {"role": "user", "content": "Hello"}
        ])
        assert result.response_text == "Hello!"
        assert result.stop_reason == "end_turn"
        assert result.turn_count == 1

    @pytest.mark.asyncio
    async def test_tool_loop(self):
        """AC-03: tool_use → execute → tool_result → end_turn."""
        mock_client = MagicMock()

        # First call: tool_use
        tool_response = MockResponse(
            content=[MockToolUseBlock()],
            stop_reason="tool_use",
        )
        # Second call: end_turn with text
        final_response = MockResponse(
            content=[MockTextBlock(text="Found 3 emails.")],
            stop_reason="end_turn",
        )
        mock_client.messages.create = AsyncMock(
            side_effect=[tool_response, final_response]
        )

        tool_executor = AsyncMock(return_value="3 emails found")
        handler = _make_handler(
            mock_client=mock_client,
            tools=[{"name": "search_gmail", "description": "Search"}],
            tool_executors={"search_gmail": tool_executor},
        )

        result = await handler.run([
            {"role": "user", "content": "Search my email"}
        ])

        assert result.response_text == "Found 3 emails."
        assert result.turn_count == 2
        assert len(result.tool_calls) == 1
        assert result.tool_calls[0].tool_name == "search_gmail"
        assert result.tool_calls[0].output == "3 emails found"
        assert not result.tool_calls[0].is_error
        tool_executor.assert_awaited_once_with({"query": "test"})

    @pytest.mark.asyncio
    async def test_concurrent_tool_calls(self):
        """AC-03: Multiple tool_use blocks executed via asyncio.gather."""
        mock_client = MagicMock()

        tool1 = MockToolUseBlock(
            id="t1", name="search_gmail", input={"query": "a"}
        )
        tool2 = MockToolUseBlock(
            id="t2", name="get_tasks", input={}
        )
        tool_response = MockResponse(
            content=[tool1, tool2], stop_reason="tool_use"
        )
        final_response = MockResponse(
            content=[MockTextBlock(text="Done.")], stop_reason="end_turn"
        )
        mock_client.messages.create = AsyncMock(
            side_effect=[tool_response, final_response]
        )

        exec_gmail = AsyncMock(return_value="emails")
        exec_tasks = AsyncMock(return_value="tasks")
        handler = _make_handler(
            mock_client=mock_client,
            tool_executors={
                "search_gmail": exec_gmail,
                "get_tasks": exec_tasks,
            },
        )

        result = await handler.run([
            {"role": "user", "content": "Check everything"}
        ])

        assert len(result.tool_calls) == 2
        exec_gmail.assert_awaited_once()
        exec_tasks.assert_awaited_once()


# ---------------------------------------------------------------------------
# Token tracking tests  (AC-08)
# ---------------------------------------------------------------------------

class TestTokenTracking:
    @pytest.mark.asyncio
    async def test_single_turn_usage(self):
        handler = _make_handler()
        result = await handler.run([
            {"role": "user", "content": "Hi"}
        ])
        assert result.token_usage.input_tokens == 100
        assert result.token_usage.output_tokens == 50

    @pytest.mark.asyncio
    async def test_cumulative_usage_across_turns(self):
        mock_client = MagicMock()
        tool_resp = MockResponse(
            content=[MockToolUseBlock()],
            stop_reason="tool_use",
            usage=MockUsage(input_tokens=200, output_tokens=100),
        )
        final_resp = MockResponse(
            usage=MockUsage(input_tokens=300, output_tokens=150),
        )
        mock_client.messages.create = AsyncMock(
            side_effect=[tool_resp, final_resp]
        )

        handler = _make_handler(
            mock_client=mock_client,
            tool_executors={"search_gmail": AsyncMock(return_value="ok")},
        )
        result = await handler.run([
            {"role": "user", "content": "test"}
        ])

        assert result.token_usage.input_tokens == 500
        assert result.token_usage.output_tokens == 250

    @pytest.mark.asyncio
    async def test_cumulative_usage_property(self):
        """token_usage property accumulates across multiple run() calls."""
        handler = _make_handler()

        await handler.run([{"role": "user", "content": "1"}])
        await handler.run([{"role": "user", "content": "2"}])

        assert handler.token_usage.input_tokens == 200
        assert handler.token_usage.output_tokens == 100


# ---------------------------------------------------------------------------
# Config tests  (AC-09)
# ---------------------------------------------------------------------------

class TestConfig:
    @pytest.mark.asyncio
    async def test_respects_model_and_params(self):
        mock_client = MagicMock()
        mock_client.messages.create = AsyncMock(
            return_value=MockResponse()
        )
        handler = _make_handler(
            mock_client=mock_client,
            max_tokens=8192,
            temperature=0.3,
        )
        handler.model = "claude-opus-4-20250514"

        await handler.run([{"role": "user", "content": "test"}])

        call_kwargs = mock_client.messages.create.call_args.kwargs
        assert call_kwargs["model"] == "claude-opus-4-20250514"
        assert call_kwargs["max_tokens"] == 8192
        assert call_kwargs["temperature"] == 0.3


# ---------------------------------------------------------------------------
# Max turns tests  (AC-25)
# ---------------------------------------------------------------------------

class TestMaxTurns:
    @pytest.mark.asyncio
    async def test_max_turns_reached(self):
        mock_client = MagicMock()
        # Always return tool_use — never end_turn
        mock_client.messages.create = AsyncMock(
            return_value=MockResponse(
                content=[MockToolUseBlock()],
                stop_reason="tool_use",
            )
        )
        handler = _make_handler(
            mock_client=mock_client,
            max_turns=3,
            tool_executors={"search_gmail": AsyncMock(return_value="ok")},
        )

        result = await handler.run([
            {"role": "user", "content": "loop forever"}
        ])

        assert result.stop_reason == "max_turns"
        assert result.turn_count == 3
        assert "[Max tool iterations reached]" in result.response_text


# ---------------------------------------------------------------------------
# Tool error tests  (AC-24)
# ---------------------------------------------------------------------------

class TestToolErrors:
    @pytest.mark.asyncio
    async def test_tool_error_continues_loop(self):
        """AC-24: Tool errors don't crash the handler."""
        mock_client = MagicMock()
        tool_resp = MockResponse(
            content=[MockToolUseBlock()],
            stop_reason="tool_use",
        )
        final_resp = MockResponse(
            content=[MockTextBlock(text="I see the error.")],
            stop_reason="end_turn",
        )
        mock_client.messages.create = AsyncMock(
            side_effect=[tool_resp, final_resp]
        )

        failing_executor = AsyncMock(
            side_effect=RuntimeError("connection failed")
        )
        handler = _make_handler(
            mock_client=mock_client,
            tool_executors={"search_gmail": failing_executor},
        )

        result = await handler.run([
            {"role": "user", "content": "search"}
        ])

        assert result.response_text == "I see the error."
        assert len(result.tool_calls) == 1
        assert result.tool_calls[0].is_error
        assert "connection failed" in result.tool_calls[0].output

    @pytest.mark.asyncio
    async def test_unknown_tool_returns_error(self):
        mock_client = MagicMock()
        unknown_tool = MockToolUseBlock(name="nonexistent_tool")
        tool_resp = MockResponse(
            content=[unknown_tool], stop_reason="tool_use"
        )
        final_resp = MockResponse(stop_reason="end_turn")
        mock_client.messages.create = AsyncMock(
            side_effect=[tool_resp, final_resp]
        )

        handler = _make_handler(mock_client=mock_client)

        result = await handler.run([
            {"role": "user", "content": "test"}
        ])

        assert len(result.tool_calls) == 1
        assert result.tool_calls[0].is_error
        assert "Unknown tool" in result.tool_calls[0].output


# ---------------------------------------------------------------------------
# dispatch_workflow stub tests  (AC-28, AC-29, AC-30)
# ---------------------------------------------------------------------------

class TestDispatchWorkflow:
    def test_stub_tool_in_tools_list(self):
        """AC-30: dispatch_workflow is in handler tools."""
        handler = _make_handler()
        tool_names = [t["name"] for t in handler.tools]
        assert "dispatch_workflow" in tool_names

    def test_stub_schema(self):
        """AC-28: dispatch_workflow has correct schema."""
        assert DISPATCH_WORKFLOW_TOOL["name"] == "dispatch_workflow"
        schema = DISPATCH_WORKFLOW_TOOL["input_schema"]
        assert "workflow_name" in schema["properties"]
        assert "workflow_name" in schema["required"]

    @pytest.mark.asyncio
    async def test_stub_response(self):
        """AC-29: stub returns fallback message."""
        mock_client = MagicMock()
        tool_block = MockToolUseBlock(
            name="dispatch_workflow",
            input={"workflow_name": "email_triage"},
        )
        tool_resp = MockResponse(
            content=[tool_block], stop_reason="tool_use"
        )
        final_resp = MockResponse(stop_reason="end_turn")
        mock_client.messages.create = AsyncMock(
            side_effect=[tool_resp, final_resp]
        )

        handler = _make_handler(mock_client=mock_client)
        result = await handler.run([
            {"role": "user", "content": "triage my email"}
        ])

        assert len(result.tool_calls) == 1
        assert result.tool_calls[0].output == DISPATCH_WORKFLOW_RESPONSE
        assert not result.tool_calls[0].is_error


# ---------------------------------------------------------------------------
# Timeout tests  (AC-26)
# ---------------------------------------------------------------------------

class TestTimeout:
    @pytest.mark.asyncio
    async def test_timeout_returns_result(self):
        mock_client = MagicMock()

        async def slow_create(**kwargs):
            await asyncio.sleep(10)
            return MockResponse()

        mock_client.messages.create = slow_create

        handler = _make_handler(
            mock_client=mock_client, timeout_seconds=0.1
        )

        result = await handler.run([
            {"role": "user", "content": "test"}
        ])

        assert result.stop_reason == "timeout"
        assert "[Request timed out]" in result.response_text


# ---------------------------------------------------------------------------
# API error tests  (AC-23)
# ---------------------------------------------------------------------------

def _make_api_status_error(status_code, headers=None):
    """Create a mock anthropic.APIStatusError."""
    import httpx

    mock_response = httpx.Response(
        status_code=status_code,
        headers=headers or {},
        request=httpx.Request("POST", "https://api.anthropic.com/v1/messages"),
    )
    return anthropic.APIStatusError(
        message=f"Error {status_code}",
        response=mock_response,
        body={"error": {"message": f"Error {status_code}"}},
    )


class TestAPIErrors:
    @pytest.mark.asyncio
    async def test_rate_limit_429(self):
        """AC-23: 429 returns rate limit message with retry_after."""
        mock_client = MagicMock()
        mock_client.messages.create = AsyncMock(
            side_effect=_make_api_status_error(429, {"retry-after": "30"})
        )
        handler = _make_handler(mock_client=mock_client)
        handler.session_id = "test-session"
        handler.user_id = "test-user"

        result = await handler.run([{"role": "user", "content": "test"}])

        assert result.stop_reason == "api_error_429"
        assert "retry after 30s" in result.response_text

    @pytest.mark.asyncio
    async def test_overloaded_529(self):
        """AC-23: 529 returns user-friendly overloaded message."""
        mock_client = MagicMock()
        mock_client.messages.create = AsyncMock(
            side_effect=_make_api_status_error(529)
        )
        handler = _make_handler(mock_client=mock_client)

        result = await handler.run([{"role": "user", "content": "test"}])

        assert result.stop_reason == "api_error_529"
        assert "overloaded" in result.response_text

    @pytest.mark.asyncio
    async def test_auth_error_401(self):
        """AC-23: 401 returns auth error message."""
        mock_client = MagicMock()
        mock_client.messages.create = AsyncMock(
            side_effect=_make_api_status_error(401)
        )
        handler = _make_handler(mock_client=mock_client)

        result = await handler.run([{"role": "user", "content": "test"}])

        assert result.stop_reason == "api_error_401"
        assert "Authentication error" in result.response_text

    @pytest.mark.asyncio
    async def test_generic_api_error(self):
        """AC-23: Other status codes return generic API error."""
        mock_client = MagicMock()
        mock_client.messages.create = AsyncMock(
            side_effect=_make_api_status_error(500)
        )
        handler = _make_handler(mock_client=mock_client)

        result = await handler.run([{"role": "user", "content": "test"}])

        assert result.stop_reason == "api_error_500"
        assert "API error: 500" in result.response_text

    @pytest.mark.asyncio
    async def test_api_error_preserves_prior_tool_calls(self):
        """API error after a tool turn preserves earlier tool call records."""
        mock_client = MagicMock()
        tool_resp = MockResponse(
            content=[MockToolUseBlock()],
            stop_reason="tool_use",
        )
        mock_client.messages.create = AsyncMock(
            side_effect=[tool_resp, _make_api_status_error(529)]
        )

        handler = _make_handler(
            mock_client=mock_client,
            tool_executors={"search_gmail": AsyncMock(return_value="ok")},
        )

        result = await handler.run([{"role": "user", "content": "test"}])

        assert result.stop_reason == "api_error_529"
        assert len(result.tool_calls) == 1
        assert result.turn_count == 2


# ---------------------------------------------------------------------------
# Context logging tests  (AC-27)
# ---------------------------------------------------------------------------

class TestContextLogging:
    def test_session_id_and_user_id_stored(self):
        """AC-27: session_id and user_id are stored on the handler."""
        handler = _make_handler()
        handler.session_id = "sess-123"
        handler.user_id = "user-456"
        assert handler.session_id == "sess-123"
        assert handler.user_id == "user-456"

    def test_constructor_accepts_context(self):
        """AC-27: Constructor accepts session_id and user_id."""
        mock_client = MagicMock()
        mock_client.messages = MagicMock()
        mock_client.messages.create = AsyncMock(return_value=MockResponse())
        handler = ConversationHandler(
            client=mock_client,
            model="test",
            system_prompt="test",
            tools=[],
            tool_executors={},
            session_id="s1",
            user_id="u1",
        )
        assert handler.session_id == "s1"
        assert handler.user_id == "u1"


# ---------------------------------------------------------------------------
# Helper function tests
# ---------------------------------------------------------------------------

class TestHelpers:
    def test_extract_text(self):
        content = [MockTextBlock(text="Hello "), MockTextBlock(text="world")]
        assert _extract_text(content) == "Hello world"

    def test_extract_text_skips_non_text(self):
        content = [MockToolUseBlock(), MockTextBlock(text="Hi")]
        assert _extract_text(content) == "Hi"

    def test_content_to_dicts_text(self):
        content = [MockTextBlock(text="test")]
        result = _content_to_dicts(content)
        assert result == [{"type": "text", "text": "test"}]

    def test_content_to_dicts_tool_use(self):
        content = [MockToolUseBlock(
            id="t1", name="search", input={"q": "x"}
        )]
        result = _content_to_dicts(content)
        assert result == [{
            "type": "tool_use",
            "id": "t1",
            "name": "search",
            "input": {"q": "x"},
        }]
