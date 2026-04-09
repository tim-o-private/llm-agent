"""Shared Telegram push utility — cross-channel notification sync.

Extracted from ChatService._push_to_telegram_if_linked (AC-33) so both
the old ChatService path and the new ConversationHandler path can call it.
"""

import logging

logger = logging.getLogger(__name__)


async def push_to_telegram_if_linked(
    user_id: str,
    session_id: str,
    response_text: str,
    db_client,
) -> None:
    """Push an agent response to Telegram if this session is the linked one.

    Args:
        user_id: The user's ID.
        session_id: The current chat session ID.
        response_text: The formatted text to send (may include Markdown).
        db_client: A Supabase client for DB lookups.
    """
    # 1. Check if user has an active Telegram link
    channel_result = (
        await db_client.table("user_channels")
        .select("channel_id")
        .eq("user_id", user_id)
        .eq("channel_type", "telegram")
        .eq("is_active", True)
        .limit(1)
        .execute()
    )
    if not channel_result.data:
        return
    telegram_chat_id = channel_result.data[0]["channel_id"]

    # 2. Check if this session is the most recent web session
    web_session = (
        await db_client.table("chat_sessions")
        .select("chat_id")
        .eq("user_id", user_id)
        .eq("channel", "web")
        .order("updated_at", desc=True)
        .limit(1)
        .execute()
    )
    if not web_session.data or str(web_session.data[0]["chat_id"]) != session_id:
        return

    # 3. Send to Telegram
    from ..channels.telegram_bot import get_telegram_bot_service

    bot_service = get_telegram_bot_service()
    if bot_service:
        await bot_service.send_notification(telegram_chat_id, response_text)
