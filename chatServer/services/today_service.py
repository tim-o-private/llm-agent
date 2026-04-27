"""TodayService — composes the Today-page response.

Reads ``today.md`` via ``VaultService``, parses the known H2 sections,
merges in pending approvals and recent vault activity, and dispatches
regeneration to the workflow engine.

See SPEC-045 §"Technical Approach" §2.
"""

from __future__ import annotations

import asyncio
import logging
import re
from datetime import date, datetime, timezone
from typing import Any, Optional

from fastapi import HTTPException
from fastapi import status as http_status

from ..workflows.dispatch import dispatch_workflow
from . import markdown_sections as md
from .approval_service import ApprovalService
from .vault_service import VaultService

logger = logging.getLogger(__name__)

_TODAY_FILE = "today.md"
_SEED_TEMPLATE_REL = "templates/today.md"

_NOTES_TIMESTAMP_FMT = "%Y-%m-%dT%H:%M:%SZ"


class TodayService:
    """Composition layer for the Today surface."""

    def __init__(
        self,
        vault: VaultService,
        approvals: ApprovalService,
    ):
        self._vault = vault
        self._approvals = approvals

    async def _load_body(self, user_id: str) -> tuple[str, Optional[float]]:
        """Read today.md, seeding from the system template if missing.

        Returns ``(body, mtime)`` where mtime is the float seconds since
        epoch (serialized as float; clients pass it back as If-Match).
        """
        await self._vault.seed_if_missing(user_id, _TODAY_FILE, _SEED_TEMPLATE_REL)
        stat = await self._vault.stat_file(user_id, _TODAY_FILE)
        body = await self._vault.read_file(user_id, _TODAY_FILE)
        mtime = stat.st_mtime if stat else None
        return body, mtime

    async def get_today(self, user_id: str) -> dict:
        body, mtime = await self._load_body(user_id)
        doc = md.parse(body)

        approvals, recent = await asyncio.gather(
            self._approvals.list_pending(user_id),
            self._vault.list_recent(user_id, limit=10),
        )

        return {
            "date": date.today().isoformat(),
            "header": {"framing": md.extract_framing(body, doc)},
            "your_day": md.extract_your_day(body, doc),
            "to_do": md.extract_todos(body, doc),
            "notes": md.extract_notes(body, doc),
            "agent": {
                "running": [],
                "watching": [],
                "recent": [],
                "blocked": [],
            },
            "approvals": approvals,
            "recent": [
                {"path": r.path, "updated_at": r.updated_at} for r in recent
            ],
            "source_mtime": mtime,
            "unknown_sections": [
                s.name for s in doc.sections if s.key not in md.KNOWN_SECTIONS
            ],
        }

    async def get_source(self, user_id: str) -> dict:
        body, mtime = await self._load_body(user_id)
        return {"body": body, "source_mtime": mtime}

    async def append_note(
        self, user_id: str, text: str
    ) -> dict:
        if not isinstance(text, str) or not text.strip():
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail="Note text required",
            )
        body, _ = await self._load_body(user_id)
        ts = datetime.now(timezone.utc).strftime(_NOTES_TIMESTAMP_FMT)
        line = f"- [{ts}] {text.strip()}"
        new_body = md.append_to_section(body, "Notes", line)
        new_mtime = await self._vault.update_body(user_id, _TODAY_FILE, new_body)
        return {
            "created_at": ts,
            "text": text.strip(),
            "source_mtime": new_mtime,
        }

    async def toggle_todo(
        self,
        user_id: str,
        line_id: str,
        checked: bool,
        expected_mtime: Optional[float] = None,
    ) -> dict:
        body, _ = await self._load_body(user_id)
        new_body, found = md.replace_todo_line(body, line_id, checked=checked)
        if not found:
            raise HTTPException(
                status_code=http_status.HTTP_409_CONFLICT,
                detail="Todo line not found — file may have been rewritten",
            )
        new_mtime = await self._vault.update_body(
            user_id, _TODAY_FILE, new_body, expected_mtime=expected_mtime
        )
        return {
            "line_id": line_id,
            "checked": checked,
            "source_mtime": new_mtime,
        }

    async def regenerate(
        self,
        user_id: str,
        db_client: Any,
        llm_client: Any,
    ) -> str:
        """Dispatch a ``regenerate-today`` workflow run. Returns run_id.

        Routes through the canonical ``dispatch_workflow`` entry point —
        the same path used by every scheduled briefing handler — rather
        than hand-rolling a ``WorkflowRunManager``.
        """
        try:
            result_msg = await dispatch_workflow(
                args={"workflow_name": "regenerate-today", "parameters": {}},
                user_id=user_id,
                db_client=db_client,
                llm_client=llm_client,
                tool_schemas=[],
                tool_executors={},
            )
        except Exception as exc:
            logger.error("regenerate-today dispatch failed: %s", exc, exc_info=True)
            raise HTTPException(
                status_code=http_status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Regeneration temporarily unavailable",
            ) from exc

        match = re.search(r"\(run_id:\s*([^)]+)\)", result_msg)
        if not match:
            logger.error("regenerate-today dispatch failed: %s", result_msg)
            raise HTTPException(
                status_code=http_status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Regeneration temporarily unavailable",
            )
        return match.group(1).strip()
