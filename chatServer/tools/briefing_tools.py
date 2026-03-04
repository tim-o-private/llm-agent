"""Briefing preferences tool for agent integration.

Manages morning/evening briefing configuration via conversation.
Uses lazy imports to avoid circular dependency (same pattern as calendar_tools.py).
"""

import logging
from typing import Optional, Type

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


def _get_briefing_service():
    """Lazy import to avoid circular dependency."""
    from chatServer.services.briefing_service import BriefingService
    return BriefingService


class ManageBriefingPreferencesInput(BaseModel):
    """Input schema for update_briefing_preferences tool."""
    action: str = Field(..., description="Action: 'get' to view current settings, 'update' to change them")
    preferences: Optional[dict] = Field(
        default=None,
        description=(
            "For 'update' action: dict with any of: timezone (IANA string), "
            "morning_briefing_enabled (bool), morning_briefing_time (HH:MM), "
            "evening_briefing_enabled (bool), evening_briefing_time (HH:MM), "
            "briefing_sections (dict of section: bool)"
        ),
    )


class ManageBriefingPreferencesTool(BaseTool):
    """View or update briefing preferences (morning/evening briefing time, timezone, enabled/disabled)."""

    name: str = "update_briefing_preferences"
    description: str = (
        "View or update briefing preferences (morning/evening briefing time, "
        "timezone, enabled/disabled). Use 'get' to view current settings, "
        "'update' to change them."
    )
    args_schema: Type[BaseModel] = ManageBriefingPreferencesInput

    # Required instance fields (set by tool loader)
    user_id: str
    agent_name: Optional[str] = None
    supabase_url: Optional[str] = None
    supabase_key: Optional[str] = None

    @classmethod
    def prompt_section(cls, channel: str) -> str | None:
        """Behavioral guidance for the agent prompt."""
        if channel in ("web", "telegram", "scheduled"):
            return (
                "Briefings: Use update_briefing_preferences to check or update "
                "the user's morning/evening briefing schedule. Ask about timezone "
                "when setting up for the first time."
            )
        return None

    def _run(self, **kwargs) -> str:
        return "update_briefing_preferences requires async execution. Use _arun."

    async def _arun(self, action: str, preferences: Optional[dict] = None) -> str:
        try:
            from ..database.scoped_client import UserScopedClient
            from ..database.supabase_client import get_supabase_client

            BriefingService = _get_briefing_service()

            raw_client = await get_supabase_client()
            db = UserScopedClient(raw_client, self.user_id)
            service = BriefingService(db)

            if action == "get":
                return await self._handle_get(service)
            elif action == "update":
                return await self._handle_update(service, preferences or {})
            else:
                return f"Unknown action: {action}. Use 'get' or 'update'."

        except ValueError as e:
            return f"Validation error: {e}"
        except Exception as e:
            logger.error(f"update_briefing_preferences failed for user {self.user_id}: {e}")
            return f"Failed to manage briefing preferences: {e}"

    async def _handle_get(self, service) -> str:
        """Get current briefing preferences."""
        prefs = await service.get_user_preferences(self.user_id)

        # Format time for display (strip :00 seconds suffix)
        morning_time = prefs.get("morning_briefing_time", "07:30:00")
        evening_time = prefs.get("evening_briefing_time", "20:00:00")
        if isinstance(morning_time, str) and morning_time.endswith(":00") and len(morning_time) == 8:
            morning_time = morning_time[:5]
        if isinstance(evening_time, str) and evening_time.endswith(":00") and len(evening_time) == 8:
            evening_time = evening_time[:5]

        lines = [
            "**Briefing Preferences:**",
            f"- Timezone: {prefs.get('timezone', 'America/New_York')}",
            f"- Morning briefing: {'enabled' if prefs.get('morning_briefing_enabled') else 'disabled'} at {morning_time}",  # noqa: E501
            f"- Evening briefing: {'enabled' if prefs.get('evening_briefing_enabled') else 'disabled'} at {evening_time}",  # noqa: E501
        ]

        sections = prefs.get("briefing_sections", {})
        if sections:
            enabled = [k for k, v in sections.items() if v]
            if enabled:
                lines.append(f"- Sections: {', '.join(enabled)}")

        return "\n".join(lines)

    async def _handle_update(self, service, preferences: dict) -> str:
        """Update briefing preferences with job creation/cancellation side effects."""
        # Get current prefs for detecting enable/disable changes
        old_prefs = await service.get_user_preferences(self.user_id)

        # Perform the update (validates internally)
        updated = await service.update_user_preferences(self.user_id, preferences)

        # Handle job side effects
        messages = ["Preferences updated."]
        await self._handle_job_side_effects(old_prefs, updated, preferences, messages)

        return "\n".join(messages)

    async def _handle_job_side_effects(
        self, old_prefs: dict, new_prefs: dict, updates: dict, messages: list
    ) -> None:
        """Create/cancel briefing jobs based on preference changes."""
        from datetime import timedelta

        from ..database.connection import get_database_manager
        from ..services.briefing_service import compute_first_briefing_time
        from ..services.job_service import JobService

        db_manager = get_database_manager()
        job_service = JobService(db_manager.pool)

        for briefing_type in ("morning", "evening"):
            enabled_key = f"{briefing_type}_briefing_enabled"
            time_key = f"{briefing_type}_briefing_time"
            job_type = f"{briefing_type}_briefing"

            was_enabled = old_prefs.get(enabled_key, briefing_type == "morning")
            is_enabled = new_prefs.get(enabled_key, was_enabled)
            time_changed = time_key in updates or "timezone" in updates

            # Disable: cancel pending jobs
            if was_enabled and not is_enabled:
                count = await job_service.fail_by_type(
                    self.user_id, job_type, "Briefing disabled by user"
                )
                messages.append(f"{briefing_type.title()} briefing disabled, {count} pending job(s) cancelled.")

            # Enable: create first job
            elif not was_enabled and is_enabled:
                tz = new_prefs.get("timezone", "America/New_York")
                btime = new_prefs.get(time_key, "07:30:00" if briefing_type == "morning" else "20:00:00")
                # Strip seconds for computation
                if isinstance(btime, str) and len(btime) == 8 and btime.endswith(":00"):
                    btime_short = btime[:5]
                else:
                    btime_short = btime
                scheduled_for = compute_first_briefing_time(tz, btime_short)
                await job_service.create(
                    job_type=job_type,
                    input={"user_id": self.user_id},
                    user_id=self.user_id,
                    scheduled_for=scheduled_for,
                    expires_at=scheduled_for + timedelta(hours=4),
                    max_retries=2,
                )
                messages.append(f"{briefing_type.title()} briefing enabled, first one scheduled.")

            # Time/timezone changed while enabled: cancel old, create new
            elif is_enabled and time_changed:
                await job_service.fail_by_type(
                    self.user_id, job_type, "Briefing time changed"
                )
                tz = new_prefs.get("timezone", "America/New_York")
                btime = new_prefs.get(time_key, "07:30:00" if briefing_type == "morning" else "20:00:00")
                if isinstance(btime, str) and len(btime) == 8 and btime.endswith(":00"):
                    btime_short = btime[:5]
                else:
                    btime_short = btime
                scheduled_for = compute_first_briefing_time(tz, btime_short)
                await job_service.create(
                    job_type=job_type,
                    input={"user_id": self.user_id},
                    user_id=self.user_id,
                    scheduled_for=scheduled_for,
                    expires_at=scheduled_for + timedelta(hours=4),
                    max_retries=2,
                )
                messages.append(f"{briefing_type.title()} briefing rescheduled with new time.")
