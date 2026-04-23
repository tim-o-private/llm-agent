"""ActivityLogService — append-only writer and scoped reader for activity_log.

Writes go through the system client because the table's RLS INSERT policy is
``service_role``-only (per SPEC-045 §4). Reads go through the user-scoped
client so user isolation is enforced at the DB.
"""

from __future__ import annotations

import asyncio
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

    # --- Extended methods (SPEC-050 FU-1) ------------------------------------

    async def list_paginated(
        self,
        user_id: str,
        *,
        limit: int = 50,
        before: str | None = None,
        workflow_run_id: str | None = None,
        status: list[str] | None = None,
        q: str | None = None,
    ) -> tuple[list[dict], bool]:
        """Return ``(entries, has_more)``.

        Cursor-based pagination: *before* is an ISO timestamp; entries with
        ``created_at < before`` are returned.  Filters compose via AND.
        """
        if self._user is None:
            raise RuntimeError("user_client required for list_paginated")

        query = (
            self._user.table("activity_log")
            .select("*")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .limit(limit + 1)  # fetch one extra to detect has_more
        )
        if before:
            query = query.lt("created_at", before)
        if workflow_run_id:
            query = query.eq("workflow_run_id", workflow_run_id)
        if status:
            query = query.in_("status", status)
        if q:
            # OR across action and actor; Supabase PostgREST supports or()
            query = query.or_(f"action.ilike.%{q}%,actor.ilike.%{q}%")

        resp = await query.execute()
        rows = list(getattr(resp, "data", None) or [])
        has_more = len(rows) > limit
        return rows[:limit], has_more

    async def count(self, user_id: str) -> int:
        """Total entries for the user."""
        if self._user is None:
            raise RuntimeError("user_client required for count")

        resp = await (
            self._user.table("activity_log")
            .select("id", count="exact")
            .eq("user_id", user_id)
            .execute()
        )
        c = getattr(resp, "count", None)
        return int(c) if c is not None else len(getattr(resp, "data", None) or [])

    async def count_since(self, user_id: str, since: str | None) -> int:
        """Entries created after *since* (ISO timestamp).

        If *since* is ``None`` (user has never viewed), returns the total count.
        """
        if self._user is None:
            raise RuntimeError("user_client required for count_since")

        query = (
            self._user.table("activity_log")
            .select("id", count="exact")
            .eq("user_id", user_id)
        )
        if since:
            query = query.gt("created_at", since)
        resp = await query.execute()
        c = getattr(resp, "count", None)
        return int(c) if c is not None else len(getattr(resp, "data", None) or [])

    async def get_counts_with_last_viewed(
        self, user_id: str
    ) -> dict:
        """Return total and since-last-viewed counts.

        Reads ``last_activity_viewed_at`` from ``user_preferences`` and
        delegates to :meth:`count` / :meth:`count_since`.
        """
        if self._user is None:
            raise RuntimeError("user_client required for get_counts_with_last_viewed")

        total_coro = self.count(user_id)
        prefs_coro = (
            self._user.table("user_preferences")
            .select("last_activity_viewed_at")
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
        total, prefs_resp = await asyncio.gather(total_coro, prefs_coro)

        prefs_data = getattr(prefs_resp, "data", None) or []
        prefs = prefs_data[0] if prefs_data else {}
        since = prefs.get("last_activity_viewed_at")

        since_count = await self.count_since(user_id, since)
        return {"total": total, "since_last_viewed": since_count}

    async def mark_viewed(self, user_id: str) -> str:
        """Set ``last_activity_viewed_at`` to now and return the timestamp."""
        if self._user is None:
            raise RuntimeError("user_client required for mark_viewed")

        now = datetime.now(timezone.utc).isoformat()
        await (
            self._user.table("user_preferences")
            .upsert(
                {"user_id": user_id, "last_activity_viewed_at": now},
                on_conflict="user_id",
            )
            .execute()
        )
        return now
