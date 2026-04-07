"""Gather metrics service node for introspection workflow.

Collects performance data from multiple sources:
- User feedback from notification_feedback table
- Interaction metrics from audit log / chat history
- Workflow run history
- Agent memory observations

Returns a structured metrics summary for the analysis step.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

logger = logging.getLogger(__name__)


async def gather_metrics(state: dict) -> str:
    """Collect introspection metrics from DB and config.

    Reads from step parameters: period_days, focus_areas, user_id.
    Returns JSON-formatted metrics summary as a string.
    """
    import json

    parameters = state.get("parameters", {})
    user_id = parameters.get("user_id", "")
    period_days = int(parameters.get("period_days", 7))
    focus_areas = parameters.get("focus_areas", [])

    if not user_id:
        logger.error("No user_id in workflow parameters")
        return json.dumps({"error": "no user_id in parameters"})

    since = datetime.now(timezone.utc) - timedelta(days=period_days)

    metrics: dict[str, Any] = {
        "period": {
            "start": since.isoformat(),
            "end": datetime.now(timezone.utc).isoformat(),
            "days": period_days,
        },
        "focus_areas": focus_areas,
        "feedback": {},
        "interaction_metrics": {},
        "workflow_runs": {},
    }

    # Collect from each source, tolerating failures
    metrics["feedback"] = await _collect_feedback(user_id, since)
    metrics["interaction_metrics"] = await _collect_interaction_metrics(user_id, since)
    metrics["workflow_runs"] = await _collect_workflow_runs(user_id, since)
    metrics["current_skills"] = await _collect_current_skills(user_id)

    return json.dumps(metrics, default=str)


async def _collect_feedback(user_id: str, since: datetime) -> dict[str, Any]:
    """Aggregate user feedback from notification_feedback table."""
    try:
        from ...database.supabase_client import create_system_client

        db_client = await create_system_client()
        result = await db_client.table("notification_feedback").select(
            "category, sentiment"
        ).eq("user_id", user_id).gte(
            "created_at", since.isoformat()
        ).execute()

        if not result.data:
            return {"total": 0, "positive": 0, "negative": 0, "neutral": 0, "by_category": {}}

        positive = sum(1 for r in result.data if r.get("sentiment") == "positive")
        negative = sum(1 for r in result.data if r.get("sentiment") == "negative")
        neutral = len(result.data) - positive - negative

        by_category: dict[str, dict[str, int]] = {}
        for row in result.data:
            cat = row.get("category", "general")
            if cat not in by_category:
                by_category[cat] = {"positive": 0, "negative": 0, "neutral": 0}
            sentiment = row.get("sentiment", "neutral")
            if sentiment in by_category[cat]:
                by_category[cat][sentiment] += 1

        return {
            "total": len(result.data),
            "positive": positive,
            "negative": negative,
            "neutral": neutral,
            "by_category": by_category,
        }
    except Exception as e:
        logger.warning("Failed to collect feedback metrics: %s", e)
        return {"error": str(e)}


async def _collect_interaction_metrics(user_id: str, since: datetime) -> dict[str, Any]:
    """Collect interaction metrics from chat_message_history."""
    try:
        from ...database.supabase_client import create_system_client

        db_client = await create_system_client()

        # Count messages by type
        result = await db_client.table("chat_message_history").select(
            "type"
        ).eq("user_id", user_id).gte(
            "created_at", since.isoformat()
        ).execute()

        if not result.data:
            return {"total_messages": 0, "by_type": {}}

        by_type: dict[str, int] = {}
        for row in result.data:
            msg_type = row.get("type", "unknown")
            by_type[msg_type] = by_type.get(msg_type, 0) + 1

        return {
            "total_messages": len(result.data),
            "by_type": by_type,
        }
    except Exception as e:
        logger.warning("Failed to collect interaction metrics: %s", e)
        return {"error": str(e)}


async def _collect_current_skills(user_id: str) -> dict[str, Any]:
    """Read current skill files from ConfigService (AC-25).

    Returns a summary of each skill's content (first 500 chars) so the
    analysis step has visibility into what config state produced the signals.
    """
    try:
        from ...services.config_service import get_config_service

        config = get_config_service()
        skill_paths = await config.list_paths("skills/", user_id)
        current_skills: dict[str, str] = {}
        for path in skill_paths:
            try:
                content = await config.read(path, user_id)
                if content:
                    current_skills[path] = content[:500]  # summary only
            except Exception as e:
                logger.debug("Could not read skill %s: %s", path, e)
        return current_skills
    except Exception as e:
        logger.warning("Failed to collect current skills: %s", e)
        return {}


async def _collect_workflow_runs(user_id: str, since: datetime) -> dict[str, Any]:
    """Collect workflow run history from workflow_runs table."""
    try:
        from ...database.supabase_client import create_system_client

        db_client = await create_system_client()
        result = await db_client.table("workflow_runs").select(
            "template_name, status"
        ).eq("user_id", user_id).gte(
            "created_at", since.isoformat()
        ).execute()

        if not result.data:
            return {"total": 0, "by_template": {}, "by_status": {}}

        by_template: dict[str, int] = {}
        by_status: dict[str, int] = {}
        for row in result.data:
            tpl = row.get("template_name", "unknown")
            status = row.get("status", "unknown")
            by_template[tpl] = by_template.get(tpl, 0) + 1
            by_status[status] = by_status.get(status, 0) + 1

        return {
            "total": len(result.data),
            "by_template": by_template,
            "by_status": by_status,
        }
    except Exception as e:
        logger.warning("Failed to collect workflow run metrics: %s", e)
        return {"error": str(e)}
