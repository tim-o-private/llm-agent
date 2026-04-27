"""Tests for OpenAIEngine — workflow step execution via OpenAI Chat Completions API."""

import json
from dataclasses import dataclass, field
from unittest.mock import AsyncMock, MagicMock

import pytest

from chatServer.workflows.openai_engine import OpenAIEngine, _openai_tools


# ---------------------------------------------------------------------------
# Mock helpers — mirror the OpenAI SDK response shape
# ---------------------------------------------------------------------------

@dataclass
class MockUsage:
    prompt_tokens: int = 100
    completion_tokens: int = 50


@dataclass
class MockFunctionCall:
    name: str = "search_gmail"
    arguments: str = '{"query": "test"}'


@dataclass
class MockToolCall:
    id: str = "call_01"
    type: str = "function"
    function: MockFunctionCall = field(default_factory=MockFunctionCall)


@dataclass
class MockMessage:
    content: str = "Step output text."
    tool_calls: list | None = None


@dataclass
class MockChoice:
    message: MockMessage = field(default_factory=MockMessage)
    finish_reason: str = "stop"


@dataclass
class MockChatResponse:
    choices: list[MockChoice] = field(default_factory=lambda: [MockChoice()])
    usage: MockUsage = field(default_factory=MockUsage)


def _make_openai_client(response=None, side_effect=None):
    client = MagicMock()
    client.chat = MagicMock()
    client.chat.completions = MagicMock()
    if side_effect:
        client.chat.completions.create = AsyncMock(side_effect=side_effect)
    else:
        client.chat.completions.create = AsyncMock(
            return_value=response or MockChatResponse()
        )
    return client


def _make_engine(client=None, tool_schemas=None, tool_executors=None):
    if client is None:
        client = _make_openai_client()
    return OpenAIEngine(
        client=client,
        tool_schemas=tool_schemas or [],
        tool_executors=tool_executors or {},
        user_id="test-user",
    )


# ---------------------------------------------------------------------------
# _openai_tools schema conversion
# ---------------------------------------------------------------------------

class TestOpenaiToolsConversion:
    def test_converts_anthropic_style_schema(self):
        schemas = [
            {
                "name": "search_gmail",
                "description": "Search emails",
                "input_schema": {"type": "object", "properties": {"q": {"type": "string"}}},
            }
        ]
        result = _openai_tools(schemas)
        assert len(result) == 1
        assert result[0]["type"] == "function"
        assert result[0]["function"]["name"] == "search_gmail"
        assert result[0]["function"]["description"] == "Search emails"
        assert result[0]["function"]["parameters"]["type"] == "object"

    def test_falls_back_to_parameters_key(self):
        schemas = [
            {
                "name": "tool_a",
                "parameters": {"type": "object", "properties": {}},
            }
        ]
        result = _openai_tools(schemas)
        assert result[0]["function"]["parameters"]["type"] == "object"

    def test_empty_list(self):
        assert _openai_tools([]) == []

    def test_missing_description_defaults_empty(self):
        schemas = [{"name": "tool_x"}]
        result = _openai_tools(schemas)
        assert result[0]["function"]["description"] == ""


# ---------------------------------------------------------------------------
# Simple prompt (no tools)
# ---------------------------------------------------------------------------

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

    @pytest.mark.asyncio
    async def test_system_prompt_passed(self):
        client = _make_openai_client()
        engine = _make_engine(client=client)
        await engine.run(prompt="Hello", tools=[], system_prompt="Be brief.")

        call_kwargs = client.chat.completions.create.call_args.kwargs
        messages = call_kwargs["messages"]
        assert messages[0] == {"role": "system", "content": "Be brief."}
        assert messages[1] == {"role": "user", "content": "Hello"}

    @pytest.mark.asyncio
    async def test_no_system_prompt(self):
        client = _make_openai_client()
        engine = _make_engine(client=client)
        await engine.run(prompt="Hello", tools=[])

        call_kwargs = client.chat.completions.create.call_args.kwargs
        messages = call_kwargs["messages"]
        assert len(messages) == 1
        assert messages[0]["role"] == "user"


# ---------------------------------------------------------------------------
# Tool loop
# ---------------------------------------------------------------------------

