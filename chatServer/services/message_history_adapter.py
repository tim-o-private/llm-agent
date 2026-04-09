"""Message history adapter — read/write chat_message_history in Anthropic format.

Reads both LangChain legacy format and Anthropic-native format from the
chat_message_history table. Writes new messages in Anthropic-native format
(per SPEC-033 modification: no backward-compat LangChain writes).
"""

import json
import logging
from typing import Any

import psycopg

from ..config.constants import CHAT_MESSAGE_HISTORY_TABLE_NAME

logger = logging.getLogger(__name__)

ANTHROPIC_FORMAT_MARKER = "anthropic"


class MessageHistoryAdapter:
    """Handles message persistence in the chat_message_history table.

    Reads messages in any format (LangChain or Anthropic-native) and
    converts them to Anthropic Messages API format. Writes new messages
    in Anthropic-native format with a ``_format`` marker.
    """

    @staticmethod
    async def load_history(
        session_id: str,
        pg_connection: psycopg.AsyncConnection,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Load conversation history from the database.

        Reads messages from chat_message_history, converting from whatever
        format they're stored in to Anthropic Messages API format.

        Args:
            session_id: Session ID to load messages for.
            pg_connection: Async psycopg connection.
            limit: Max number of raw rows to load (most recent).

        Returns:
            List of Anthropic-format message dicts with alternating roles.
        """
        table = CHAT_MESSAGE_HISTORY_TABLE_NAME
        async with pg_connection.cursor() as cur:
            await cur.execute(
                f"SELECT message FROM {table} "
                f"WHERE session_id = %(sid)s ORDER BY id ASC",
                {"sid": session_id},
            )
            rows = await cur.fetchall()

        messages: list[dict[str, Any]] = []
        for (msg_json,) in rows:
            if isinstance(msg_json, str):
                msg_json = json.loads(msg_json)

            converted = _convert_message(msg_json)
            if converted is not None:
                messages.append(converted)

        # Apply window: keep last *limit* messages
        if limit and len(messages) > limit:
            messages = messages[-limit:]

        return _merge_tool_results(messages)

    @staticmethod
    async def save_messages(
        session_id: str,
        messages: list[dict[str, Any]],
        pg_connection: psycopg.AsyncConnection,
    ) -> None:
        """Save messages to chat_message_history in Anthropic-native format.

        Each message is stored with a ``_format: "anthropic"`` marker so
        future reads can distinguish them from LangChain-format rows.
        """
        if not messages:
            return

        table = CHAT_MESSAGE_HISTORY_TABLE_NAME
        async with pg_connection.cursor() as cur:
            for msg in messages:
                stored = {"_format": ANTHROPIC_FORMAT_MARKER, **msg}
                await cur.execute(
                    f"INSERT INTO {table} (session_id, message) "
                    f"VALUES (%(sid)s, %(msg)s)",
                    {"sid": session_id, "msg": json.dumps(stored)},
                )
        await pg_connection.commit()


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _convert_message(msg: dict) -> dict | None:
    """Convert a stored message to Anthropic format.

    Handles both LangChain format and Anthropic-native format.
    """
    # Anthropic-native format (written by ConversationHandler)
    if msg.get("_format") == ANTHROPIC_FORMAT_MARKER:
        return {k: v for k, v in msg.items() if k != "_format"}

    # LangChain format: {"type": "human|ai|tool", "data": {...}}
    msg_type = msg.get("type")
    data = msg.get("data", {})
    content = data.get("content", "")

    if msg_type == "human":
        return {"role": "user", "content": _normalize_content(content)}

    if msg_type == "ai":
        return _convert_ai_message(data)

    if msg_type == "tool":
        tool_call_id = data.get("tool_call_id", "")
        return {
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": tool_call_id,
                    "content": _normalize_content(content),
                }
            ],
        }

    logger.warning("Unknown message type in chat_message_history: %s", msg_type)
    return None


def _convert_ai_message(data: dict) -> dict:
    """Convert an AI message from LangChain format to Anthropic format."""
    content = data.get("content", "")
    tool_calls = data.get("tool_calls", [])

    # AIMessageChunk stores tool_calls in additional_kwargs
    if not tool_calls:
        additional_kwargs = data.get("additional_kwargs", {})
        tool_calls = additional_kwargs.get("tool_calls", [])

    if not tool_calls:
        return {"role": "assistant", "content": _normalize_content(content)}

    # Build content blocks: text (if any) + tool_use blocks
    content_blocks: list[dict] = []

    text = _normalize_content(content)
    if text:
        content_blocks.append({"type": "text", "text": text})

    for tc in tool_calls:
        content_blocks.append({
            "type": "tool_use",
            "id": tc.get("id", ""),
            "name": tc.get("name", ""),
            "input": tc.get("args", {}),
        })

    return {"role": "assistant", "content": content_blocks}


def _normalize_content(content: Any) -> str:
    """Normalize content that may be a string or list of content blocks."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(block.get("text", ""))
            elif isinstance(block, str):
                parts.append(block)
        return "".join(parts)
    return str(content) if content else ""


def _merge_tool_results(messages: list[dict]) -> list[dict]:
    """Merge consecutive tool_result messages into single user messages.

    The Anthropic API requires strict user/assistant alternation.
    Tool results may be stored as separate rows but must be merged.
    """
    if not messages:
        return messages

    merged: list[dict] = []
    i = 0
    while i < len(messages):
        msg = messages[i]

        if _is_tool_result_msg(msg):
            tool_results = list(msg["content"])
            j = i + 1
            while j < len(messages) and _is_tool_result_msg(messages[j]):
                tool_results.extend(messages[j]["content"])
                j += 1
            merged.append({"role": "user", "content": tool_results})
            i = j
        else:
            merged.append(msg)
            i += 1

    return merged


def _is_tool_result_msg(msg: dict) -> bool:
    """Check if a message is a user message containing tool_result blocks."""
    if msg.get("role") != "user":
        return False
    content = msg.get("content")
    if not isinstance(content, list) or not content:
        return False
    return content[0].get("type") == "tool_result"
