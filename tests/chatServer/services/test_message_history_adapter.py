"""Tests for MessageHistoryAdapter — message format conversion & persistence.

Covers AC-06 (load), AC-07 modified (save in Anthropic format), and AC-34
(comprehensive format variant fixtures based on real DB rows).
"""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from chatServer.services.message_history_adapter import (
    MessageHistoryAdapter,
    _convert_message,
    _merge_tool_results,
    _normalize_content,
)

# ---------------------------------------------------------------------------
# Realistic LangChain message fixtures  (AC-34)
# ---------------------------------------------------------------------------

HUMAN_MESSAGE = {
    "type": "human",
    "data": {
        "content": "What's on my calendar today?",
        "type": "HumanMessage",
        "additional_kwargs": {},
        "response_metadata": {},
        "name": None,
        "id": None,
    },
}

AI_MESSAGE_TEXT = {
    "type": "ai",
    "data": {
        "content": "Let me check your calendar.",
        "type": "AIMessage",
        "additional_kwargs": {},
        "response_metadata": {"model": "claude-sonnet-4-20250514"},
        "tool_calls": [],
        "name": None,
        "id": "msg_abc123",
    },
}

AI_MESSAGE_WITH_TOOL_CALLS = {
    "type": "ai",
    "data": {
        "content": "",
        "type": "AIMessage",
        "tool_calls": [
            {
                "name": "search_gmail",
                "args": {"query": "invoice", "max_results": 5},
                "id": "toolu_01XYZ",
            }
        ],
        "additional_kwargs": {},
        "response_metadata": {},
        "name": None,
        "id": "msg_def456",
    },
}

AI_MESSAGE_CHUNK_WITH_ADDITIONAL_KWARGS = {
    "type": "ai",
    "data": {
        "content": "Looking at your emails...",
        "type": "AIMessageChunk",
        "additional_kwargs": {
            "tool_calls": [
                {
                    "name": "get_gmail",
                    "args": {"message_id": "abc123"},
                    "id": "toolu_02ABC",
                }
            ]
        },
        "tool_calls": [],
        "response_metadata": {},
    },
}

AI_MESSAGE_CONTENT_BLOCKS = {
    "type": "ai",
    "data": {
        "content": [
            {"type": "text", "text": "Here's what I found:"},
            {"type": "text", "text": " 3 new emails."},
        ],
        "type": "AIMessage",
        "tool_calls": [],
        "additional_kwargs": {},
    },
}

TOOL_MESSAGE = {
    "type": "tool",
    "data": {
        "content": "Found 3 emails matching 'invoice'.",
        "type": "ToolMessage",
        "tool_call_id": "toolu_01XYZ",
        "name": "search_gmail",
        "additional_kwargs": {},
    },
}

ANTHROPIC_NATIVE_USER = {
    "_format": "anthropic",
    "role": "user",
    "content": "Hello from the new handler!",
}

ANTHROPIC_NATIVE_ASSISTANT = {
    "_format": "anthropic",
    "role": "assistant",
    "content": [
        {"type": "text", "text": "Hi there!"},
        {
            "type": "tool_use",
            "id": "toolu_03NEW",
            "name": "get_tasks",
            "input": {},
        },
    ],
}


# ---------------------------------------------------------------------------
# _convert_message tests  (AC-06, AC-34)
# ---------------------------------------------------------------------------

