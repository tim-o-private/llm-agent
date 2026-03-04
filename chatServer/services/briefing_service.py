"""Briefing Service — composes signals and generates daily briefings via LLM synthesis.

Gathers context from calendar, tasks, email, and deferred observations,
builds a synthesis prompt, invokes the agent, and delivers the result.
"""

import asyncio
import logging
import re
from datetime import date, datetime, timedelta, timezone
from typing import Any

logger = logging.getLogger(__name__)

TELEGRAM_CHAR_LIMIT = 4000  # Hard limit is 4096, bot truncates at 4000


def format_for_telegram(markdown: str) -> str:
    """Post-process rich markdown for Telegram's legacy Markdown v1.

    - Strips ### headers -> **Header** (bold on its own line)
    - Flattens nested lists to single-level
    - Preserves bold, italic, and flat bullet points
    - Truncates to TELEGRAM_CHAR_LIMIT chars
    """
    # Convert ### headers to bold
    result = re.sub(r'^###\s+(.+)$', r'**\1**', markdown, flags=re.MULTILINE)
    # Also handle ## headers
    result = re.sub(r'^##\s+(.+)$', r'**\1**', result, flags=re.MULTILINE)

    # Flatten nested lists (  - item -> - item)
    result = re.sub(r'^(\s{2,})-\s+', r'- ', result, flags=re.MULTILINE)

    # Truncate if needed
    if len(result) > TELEGRAM_CHAR_LIMIT:
        result = result[:TELEGRAM_CHAR_LIMIT - 3] + "..."

    return result


def compute_next_briefing_time(
    tz_name: str, briefing_time: str, briefing_type: str
) -> datetime:
    """Compute the next occurrence of a briefing in UTC.

    Args:
        tz_name: IANA timezone (e.g., 'America/New_York')
        briefing_time: HH:MM or HH:MM:SS string (e.g., '07:30' or '07:30:00')
        briefing_type: 'morning' or 'evening' (unused, reserved for future logic)

    Returns:
        datetime in UTC for the next occurrence (always tomorrow or later).
    """
    from zoneinfo import ZoneInfo

    tz = ZoneInfo(tz_name)
    now_local = datetime.now(tz)
    # Handle both HH:MM and HH:MM:SS from TIME column
    parts = briefing_time.split(":")
    hour, minute = int(parts[0]), int(parts[1])
    tomorrow_local = (now_local + timedelta(days=1)).replace(
        hour=hour, minute=minute, second=0, microsecond=0
    )
    return tomorrow_local.astimezone(timezone.utc)


def compute_first_briefing_time(
    tz_name: str, briefing_time: str
) -> datetime:
    """Compute the first briefing time — today if not yet passed, else tomorrow.

    Returns datetime in UTC.
    """
    from zoneinfo import ZoneInfo

    tz = ZoneInfo(tz_name)
    now_local = datetime.now(tz)
    parts = briefing_time.split(":")
    hour, minute = int(parts[0]), int(parts[1])
    target_local = now_local.replace(
        hour=hour, minute=minute, second=0, microsecond=0
    )
    if target_local <= now_local:
        # Already passed today, schedule for tomorrow
        target_local += timedelta(days=1)
    return target_local.astimezone(timezone.utc)