class TestRunWithTools:
    @pytest.mark.asyncio
    async def test_tool_call_dispatched(self):
        tool_response = MockChatResponse(
            choices=[MockChoice(
                message=MockMessage(
                    content="I'll search",
                    tool_calls=[MockToolCall()],
                ),
                finish_reason="tool_calls",
            )]
        )
        final_response = MockChatResponse(
            choices=[MockChoice(
                message=MockMessage(content="Found 3 emails."),
                finish_reason="stop",
            )]
        )
        client = _make_openai_client(side_effect=[tool_response, final_response])
        mock_executor = AsyncMock(return_value="3 emails found")

        engine = _make_engine(
            client=client,
            tool_schemas=[{"name": "search_gmail", "description": "", "input_schema": {}}],
            tool_executors={"search_gmail": mock_executor},
        )
        result = await engine.run(prompt="Search emails", tools=["search_gmail"])

        assert result.output == "Found 3 emails."
        assert len(result.tool_calls) == 1
        assert result.tool_calls[0].tool_name == "search_gmail"
        mock_executor.assert_called_once_with({"query": "test"})

    @pytest.mark.asyncio
    async def test_filters_tools_to_step(self):
        client = _make_openai_client()
        engine = _make_engine(
            client=client,
            tool_schemas=[
                {"name": "search_gmail", "description": "", "input_schema": {}},
                {"name": "compose_email", "description": "", "input_schema": {}},
            ],
        )
        await engine.run(prompt="Test", tools=["search_gmail"])

        call_kwargs = client.chat.completions.create.call_args.kwargs
        assert len(call_kwargs["tools"]) == 1
        assert call_kwargs["tools"][0]["function"]["name"] == "search_gmail"

    @pytest.mark.asyncio
    async def test_no_tools_passes_none(self):
        client = _make_openai_client()
        engine = _make_engine(client=client)
        await engine.run(prompt="Test", tools=[])

        call_kwargs = client.chat.completions.create.call_args.kwargs
        assert call_kwargs["tools"] is None
        assert call_kwargs["tool_choice"] is None


# ---------------------------------------------------------------------------
# Iteration cap
# ---------------------------------------------------------------------------

class TestRunMaxIterations:
    @pytest.mark.asyncio
    async def test_stops_after_max_iterations(self):
        tool_response = MockChatResponse(
            choices=[MockChoice(
                message=MockMessage(
                    content="",
                    tool_calls=[MockToolCall()],
                ),
                finish_reason="tool_calls",
            )]
        )
        client = _make_openai_client(response=tool_response)
        mock_executor = AsyncMock(return_value="ok")

        engine = _make_engine(
            client=client,
            tool_schemas=[{"name": "search_gmail", "description": "", "input_schema": {}}],
            tool_executors={"search_gmail": mock_executor},
        )
        result = await engine.run(prompt="Loop forever", tools=["search_gmail"])

        assert "Max tool iterations" in result.output
        assert client.chat.completions.create.call_count == 15


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------

class TestRunErrors:
    @pytest.mark.asyncio
    async def test_api_error_returns_gracefully(self):
        exc = Exception("rate limit")
        exc.status_code = 429
        client = _make_openai_client(side_effect=exc)
        engine = _make_engine(client=client)

        result = await engine.run(prompt="Test", tools=[])
        assert "API error" in result.output
        assert "429" in result.output

    @pytest.mark.asyncio
    async def test_unknown_tool(self):
        tool_response = MockChatResponse(
            choices=[MockChoice(
                message=MockMessage(
                    content="",
                    tool_calls=[MockToolCall(function=MockFunctionCall(name="unknown_tool"))],
                ),
                finish_reason="tool_calls",
            )]
        )
        final_response = MockChatResponse(
            choices=[MockChoice(
                message=MockMessage(content="Handled."),
                finish_reason="stop",
            )]
        )
        client = _make_openai_client(side_effect=[tool_response, final_response])
        engine = _make_engine(client=client)

        result = await engine.run(prompt="Test", tools=[])
        assert len(result.tool_calls) == 1
        assert result.tool_calls[0].is_error is True
        assert "Unknown tool" in result.tool_calls[0].output

    @pytest.mark.asyncio
    async def test_tool_exception(self):
        tool_response = MockChatResponse(
            choices=[MockChoice(
                message=MockMessage(
                    content="",
                    tool_calls=[MockToolCall()],
                ),
                finish_reason="tool_calls",
            )]
        )
        final_response = MockChatResponse(
            choices=[MockChoice(
                message=MockMessage(content="Recovered."),
                finish_reason="stop",
            )]
        )
        client = _make_openai_client(side_effect=[tool_response, final_response])
        failing_executor = AsyncMock(side_effect=RuntimeError("connection failed"))

        engine = _make_engine(
            client=client,
            tool_schemas=[{"name": "search_gmail", "description": "", "input_schema": {}}],
            tool_executors={"search_gmail": failing_executor},
        )
        result = await engine.run(prompt="Test", tools=["search_gmail"])

        assert result.tool_calls[0].is_error is True
        assert "connection failed" in result.tool_calls[0].output

    @pytest.mark.asyncio
    async def test_malformed_tool_arguments(self):
        tool_response = MockChatResponse(
            choices=[MockChoice(
                message=MockMessage(
                    content="",
                    tool_calls=[MockToolCall(
                        function=MockFunctionCall(arguments="not valid json"),
                    )],
                ),
                finish_reason="tool_calls",
            )]
        )
        final_response = MockChatResponse(
            choices=[MockChoice(
                message=MockMessage(content="Done."),
                finish_reason="stop",
            )]
        )
        client = _make_openai_client(side_effect=[tool_response, final_response])
        mock_executor = AsyncMock(return_value="ok")

        engine = _make_engine(
            client=client,
            tool_schemas=[{"name": "search_gmail", "description": "", "input_schema": {}}],
            tool_executors={"search_gmail": mock_executor},
        )
        result = await engine.run(prompt="Test", tools=["search_gmail"])

        assert result.tool_calls[0].input == {"raw": "not valid json"}
        mock_executor.assert_called_once_with({"raw": "not valid json"})

    @pytest.mark.asyncio
    async def test_tool_returns_none(self):
        tool_response = MockChatResponse(
            choices=[MockChoice(
                message=MockMessage(
                    content="",
                    tool_calls=[MockToolCall()],
                ),
                finish_reason="tool_calls",
            )]
        )
        final_response = MockChatResponse(
            choices=[MockChoice(
                message=MockMessage(content="Done."),
                finish_reason="stop",
            )]
        )
        client = _make_openai_client(side_effect=[tool_response, final_response])
        mock_executor = AsyncMock(return_value=None)

        engine = _make_engine(
            client=client,
            tool_schemas=[{"name": "search_gmail", "description": "", "input_schema": {}}],
            tool_executors={"search_gmail": mock_executor},
        )
        result = await engine.run(prompt="Test", tools=["search_gmail"])

        assert result.tool_calls[0].output == "(No output)"
        assert result.tool_calls[0].is_error is False


