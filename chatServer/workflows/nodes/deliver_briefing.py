"""Deliver briefing via NotificationService — service node for briefing workflows."""

import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


async def deliver_briefing(state: dict) -> str:
    """Deliver composed briefing via NotificationService.

    Reads the briefing text from step_outputs["compose-briefing"],
    sends it as a notification, and marks deferred observations consumed.
    """
    from ...database.supabase_client import create_system_client
    from ...services.notification_service import NotificationService

    step_outputs = state.get("step_outputs", {})
    briefing_text = step_outputs.get("compose-briefing", "")
    parameters = state.get("parameters", {})
    user_id = parameters.get("user_id", "")

    if not briefing_text:
        logger.warning("No briefing text to deliver for user %s", user_id)
        return "No briefing content to deliver"

    if not user_id:
        logger.error("No user_id in workflow parameters")
        return "Error: no user_id in parameters"

    db_client = await create_system_client()
    notification_service = NotificationService(db_client)

    await notification_service.notify_user(
        user_id=user_id,
        title="Morning Briefing",
        body=briefing_text,
        category="briefing",
        metadata={"source": "workflow"},
    )

    # Mark deferred observations consumed
    try:
        now = datetime.now(timezone.utc).isoformat()
        await db_client.table("deferred_observations").update(
            {"consumed_at": now}
        ).eq("user_id", user_id).is_("consumed_at", "null").execute()
    except Exception as e:
        logger.warning("Failed to mark observations consumed: %s", e)

    return "Briefing delivered"
