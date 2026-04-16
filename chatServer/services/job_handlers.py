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


async def handle_workflow(job: dict) -> dict:
    """Execute a workflow via the workflow engine.

    job["input"] contains: {user_id, template_name, parameters}.
    Returns {"run_id": str, "status": "started"}.
    """
    from ..database.supabase_client import create_system_client
    from ..workflows.dispatch import dispatch_workflow

    job_input = job.get("input", {})
    user_id = str(job_input["user_id"])
    template_name = str(job_input["template_name"])
    parameters = job_input.get("parameters", {})

    db_client = await create_system_client()

    # Use dispatch_workflow which handles all the setup
    result_msg = await dispatch_workflow(
        args={"workflow_name": template_name, "parameters": parameters},
        user_id=user_id,
        db_client=db_client,
        anthropic_client=_get_anthropic_client_for_workflow(),
        tool_schemas=[],
        tool_executors={},
    )

    if "Failed" in result_msg or "Error" in result_msg or "Unknown" in result_msg:
        raise RuntimeError(result_msg)

    return {"status": "started", "message": result_msg}


_workflow_anthropic_client = None


def _get_anthropic_client_for_workflow():
    """Get or create a shared Anthropic client for workflow execution."""
    global _workflow_anthropic_client
    if _workflow_anthropic_client is None:
        import anthropic
        _workflow_anthropic_client = anthropic.AsyncAnthropic()
    return _workflow_anthropic_client


async def handle_morning_briefing(job: dict) -> dict:
    """Execute morning briefing as a workflow and self-schedule next occurrence.

    Schedule next FIRST, then dispatch workflow — so workflow failure
    doesn't break the scheduling chain.
    """
    from datetime import timedelta

    from ..database.connection import get_database_manager
    from ..services.briefing_service import BriefingService, compute_next_briefing_time
    from ..services.job_service import JobService
    from ..workflows.dispatch import dispatch_workflow

    user_id = str(job["input"]["user_id"])
    db_client = await create_system_client()
    briefing_service = BriefingService(db_client)

    prefs = await briefing_service.get_user_preferences(user_id)

    # 1. Self-schedule next occurrence FIRST
    if prefs.get("morning_briefing_enabled", True):
        next_scheduled = compute_next_briefing_time(
            prefs["timezone"], prefs["morning_briefing_time"], "morning"
        )
        db_manager = get_database_manager()
        job_service = JobService(db_manager.pool)
        await job_service.create(
            job_type="morning_briefing",
            input={"user_id": user_id},
            user_id=user_id,
            scheduled_for=next_scheduled,
            expires_at=next_scheduled + timedelta(hours=4),
            max_retries=2,
        )

    # 2. Dispatch morning-briefing workflow
    result_msg = await dispatch_workflow(
        args={
            "workflow_name": "morning-briefing",
            "parameters": {
                "user_id": user_id,
                "timezone": prefs.get("timezone", "UTC"),
                "briefing_sections": prefs.get("briefing_sections", {}),
            },
        },
        user_id=user_id,
        db_client=db_client,
        anthropic_client=_get_anthropic_client_for_workflow(),
        tool_schemas=[],
        tool_executors={},
    )

    if "Failed" in result_msg or "Error" in result_msg:
        raise RuntimeError(result_msg)

    return {"status": "workflow_dispatched", "message": result_msg}


async def handle_evening_briefing(job: dict) -> dict:
    """Execute evening briefing as a workflow and self-schedule next occurrence.

    Same pattern as morning: schedule next first, then dispatch workflow.
    """
    from datetime import timedelta

    from ..database.connection import get_database_manager
    from ..services.briefing_service import BriefingService, compute_next_briefing_time
    from ..services.job_service import JobService
    from ..workflows.dispatch import dispatch_workflow

    user_id = str(job["input"]["user_id"])
    db_client = await create_system_client()
    briefing_service = BriefingService(db_client)

    prefs = await briefing_service.get_user_preferences(user_id)

    # 1. Self-schedule next occurrence FIRST
    if prefs.get("evening_briefing_enabled", False):
        next_scheduled = compute_next_briefing_time(
            prefs["timezone"], prefs["evening_briefing_time"], "evening"
        )
        db_manager = get_database_manager()
        job_service = JobService(db_manager.pool)
        await job_service.create(
            job_type="evening_briefing",
            input={"user_id": user_id},
            user_id=user_id,
            scheduled_for=next_scheduled,
            expires_at=next_scheduled + timedelta(hours=4),
            max_retries=2,
        )

    # 2. Dispatch evening-briefing workflow
    result_msg = await dispatch_workflow(
        args={
            "workflow_name": "evening-briefing",
            "parameters": {
                "user_id": user_id,
                "timezone": prefs.get("timezone", "UTC"),
                "briefing_sections": prefs.get("briefing_sections", {}),
            },
        },
        user_id=user_id,
        db_client=db_client,
        anthropic_client=_get_anthropic_client_for_workflow(),
        tool_schemas=[],
        tool_executors={},
    )

    if "Failed" in result_msg or "Error" in result_msg:
        raise RuntimeError(result_msg)

    return {"status": "workflow_dispatched", "message": result_msg}


async def handle_email_triage(job: dict) -> dict:
    """Execute email triage workflow and self-schedule next occurrence.

    Schedule next FIRST, then dispatch — same resilience pattern as briefings.
    """
    from datetime import timedelta

    from ..database.connection import get_database_manager
    from ..services.briefing_service import BriefingService
    from ..services.job_service import JobService
    from ..workflows.dispatch import dispatch_workflow

    user_id = str(job["input"]["user_id"])
    db_client = await create_system_client()
    briefing_service = BriefingService(db_client)

    prefs = await briefing_service.get_user_preferences(user_id)

    # 1. Self-schedule next occurrence FIRST
    interval_hours = prefs.get("email_triage_interval_hours", 6)
    if prefs.get("email_triage_enabled", False):
        from datetime import datetime, timezone

        next_scheduled = datetime.now(timezone.utc) + timedelta(hours=interval_hours)
        db_manager = get_database_manager()
        job_service = JobService(db_manager.pool)
        await job_service.create(
            job_type="email_triage",
            input={"user_id": user_id},
            user_id=user_id,
            scheduled_for=next_scheduled,
            expires_at=next_scheduled + timedelta(hours=interval_hours),
            max_retries=2,
        )

    # 2. Dispatch email-triage workflow
    hours_back = prefs.get("email_triage_hours_back", 12)
    max_emails = prefs.get("email_triage_max_emails", 20)

    result_msg = await dispatch_workflow(
        args={
            "workflow_name": "email-triage",
            "parameters": {
                "user_id": user_id,
                "hours_back": hours_back,
                "max_emails": max_emails,
            },
        },
        user_id=user_id,
        db_client=db_client,
        anthropic_client=_get_anthropic_client_for_workflow(),
        tool_schemas=[],
        tool_executors={},
    )

    if "Failed" in result_msg or "Error" in result_msg:
        raise RuntimeError(result_msg)

    return {"status": "workflow_dispatched", "message": result_msg}


