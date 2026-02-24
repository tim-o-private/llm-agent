"""
Schedule Service.

Manages agent schedules: create, delete, list.
Used by schedule tools (agent-facing) and the background task loop.
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from croniter import croniter

logger = logging.getLogger(__name__)


class ScheduleService:
    """Service for managing agent schedules."""

    def __init__(self, db_client):
        self.db = db_client

    async def create_schedule(
        self,
        user_id: str,
        agent_name: str,
        schedule_cron: str,
        prompt: str,
        config: Optional[dict] = None,
    ) -> dict:
        """Create a new agent schedule.

        Args:
            user_id: Owner of the schedule.
            agent_name: Name of the agent to run.
            schedule_cron: Cron expression (validated with croniter).
            prompt: The prompt to send to the agent on each run.
            config: Optional JSONB config (model_override, notify_channels, schedule_type).

        Returns:
            The created schedule row as a dict.
        """
        if not prompt or not prompt.strip():
            raise ValueError("prompt is required and must not be empty")

        if not croniter.is_valid(schedule_cron):
            raise ValueError(f"Invalid cron expression: '{schedule_cron}'")

        # Validate agent_name exists
        agent_result = (
            await self.db.table("agent_configurations")
            .select("id")
            .eq("agent_name", agent_name)
            .maybe_single()
            .execute()
        )
        if not agent_result.data:
            raise ValueError(f"Unknown agent: '{agent_name}'")

        entry = {
            "user_id": user_id,
            "agent_name": agent_name,
            "schedule_cron": schedule_cron,
            "prompt": prompt,
            "active": True,
            "config": config or {},
        }

        result = await self.db.table("agent_schedules").insert(entry).execute()

        if not result.data or len(result.data) == 0:
            raise Exception("Failed to create schedule")

        logger.info(f"Created schedule {result.data[0]['id']} for user {user_id}")
        return result.data[0]

    async def get_schedule(self, schedule_id: str, user_id: str) -> dict | None:
        """Fetch a single schedule by ID, scoped to user.

        Returns:
            Schedule dict or None if not found.
        """
        result = (
            await self.db.table("agent_schedules")
            .select("*")
            .eq("id", schedule_id)
            .eq("user_id", user_id)
            .maybe_single()
            .execute()
        )
        return result.data

    async def delete_schedule(self, schedule_id: str, user_id: str) -> bool:
        """Soft-delete a schedule by setting active = false, scoped to the user.

        Returns:
            True if a schedule was deactivated, False if not found.
        """
        result = (
            await self.db.table("agent_schedules")
            .update({"active": False, "updated_at": datetime.now(timezone.utc).isoformat()})
            .eq("id", schedule_id)
            .eq("user_id", user_id)
            .execute()
        )

        deleted = bool(result.data and len(result.data) > 0)
        if deleted:
            logger.info(f"Soft-deleted schedule {schedule_id} for user {user_id}")
        else:
            logger.warning(f"Schedule {schedule_id} not found for user {user_id}")
        return deleted

    async def list_schedules(self, user_id: str, active_only: bool = True) -> list[dict]:
        """List schedules for a user.

        Args:
            user_id: Owner of the schedules.
            active_only: If True, only return active schedules.

        Returns:
            List of schedule dicts.
        """
        query = self.db.table("agent_schedules").select("*").eq("user_id", user_id)

        if active_only:
            query = query.eq("active", True)

        result = await query.order("created_at").execute()
        return result.data or []
