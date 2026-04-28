"""Job handler functions for each job type in the universal queue."""

import logging
from datetime import datetime, timedelta, timezone
from typing import Callable, Tuple

from ..database.supabase_client import create_system_client
from ..services.tool_resolver_service import resolve_tools_for_agent
from ..workflows.services import DEFAULT_SERVICE_REGISTRY

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
    # Lazy re-import so tests patching ``supabase_client.create_system_client``
    # intercept the call (module-level binding is captured at import time).
    from ..database.supabase_client import create_system_client
    from ..workflows.dispatch import dispatch_workflow

    job_input = job.get("input", {})
    user_id = str(job_input["user_id"])
    template_name = str(job_input["template_name"])
    parameters = job_input.get("parameters", {})

    db_client = await create_system_client()

    tool_schemas, tool_executors, _ = await resolve_tools_for_agent(user_id, "assistant")

    # Use dispatch_workflow which handles all the setup
    result_msg = await dispatch_workflow(
        args={"workflow_name": template_name, "parameters": parameters},
        user_id=user_id,
        db_client=db_client,
        llm_client=_get_llm_client_for_workflow(),
        tool_schemas=tool_schemas,
        tool_executors=tool_executors,
        service_registry=DEFAULT_SERVICE_REGISTRY,
    )

    if "Failed" in result_msg or "Error" in result_msg or "Unknown" in result_msg:
        raise RuntimeError(result_msg)

    return {"status": "started", "message": result_msg}


_workflow_llm_client = None


def _get_llm_client_for_workflow():
    """Get or create a shared LLM client for workflow execution."""
    global _workflow_llm_client
    if _workflow_llm_client is None:
        from chatServer.services.llm_client import get_llm_client
        _workflow_llm_client = get_llm_client()
    return _workflow_llm_client


async def _run_scheduled_workflow(
    job: dict,
    *,
    job_type: str,
    workflow_name: str,
    enabled_pref: str,
    default_enabled: bool,
    build_parameters: Callable[[str, dict], dict],
    compute_schedule: Callable[[dict], Tuple[datetime, datetime]],
    next_job_input: Callable[[str], dict] | None = None,
    failure_keywords: Tuple[str, ...] = ("Failed", "Error"),
) -> dict:
    """Shared skeleton for recurring workflow handlers.

    Schedule next occurrence FIRST so workflow failures don't break the
    chain, then dispatch and raise if the result matches a failure keyword.

    Uses the module-level ``create_system_client`` binding so tests patching
    ``chatServer.services.job_handlers.create_system_client`` intercept it.
    """
    from ..database.connection import get_database_manager
    from ..services.briefing_service import BriefingService
    from ..services.job_service import JobService
    from ..workflows.dispatch import dispatch_workflow

    user_id = str(job["input"]["user_id"])
    db_client = await create_system_client()
    briefing_service = BriefingService(db_client)
    prefs = await briefing_service.get_user_preferences(user_id)

    if prefs.get(enabled_pref, default_enabled):
        scheduled_for, expires_at = compute_schedule(prefs)
        db_manager = get_database_manager()
        job_service = JobService(db_manager.pool)
        payload = next_job_input(user_id) if next_job_input else {"user_id": user_id}
        await job_service.create(
            job_type=job_type,
            input=payload,
            user_id=user_id,
            scheduled_for=scheduled_for,
            expires_at=expires_at,
            max_retries=2,
        )

    tool_schemas, tool_executors, _ = await resolve_tools_for_agent(user_id, "assistant")

    result_msg = await dispatch_workflow(
        args={"workflow_name": workflow_name, "parameters": build_parameters(user_id, prefs)},
        user_id=user_id,
        db_client=db_client,
        llm_client=_get_llm_client_for_workflow(),
        tool_schemas=tool_schemas,
        tool_executors=tool_executors,
        service_registry=DEFAULT_SERVICE_REGISTRY,
    )

    if any(keyword in result_msg for keyword in failure_keywords):
        raise RuntimeError(result_msg)

    return {"status": "workflow_dispatched", "message": result_msg}


