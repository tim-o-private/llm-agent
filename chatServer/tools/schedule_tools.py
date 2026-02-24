"""Schedule tools for agent integration.

Provides GetSchedulesTool, CreateSchedulesTool, and DeleteSchedulesTool for LangChain agents.
Follows the same BaseTool pattern as reminder_tools.py.
"""

import logging
from datetime import datetime, timezone
from typing import Optional, Type

from croniter import croniter
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# Day-of-week names for human-readable cron descriptions
_DOW_NAMES = {
    "0": "Sunday", "1": "Monday", "2": "Tuesday", "3": "Wednesday",
    "4": "Thursday", "5": "Friday", "6": "Saturday", "7": "Sunday",
}


def _human_readable_cron(cron_expr: str) -> str:
    """Convert a 5-field cron expression to a rough human-readable string."""
    try:
        parts = cron_expr.strip().split()
        if len(parts) != 5:
            return cron_expr

        minute, hour, dom, month, dow = parts

        time_str = ""
        if hour != "*" and minute != "*":
            time_str = f"at {hour.zfill(2)}:{minute.zfill(2)} UTC"
        elif hour != "*":
            time_str = f"at {hour.zfill(2)}:00 UTC"

        if dom == "*" and month == "*" and dow == "*":
            return f"every day {time_str}".strip() if time_str else "every minute"
        if dow != "*" and dom == "*" and month == "*":
            day_name = _DOW_NAMES.get(dow, dow)
            return f"every {day_name} {time_str}".strip()
        if dom != "*" and month == "*" and dow == "*":
            return f"monthly on day {dom} {time_str}".strip()

        return cron_expr
    except Exception:
        return cron_expr


# --- GetSchedulesTool ---

class GetSchedulesInput(BaseModel):
    """Input schema for get_schedules tool."""

    id: Optional[str] = Field(default=None, description="Optional schedule UUID to fetch a single schedule")
    active_only: bool = Field(default=True, description="If true, only show active schedules")


class GetSchedulesTool(BaseTool):
    """Get the user's agent schedules, optionally filtered by ID."""

    name: str = "get_schedules"
    description: str = (
        "Get the user's recurring agent schedules. Shows each schedule's prompt, "
        "cron expression, agent, and next run time. Optionally pass an id to fetch a single schedule. "
        "Use this when the user asks about their scheduled tasks."
    )
    args_schema: Type[BaseModel] = GetSchedulesInput

    user_id: str
    agent_name: Optional[str] = None
    supabase_url: Optional[str] = None
    supabase_key: Optional[str] = None

    @classmethod
    def prompt_section(cls, channel: str) -> str | None:
        """Return behavioral guidance for the agent prompt, or None to omit."""
        if channel in ("web", "telegram"):
            return "Schedules: When the user wants recurring work (daily summaries, weekly reports), use create_schedules with a cron expression. Use get_schedules to show existing schedules."  # noqa: E501
        else:
            return None

    def _run(self, id: Optional[str] = None, active_only: bool = True) -> str:
        return "get_schedules requires async execution. Use _arun."

    async def _arun(self, id: Optional[str] = None, active_only: bool = True) -> str:
        try:
            from chatServer.database.scoped_client import UserScopedClient
            from chatServer.database.supabase_client import get_supabase_client
            from chatServer.services.schedule_service import ScheduleService

            raw_client = await get_supabase_client()
            db = UserScopedClient(raw_client, self.user_id)

            if id:
                # Fetch a single schedule by ID
                result = (
                    await db.table("agent_schedules")
                    .select("*")
                    .eq("id", id)
                    .eq("user_id", self.user_id)
                    .maybe_single()
                    .execute()
                )
                if not result.data:
                    return f"Schedule {id} not found or does not belong to you."
                schedules = [result.data]
            else:
                service = ScheduleService(db)
                schedules = await service.list_schedules(user_id=self.user_id, active_only=active_only)

            if not schedules:
                return "You have no active schedules." if active_only else "You have no schedules."

            now = datetime.now(timezone.utc)
            lines = [f"You have {len(schedules)} schedule(s):\n"]
            for i, s in enumerate(schedules, 1):
                cron_expr = s.get("schedule_cron", "?")
                prompt_text = s.get("prompt", "")
                agent = s.get("agent_name", "assistant")
                active = s.get("active", True)
                schedule_id = s.get("id", "?")

                # Compute next run time
                next_run_str = "N/A"
                try:
                    cron = croniter(cron_expr, now)
                    next_run = cron.get_next(datetime)
                    next_run_str = next_run.strftime("%Y-%m-%d %H:%M UTC")
                except (ValueError, KeyError):
                    pass

                status = "active" if active else "paused"
                if len(prompt_text) > 80:
                    prompt_text = prompt_text[:80] + "..."

                lines.append(
                    f"{i}. [{status}] \"{prompt_text}\" | cron: {cron_expr} | "
                    f"agent: {agent} | next: {next_run_str} | id: {schedule_id}"
                )

            return "\n".join(lines)

        except Exception as e:
            logger.error(f"get_schedules failed for user {self.user_id}: {e}")
            return f"Failed to get schedules: {e}"


