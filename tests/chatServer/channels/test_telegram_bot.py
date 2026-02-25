"""Unit tests for TelegramBotService."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from chatServer.channels.telegram_bot import TelegramBotService, handle_feedback_callback


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


# ---------------------------------------------------------------------------
# handle_feedback_callback
# ---------------------------------------------------------------------------


def _make_callback(data: str, chat_id: int = 12345) -> MagicMock:
    """Build a mock CallbackQuery with the given callback data."""
    callback = MagicMock(spec=["data", "message", "answer"])
    callback.data = data
    callback.answer = AsyncMock()
    callback.message = MagicMock()
    callback.message.chat = MagicMock()
    callback.message.chat.id = chat_id
    callback.message.edit_reply_markup = AsyncMock()
    return callback


def _make_bot_service(user_id: str = "user-abc") -> MagicMock:
    """Build a mock TelegramBotService with a db_client that returns a user_id."""
    bot_svc = MagicMock()
    db = MagicMock()
    chain = db.table.return_value.select.return_value
    chain.eq.return_value = chain
    chain.single.return_value = chain
    chain.execute = AsyncMock(return_value=MagicMock(data={"user_id": user_id}))
    bot_svc._db_client = db
    return bot_svc


@pytest.mark.asyncio
async def test_feedback_callback_parses_useful():
    """'useful' suffix is correctly parsed from callback data."""
    notification_id = "550e8400-e29b-41d4-a716-446655440000"
    callback = _make_callback(f"nfb_{notification_id}_useful")
    bot_svc = _make_bot_service()

    with (
        patch("chatServer.channels.telegram_bot.get_telegram_bot_service", return_value=bot_svc),
        patch("chatServer.channels.telegram_bot.NotificationService") as MockSvc,
    ):
        mock_notif_svc = MagicMock()
        mock_notif_svc.submit_feedback = AsyncMock(return_value={"status": "ok"})
        MockSvc.return_value = mock_notif_svc

        await handle_feedback_callback(callback)

        mock_notif_svc.submit_feedback.assert_awaited_once_with(notification_id, "useful", "user-abc")
    callback.answer.assert_awaited_once_with("Got it, thanks!")


@pytest.mark.asyncio
async def test_feedback_callback_parses_not_useful():
    """'not_useful' suffix (with extra underscore) is correctly parsed."""
    notification_id = "550e8400-e29b-41d4-a716-446655440000"
    callback = _make_callback(f"nfb_{notification_id}_not_useful")
    bot_svc = _make_bot_service()

    with (
        patch("chatServer.channels.telegram_bot.get_telegram_bot_service", return_value=bot_svc),
        patch("chatServer.channels.telegram_bot.NotificationService") as MockSvc,
    ):
        mock_notif_svc = MagicMock()
        mock_notif_svc.submit_feedback = AsyncMock(return_value={"status": "ok"})
        MockSvc.return_value = mock_notif_svc

        await handle_feedback_callback(callback)

        mock_notif_svc.submit_feedback.assert_awaited_once_with(notification_id, "not_useful", "user-abc")
    callback.answer.assert_awaited_once_with("Got it, thanks!")


@pytest.mark.asyncio
async def test_feedback_callback_calls_service():
    """submit_feedback is called with parsed notification_id, feedback, user_id."""
    notification_id = "a1b2c3d4-0000-1111-2222-333344445555"
    callback = _make_callback(f"nfb_{notification_id}_useful")
    bot_svc = _make_bot_service(user_id="user-xyz")

    with (
        patch("chatServer.channels.telegram_bot.get_telegram_bot_service", return_value=bot_svc),
        patch("chatServer.channels.telegram_bot.NotificationService") as MockSvc,
    ):
        mock_notif_svc = MagicMock()
        mock_notif_svc.submit_feedback = AsyncMock(return_value={"status": "ok"})
        MockSvc.return_value = mock_notif_svc

        await handle_feedback_callback(callback)

        MockSvc.assert_called_once_with(bot_svc._db_client)
        mock_notif_svc.submit_feedback.assert_awaited_once_with(notification_id, "useful", "user-xyz")


@pytest.mark.asyncio
async def test_feedback_callback_duplicate_answers_already_recorded():
    """already_set status results in 'Already recorded!' answer."""
    notification_id = "aaaabbbb-cccc-dddd-eeee-ffff00001111"
    callback = _make_callback(f"nfb_{notification_id}_useful")
    bot_svc = _make_bot_service()

    with (
        patch("chatServer.channels.telegram_bot.get_telegram_bot_service", return_value=bot_svc),
        patch("chatServer.channels.telegram_bot.NotificationService") as MockSvc,
    ):
        mock_notif_svc = MagicMock()
        mock_notif_svc.submit_feedback = AsyncMock(return_value={"status": "already_set"})
        MockSvc.return_value = mock_notif_svc

        await handle_feedback_callback(callback)

    callback.answer.assert_awaited_once_with("Already recorded!")
