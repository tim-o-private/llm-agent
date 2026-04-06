"""Tests for AnthropicEngine — workflow step execution via Anthropic API."""

from dataclasses import dataclass
from unittest.mock import AsyncMock, MagicMock

import pytest

from chatServer.workflows.engine import AnthropicEngine


@dataclass
class MockUsage:
    input_tokens: int = 100
    output_tokens: int = 50


@dataclass
class MockTextBlock:
    type: str = "text"
    text: str = "Step output text."


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


def _make_engine(mock_client=None, tool_schemas=None, tool_executors=None):
    if mock_client is None:
        mock_client = MagicMock()
        mock_client.messages = MagicMock()
        mock_client.messages.create = AsyncMock(return_value=MockResponse())
    return AnthropicEngine(
        client=mock_client,
        tool_schemas=tool_schemas or [],
        tool_executors=tool_executors or {},
        user_id="test-user",
    )


class TestRunSimplePrompt:
    @pytest.mark.asyncio
    async def test_returns_output(self):
        engine = _make_engine()
        result = await engine.run(prompt="Do something", tools=[])
        assert result.output == "Step output text."
        assert result.tool_calls == []

    @pytest.mark.asyncio
    async def test_tracks_token_usage(self):
        engine = _make_engine()
        result = await engine.run(prompt="Do something", tools=[])
        assert result.token_usage.input_tokens == 100
        assert result.token_usage.output_tokens == 50


class TestRunWithTools:
    @pytest.mark.asyncio
    async def test_tool_call_dispatched(self):
        mock_client = MagicMock()
        # First call: tool_use, second call: end_turn
        tool_response = MockResponse(
            content=[
                MockTextBlock(text="I'll search"),
                MockToolUseBlock(),
            ],
            stop_reason="tool_use",
        )
        final_response = MockResponse(
            content=[MockTextBlock(text="Found 3 emails.")],
            stop_reason="end_turn",
        )
        mock_client.messages = MagicMock()
        mock_client.messages.create = AsyncMock(
            side_effect=[tool_response, final_response]
        )

        mock_executor = AsyncMock(return_value="3 emails found")
        engine = _make_engine(
            mock_client=mock_client,
            tool_schemas=[{"name": "search_gmail", "description": "", "input_schema": {}}],
            tool_executors={"search_gmail": mock_executor},
        )

        result = await engine.run(
            prompt="Search emails", tools=["search_gmail"]
        )
        assert result.output == "Found 3 emails."
        assert len(result.tool_calls) == 1
        assert result.tool_calls[0].tool_name == "search_gmail"
        mock_executor.assert_called_once_with({"query": "test"})

    @pytest.mark.asyncio
    async def test_filters_tools_to_step(self):
        mock_client = MagicMock()
        mock_client.messages = MagicMock()
        mock_client.messages.create = AsyncMock(return_value=MockResponse())

        engine = _make_engine(
            mock_client=mock_client,
            tool_schemas=[
                {"name": "search_gmail", "description": "", "input_schema": {}},
                {"name": "compose_email", "description": "", "input_schema": {}},
            ],
        )

        await engine.run(prompt="Test", tools=["search_gmail"])

        # Verify only search_gmail was passed
        call_kwargs = mock_client.messages.create.call_args.kwargs
        assert len(call_kwargs["tools"]) == 1
        assert call_kwargs["tools"][0]["name"] == "search_gmail"


class TestRunMaxIterations:
    @pytest.mark.asyncio
    async def test_stops_after_max_iterations(self):
        mock_client = MagicMock()
        # Always returns tool_use → never end_turn
        tool_response = MockResponse(
            content=[MockToolUseBlock()],
            stop_reason="tool_use",
        )
        mock_client.messages = MagicMock()
        mock_client.messages.create = AsyncMock(return_value=tool_response)

        mock_executor = AsyncMock(return_value="ok")
        engine = _make_engine(
            mock_client=mock_client,
            tool_schemas=[{"name": "search_gmail", "description": "", "input_schema": {}}],
            tool_executors={"search_gmail": mock_executor},
        )

        result = await engine.run(
            prompt="Loop forever", tools=["search_gmail"]
        )
        assert "Max tool iterations" in result.output
        # Should have been called 15 times (max iterations)
        assert mock_client.messages.create.call_count == 15


class TestRunToolErrors:
    @pytest.mark.asyncio
    async def test_unknown_tool(self):
        mock_client = MagicMock()
        tool_response = MockResponse(
            content=[MockToolUseBlock(name="unknown_tool")],
            stop_reason="tool_use",
        )
        final_response = MockResponse(
            content=[MockTextBlock(text="Handled error.")],
            stop_reason="end_turn",
        )
        mock_client.messages = MagicMock()
        mock_client.messages.create = AsyncMock(
            side_effect=[tool_response, final_response]
        )

        engine = _make_engine(mock_client=mock_client)
        result = await engine.run(prompt="Test", tools=[])
        assert len(result.tool_calls) == 1
        assert result.tool_calls[0].is_error is True
        assert "Unknown tool" in result.tool_calls[0].output

    @pytest.mark.asyncio
    async def test_tool_exception(self):
        mock_client = MagicMock()
        tool_response = MockResponse(
            content=[MockToolUseBlock()],
            stop_reason="tool_use",
        )
        final_response = MockResponse(
            content=[MockTextBlock(text="Recovered.")],
            stop_reason="end_turn",
        )
        mock_client.messages = MagicMock()
        mock_client.messages.create = AsyncMock(
            side_effect=[tool_response, final_response]
        )

        failing_executor = AsyncMock(side_effect=RuntimeError("connection failed"))
        engine = _make_engine(
            mock_client=mock_client,
            tool_schemas=[{"name": "search_gmail", "description": "", "input_schema": {}}],
            tool_executors={"search_gmail": failing_executor},
        )

        result = await engine.run(
            prompt="Test", tools=["search_gmail"]
        )
        assert result.tool_calls[0].is_error is True
        assert "connection failed" in result.tool_calls[0].output


class TestRunModelConfig:
    @pytest.mark.asyncio
    async def test_custom_model_params(self):
        mock_client = MagicMock()
        mock_client.messages = MagicMock()
        mock_client.messages.create = AsyncMock(return_value=MockResponse())

        engine = _make_engine(mock_client=mock_client)
        await engine.run(
            prompt="Test",
            tools=[],
            model="claude-haiku-3-5",
            max_tokens=2048,
            temperature=0.2,
        )

        call_kwargs = mock_client.messages.create.call_args.kwargs
        assert call_kwargs["model"] == "claude-haiku-3-5"
        assert call_kwargs["max_tokens"] == 2048
        assert call_kwargs["temperature"] == 0.2