# ---------------------------------------------------------------------------
# Unexpected finish reason
# ---------------------------------------------------------------------------

class TestUnexpectedFinish:
    @pytest.mark.asyncio
    async def test_unexpected_finish_reason(self):
        response = MockChatResponse(
            choices=[MockChoice(
                message=MockMessage(content=""),
                finish_reason="content_filter",
            )]
        )
        client = _make_openai_client(response=response)
        engine = _make_engine(client=client)

        result = await engine.run(prompt="Test", tools=[])
        assert "Unexpected finish" in result.output

    @pytest.mark.asyncio
    async def test_length_finish_returns_partial(self):
        response = MockChatResponse(
            choices=[MockChoice(
                message=MockMessage(content="Partial output..."),
                finish_reason="length",
            )]
        )
        client = _make_openai_client(response=response)
        engine = _make_engine(client=client)

        result = await engine.run(prompt="Test", tools=[])
        assert result.output == "Partial output..."


# ---------------------------------------------------------------------------
# Model config pass-through
# ---------------------------------------------------------------------------

class TestRunModelConfig:
    @pytest.mark.asyncio
    async def test_custom_model_params(self):
        client = _make_openai_client()
        engine = _make_engine(client=client)
        await engine.run(
            prompt="Test",
            tools=[],
            model="gpt-4o",
            max_tokens=2048,
            temperature=0.2,
        )

        call_kwargs = client.chat.completions.create.call_args.kwargs
        assert call_kwargs["model"] == "gpt-4o"
        assert call_kwargs["max_tokens"] == 2048
        assert call_kwargs["temperature"] == 0.2


# ---------------------------------------------------------------------------
# Token accumulation across iterations
# ---------------------------------------------------------------------------

class TestTokenAccumulation:
    @pytest.mark.asyncio
    async def test_tokens_accumulate_across_tool_loop(self):
        tool_response = MockChatResponse(
            choices=[MockChoice(
                message=MockMessage(content="", tool_calls=[MockToolCall()]),
                finish_reason="tool_calls",
            )],
            usage=MockUsage(prompt_tokens=100, completion_tokens=20),
        )
        final_response = MockChatResponse(
            choices=[MockChoice(
                message=MockMessage(content="Done."),
                finish_reason="stop",
            )],
            usage=MockUsage(prompt_tokens=150, completion_tokens=30),
        )
        client = _make_openai_client(side_effect=[tool_response, final_response])
        mock_executor = AsyncMock(return_value="ok")

        engine = _make_engine(
            client=client,
            tool_schemas=[{"name": "search_gmail", "description": "", "input_schema": {}}],
            tool_executors={"search_gmail": mock_executor},
        )
        result = await engine.run(prompt="Test", tools=["search_gmail"])

        assert result.token_usage.input_tokens == 250
        assert result.token_usage.output_tokens == 50
