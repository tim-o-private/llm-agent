"""Job handler functions for each job type in the universal queue."""

import logging

from ..database.supabase_client import create_system_client

logger = logging.getLogger(__name__)


async def handle_email_processing(job: dict) -> dict:
    """Adapt job shape to EmailOnboardingService.process_job().

    job["input"]["connection_id"] → service expects {id, user_id, connection_id, status}.
    If result["success"] is False, raise RuntimeError.
    """
    from ..services.email_onboarding_service import EmailOnboardingService

    job_input = job.get("input", {})
    adapted = {
        "id": str(job["id"]),
        "user_id": str(job["user_id"]),
        "connection_id": str(job_input["connection_id"]),
        "status": job.get("status", "claimed"),
    }

    service = EmailOnboardingService()
    result = await service.process_job(adapted)

    if not result.get("success"):
        raise RuntimeError(result.get("error", "email_processing failed"))

    return result


async def handle_agent_invocation(job: dict) -> dict:
    """Wrap ScheduledExecutionService.execute().

    job["input"] IS the schedule dict (id, user_id, agent_name, prompt, config).
    If result["success"] is False, raise RuntimeError.
    """
    from ..services.scheduled_execution_service import ScheduledExecutionService

    schedule = job.get("input", {})
    service = ScheduledExecutionService()
    result = await service.execute(schedule)

    if not result.get("success"):
        raise RuntimeError(result.get("error", "agent_invocation failed"))

    return result


async def handle_reminder_delivery(job: dict) -> dict:
    """Deliver a reminder: fetch reminder, notify, mark_sent, handle_recurrence.

    Uses create_system_client() for DB access.
    Returns {"delivered": True, "reminder_id": str} or {"skipped": True} if not found.
    """
    from ..services.notification_service import NotificationService
    from ..services.reminder_service import ReminderService

    job_input = job.get("input", {})
    reminder_id = str(job_input["reminder_id"])
    user_id = str(job_input["user_id"])

    db_client = await create_system_client()
    reminder_service = ReminderService(db_client)
    reminder = await reminder_service.get_by_id(user_id, reminder_id)

    if reminder is None:
        logger.warning(f"Reminder {reminder_id} not found for user {user_id}, skipping")
        return {"skipped": True}

    notification_service = NotificationService(db_client)
    await notification_service.notify_user(
        user_id=user_id,
        title=f"Reminder: {reminder['title']}",
        body=reminder.get("body") or reminder["title"],
        category="reminder",
        metadata={"reminder_id": reminder_id},
    )

    await reminder_service.mark_sent(reminder_id)
    await reminder_service.handle_recurrence(reminder)

    return {"delivered": True, "reminder_id": reminder_id}
