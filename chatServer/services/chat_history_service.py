"""
Chat history service.

Provides session listing and message fetching for the unified session registry.
All channels (web, Telegram, scheduled) are queryable through this service.
"""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ChatHistoryService:
    """Service for querying chat sessions and their messages."""

    def __init__(self, db_client):
        self.db = db_client

    async def get_sessions(
        self,
        user_id: str,
        channel: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """List chat sessions for a user, optionally filtered by channel.

        Args:
            user_id: The authenticated user's ID.
            channel: Optional channel filter ('web', 'telegram', 'scheduled').
            limit: Max results to return.
            offset: Pagination offset.

        Returns:
            List of session dicts.
        """
        try:
            query = (
                self.db.table("chat_sessions")
                .select("*")
                .eq("user_id", user_id)
                .order("created_at", desc=True)
                .range(offset, offset + limit - 1)
            )

            if channel:
                query = query.eq("channel", channel)

            result = await query.execute()
            return result.data or []

        except Exception as e:
            logger.error(f"Failed to fetch sessions for user {user_id}: {e}")
            return []

    async def get_session_messages(
        self,
        session_id: str,
        user_id: str,
        limit: int = 50,
        before_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Fetch messages for a session with cursor-based pagination.

        Args:
            session_id: The session_id to fetch messages for.
            user_id: The authenticated user's ID (for ownership check).
            limit: Max messages to return.
            before_id: Cursor — return messages with id < this value.

        Returns:
            List of message dicts, or empty list if session not owned by user.
        """
        try:
            # Verify the session belongs to the user
            session_check = (
                await self.db.table("chat_sessions")
                .select("id")
                .eq("session_id", session_id)
                .eq("user_id", user_id)
                .execute()
            )

            if not session_check.data:
                return []

            # Fetch messages from chat_message_history
            query = (
                self.db.table("chat_message_history")
                .select("*")
                .eq("session_id", session_id)
                .order("id", desc=True)
                .limit(limit)
            )

            if before_id is not None:
                query = query.lt("id", before_id)

            result = await query.execute()
            return result.data or []

        except Exception as e:
            logger.error(f"Failed to fetch messages for session {session_id}: {e}")
            return []
