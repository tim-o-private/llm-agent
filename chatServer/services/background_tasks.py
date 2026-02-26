"""Background task service for managing scheduled tasks."""

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Tuple

from croniter import croniter

from ..config.constants import SCHEDULED_TASK_INTERVAL_SECONDS, SESSION_INSTANCE_TTL_SECONDS
from ..database.connection import get_database_manager
from ..database.supabase_client import create_system_client
from .job_handlers import handle_agent_invocation, handle_email_processing, handle_reminder_delivery
from .job_runner_service import JobRunnerService
from .job_service import JobService

logger = logging.getLogger(__name__)


class BackgroundTaskService:
    """Service for managing background tasks like session cleanup, cache eviction, and scheduled agent execution."""

    def __init__(self):
        self.deactivate_task: Optional[asyncio.Task] = None
        self.evict_task: Optional[asyncio.Task] = None
        self.scheduled_agents_task: Optional[asyncio.Task] = None
        self.reminder_task: Optional[asyncio.Task] = None
        self.job_runner_task: Optional[asyncio.Task] = None
        self._agent_executor_cache: Optional[Dict[Tuple[str, str], Any]] = None
        self.agent_schedules: Dict[str, Dict] = {}
        self._last_schedule_check: Optional[datetime] = None
        self._job_service = None
        self._job_runner = None

    def set_agent_executor_cache(self, cache: Dict[Tuple[str, str], Any]) -> None:
        """Set the agent executor cache reference for eviction tasks."""
        self._agent_executor_cache = cache

    async def deactivate_stale_chat_session_instances(self) -> None:
        """Periodically deactivates stale chat session instances."""
        while True:
            await asyncio.sleep(SCHEDULED_TASK_INTERVAL_SECONDS)
            logger.debug("Running task: deactivate_stale_chat_session_instances")

            db_manager = get_database_manager()
            if db_manager.pool is None:
                logger.warning("db_pool not available, skipping deactivation task cycle.")
                continue

            try:
                async with db_manager.pool.connection() as conn:
                    async with conn.cursor() as cur:
                        threshold_time = datetime.now(timezone.utc) - timedelta(seconds=SESSION_INSTANCE_TTL_SECONDS)
                        await cur.execute(
                            """UPDATE chat_sessions
                               SET is_active = false, updated_at = %s
                               WHERE is_active = true AND updated_at < %s""",
                            (datetime.now(timezone.utc), threshold_time)
                        )
                        if cur.rowcount > 0:
                            logger.info(f"Deactivated {cur.rowcount} stale chat session instances.")
            except Exception as e:
                logger.error(f"Error in deactivate_stale_chat_session_instances: {e}", exc_info=True)

    async def evict_inactive_executors(self) -> None:
        """Periodically evicts agent executors if no active session instances exist for them."""
        while True:
            await asyncio.sleep(SCHEDULED_TASK_INTERVAL_SECONDS + 30)  # Stagger slightly from the other task
            logger.debug("Running task: evict_inactive_executors")

            db_manager = get_database_manager()
            if db_manager.pool is None or self._agent_executor_cache is None:
                logger.warning("db_pool or agent_executor_cache not available, skipping eviction task cycle.")
                continue

            keys_to_evict = []
            # Create a copy of keys to iterate over as cache might be modified
            current_cache_keys = list(self._agent_executor_cache.keys())

            for user_id, agent_name in current_cache_keys:
                try:
                    async with db_manager.pool.connection() as conn:
                        async with conn.cursor() as cur:
                            await cur.execute(
                                """SELECT 1 FROM chat_sessions
                                   WHERE user_id = %s AND agent_name = %s AND is_active = true LIMIT 1""",
                                (user_id, agent_name)
                            )
                            active_session_exists = await cur.fetchone()
                            if not active_session_exists:
                                keys_to_evict.append((user_id, agent_name))
                except Exception as e:
                    logger.error(f"Error checking active sessions for ({user_id}, {agent_name}): {e}", exc_info=True)

            for key in keys_to_evict:
                if key in self._agent_executor_cache:
                    del self._agent_executor_cache[key]
                    logger.info(f"Evicted agent executor for {key} due to no active sessions.")

    async def run_scheduled_agents(self) -> None:
        """Execute scheduled agents (like daily email digest)."""
        while True:
            await asyncio.sleep(60)  # Check every minute
            logger.debug("Running task: run_scheduled_agents")

            db_manager = get_database_manager()
            if db_manager.pool is None:
                logger.warning("db_pool not available, skipping scheduled agents task cycle.")
                continue

            try:
                current_time = datetime.now(timezone.utc)

                # Reload schedules periodically (every 5 minutes) or on first run
                if (self._last_schedule_check is None or
                    current_time - self._last_schedule_check > timedelta(minutes=1)):
                    await self._reload_agent_schedules()
                    self._last_schedule_check = current_time

                # Check for agents that need to run
                for schedule_id, schedule in self.agent_schedules.items():
                    if self._should_run_now(schedule, current_time):
                        # Create task for async execution without blocking the loop
                        asyncio.create_task(self._execute_scheduled_agent(schedule))

            except Exception as e:
                logger.error(f"Error in run_scheduled_agents: {e}", exc_info=True)

    async def _reload_agent_schedules(self) -> None:
        """Reload agent schedules from database."""
        try:
            db_manager = get_database_manager()
            async with db_manager.pool.connection() as conn:
                async with conn.cursor() as cur:
                    await cur.execute("""
                        SELECT id, user_id, agent_name, schedule_cron, prompt, config
                        FROM agent_schedules
                        WHERE active = true
                    """)

                    schedules = await cur.fetchall()

                    # Clear existing schedules and reload
                    self.agent_schedules.clear()

                    for schedule_row in schedules:
                        schedule_id, user_id, agent_name, schedule_cron, prompt, config = schedule_row

                        self.agent_schedules[str(schedule_id)] = {
                            'id': schedule_id,
                            'user_id': str(user_id),
                            'agent_name': agent_name,
                            'schedule_cron': schedule_cron,
                            'prompt': prompt,
                            'config': config or {},
                            'last_run': None  # Track last execution time
                        }

                    logger.info(f"Loaded {len(self.agent_schedules)} active agent schedules")

        except Exception as e:
            logger.error(f"Error reloading agent schedules: {e}", exc_info=True)

    def _should_run_now(self, schedule: Dict, current_time: datetime) -> bool:
        """Check if a schedule should run now based on cron expression."""
        try:
            cron_expr = schedule['schedule_cron']
            last_run = schedule.get('last_run')

            # Create croniter instance
            cron = croniter(cron_expr, current_time)

            # Get the previous scheduled time
            prev_time = cron.get_prev(datetime)

            # If we've never run, or the previous scheduled time is after our last run
            if last_run is None or prev_time > last_run:
                # Check if we're within 2 minutes of the scheduled time to avoid missing runs
                time_diff = abs((current_time - prev_time).total_seconds())
                if time_diff <= 120:  # Within 2 minutes
                    schedule['last_run'] = current_time  # Update last run time
                    return True

            return False

        except Exception as e:
            logger.error(f"Error checking schedule for {schedule.get('id')}: {e}")
            return False

    async def _execute_scheduled_agent(self, schedule: Dict) -> None:
        """Execute a single scheduled agent.

        Email digest schedules use EmailDigestService for backward compatibility.
        All other schedules enqueue an agent_invocation job via the job queue.
        """
        schedule_id = schedule.get('id')
        user_id = schedule.get('user_id')
        agent_name = schedule.get('agent_name')
        prompt = schedule.get('prompt', '')
        config = schedule.get('config', {})

        try:
            logger.info(f"Scheduling agent {agent_name} for user {user_id} (schedule {schedule_id})")

            # TODO: SPEC-020 — Remove email digest special case. The agent should
            # use search_gmail and reason about results instead of a dedicated service.
            # Keeping for now to avoid breaking existing scheduled digests.
            is_email_digest = (
                'email digest' in prompt.lower()
                and config.get('schedule_type') != 'heartbeat'
            )

            if is_email_digest:
                logger.warning("Email digest schedule detected — this path is deprecated (SPEC-020)")
                from ..services.email_digest_service import EmailDigestService

                service = EmailDigestService(user_id, context="scheduled")
                result = await service.generate_digest(
                    hours_back=config.get('hours_back', 24),
                    include_read=config.get('include_read', False),
                    context="scheduled"
                )

                if result.get("success"):
                    logger.info(f"Scheduled email digest completed for user {user_id}")
                else:
                    logger.error(f"Scheduled email digest failed for user {user_id}: {result.get('error')}")
            else:
                # All other schedules enqueue an agent_invocation job
                if self._job_service is None:
                    logger.error(
                        f"job_service not initialized, cannot enqueue agent_invocation "
                        f"for schedule {schedule_id}"
                    )
                    return

                await self._job_service.create(
                    job_type='agent_invocation',
                    input={
                        'id': str(schedule_id),
                        'user_id': user_id,
                        'agent_name': agent_name,
                        'prompt': prompt,
                        'config': config,
                    },
                    user_id=user_id,
                )
                logger.info(
                    f"Enqueued agent_invocation job for {agent_name} (schedule {schedule_id})"
                )

        except Exception as e:
            logger.error(f"Scheduled agent execution failed for schedule {schedule_id}: {e}", exc_info=True)

    async def check_due_reminders(self) -> None:
        """Check for due reminders every 60 seconds and enqueue delivery jobs."""
        while True:
            await asyncio.sleep(60)
            logger.debug("Running task: check_due_reminders")

            try:
                if self._job_service is None:
                    logger.warning("job_service not available, skipping reminder enqueue cycle.")
                    continue

                db_client = await create_system_client()

                from ..services.reminder_service import ReminderService

                reminder_service = ReminderService(db_client)
                due = await reminder_service.get_due_reminders()

                for reminder in due:
                    try:
                        await self._job_service.create(
                            job_type='reminder_delivery',
                            input={
                                'reminder_id': str(reminder['id']),
                                'user_id': reminder['user_id'],
                            },
                            user_id=reminder['user_id'],
                        )
                    except Exception as e:
                        logger.error(f"Failed to enqueue reminder {reminder.get('id')}: {e}")
            except Exception as e:
                logger.error(f"Error in check_due_reminders: {e}", exc_info=True)

    def start_background_tasks(self) -> None:
        """Start all background tasks."""
        db_manager = get_database_manager()
        self._job_service = JobService(db_manager.pool)
        self._job_runner = JobRunnerService(self._job_service)
        self._job_runner.register_handler('email_processing', handle_email_processing)
        self._job_runner.register_handler('agent_invocation', handle_agent_invocation)
        self._job_runner.register_handler('reminder_delivery', handle_reminder_delivery)

        self.deactivate_task = asyncio.create_task(self.deactivate_stale_chat_session_instances())
        self.evict_task = asyncio.create_task(self.evict_inactive_executors())
        self.scheduled_agents_task = asyncio.create_task(self.run_scheduled_agents())
        self.reminder_task = asyncio.create_task(self.check_due_reminders())
        self.job_runner_task = asyncio.create_task(self._job_runner.run())
        logger.info(
            "Background tasks for session cleanup, cache eviction, scheduled agents, "
            "reminders, and job runner started."
        )

    async def stop_background_tasks(self) -> None:
        """Stop all background tasks gracefully."""
        if self.deactivate_task:
            self.deactivate_task.cancel()
            logger.info("Deactivate stale sessions task cancelling...")
            try:
                await self.deactivate_task
            except asyncio.CancelledError:
                logger.info("Deactivate stale sessions task successfully cancelled.")

        if self.evict_task:
            self.evict_task.cancel()
            logger.info("Evict inactive executors task cancelling...")
            try:
                await self.evict_task
            except asyncio.CancelledError:
                logger.info("Evict inactive executors task successfully cancelled.")

        if self.scheduled_agents_task:
            self.scheduled_agents_task.cancel()
            logger.info("Scheduled agents task cancelling...")
            try:
                await self.scheduled_agents_task
            except asyncio.CancelledError:
                logger.info("Scheduled agents task successfully cancelled.")

        if self.reminder_task:
            self.reminder_task.cancel()
            logger.info("Reminder delivery task cancelling...")
            try:
                await self.reminder_task
            except asyncio.CancelledError:
                logger.info("Reminder delivery task successfully cancelled.")

        if self.job_runner_task:
            self.job_runner_task.cancel()
            logger.info("Job runner task cancelling...")
            try:
                await self.job_runner_task
            except asyncio.CancelledError:
                logger.info("Job runner task successfully cancelled.")


# Global instance for use in main.py
_background_task_service: Optional[BackgroundTaskService] = None


def get_background_task_service() -> BackgroundTaskService:
    """Get the global background task service instance."""
    global _background_task_service
    if _background_task_service is None:
        _background_task_service = BackgroundTaskService()
    return _background_task_service
