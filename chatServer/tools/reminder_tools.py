"""Reminder tools for agent integration.

Provides GetRemindersTool, CreateRemindersTool, and DeleteRemindersTool
for LangChain agents. Follows SPEC-019 verb_resource naming convention.
"""

import logging
from datetime import datetime, timezone
from typing import Optional, Type

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# --- GetRemindersTool ---

class GetRemindersInput(BaseModel):
    """Input schema for get_reminders tool."""

    id: Optional[str] = Field(default=None, description="Optional reminder ID to fetch a single reminder")
    limit: int = Field(default=10, ge=1, le=50, description="Maximum number of reminders to return (1-50)")


class GetRemindersTool(BaseTool):
    """Get reminders for the user. Optionally filter by ID for a single reminder."""

    name: str = "get_reminders"
    description: str = (
        "Get the user's upcoming reminders. Returns pending reminders ordered by time. "
        "Pass an 'id' to fetch a single reminder's details. "
        "Use this when the user asks about their reminders."
    )
    args_schema: Type[BaseModel] = GetRemindersInput

    user_id: str
    agent_name: Optional[str] = None
    supabase_url: Optional[str] = None
    supabase_key: Optional[str] = None

    @classmethod
    def prompt_section(cls, channel: str) -> str | None:
        """Return behavioral guidance for the agent prompt, or None to omit."""
        if channel in ("web", "telegram"):
            return "Reminders: Use create_reminders to set reminders with ISO datetimes. Use get_reminders to show upcoming reminders. Use delete_reminders to cancel reminders."  # noqa: E501
        else:
            return None

    def _run(self, id: Optional[str] = None, limit: int = 10) -> str:  # noqa: A002
        return "get_reminders requires async execution. Use _arun."

    async def _arun(self, id: Optional[str] = None, limit: int = 10) -> str:  # noqa: A002
        try:
            from ..database.scoped_client import UserScopedClient
            from ..database.supabase_client import get_supabase_client
            from ..services.reminder_service import ReminderService

            raw_client = await get_supabase_client()
            db = UserScopedClient(raw_client, self.user_id)
            service = ReminderService(db)

            if id:
                reminder = await service.get_by_id(user_id=self.user_id, reminder_id=id)
                if not reminder:
                    return f"No reminder found with ID {id}."
                dt_str = reminder.get("remind_at", "unknown time")
                try:
                    dt = datetime.fromisoformat(dt_str)
                    dt_str = dt.strftime("%Y-%m-%d %H:%M %Z")
                except (ValueError, TypeError):
                    pass
                rec = f" (repeats {reminder['recurrence']})" if reminder.get("recurrence") else ""
                body_text = reminder.get("body", "")
                body_line = f"\nDetails: {body_text}" if body_text else ""
                status = reminder.get('status', 'unknown')
                return f"Reminder: [{dt_str}] {reminder['title']}{rec} (status: {status}){body_line}"

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
                lines.append(f"{i}. [{r['id']}] [{dt_str}] {r['title']}{rec}{body_preview}")

            return "\n".join(lines)

        except Exception as e:
            logger.error(f"get_reminders failed for user {self.user_id}: {e}")
            return f"Failed to get reminders: {e}"


# --- CreateRemindersTool ---

class CreateRemindersInput(BaseModel):
    """Input schema for create_reminders tool."""

    reminders: list[dict] = Field(
        ...,
        description=(
            "List of reminders to create. Each dict should have: "
            "'title' (str, required), 'remind_at' (str, ISO 8601 datetime, required), "
            "'body' (str, optional), 'recurrence' (str, optional: 'daily', 'weekly', or 'monthly')"
        ),
    )