class TestConvertMessage:
    def test_human_message(self):
        result = _convert_message(HUMAN_MESSAGE)
        assert result == {
            "role": "user",
            "content": "What's on my calendar today?",
        }

    def test_ai_message_text_only(self):
        result = _convert_message(AI_MESSAGE_TEXT)
        assert result == {
            "role": "assistant",
            "content": "Let me check your calendar.",
        }

    def test_ai_message_with_tool_calls(self):
        result = _convert_message(AI_MESSAGE_WITH_TOOL_CALLS)
        assert result["role"] == "assistant"
        assert isinstance(result["content"], list)
        # No text block (content was empty)
        tool_block = result["content"][0]
        assert tool_block["type"] == "tool_use"
        assert tool_block["name"] == "search_gmail"
        assert tool_block["id"] == "toolu_01XYZ"
        assert tool_block["input"] == {
            "query": "invoice",
            "max_results": 5,
        }

    def test_ai_message_chunk_additional_kwargs(self):
        result = _convert_message(AI_MESSAGE_CHUNK_WITH_ADDITIONAL_KWARGS)
        assert result["role"] == "assistant"
        blocks = result["content"]
        # Should have text + tool_use
        assert len(blocks) == 2
        assert blocks[0] == {
            "type": "text",
            "text": "Looking at your emails...",
        }
        assert blocks[1]["type"] == "tool_use"
        assert blocks[1]["name"] == "get_gmail"

    def test_ai_message_content_block_list(self):
        result = _convert_message(AI_MESSAGE_CONTENT_BLOCKS)
        assert result["role"] == "assistant"
        assert result["content"] == "Here's what I found: 3 new emails."

    def test_tool_message(self):
        result = _convert_message(TOOL_MESSAGE)
        assert result["role"] == "user"
        assert isinstance(result["content"], list)
        tr = result["content"][0]
        assert tr["type"] == "tool_result"
        assert tr["tool_use_id"] == "toolu_01XYZ"
        assert tr["content"] == "Found 3 emails matching 'invoice'."

    def test_anthropic_native_user(self):
        result = _convert_message(ANTHROPIC_NATIVE_USER)
        assert result == {
            "role": "user",
            "content": "Hello from the new handler!",
        }
        assert "_format" not in result

    def test_anthropic_native_assistant(self):
        result = _convert_message(ANTHROPIC_NATIVE_ASSISTANT)
        assert result["role"] == "assistant"
        assert len(result["content"]) == 2
        assert "_format" not in result

    def test_unknown_type_returns_none(self):
        result = _convert_message({"type": "system", "data": {}})
        assert result is None


# ---------------------------------------------------------------------------
# _normalize_content tests
# ---------------------------------------------------------------------------

class TestNormalizeContent:
    def test_string(self):
        assert _normalize_content("hello") == "hello"

    def test_content_block_list(self):
        blocks = [
            {"type": "text", "text": "part1"},
            {"type": "text", "text": "part2"},
        ]
        assert _normalize_content(blocks) == "part1part2"

    def test_mixed_block_types(self):
        blocks = [
            {"type": "text", "text": "text"},
            {"type": "tool_use", "id": "t1"},
        ]
        assert _normalize_content(blocks) == "text"

    def test_empty_string(self):
        assert _normalize_content("") == ""

    def test_none(self):
        assert _normalize_content(None) == ""

    def test_list_of_strings(self):
        assert _normalize_content(["a", "b"]) == "ab"


# ---------------------------------------------------------------------------
# _merge_tool_results tests
# ---------------------------------------------------------------------------

class TestMergeToolResults:
    def test_no_merging_needed(self):
        msgs = [
            {"role": "user", "content": "hi"},
            {"role": "assistant", "content": "hello"},
        ]
        assert _merge_tool_results(msgs) == msgs

    def test_merge_consecutive_tool_results(self):
        msgs = [
            {"role": "assistant", "content": [
                {"type": "tool_use", "id": "t1", "name": "a", "input": {}},
                {"type": "tool_use", "id": "t2", "name": "b", "input": {}},
            ]},
            {"role": "user", "content": [
                {"type": "tool_result", "tool_use_id": "t1", "content": "r1"}
            ]},
            {"role": "user", "content": [
                {"type": "tool_result", "tool_use_id": "t2", "content": "r2"}
            ]},
        ]
        merged = _merge_tool_results(msgs)
        assert len(merged) == 2  # assistant + merged user
        user_msg = merged[1]
        assert len(user_msg["content"]) == 2
        assert user_msg["content"][0]["tool_use_id"] == "t1"
        assert user_msg["content"][1]["tool_use_id"] == "t2"

    def test_empty_list(self):
        assert _merge_tool_results([]) == []

    def test_text_user_messages_not_merged(self):
        msgs = [
            {"role": "user", "content": "first"},
            {"role": "user", "content": "second"},
        ]
        assert _merge_tool_results(msgs) == msgs


# ---------------------------------------------------------------------------
# load_history tests  (AC-06)
# ---------------------------------------------------------------------------

