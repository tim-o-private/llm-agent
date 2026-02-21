"""Schedule tools for agent integration.

Provides CreateScheduleTool, DeleteScheduleTool, and ListSchedulesTool for LangChain agents.
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


class CreateScheduleInput(BaseModel):
    """Input schema for create_schedule tool."""

    prompt: str = Field(..., description="The prompt to send to the agent on each scheduled run")
    schedule_cron: str = Field(
        ...,
        description=(
            "Cron expression defining the schedule (e.g. '0 7 * * *' for daily at 7 AM UTC, "
            "'0 9 * * 1' for every Monday at 9 AM UTC). Uses standard 5-field cron syntax."
        ),
    )
    agent_name: str = Field(
        default="assistant",
        description="Name of the agent to run (defaults to 'assistant')",
    )
    config: Optional[dict] = Field(
        default=None,
        description="Optional configuration: model_override, notify_channels, schedule_type",
    )


class CreateScheduleTool(BaseTool):
    """Create a recurring agent schedule."""

    name: str = "create_schedule"
    description: str = (
        "Create a recurring schedule that runs an agent with a given prompt on a cron schedule. "
        "Use this when the user wants something done periodically (e.g. daily summaries, weekly reports). "
        "The schedule_cron must be a valid 5-field cron expression."
    )
    args_schema: Type[BaseModel] = CreateScheduleInput

    user_id: str
    agent_name: Optional[str] = None
    supabase_url: Optional[str] = None
    supabase_key: Optional[str] = None

    @classmethod
    def prompt_section(cls, channel: str) -> str | None:
        """Return behavioral guidance for the agent prompt, or None to omit."""
        if channel in ("web", "telegram"):
            return "Schedules: When the user wants recurring work (daily summaries, weekly reports), use create_schedule with a cron expression. Use list_schedules to show existing schedules."  # noqa: E501
        else:
            return None

    def _run(
        self,
        prompt: str,
        schedule_cron: str,
        agent_name: str = "assistant",
        config: Optional[dict] = None,
    ) -> str:
        return "create_schedule requires async execution. Use _arun."

    async def _arun(
        self,
        prompt: str,
        schedule_cron: str,
        agent_name: str = "assistant",
        config: Optional[dict] = None,
    ) -> str:
        try:
            if not croniter.is_valid(schedule_cron):
                return f"Error: invalid cron expression '{schedule_cron}'. Use standard 5-field cron syntax."

            from chatServer.database.supabase_client import get_supabase_client
            from chatServer.services.schedule_service import ScheduleService

            db = await get_supabase_client()
            service = ScheduleService(db)
            await service.create_schedule(
                user_id=self.user_id,
                agent_name=agent_name,
                schedule_cron=schedule_cron,
                prompt=prompt,
                config=config,
            )

            # Compute human-readable description and next run time
            cron = croniter(schedule_cron, datetime.now(timezone.utc))
            next_run = cron.get_next(datetime)
            next_run_str = next_run.strftime("%Y-%m-%d %H:%M UTC")

            # Build a human-readable cron description
            human_cron = _human_readable_cron(schedule_cron)

            return (
                f"Schedule created: {prompt} \u2014 runs {human_cron} "
                f"(next: {next_run_str})"
            )

        except ValueError as e:
            return f"Error: {e}"
        except Exception as e:
            logger.error(f"create_schedule failed for user {self.user_id}: {e}")
            return f"Failed to create schedule: {e}"


class DeleteScheduleInput(BaseModel):
    """Input schema for delete_schedule tool."""

    schedule_id: str = Field(..., description="The UUID of the schedule to delete")


class DeleteScheduleTool(BaseTool):
    """Delete an agent schedule."""

    name: str = "delete_schedule"
    description: str = (
        "Delete a recurring schedule by its ID. "
        "Use this when the user wants to stop a scheduled task."
    )
    args_schema: Type[BaseModel] = DeleteScheduleInput

    user_id: str
    agent_name: Optional[str] = None
    supabase_url: Optional[str] = None
    supabase_key: Optional[str] = None

    def _run(self, schedule_id: str) -> str:
        return "delete_schedule requires async execution. Use _arun."

    async def _arun(self, schedule_id: str) -> str:
        try:
            from chatServer.database.supabase_client import get_supabase_client
            from chatServer.services.schedule_service import ScheduleService

            db = await get_supabase_client()
            service = ScheduleService(db)
            deleted = await service.delete_schedule(schedule_id=schedule_id, user_id=self.user_id)

            if deleted:
                return f"Schedule {schedule_id} deleted successfully."
            else:
                return f"Schedule {schedule_id} not found or does not belong to you."

        except Exception as e:
            logger.error(f"delete_schedule failed for user {self.user_id}: {e}")
            return f"Failed to delete schedule: {e}"


class ListSchedulesInput(BaseModel):
    """Input schema for list_schedules tool."""

    active_only: bool = Field(default=True, description="If true, only show active schedules")


class ListSchedulesTool(BaseTool):
    """List the user's agent schedules."""

    name: str = "list_schedules"
    description: str = (
        "List the user's recurring agent schedules. Shows each schedule's prompt, "
        "cron expression, agent, and next run time. "
        "Use this when the user asks about their scheduled tasks."
    )
    args_schema: Type[BaseModel] = ListSchedulesInput

    user_id: str
    agent_name: Optional[str] = None
    supabase_url: Optional[str] = None
    supabase_key: Optional[str] = None

    def _run(self, active_only: bool = True) -> str:
        return "list_schedules requires async execution. Use _arun."

    async def _arun(self, active_only: bool = True) -> str:
        try:
            from chatServer.database.supabase_client import get_supabase_client
            from chatServer.services.schedule_service import ScheduleService

            db = await get_supabase_client()
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
            logger.error(f"list_schedules failed for user {self.user_id}: {e}")
            return f"Failed to list schedules: {e}"