class BriefingService:
    """Composes signals and generates daily briefings via LLM synthesis."""

    def __init__(self, db_client):
        self.db = db_client

    async def generate_morning_briefing(self, user_id: str) -> dict:
        """Gather context, invoke agent for synthesis, deliver notification.

        Returns: {"success": True, "briefing": str, "notification_id": str}
        """
        from chatServer.services.briefing_prompts import (
            MORNING_BRIEFING_PROMPT,
            _format_context_block,
        )

        prefs = await self.get_user_preferences(user_id)
        sections = prefs.get("briefing_sections", {})

        # 1. Gather signals in parallel (richer than bootstrap)
        context = await self._gather_morning_context(user_id, sections)

        # 2. Build synthesis prompt
        context_text = _format_context_block(context)
        prompt = MORNING_BRIEFING_PROMPT
        if context_text:
            prompt += "\n\n" + context_text

        # 3. Invoke agent via ScheduledExecutionService
        result = await self._invoke_briefing_agent(
            user_id=user_id,
            prompt=prompt,
            briefing_type="morning",
        )

        # 4. Deliver via NotificationService (for Telegram + read tracking)
        notification_id = await self._deliver_briefing(
            user_id=user_id,
            title="Good morning — here's your day",
            body=result["output"],
            briefing_type="morning",
        )

        # 5. Mark deferred observations as consumed
        await self._consume_deferred_observations(user_id)

        return {
            "success": True,
            "briefing": result["output"],
            "notification_id": notification_id,
        }

    async def generate_evening_briefing(self, user_id: str) -> dict:
        """Same pattern as morning but different context and prompt."""
        from chatServer.services.briefing_prompts import (
            EVENING_BRIEFING_PROMPT,
            _format_context_block,
        )

        prefs = await self.get_user_preferences(user_id)
        sections = prefs.get("briefing_sections", {})

        context = await self._gather_evening_context(user_id, sections)

        context_text = _format_context_block(context)
        prompt = EVENING_BRIEFING_PROMPT
        if context_text:
            prompt += "\n\n" + context_text

        result = await self._invoke_briefing_agent(
            user_id=user_id,
            prompt=prompt,
            briefing_type="evening",
        )

        notification_id = await self._deliver_briefing(
            user_id=user_id,
            title="Here's your evening wrap-up",
            body=result["output"],
            briefing_type="evening",
        )

        await self._consume_deferred_observations(user_id)

        return {
            "success": True,
            "briefing": result["output"],
            "notification_id": notification_id,
        }

    async def get_user_preferences(self, user_id: str) -> dict:
        """Get or lazily create user preferences."""
        resp = await self.db.table("user_preferences").select("*").eq(
            "user_id", user_id
        ).execute()

        if resp.data:
            return resp.data[0]

        # Lazy init: create with defaults
        await self.db.table("user_preferences").insert({
            "user_id": user_id,
        }).execute()

        # Re-fetch to get defaults applied by DB
        resp = await self.db.table("user_preferences").select("*").eq(
            "user_id", user_id
        ).execute()
        return resp.data[0] if resp.data else {"user_id": user_id}

    async def update_user_preferences(self, user_id: str, updates: dict) -> dict:
        """Update specific preference fields. Validates timezone and time format."""
        from zoneinfo import available_timezones

        from chatServer.services.briefing_prompts import get_enabled_sections

        validated = {}

        if "timezone" in updates:
            tz = updates["timezone"]
            if tz not in available_timezones():
                raise ValueError(f"Invalid timezone: {tz}")
            validated["timezone"] = tz

        for time_field in ("morning_briefing_time", "evening_briefing_time"):
            if time_field in updates:
                time_val = updates[time_field]
                # Validate HH:MM format and normalize to HH:MM:SS
                if not re.match(r'^\d{2}:\d{2}$', time_val):
                    raise ValueError(f"Invalid time format for {time_field}: {time_val}. Use HH:MM (e.g., 07:30)")  # noqa: E501
                h, m = int(time_val[:2]), int(time_val[3:5])
                if h > 23 or m > 59:
                    raise ValueError(f"Invalid time value for {time_field}: {time_val}")
                validated[time_field] = f"{time_val}:00"

        for bool_field in ("morning_briefing_enabled", "evening_briefing_enabled"):
            if bool_field in updates:
                val = updates[bool_field]
                if not isinstance(val, bool):
                    raise ValueError(f"{bool_field} must be boolean, got {type(val).__name__}")
                validated[bool_field] = val

        if "briefing_sections" in updates:
            validated["briefing_sections"] = get_enabled_sections(updates["briefing_sections"])

        if not validated:
            return await self.get_user_preferences(user_id)

        # Ensure row exists (lazy init)
        await self.get_user_preferences(user_id)

        resp = await self.db.table("user_preferences").update(
            validated
        ).eq("user_id", user_id).execute()

        return resp.data[0] if resp.data else await self.get_user_preferences(user_id)

    async def _gather_morning_context(self, user_id: str, sections: dict) -> dict:
        """Parallel fetch: calendar, tasks, email, observations.

        Returns richer data than BootstrapContextService — full event lists,
        actual email subjects, task details with due dates.
        """
        from chatServer.services.briefing_prompts import BRIEFING_SECTIONS_DEFAULT

        effective = {**BRIEFING_SECTIONS_DEFAULT, **sections}
        tasks = []

        async def _get_calendar():
            if not effective.get("calendar"):
                return []
            return await self._fetch_calendar_events(user_id)

        async def _get_tasks():
            if not effective.get("tasks"):
                return []
            return await self._fetch_tasks(user_id)

        async def _get_email():
            if not effective.get("email"):
                return []
            return await self._fetch_recent_emails(user_id)

        async def _get_observations():
            if not effective.get("observations"):
                return []
            return await self._fetch_deferred_observations(user_id)

        results = await asyncio.gather(
            _get_calendar(),
            _get_tasks(),
            _get_email(),
            _get_observations(),
            return_exceptions=True,
        )

        context = {}
        labels = ["calendar", "tasks", "email", "observations"]
        for label, result in zip(labels, results):
            if isinstance(result, Exception):
                logger.warning(f"Failed to gather {label} for briefing: {result}")
                continue
            if result:
                context[label] = result

        return context

    async def _gather_evening_context(self, user_id: str, sections: dict) -> dict:
        """Evening context: tasks completed today, tasks still open, tomorrow's calendar."""
        from chatServer.services.briefing_prompts import BRIEFING_SECTIONS_DEFAULT

        effective = {**BRIEFING_SECTIONS_DEFAULT, **sections}
        context = {}

        if effective.get("tasks"):
            try:
                completed = await self._fetch_completed_tasks_today(user_id)
                if completed:
                    context["completed_today"] = completed
                open_tasks = await self._fetch_tasks(user_id)
                if open_tasks:
                    context["still_open"] = open_tasks
            except Exception as e:
                logger.warning(f"Failed to gather evening tasks: {e}")

        if effective.get("calendar"):
            try:
                tomorrow = await self._fetch_tomorrow_calendar(user_id)
                if tomorrow:
                    context["tomorrow"] = tomorrow
            except Exception as e:
                logger.warning(f"Failed to gather tomorrow calendar: {e}")

        if effective.get("observations"):
            try:
                obs = await self._fetch_deferred_observations(user_id)
                if obs:
                    context["observations"] = obs
            except Exception as e:
                logger.warning(f"Failed to gather observations: {e}")

        return context

    async def _fetch_calendar_events(self, user_id: str) -> list[str]:
        """Fetch today's calendar events with times and titles."""
        try:
            from chatServer.services.calendar_service import CalendarService
            from chatServer.tools.calendar_tools import CalendarToolProvider

            providers = await CalendarToolProvider.get_all_providers(user_id)
            if not providers:
                return []

            all_events = []
            for provider in providers:
                try:
                    creds = await provider.get_credentials()
                    svc = CalendarService(creds)
                    events = svc.list_events(max_results=10)
                    all_events.extend(events)
                except Exception as e:
                    logger.warning(f"Calendar fetch failed for {provider.account_email}: {e}")

            if not all_events:
                return []

            all_events.sort(key=lambda e: e.get("start", ""))
            formatted = []
            for ev in all_events:
                start = ev.get("start", "")
                title = ev.get("title", "(No title)")
                if "T" in start:
                    time_part = start.split("T")[1][:5]
                    formatted.append(f"{time_part}: {title}")
                else:
                    formatted.append(f"All day: {title}")
            return formatted
        except Exception as e:
            logger.warning(f"Calendar context gathering failed: {e}")
            return []

    async def _fetch_tomorrow_calendar(self, user_id: str) -> list[str]:
        """Fetch tomorrow's calendar events."""
        try:
            from chatServer.services.calendar_service import CalendarService
            from chatServer.tools.calendar_tools import CalendarToolProvider

            providers = await CalendarToolProvider.get_all_providers(user_id)
            if not providers:
                return []

            tomorrow_start = datetime.combine(
                date.today() + timedelta(days=1), datetime.min.time()
            ).replace(tzinfo=timezone.utc)
            tomorrow_end = tomorrow_start + timedelta(days=1)

            all_events = []
            for provider in providers:
                try:
                    creds = await provider.get_credentials()
                    svc = CalendarService(creds)
                    events = svc.list_events(
                        time_min=tomorrow_start,
                        time_max=tomorrow_end,
                        max_results=10,
                    )
                    all_events.extend(events)
                except Exception as e:
                    logger.warning(f"Tomorrow calendar fetch failed: {e}")

            if not all_events:
                return []

            all_events.sort(key=lambda e: e.get("start", ""))
            formatted = []
            for ev in all_events:
                start = ev.get("start", "")
                title = ev.get("title", "(No title)")
                if "T" in start:
                    time_part = start.split("T")[1][:5]
                    formatted.append(f"{time_part}: {title}")
                else:
                    formatted.append(f"All day: {title}")
            return formatted
        except Exception as e:
            logger.warning(f"Tomorrow calendar failed: {e}")
            return []

    async def _fetch_tasks(self, user_id: str) -> list[str]:
        """Fetch active/overdue tasks with due dates."""
        try:
            resp = await self.db.table("tasks").select(
                "id, title, status, due_date, priority"
            ).eq(
                "user_id", user_id
            ).eq(
                "deleted", False
            ).in_(
                "status", ["pending", "in_progress", "planning"]
            ).order("due_date").limit(20).execute()

            tasks = resp.data or []
            if not tasks:
                return []

            today = date.today().isoformat()
            formatted = []
            for t in tasks:
                title = t.get("title", "Untitled")
                due = t.get("due_date")
                if due and due < today:
                    formatted.append(f"[overdue] {title} (due {due})")
                elif due and due == today:
                    formatted.append(f"[today] {title}")
                elif due:
                    formatted.append(f"{title} (due {due})")
                else:
                    formatted.append(title)
            return formatted
        except Exception as e:
            logger.warning(f"Tasks fetch failed: {e}")
            return []

    async def _fetch_completed_tasks_today(self, user_id: str) -> list[str]:
        """Fetch tasks completed today."""
        try:
            today_start = datetime.combine(
                date.today(), datetime.min.time()
            ).replace(tzinfo=timezone.utc).isoformat()

            resp = await self.db.table("tasks").select(
                "id, title"
            ).eq(
                "user_id", user_id
            ).eq(
                "status", "completed"
            ).gte(
                "updated_at", today_start
            ).limit(20).execute()

            tasks = resp.data or []
            return [t.get("title", "Untitled") for t in tasks]
        except Exception as e:
            logger.warning(f"Completed tasks fetch failed: {e}")
            return []

    async def _fetch_recent_emails(self, user_id: str) -> list[str]:
        """Fetch recent unread emails with sender and subject."""
        try:
            from chatServer.tools.gmail_tools import GmailToolProvider

            providers = await GmailToolProvider.get_all_providers(user_id, "scheduler")
            if not providers:
                return []

            all_emails = []
            for provider in providers:
                try:
                    gmail_tools = await provider.get_gmail_tools()
                    search_tool = next(
                        (t for t in gmail_tools if "search" in t.name.lower()), None
                    )
                    if not search_tool:
                        continue
                    result = await search_tool.arun({
                        "query": "is:unread newer_than:1d",
                        "max_results": 5,
                    })
                    if isinstance(result, list):
                        for msg in result:
                            subject = msg.get("subject", "(no subject)")
                            sender = msg.get("sender", "(unknown)")
                            all_emails.append(f'"{subject}" from {sender}')
                    elif isinstance(result, str) and "No messages" not in result:
                        all_emails.append(result)
                except Exception as e:
                    logger.warning(f"Email fetch failed for {provider.account_email}: {e}")

            return all_emails
        except Exception as e:
            logger.warning(f"Email context gathering failed: {e}")
            return []

    async def _fetch_deferred_observations(self, user_id: str) -> list[str]:
        """Fetch unconsumed deferred observations."""
        try:
            resp = await self.db.table("deferred_observations").select(
                "content, source, created_at"
            ).eq(
                "user_id", user_id
            ).is_(
                "consumed_at", "null"
            ).order("created_at").limit(20).execute()

            observations = resp.data or []
            return [obs["content"] for obs in observations]
        except Exception as e:
            logger.warning(f"Deferred observations fetch failed: {e}")
            return []

    async def _invoke_briefing_agent(
        self, user_id: str, prompt: str, briefing_type: str
    ) -> dict:
        """Invoke via ScheduledExecutionService with the schedule dict interface."""
        from chatServer.services.scheduled_execution_service import (
            ScheduledExecutionService,
        )

        return await ScheduledExecutionService().execute({
            "user_id": user_id,
            "agent_name": "assistant",
            "prompt": prompt,
            "config": {
                "model_override": "claude-haiku-4-5-20251001",
                "skip_notification": True,
                "schedule_type": "briefing",
            },
            "id": None,  # no agent_schedule row
        })

    async def _deliver_briefing(
        self, user_id: str, title: str, body: str, briefing_type: str
    ) -> str | None:
        """Deliver via NotificationService for Telegram + tracking.

        Post-processes markdown for Telegram before delivery.
        """
        try:
            from chatServer.services.notification_service import NotificationService

            telegram_body = format_for_telegram(body)
            notification_service = NotificationService(self.db)
            return await notification_service.notify_user(
                user_id=user_id,
                title=title,
                body=telegram_body,
                category="briefing",
                metadata={
                    "briefing_type": briefing_type,
                    "full_markdown": body,
                },
                type="notify",
            )
        except Exception as e:
            logger.warning(f"Failed to deliver briefing notification: {e}")
            return None

    async def _consume_deferred_observations(self, user_id: str) -> None:
        """Mark unconsumed observations as consumed."""
        try:
            await self.db.table("deferred_observations").update({
                "consumed_at": datetime.now(timezone.utc).isoformat(),
            }).eq(
                "user_id", user_id
            ).is_(
                "consumed_at", "null"
            ).execute()
        except Exception as e:
            logger.warning(f"Failed to consume deferred observations: {e}")
