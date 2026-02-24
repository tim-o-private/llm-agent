"""Reminder tools for agent integration.

Provides CreateReminderTool and ListRemindersTool for LangChain agents.
Follows the same BaseTool pattern as email_digest_tool.py.
"""

import logging
from datetime import datetime, timezone
from typing import Optional, Type

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class CreateReminderInput(BaseModel):
    """Input schema for create_reminder tool."""

    title: str = Field(..., description="Short title for the reminder")
    body: Optional[str] = Field(default=None, description="Optional longer description")
    remind_at: str = Field(
        ...,
        description=(
            "ISO 8601 datetime string for when to send the reminder "
            "(e.g. '2026-02-19T09:00:00Z'). Must be in the future."
        ),
    )
    recurrence: Optional[str] = Field(
        default=None,
        description="Optional recurrence: 'daily', 'weekly', or 'monthly'",
    )


class CreateReminderTool(BaseTool):
    """Create a reminder for the user."""

    name: str = "create_reminder"
    description: str = (
        "Create a reminder that will notify the user at a specified time. "
        "Use this when the user asks to be reminded about something. "
        "The remind_at must be an ISO 8601 datetime in the future."
    )
    args_schema: Type[BaseModel] = CreateReminderInput

    user_id: str
    agent_name: Optional[str] = None
    supabase_url: Optional[str] = None
    supabase_key: Optional[str] = None

    @classmethod
    def prompt_section(cls, channel: str) -> str | None:
        """Return behavioral guidance for the agent prompt, or None to omit."""
        if channel in ("web", "telegram"):
            return "Reminders: When the user mentions a deadline or wants to be reminded, use create_reminder with an ISO datetime. Use list_reminders to show upcoming reminders."  # noqa: E501
        else:
            return None

    def _run(self, title: str, remind_at: str, body: Optional[str] = None, recurrence: Optional[str] = None) -> str:
        return "create_reminder requires async execution. Use _arun."

    async def _arun(
        self,
        title: str,
        remind_at: str,
        body: Optional[str] = None,
        recurrence: Optional[str] = None,
    ) -> str:
        try:
            parsed_dt = datetime.fromisoformat(remind_at.replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)
            if parsed_dt <= now:
                return "Error: remind_at must be in the future."

            if recurrence and recurrence not in ("daily", "weekly", "monthly"):
                return f"Error: invalid recurrence '{recurrence}'. Must be 'daily', 'weekly', or 'monthly'."

            from ..database.scoped_client import UserScopedClient
            from ..database.supabase_client import get_supabase_client
            from ..services.reminder_service import ReminderService

            raw_client = await get_supabase_client()
            db = UserScopedClient(raw_client, self.user_id)
            service = ReminderService(db)
            await service.create_reminder(
                user_id=self.user_id,
                title=title,
                body=body,
                remind_at=parsed_dt,
                recurrence=recurrence,
                created_by="agent",
                agent_name=self.agent_name,
            )

            recurrence_msg = f" (repeats {recurrence})" if recurrence else ""
            return f"Reminder set: \"{title}\" at {parsed_dt.strftime('%Y-%m-%d %H:%M %Z')}{recurrence_msg}."

        except ValueError as e:
            return f"Error parsing remind_at: {e}. Please use ISO 8601 format."
        except Exception as e:
            logger.error(f"create_reminder failed for user {self.user_id}: {e}")
            return f"Failed to create reminder: {e}"


class ListRemindersInput(BaseModel):
    """Input schema for list_reminders tool."""

    limit: int = Field(default=10, ge=1, le=50, description="Maximum number of reminders to return (1-50)")


class ListRemindersTool(BaseTool):
    """List upcoming reminders for the user."""

    name: str = "list_reminders"
    description: str = (
        "List the user's upcoming reminders. Returns pending reminders ordered by time. "
        "Use this when the user asks about their reminders."
    )
    args_schema: Type[BaseModel] = ListRemindersInput

    user_id: str
    agent_name: Optional[str] = None
    supabase_url: Optional[str] = None
    supabase_key: Optional[str] = None

    def _run(self, limit: int = 10) -> str:
        return "list_reminders requires async execution. Use _arun."

    async def _arun(self, limit: int = 10) -> str:
        try:
            from ..database.scoped_client import UserScopedClient
            from ..database.supabase_client import get_supabase_client
            from ..services.reminder_service import ReminderService

            raw_client = await get_supabase_client()
            db = UserScopedClient(raw_client, self.user_id)
            service = ReminderService(db)
            reminders = await service.list_upcoming(user_id=self.user_id, limit=limit)

            if not reminders:
                return "You have no upcoming reminders."

            lines = [f"You have {len(reminders)} upcoming reminder(s):\n"]
            for i, r in enumerate(reminders, 1):
                dt_str = r.get("remind_at", "unknown time")
                try:
                    dt = datetime.fromisoformat(dt_str)
                    dt_str = dt.strftime("%Y-%m-%d %H:%M %Z")
                except (ValueError, TypeError):
                    pass
                rec = f" (repeats {r['recurrence']})" if r.get("recurrence") else ""
                body_text = r.get("body")
                if body_text and len(body_text) > 80:
                    body_preview = f" - {body_text[:80]}..."
                elif body_text:
                    body_preview = f" - {body_text}"
                else:
                    body_preview = ""
                lines.append(f"{i}. [{dt_str}] {r['title']}{rec}{body_preview}")

            return "\n".join(lines)

        except Exception as e:
            logger.error(f"list_reminders failed for user {self.user_id}: {e}")
            return f"Failed to list reminders: {e}"
