"""ActivityLogService — append-only writer and scoped reader for activity_log.

Writes go through the system client because the table's RLS INSERT policy is
``service_role``-only (per SPEC-045 §4). Reads go through the user-scoped
client so user isolation is enforced at the DB.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)

_VALID_STATUSES = frozenset({"done", "failed", "awaiting_approval"})


class ActivityLogService:
    """Append entries to ``activity_log`` and read a user's entries.

    ``system_client`` must be a ``SystemClient`` (unscoped) — required for
    the service-role INSERT policy.
    ``user_client`` (optional) is a ``UserScopedClient`` used for reads.
    """

    def __init__(
        self,
        system_client: Any,
        user_client: Optional[Any] = None,
    ):
        self._system = system_client
        self._user = user_client

    async def append(
        self,
        *,
        user_id: str,
        actor: str,
        action: str,
        status: str,
        subject_path: Optional[str] = None,
        workflow_run_id: Optional[str] = None,
        reasoning: Optional[str] = None,
    ) -> dict:
        """Insert a new activity_log row via the system client.

        Returns the inserted row. Raises ``ValueError`` on bad status.
        """
        if status not in _VALID_STATUSES:
            raise ValueError(
                f"status must be one of {sorted(_VALID_STATUSES)}, got {status!r}"
            )

        payload: dict[str, Any] = {
            "user_id": user_id,
            "actor": actor,
            "action": action,
            "status": status,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        if subject_path is not None:
            payload["subject_path"] = subject_path
        if workflow_run_id is not None:
            payload["workflow_run_id"] = workflow_run_id
        if reasoning is not None:
            payload["reasoning"] = reasoning

        resp = await self._system.table("activity_log").insert(payload).execute()
        rows = getattr(resp, "data", None) or []
        return rows[0] if rows else payload

    async def list_recent(self, user_id: str, limit: int = 50) -> list[dict]:
        """Read the user's recent activity via the user-scoped client."""
        if self._user is None:
            raise RuntimeError("user_client required for list_recent")
        resp = await (
            self._user.table("activity_log")
            .select("*")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return list(getattr(resp, "data", None) or [])
