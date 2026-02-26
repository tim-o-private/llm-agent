"""Bootstrap context pre-computation for returning users.

Gathers task, reminder, and email summaries via direct DB queries
and API calls — no LLM involved. Injected into the system prompt
as $bootstrap_context for session_open channel.
"""

import asyncio
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class BootstrapContext:
    """Pre-computed context for returning user session_open."""

    tasks_summary: str = "(unavailable)"
    reminders_summary: str = "(unavailable)"
    email_summary: str = "(unavailable)"

    def render(self) -> str:
        """Format as prompt section text."""
        lines = []
        lines.append(f"Tasks: {self.tasks_summary}")
        lines.append(f"Reminders: {self.reminders_summary}")
        lines.append(f"Email: {self.email_summary}")
        return "\n".join(lines)


class BootstrapContextService:
    """Pre-compute context for returning user session_open.

    All calls are non-LLM — direct DB queries and API calls.
    Individual source failures produce "(unavailable)".
    Target wall time: <2s.
    """

    def __init__(self, db_client):
        self.db = db_client

    async def gather(self, user_id: str) -> BootstrapContext:
        """Gather context from all sources. Never raises."""
        tasks_result, reminders_result, email_result = await asyncio.gather(
            self._get_tasks_summary(user_id),
            self._get_reminders_summary(user_id),
            self._get_email_summary(user_id),
            return_exceptions=True,
        )

        return BootstrapContext(
            tasks_summary=tasks_result if isinstance(tasks_result, str) else "(unavailable)",
            reminders_summary=reminders_result if isinstance(reminders_result, str) else "(unavailable)",
            email_summary=email_result if isinstance(email_result, str) else "(unavailable)",
        )

    async def _get_tasks_summary(self, user_id: str) -> str:
        """Count active tasks, find overdue items."""
        try:
            resp = await self.db.table("tasks").select(
                "id, title, status, due_date, priority"
            ).eq(
                "user_id", user_id
            ).eq(
                "deleted", False
            ).in_(
                "status", ["pending", "in_progress", "planning"]
            ).execute()

            tasks = resp.data or []
            if not tasks:
                return "No active tasks."

            from datetime import date
            today = date.today().isoformat()
            overdue = [t for t in tasks if t.get("due_date") and t["due_date"] < today]

            summary = f"{len(tasks)} active task(s)"
            if overdue:
                top = overdue[0]
                summary += f" ({len(overdue)} overdue). Top overdue: '{top.get('title', '?')}'"
            return summary
        except Exception as e:
            logger.warning("Failed to get tasks summary for %s: %s", user_id, e)
            return "(unavailable)"

    async def _get_reminders_summary(self, user_id: str) -> str:
        """Count upcoming reminders, find next due."""
        try:
            from datetime import datetime, timezone
            now = datetime.now(timezone.utc).isoformat()

            resp = await self.db.table("reminders").select(
                "id, title, remind_at"
            ).eq(
                "user_id", user_id
            ).eq(
                "status", "pending"
            ).gte(
                "remind_at", now
            ).order(
                "remind_at"
            ).limit(5).execute()

            reminders = resp.data or []
            if not reminders:
                return "No upcoming reminders."

            next_r = reminders[0]
            summary = f"{len(reminders)} upcoming reminder(s). Next: '{next_r.get('title', '?')}'"
            return summary
        except Exception as e:
            logger.warning("Failed to get reminders summary for %s: %s", user_id, e)
            return "(unavailable)"

    async def _get_email_summary(self, user_id: str) -> str:
        """Check connected email accounts (no content fetched)."""
        try:
            resp = await self.db.table("external_api_connections").select(
                "id, service_user_email"
            ).eq(
                "user_id", user_id
            ).eq(
                "service_name", "gmail"
            ).eq(
                "is_active", True
            ).execute()

            connections = resp.data or []
            if not connections:
                return "No email connected."

            accounts = [c.get("service_user_email", "?") for c in connections]
            return f"{len(accounts)} account(s) connected: {', '.join(accounts)}"
        except Exception as e:
            logger.warning("Failed to get email summary for %s: %s", user_id, e)
            return "(unavailable)"