class TestLoadHistory:
    @pytest.mark.asyncio
    async def test_loads_and_converts_messages(self):
        rows = [
            (HUMAN_MESSAGE,),
            (AI_MESSAGE_TEXT,),
        ]
        mock_cursor = AsyncMock()
        mock_cursor.fetchall = AsyncMock(return_value=rows)
        mock_cursor.__aenter__ = AsyncMock(return_value=mock_cursor)
        mock_cursor.__aexit__ = AsyncMock(return_value=False)

        mock_conn = MagicMock()
        mock_conn.cursor = MagicMock(return_value=mock_cursor)

        result = await MessageHistoryAdapter.load_history(
            "session-1", mock_conn, limit=100
        )
        assert len(result) == 2
        assert result[0]["role"] == "user"
        assert result[1]["role"] == "assistant"

    @pytest.mark.asyncio
    async def test_applies_window_limit(self):
        rows = [(HUMAN_MESSAGE,)] * 10 + [(AI_MESSAGE_TEXT,)] * 10
        mock_cursor = AsyncMock()
        mock_cursor.fetchall = AsyncMock(return_value=rows)
        mock_cursor.__aenter__ = AsyncMock(return_value=mock_cursor)
        mock_cursor.__aexit__ = AsyncMock(return_value=False)

        mock_conn = MagicMock()
        mock_conn.cursor = MagicMock(return_value=mock_cursor)

        result = await MessageHistoryAdapter.load_history(
            "session-1", mock_conn, limit=5
        )
        assert len(result) == 5

    @pytest.mark.asyncio
    async def test_handles_json_string_messages(self):
        rows = [(json.dumps(HUMAN_MESSAGE),)]
        mock_cursor = AsyncMock()
        mock_cursor.fetchall = AsyncMock(return_value=rows)
        mock_cursor.__aenter__ = AsyncMock(return_value=mock_cursor)
        mock_cursor.__aexit__ = AsyncMock(return_value=False)

        mock_conn = MagicMock()
        mock_conn.cursor = MagicMock(return_value=mock_cursor)

        result = await MessageHistoryAdapter.load_history(
            "session-1", mock_conn
        )
        assert len(result) == 1
        assert result[0]["role"] == "user"


# ---------------------------------------------------------------------------
# save_messages tests  (AC-07 modified: Anthropic format)
# ---------------------------------------------------------------------------

class TestSaveMessages:
    @pytest.mark.asyncio
    async def test_saves_with_format_marker(self):
        mock_cursor = AsyncMock()
        mock_cursor.__aenter__ = AsyncMock(return_value=mock_cursor)
        mock_cursor.__aexit__ = AsyncMock(return_value=False)

        mock_conn = MagicMock()
        mock_conn.cursor = MagicMock(return_value=mock_cursor)
        mock_conn.commit = AsyncMock()

        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
        ]

        await MessageHistoryAdapter.save_messages(
            "session-1", messages, mock_conn
        )

        assert mock_cursor.execute.await_count == 2
        mock_conn.commit.assert_awaited_once()

        # Verify format marker is in the stored JSON
        first_call = mock_cursor.execute.await_args_list[0]
        stored_json = json.loads(first_call.args[1]["msg"])
        assert stored_json["_format"] == "anthropic"
        assert stored_json["role"] == "user"
        assert stored_json["content"] == "Hello"

    @pytest.mark.asyncio
    async def test_save_empty_list_is_noop(self):
        mock_conn = MagicMock()
        mock_conn.commit = AsyncMock()
        await MessageHistoryAdapter.save_messages("s1", [], mock_conn)
        mock_conn.commit.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_saves_assistant_with_tool_use(self):
        mock_cursor = AsyncMock()
        mock_cursor.__aenter__ = AsyncMock(return_value=mock_cursor)
        mock_cursor.__aexit__ = AsyncMock(return_value=False)

        mock_conn = MagicMock()
        mock_conn.cursor = MagicMock(return_value=mock_cursor)
        mock_conn.commit = AsyncMock()

        messages = [
            {
                "role": "assistant",
                "content": [
                    {"type": "text", "text": "Searching..."},
                    {
                        "type": "tool_use",
                        "id": "toolu_01",
                        "name": "search_gmail",
                        "input": {"query": "test"},
                    },
                ],
            },
        ]

        await MessageHistoryAdapter.save_messages(
            "session-1", messages, mock_conn
        )

        stored_json = json.loads(
            mock_cursor.execute.await_args_list[0].args[1]["msg"]
        )
        assert stored_json["_format"] == "anthropic"
        assert stored_json["role"] == "assistant"
        assert len(stored_json["content"]) == 2
