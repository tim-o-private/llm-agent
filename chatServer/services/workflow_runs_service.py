"""Read-side service for the `workflow_runs` table.

Routers delegate here per A1; cross-user isolation is enforced by the
user-scoped client (A8) plus Postgres RLS.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from ..database.scoped_client import UserScopedClient

logger = logging.getLogger(__name__)

_RUN_COLUMNS = "id,template_name,status,current_step,error,started_at,completed_at,created_at"

_DETAILED_COLUMNS = (
    "id,template_name,status,current_step,error,"
    "parameters,step_outputs,started_at,completed_at,created_at"
)


class WorkflowRunsService:
    def __init__(self, db: UserScopedClient):
        self._db = db

    async def list_runs(
        self,
        *,
        template_name: Optional[str] = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        query = (
            self._db.table("workflow_runs")
            .select(_RUN_COLUMNS)
            .order("created_at", desc=True)
            .limit(limit)
        )
        if template_name is not None:
            query = query.eq("template_name", template_name)

        result = await query.execute()
        return list(result.data or [])

    async def list_runs_detailed(
        self,
        *,
        template_name: Optional[str] = None,
        limit: int = 25,
    ) -> list[dict[str, Any]]:
        """Like ``list_runs`` but selects all columns including
        ``step_outputs`` and ``parameters`` for the run detail view.
        """
        query = (
            self._db.table("workflow_runs")
            .select(_DETAILED_COLUMNS)
            .order("created_at", desc=True)
            .limit(limit)
        )
        if template_name is not None:
            query = query.eq("template_name", template_name)

        result = await query.execute()
        return list(result.data or [])