class CreateRemindersTool(BaseTool):
    """Create one or more reminders for the user."""

    name: str = "create_reminders"
    description: str = (
        "Create reminders that will notify the user at specified times. "
        "Accepts a list of reminders, each with a title and remind_at (ISO 8601 datetime). "
        "Use this when the user asks to be reminded about something."
    )
    args_schema: Type[BaseModel] = CreateRemindersInput

    user_id: str
    agent_name: Optional[str] = None
    supabase_url: Optional[str] = None
    supabase_key: Optional[str] = None

    def _run(self, reminders: list[dict]) -> str:
        return "create_reminders requires async execution. Use _arun."

    async def _arun(self, reminders: list[dict]) -> str:
        from ..database.scoped_client import UserScopedClient
        from ..database.supabase_client import get_supabase_client
        from ..services.reminder_service import ReminderService

        raw_client = await get_supabase_client()
        db = UserScopedClient(raw_client, self.user_id)
        service = ReminderService(db)

        results = []
        for item in reminders:
            try:
                title = item.get("title")
                remind_at_str = item.get("remind_at")
                body = item.get("body")
                recurrence = item.get("recurrence")

                if not title or not remind_at_str:
                    results.append(f"Error: each reminder needs 'title' and 'remind_at'. Got: {item}")
                    continue

                parsed_dt = datetime.fromisoformat(remind_at_str.replace("Z", "+00:00"))
                now = datetime.now(timezone.utc)
                if parsed_dt <= now:
                    results.append(f"Error: remind_at must be in the future for '{title}'.")
                    continue

                if recurrence and recurrence not in ("daily", "weekly", "monthly"):
                    results.append(f"Error: invalid recurrence '{recurrence}' for '{title}'. Must be 'daily', 'weekly', or 'monthly'.")  # noqa: E501
                    continue

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
                time_str = parsed_dt.strftime('%Y-%m-%d %H:%M %Z')
                results.append(f"Reminder set: \"{title}\" at {time_str}{recurrence_msg}.")

            except ValueError as e:
                results.append(f"Error parsing remind_at for '{item.get('title', '?')}': {e}. Use ISO 8601 format.")
            except Exception as e:
                logger.error(f"create_reminders failed for item {item}: {e}")
                results.append(f"Failed to create reminder '{item.get('title', '?')}': {e}")

        return "\n".join(results)


# --- DeleteRemindersTool ---

class DeleteRemindersInput(BaseModel):
    """Input schema for delete_reminders tool."""

    ids: list[str] = Field(..., description="List of reminder IDs to delete")


class DeleteRemindersTool(BaseTool):
    """Delete (cancel) one or more reminders."""

    name: str = "delete_reminders"
    description: str = (
        "Delete reminders by their IDs. Use this when the user wants to cancel reminders. "
        "Get reminder IDs from get_reminders first."
    )
    args_schema: Type[BaseModel] = DeleteRemindersInput

    user_id: str
    agent_name: Optional[str] = None
    supabase_url: Optional[str] = None
    supabase_key: Optional[str] = None

    def _run(self, ids: list[str]) -> str:
        return "delete_reminders requires async execution. Use _arun."

    async def _arun(self, ids: list[str]) -> str:
        try:
            from ..database.scoped_client import UserScopedClient
            from ..database.supabase_client import get_supabase_client
            from ..services.reminder_service import ReminderService

            raw_client = await get_supabase_client()
            db = UserScopedClient(raw_client, self.user_id)
            service = ReminderService(db)
            deleted = await service.delete_reminders(user_id=self.user_id, ids=ids)

            if not deleted:
                return f"No reminders found with the given IDs: {', '.join(ids)}"

            not_found = set(ids) - set(deleted)
            msg = f"Deleted {len(deleted)} reminder(s)."
            if not_found:
                msg += f" Not found: {', '.join(not_found)}."
            return msg

        except Exception as e:
            logger.error(f"delete_reminders failed for user {self.user_id}: {e}")
            return f"Failed to delete reminders: {e}"


# Backward-compat aliases — agent_loader_db.py still imports old names until FU-6 updates registries
CreateReminderTool = CreateRemindersTool
ListRemindersTool = GetRemindersTool
