"""
Notification routing service.

Routes notifications to appropriate channels:
- Web: stores in notifications table (frontend polls)
- Telegram: sends via TelegramBotService (Phase 3)
"""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class NotificationService:
    """
    Routes notifications to user channels (web, Telegram).

    Web notifications are always stored in the database.
    Telegram notifications are sent when the user has linked their account
    and the channel is in the requested list.
    """

    def __init__(self, db_client):
        self.db = db_client

    async def notify_user(
        self,
        user_id: str,
        title: str,
        body: str,
        category: str = "info",
        metadata: Optional[Dict[str, Any]] = None,
        channels: Optional[List[str]] = None,
    ) -> str:
        """
        Send a notification to the user via requested channels.

        Args:
            user_id: Target user
            title: Notification title (short)
            body: Notification body (can be multi-line markdown)
            category: One of: heartbeat, approval_needed, agent_result, error, info
            metadata: Structured context (schedule_id, agent_name, execution_id, etc.)
            channels: List of channels to use. None = all available.

        Returns:
            Notification ID
        """
        metadata = metadata or {}

        # 1. Always store in notifications table (web channel)
        notification_id = await self._store_web_notification(
            user_id=user_id,
            title=title,
            body=body,
            category=category,
            metadata=metadata,
        )

        # 2. Send via Telegram if user has it linked and it's requested
        if channels is None or "telegram" in channels:
            await self._send_telegram_notification(
                user_id=user_id,
                title=title,
                body=body,
                metadata=metadata,
            )

        return notification_id

    async def notify_pending_actions(
        self,
        user_id: str,
        pending_count: int,
        agent_name: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Notify user about pending actions that need approval.

        Creates a summary notification and (in Phase 3) sends
        per-action approval requests via Telegram.
        """
        if pending_count <= 0:
            return

        title = f"{pending_count} action{'s' if pending_count != 1 else ''} pending approval"
        body = (
            f"Agent **{agent_name}** queued {pending_count} "
            f"action{'s' if pending_count != 1 else ''} that "
            f"{'need' if pending_count != 1 else 'needs'} your approval."
        )

        await self.notify_user(
            user_id=user_id,
            title=title,
            body=body,
            category="approval_needed",
            metadata=metadata or {},
        )

    async def get_notifications(
        self,
        user_id: str,
        unread_only: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """Fetch notifications for a user."""
        try:
            query = (
                self.db.table("notifications")
                .select("*")
                .eq("user_id", user_id)
                .order("created_at", desc=True)
                .range(offset, offset + limit - 1)
            )

            if unread_only:
                query = query.eq("read", False)

            result = await query.execute()
            return result.data or []

        except Exception as e:
            logger.error(f"Failed to fetch notifications for user {user_id}: {e}")
            return []

    async def get_unread_count(self, user_id: str) -> int:
        """Get count of unread notifications."""
        try:
            result = (
                await self.db.table("notifications")
                .select("id", count="exact")
                .eq("user_id", user_id)
                .eq("read", False)
                .execute()
            )
            return result.count or 0

        except Exception as e:
            logger.error(f"Failed to get unread count for user {user_id}: {e}")
            return 0

    async def mark_read(self, user_id: str, notification_id: str) -> bool:
        """Mark a single notification as read."""
        try:
            await (
                self.db.table("notifications")
                .update({"read": True})
                .eq("id", notification_id)
                .eq("user_id", user_id)
                .execute()
            )
            return True

        except Exception as e:
            logger.error(f"Failed to mark notification {notification_id} as read: {e}")
            return False

    async def mark_all_read(self, user_id: str) -> int:
        """Mark all notifications as read for a user. Returns count updated."""
        try:
            result = (
                await self.db.table("notifications")
                .update({"read": True})
                .eq("user_id", user_id)
                .eq("read", False)
                .execute()
            )
            return len(result.data) if result.data else 0

        except Exception as e:
            logger.error(f"Failed to mark all notifications as read for user {user_id}: {e}")
            return 0

    async def _store_web_notification(
        self,
        user_id: str,
        title: str,
        body: str,
        category: str,
        metadata: Dict[str, Any],
    ) -> str:
        """Store notification in the database for web UI polling."""
        try:
            result = (
                await self.db.table("notifications")
                .insert(
                    {
                        "user_id": user_id,
                        "title": title,
                        "body": body[:10000] if body else "",  # Truncate very long bodies
                        "category": category,
                        "metadata": metadata,
                    }
                )
                .execute()
            )

            notification_id = result.data[0]["id"] if result.data else "unknown"
            logger.debug(f"Stored notification {notification_id} for user {user_id}")
            return notification_id

        except Exception as e:
            logger.error(f"Failed to store notification for user {user_id}: {e}", exc_info=True)
            return "error"

    async def _send_telegram_notification(
        self,
        user_id: str,
        title: str,
        body: str,
        metadata: Dict[str, Any],
    ) -> None:
        """Send notification via Telegram if user has it linked."""
        chat_id = await self._get_telegram_chat_id(user_id)
        if not chat_id:
            return

        try:
            from chatServer.channels.telegram_bot import get_telegram_bot_service

            bot_service = get_telegram_bot_service()
            if not bot_service:
                return

            text = f"*{title}*\n\n{body}"
            await bot_service.send_notification(chat_id, text)

        except Exception as e:
            logger.warning(f"Failed to send Telegram notification to user {user_id}: {e}")

    async def _get_telegram_chat_id(self, user_id: str) -> Optional[str]:
        """Look up Telegram chat_id for a user from user_channels table."""
        try:
            result = (
                await self.db.table("user_channels")
                .select("channel_id")
                .eq("user_id", user_id)
                .eq("channel_type", "telegram")
                .eq("is_active", True)
                .single()
                .execute()
            )
            return result.data.get("channel_id") if result.data else None
        except Exception:
            return None
