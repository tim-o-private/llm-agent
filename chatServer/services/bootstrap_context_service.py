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
    calendar_summary: str = "(unavailable)"
    briefing_note: str = ""

    def render(self) -> str:
        """Format as prompt section text."""
        lines = []
        lines.append(f"Tasks: {self.tasks_summary}")
        lines.append(f"Reminders: {self.reminders_summary}")
        lines.append(f"Email: {self.email_summary}")
        lines.append(f"Calendar: {self.calendar_summary}")
        if self.briefing_note:
            lines.append(f"Briefing: {self.briefing_note}")
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
        tasks_result, reminders_result, email_result, calendar_result, briefing_check = await asyncio.gather(  # noqa: E501
            self._get_tasks_summary(user_id),
            self._get_reminders_summary(user_id),
            self._get_email_summary(user_id),
            self._get_calendar_summary(user_id),
            self._check_briefing_setup(user_id),
            return_exceptions=True,
        )

        ctx = BootstrapContext(
            tasks_summary=tasks_result if isinstance(tasks_result, str) else "(unavailable)",
            reminders_summary=reminders_result if isinstance(reminders_result, str) else "(unavailable)",  # noqa: E501
            email_summary=email_result if isinstance(email_result, str) else "(unavailable)",
            calendar_summary=calendar_result if isinstance(calendar_result, str) else "(unavailable)",
        )

        # Append first-use discovery note
        if isinstance(briefing_check, str) and briefing_check:
            ctx.briefing_note = briefing_check

        return ctx

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

    async def _get_calendar_summary(self, user_id: str) -> str:
        """Fetch today's calendar events across all connected accounts."""
        try:
            from chatServer.services.calendar_service import CalendarService
            from chatServer.tools.calendar_tools import CalendarToolProvider

            providers = await CalendarToolProvider.get_all_providers(user_id)
            if not providers:
                return "No calendar connected."

            all_events = []
            account_count = 0
            for provider in providers:
                try:
                    creds = await provider.get_credentials()
                    svc = CalendarService(creds)
                    events = svc.list_events(max_results=5)
                    for e in events:
                        e["account"] = provider.account_email
                    all_events.extend(events)
                    account_count += 1
                except Exception as e:
                    logger.warning(
                        "Failed to fetch calendar for %s account %s: %s",
                        user_id, provider.account_email, e
                    )

            if not all_events:
                label = f" ({account_count} account(s))" if account_count > 1 else ""
                return f"No events today{label}."

            # Sort by start time
            all_events.sort(key=lambda e: e.get("start", ""))

            summary = f"{len(all_events)} event(s) today"
            if account_count > 1:
                summary += f" across {account_count} account(s)"
            summary += "."

            # Show next 3 events
            next_events = all_events[:3]
            for ev in next_events:
                start = ev.get("start", "")
                title = ev.get("title", "(No title)")
                # Extract just the time portion if it's a dateTime
                if "T" in start:
                    time_part = start.split("T")[1][:5]  # HH:MM
                    summary += f" {time_part}: {title}."
                else:
                    summary += f" All day: {title}."

            return summary
        except Exception as e:
            logger.warning("Failed to get calendar summary for %s: %s", user_id, e)
            return "(unavailable)"

    async def _check_briefing_setup(self, user_id: str) -> str:
        """Check if user has configured briefings. Returns note if not."""
        try:
            resp = await self.db.table("user_preferences").select("id").eq(
                "user_id", user_id
            ).limit(1).execute()
            if not (resp.data or []):
                return "User hasn't configured morning briefings yet — you can offer to set this up."
            return ""
        except Exception:
            return ""