def _briefing_schedule(variant: str, default_tz: str | None = None, default_time: str | None = None):
    """Build a compute_schedule fn that uses compute_next_briefing_time."""
    from ..services.briefing_service import compute_next_briefing_time

    def _compute(prefs: dict) -> Tuple[datetime, datetime]:
        tz = prefs.get("timezone", default_tz) if default_tz else prefs["timezone"]
        if variant in ("morning", "evening"):
            time_key = f"{variant}_briefing_time"
        elif variant == "orchestration_check":
            time_key = "orchestration_check_time"
        else:
            time_key = "today_regeneration_time"
        btime = prefs.get(time_key, default_time) if default_time else prefs[time_key]
        scheduled = compute_next_briefing_time(tz, btime, variant)
        return scheduled, scheduled + timedelta(hours=4)

    return _compute


async def handle_morning_briefing(job: dict) -> dict:
    """Execute morning briefing as a workflow and self-schedule next occurrence."""
    return await _run_scheduled_workflow(
        job,
        job_type="morning_briefing",
        workflow_name="morning-briefing",
        enabled_pref="morning_briefing_enabled",
        default_enabled=True,
        compute_schedule=_briefing_schedule("morning"),
        build_parameters=lambda user_id, prefs: {
            "user_id": user_id,
            "timezone": prefs.get("timezone", "UTC"),
            "briefing_sections": prefs.get("briefing_sections", {}),
        },
    )


async def handle_evening_briefing(job: dict) -> dict:
    """Execute evening briefing as a workflow and self-schedule next occurrence."""
    return await _run_scheduled_workflow(
        job,
        job_type="evening_briefing",
        workflow_name="evening-briefing",
        enabled_pref="evening_briefing_enabled",
        default_enabled=False,
        compute_schedule=_briefing_schedule("evening"),
        build_parameters=lambda user_id, prefs: {
            "user_id": user_id,
            "timezone": prefs.get("timezone", "UTC"),
            "briefing_sections": prefs.get("briefing_sections", {}),
        },
    )


async def handle_regenerate_today(job: dict) -> dict:
    """Execute regenerate-today workflow and self-schedule next occurrence.

    Reads `today_regeneration_enabled` / `today_regeneration_time` from
    user_preferences. Uses the dedicated `regenerate_today` job_type (AC-19)
    so `fail_by_type` can cancel precisely.
    """
    return await _run_scheduled_workflow(
        job,
        job_type="regenerate_today",
        workflow_name="regenerate-today",
        enabled_pref="today_regeneration_enabled",
        default_enabled=False,
        compute_schedule=_briefing_schedule(
            "today_regen", default_tz="America/New_York", default_time="06:30"
        ),
        next_job_input=lambda user_id: {
            "user_id": user_id,
            "template_name": "regenerate-today",
        },
        build_parameters=lambda user_id, prefs: {},
        failure_keywords=("Failed", "Error", "Unknown"),
    )


async def handle_email_triage(job: dict) -> dict:
    """Execute email triage workflow and self-schedule next occurrence.

    Unlike briefings, this uses `email_triage_interval_hours` rather than a
    wall-clock time — the next run is simply now + interval.
    """
    def _compute(prefs: dict) -> Tuple[datetime, datetime]:
        interval_hours = prefs.get("email_triage_interval_hours", 6)
        scheduled = datetime.now(timezone.utc) + timedelta(hours=interval_hours)
        return scheduled, scheduled + timedelta(hours=interval_hours)

    return await _run_scheduled_workflow(
        job,
        job_type="email_triage",
        workflow_name="email-triage",
        enabled_pref="email_triage_enabled",
        default_enabled=False,
        compute_schedule=_compute,
        build_parameters=lambda user_id, prefs: {
            "user_id": user_id,
            "hours_back": prefs.get("email_triage_hours_back", 12),
            "max_emails": prefs.get("email_triage_max_emails", 20),
        },
    )


async def handle_orchestration_check(job: dict) -> dict:
    """Execute orchestration-check workflow and self-schedule next occurrence.

    Reads ``orchestration_check_enabled`` / ``orchestration_check_time`` from
    user_preferences. Uses the same ``_run_scheduled_workflow`` skeleton as
    briefings and regenerate-today.

    SPEC-054 AC-09.
    """
    return await _run_scheduled_workflow(
        job,
        job_type="orchestration_check",
        workflow_name="orchestration-check",
        enabled_pref="orchestration_check_enabled",
        default_enabled=False,
        compute_schedule=_briefing_schedule(
            "orchestration_check",
            default_tz="America/New_York",
            default_time="07:00",
        ),
        next_job_input=lambda user_id: {
            "user_id": user_id,
            "template_name": "orchestration-check",
        },
        build_parameters=lambda user_id, prefs: {},
        failure_keywords=("Failed", "Error", "Unknown"),
    )
