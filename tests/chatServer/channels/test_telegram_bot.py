"""Unit tests for TelegramBotService."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from chatServer.channels.telegram_bot import TelegramBotService


def _make_service():
    """Create a TelegramBotService with a mocked bot."""
    service = TelegramBotService.__new__(TelegramBotService)
    service.bot = MagicMock()
    service.bot.send_message = AsyncMock()
    return service


@pytest.mark.asyncio
async def test_send_notification_truncates_at_4000_chars():
    service = _make_service()
    long_text = "x" * 5000

    await service.send_notification("chat-1", long_text)

    service.bot.send_message.assert_awaited_once()
    call_kwargs = service.bot.send_message.call_args[1]
    sent_text = call_kwargs["text"]
    assert len(sent_text) == 4000
    assert sent_text.endswith("...")
    assert sent_text == "x" * 3997 + "..."


@pytest.mark.asyncio
async def test_send_notification_short_text_not_truncated():
    service = _make_service()
    text = "Hello, user!"

    await service.send_notification("chat-1", text)

    call_kwargs = service.bot.send_message.call_args[1]
    assert call_kwargs["text"] == "Hello, user!"


@pytest.mark.asyncio
async def test_send_approval_request_has_inline_keyboard():
    service = _make_service()

    await service.send_approval_request(
        chat_id="chat-1",
        action_id="action-42",
        tool_name="send_email",
        tool_args={"to": "user@example.com", "subject": "Hello"},
    )

    service.bot.send_message.assert_awaited_once()
    call_kwargs = service.bot.send_message.call_args[1]

    # Verify inline keyboard is present
    reply_markup = call_kwargs["reply_markup"]
    assert reply_markup is not None

    # Check approve and reject buttons
    buttons = reply_markup.inline_keyboard[0]
    assert len(buttons) == 2
    assert buttons[0].text == "Approve"
    assert buttons[0].callback_data == "approve:action-42"
    assert buttons[1].text == "Reject"
    assert buttons[1].callback_data == "reject:action-42"

    # Verify message contains tool name
    assert "send_email" in call_kwargs["text"]


@pytest.mark.asyncio
async def test_send_notification_handles_error():
    service = _make_service()
    service.bot.send_message = AsyncMock(side_effect=Exception("Network error"))

    # Should not raise
    await service.send_notification("chat-1", "test message")

    service.bot.send_message.assert_awaited_once()
