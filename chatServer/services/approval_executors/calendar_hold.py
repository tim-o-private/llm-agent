"""CalendarHoldExecutor — create a calendar event via Google Calendar API.

Uses ``CalendarService.create_event()`` (new in SPEC-052). Falls back with a
descriptive error if write scope is missing or credentials are unavailable.
"""

from __future__ import annotations

import logging

from . import ExecutionResult
from .registry import register_executor

logger = logging.getLogger(__name__)


@register_executor("calendar_hold")
class CalendarHoldExecutor:
    """Create a calendar event via the Google Calendar API."""

    async def execute(self, card: dict, user_id: str) -> ExecutionResult:
        payload = card.get("payload") or {}
        title = payload.get("title")
        start_at = payload.get("start_at")
        end_at = payload.get("end_at")

        if not title or not start_at or not end_at:
            missing = [k for k in ("title", "start_at", "end_at") if not payload.get(k)]
            return ExecutionResult(
                success=False,
                error=f"Missing required payload fields: {', '.join(missing)}",
            )

        try:
            credentials = await self._resolve_credentials(user_id)
            if credentials is None:
                return ExecutionResult(
                    success=False,
                    error=(
                        "Calendar not connected. Connect Google Calendar in "
                        "Settings > Integrations to enable this."
                    ),
                )

            svc = self._build_calendar_service(credentials)
            result = svc.create_event(
                title=title,
                start_at=start_at,
                end_at=end_at,
                description=payload.get("source_ref", ""),
            )

            return ExecutionResult(
                success=True,
                result=result,
                activity_action=f"Created calendar event: {title}",
            )
        except Exception as exc:
            logger.error("CalendarHoldExecutor failed for user %s: %s", user_id, exc)
            error_msg = str(exc)
            if "scope" in error_msg.lower() or "permission" in error_msg.lower():
                return ExecutionResult(
                    success=False,
                    error=(
                        "Calendar write permission missing. Reconnect Google Calendar "
                        "in Settings > Integrations with write access to enable this."
                    ),
                )
            return ExecutionResult(
                success=False,
                error=f"Calendar API error: {exc}",
            )

    async def _resolve_credentials(self, user_id: str):
        """Resolve the user's first Calendar credentials. Returns None if none connected."""
        from chatServer.tools.calendar_tools import CalendarToolProvider

        providers = await CalendarToolProvider.get_all_providers(user_id, "user")
        if not providers:
            return None
        provider = providers[0]
        return await provider.get_credentials()

    def _build_calendar_service(self, credentials):
        """Create a CalendarService. Factored out for testability."""
        from chatServer.services.calendar_service import CalendarService

        return CalendarService(credentials)
