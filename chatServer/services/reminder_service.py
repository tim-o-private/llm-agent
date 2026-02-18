"""
Reminder Service.

Manages reminders: CRUD, due-reminder queries, recurrence handling.
Used by reminder tools (agent-facing) and the delivery loop (background).
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

logger = logging.getLogger(__name__)


class ReminderService:
    """Service for managing user reminders."""

    def __init__(self, db_client):
        self.db = db_client

    async def create_reminder(
        self,
        user_id: str,
        title: str,
        body: Optional[str] = None,
        remind_at: Optional[datetime] = None,
        recurrence: Optional[str] = None,
        created_by: str = "agent",
        agent_name: Optional[str] = None,
    ) -> dict:
        """Create a new reminder.

        Args:
            user_id: Owner of the reminder.
            title: Short reminder title.
            body: Optional longer description.
            remind_at: When to fire (must be in the future).
            recurrence: Optional recurrence rule (daily/weekly/monthly).
            created_by: 'user' or 'agent'.
            agent_name: Name of the agent that created it (if agent).

        Returns:
            The created reminder row as a dict.
        """
        if remind_at is None:
            raise ValueError("remind_at is required")

        entry = {
            "user_id": user_id,
            "title": title,
            "body": body,
            "remind_at": remind_at.isoformat(),
            "recurrence": recurrence,
            "created_by": created_by,
            "agent_name": agent_name,
            "status": "pending",
            "metadata": {},
        }

        result = await self.db.table("reminders").insert(entry).execute()

        if not result.data or len(result.data) == 0:
            raise Exception("Failed to create reminder")

        logger.info(f"Created reminder {result.data[0]['id']} for user {user_id}")
        return result.data[0]

    async def list_upcoming(self, user_id: str, limit: int = 20) -> list[dict]:
        """List upcoming pending reminders for a user, ordered by remind_at."""
        result = (
            await self.db.table("reminders")
            .select("*")
            .eq("user_id", user_id)
            .eq("status", "pending")
            .order("remind_at")
            .limit(limit)
            .execute()
        )
        return result.data or []

    async def get_due_reminders(self) -> list[dict]:
        """Get all pending reminders whose remind_at <= now (across all users)."""
        now = datetime.now(timezone.utc).isoformat()
        result = (
            await self.db.table("reminders")
            .select("*")
            .eq("status", "pending")
            .lte("remind_at", now)
            .execute()
        )
        return result.data or []

    async def mark_sent(self, reminder_id: str) -> None:
        """Mark a reminder as sent."""
        await (
            self.db.table("reminders")
            .update({"status": "sent", "updated_at": datetime.now(timezone.utc).isoformat()})
            .eq("id", reminder_id)
            .execute()
        )
        logger.info(f"Marked reminder {reminder_id} as sent")

    async def dismiss(self, user_id: str, reminder_id: str) -> None:
        """Dismiss a reminder (user-initiated)."""
        await (
            self.db.table("reminders")
            .update({"status": "dismissed", "updated_at": datetime.now(timezone.utc).isoformat()})
            .eq("id", reminder_id)
            .eq("user_id", user_id)
            .execute()
        )
        logger.info(f"Dismissed reminder {reminder_id} for user {user_id}")

    async def handle_recurrence(self, reminder: dict) -> None:
        """If the reminder is recurring, create the next occurrence."""
        recurrence = reminder.get("recurrence")
        if not recurrence:
            return

        remind_at_str = reminder["remind_at"]
        if isinstance(remind_at_str, str):
            remind_at = datetime.fromisoformat(remind_at_str)
        else:
            remind_at = remind_at_str

        if recurrence == "daily":
            next_remind_at = remind_at + timedelta(days=1)
        elif recurrence == "weekly":
            next_remind_at = remind_at + timedelta(weeks=1)
        elif recurrence == "monthly":
            # Approximate: add 30 days
            next_remind_at = remind_at + timedelta(days=30)
        else:
            logger.warning(f"Unknown recurrence type: {recurrence}")
            return

        await self.create_reminder(
            user_id=reminder["user_id"],
            title=reminder["title"],
            body=reminder.get("body"),
            remind_at=next_remind_at,
            recurrence=recurrence,
            created_by=reminder.get("created_by", "agent"),
            agent_name=reminder.get("agent_name"),
        )
        logger.info(f"Created next {recurrence} occurrence for reminder {reminder['id']}")