# --- CreateSchedulesTool ---

class CreateSchedulesInput(BaseModel):
    """Input schema for create_schedules tool."""

    schedules: list[dict] = Field(
        ...,
        description=(
            "List of schedule objects to create. Each dict should have: "
            "prompt (str, required), schedule_cron (str, required, 5-field cron), "
            "agent_name (str, optional, defaults to 'assistant'), "
            "config (dict, optional: model_override, notify_channels, schedule_type)"
        ),
    )


class CreateSchedulesTool(BaseTool):
    """Create one or more recurring agent schedules."""

    name: str = "create_schedules"
    description: str = (
        "Create one or more recurring schedules that run an agent with a given prompt on a cron schedule. "
        "Use this when the user wants something done periodically (e.g. daily summaries, weekly reports). "
        "Each schedule needs a prompt and a valid 5-field cron expression."
    )
    args_schema: Type[BaseModel] = CreateSchedulesInput

    user_id: str
    agent_name: Optional[str] = None
    supabase_url: Optional[str] = None
    supabase_key: Optional[str] = None

    def _run(self, schedules: list[dict]) -> str:
        return "create_schedules requires async execution. Use _arun."

    async def _arun(self, schedules: list[dict]) -> str:
        from chatServer.database.scoped_client import UserScopedClient
        from chatServer.database.supabase_client import get_supabase_client
        from chatServer.services.schedule_service import ScheduleService

        raw_client = await get_supabase_client()
        db = UserScopedClient(raw_client, self.user_id)
        service = ScheduleService(db)

        results = []
        for idx, entry in enumerate(schedules):
            prompt = entry.get("prompt", "")
            schedule_cron = entry.get("schedule_cron", "")
            agent_name = entry.get("agent_name", "assistant")
            config = entry.get("config")

            try:
                if not croniter.is_valid(schedule_cron):
                    results.append(f"#{idx + 1}: Error — invalid cron expression '{schedule_cron}'")
                    continue

                await service.create_schedule(
                    user_id=self.user_id,
                    agent_name=agent_name,
                    schedule_cron=schedule_cron,
                    prompt=prompt,
                    config=config,
                )

                cron = croniter(schedule_cron, datetime.now(timezone.utc))
                next_run = cron.get_next(datetime)
                next_run_str = next_run.strftime("%Y-%m-%d %H:%M UTC")
                human_cron = _human_readable_cron(schedule_cron)

                results.append(f"#{idx + 1}: Created — \"{prompt}\" runs {human_cron} (next: {next_run_str})")

            except ValueError as e:
                results.append(f"#{idx + 1}: Error — {e}")
            except Exception as e:
                logger.error(f"create_schedules item {idx + 1} failed for user {self.user_id}: {e}")
                results.append(f"#{idx + 1}: Failed — {e}")

        return "\n".join(results)


# --- DeleteSchedulesTool ---

class DeleteSchedulesInput(BaseModel):
    """Input schema for delete_schedules tool."""

    ids: list[str] = Field(..., description="List of schedule UUIDs to delete")


class DeleteSchedulesTool(BaseTool):
    """Delete one or more agent schedules."""

    name: str = "delete_schedules"
    description: str = (
        "Delete one or more recurring schedules by their IDs. "
        "Use this when the user wants to stop scheduled tasks."
    )
    args_schema: Type[BaseModel] = DeleteSchedulesInput

    user_id: str
    agent_name: Optional[str] = None
    supabase_url: Optional[str] = None
    supabase_key: Optional[str] = None

    def _run(self, ids: list[str]) -> str:
        return "delete_schedules requires async execution. Use _arun."

    async def _arun(self, ids: list[str]) -> str:
        from chatServer.database.scoped_client import UserScopedClient
        from chatServer.database.supabase_client import get_supabase_client
        from chatServer.services.schedule_service import ScheduleService

        raw_client = await get_supabase_client()
        db = UserScopedClient(raw_client, self.user_id)
        service = ScheduleService(db)

        results = []
        for schedule_id in ids:
            try:
                deleted = await service.delete_schedule(schedule_id=schedule_id, user_id=self.user_id)
                if deleted:
                    results.append(f"{schedule_id}: deleted")
                else:
                    results.append(f"{schedule_id}: not found or not yours")
            except Exception as e:
                logger.error(f"delete_schedules failed for {schedule_id}, user {self.user_id}: {e}")
                results.append(f"{schedule_id}: failed — {e}")

        return "\n".join(results)
