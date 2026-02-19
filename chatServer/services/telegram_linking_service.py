"""
Telegram account linking service.

Manages the token-based flow for linking a user's web account
to their Telegram chat.
"""

import logging
import secrets
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


async def create_linking_token(db_client, user_id: str) -> str:
    """
    Generate a linking token for a user.

    Tokens expire after 10 minutes and are single-use.
    """
    token = secrets.token_urlsafe(32)

    await (
        db_client.table("channel_linking_tokens")
        .insert(
            {
                "user_id": user_id,
                "channel_type": "telegram",
                "token": token,
            }
        )
        .execute()
    )

    logger.info(f"Created Telegram linking token for user {user_id}")
    return token


async def link_telegram_account(db_client, token: str, chat_id: str) -> bool:
    """
    Complete the linking flow: validate token and store channel.

    Called when the Telegram bot receives /start <token>.
    """
    try:
        # Find valid token
        result = (
            await db_client.table("channel_linking_tokens")
            .select("*")
            .eq("token", token)
            .eq("used", False)
            .single()
            .execute()
        )

        if not result.data:
            logger.warning(f"Invalid or used linking token attempted: {token[:8]}...")
            return False

        token_data = result.data
        user_id = token_data["user_id"]

        # Check expiry
        expires_at = datetime.fromisoformat(token_data["expires_at"].replace("Z", "+00:00"))
        if datetime.now(timezone.utc) > expires_at:
            logger.warning(f"Expired linking token for user {user_id}")
            return False

        # Upsert into user_channels
        await (
            db_client.table("user_channels")
            .upsert(
                {
                    "user_id": user_id,
                    "channel_type": "telegram",
                    "channel_id": chat_id,
                    "is_active": True,
                },
                on_conflict="user_id,channel_type",
            )
            .execute()
        )

        # Mark token as used
        await db_client.table("channel_linking_tokens").update({"used": True}).eq("id", token_data["id"]).execute()

        logger.info(f"Linked Telegram chat {chat_id} to user {user_id}")
        return True

    except Exception as e:
        logger.error(f"Error linking Telegram account: {e}", exc_info=True)
        return False


async def unlink_telegram_account(db_client, user_id: str) -> bool:
    """Deactivate Telegram channel for a user."""
    try:
        await (
            db_client.table("user_channels")
            .update({"is_active": False})
            .eq("user_id", user_id)
            .eq("channel_type", "telegram")
            .execute()
        )

        logger.info(f"Unlinked Telegram for user {user_id}")
        return True

    except Exception as e:
        logger.error(f"Error unlinking Telegram: {e}", exc_info=True)
        return False


async def get_telegram_status(db_client, user_id: str) -> dict:
    """Check if user has Telegram linked, including which web session is synced."""
    try:
        result = (
            await db_client.table("user_channels")
            .select("channel_id, is_active, linked_at")
            .eq("user_id", user_id)
            .eq("channel_type", "telegram")
            .single()
            .execute()
        )

        if result.data and result.data.get("is_active"):
            # Find the most recent web session — this is the one synced to Telegram
            linked_session_id = None
            try:
                web_session = (
                    await db_client.table("chat_sessions")
                    .select("chat_id")
                    .eq("user_id", user_id)
                    .eq("channel", "web")
                    .order("updated_at", desc=True)
                    .limit(1)
                    .execute()
                )
                if web_session.data:
                    linked_session_id = str(web_session.data[0]["chat_id"])
            except Exception as e:
                logger.debug(f"Could not resolve linked session for user {user_id}: {e}")

            return {
                "linked": True,
                "linked_at": result.data["linked_at"],
                "linked_session_id": linked_session_id,
            }
        return {"linked": False}

    except Exception:
        return {"linked": False}
