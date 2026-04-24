"""ApprovalService — state machine + edit path for approval_cards.

- approve / reject flip ``status`` and record ``decided_at`` / ``decided_by``.
- Edit mutates the JSONB ``payload`` and leaves status=pending.
- Every transition emits an ``activity_log`` row via ``ActivityLogService``.
- After approval, dispatches execution via the executor pattern (SPEC-052).

INSERT is out of scope for this spec (agent-side work lands later).
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import HTTPException
from fastapi import status as http_status

from .activity_log_service import ActivityLogService

logger = logging.getLogger(__name__)

_VALID_CARD_TYPES = frozenset({
    "email_draft",
    "calendar_hold",
    "outreach",
    "workflow_proposal",
    "config_change",
    "file_operation",
})


class ApprovalService:
    """State transitions over approval_cards + activity_log side effects.

    ``user_client`` is the user-scoped Supabase client (routers use this).
    ``activity_log`` writes go via a ``SystemClient`` since the RLS INSERT
    policy is service-role-only.
    """

    def __init__(self, user_client: Any, activity_log: ActivityLogService):
        self._db = user_client
        self._log = activity_log

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    async def list_pending(self, user_id: str, limit: int = 50) -> list[dict]:
        resp = await (
            self._db.table("approval_cards")
            .select("*")
            .eq("user_id", user_id)
            .eq("status", "pending")
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return list(getattr(resp, "data", None) or [])

    async def count_pending(self, user_id: str) -> int:
        resp = await (
            self._db.table("approval_cards")
            .select("id", count="exact")
            .eq("user_id", user_id)
            .eq("status", "pending")
            .execute()
        )
        count = getattr(resp, "count", None)
        if count is not None:
            return int(count)
        data = getattr(resp, "data", None) or []
        return len(data)

    async def get(self, user_id: str, card_id: str) -> dict:
        resp = await (
            self._db.table("approval_cards")
            .select("*")
            .eq("user_id", user_id)
            .eq("id", card_id)
            .limit(1)
            .execute()
        )
        rows = getattr(resp, "data", None) or []
        if not rows:
            raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND)
        return rows[0]

    # ------------------------------------------------------------------
    # Transitions
    # ------------------------------------------------------------------

    async def approve(
        self,
        user_id: str,
        card_id: str,
        decision_note: Optional[str] = None,
    ) -> dict:
        return await self._transition(
            user_id=user_id,
            card_id=card_id,
            new_status="approved",
            decision_note=decision_note,
        )

    async def reject(
        self,
        user_id: str,
        card_id: str,
        reason: Optional[str] = None,
    ) -> dict:
        return await self._transition(
            user_id=user_id,
            card_id=card_id,
            new_status="rejected",
            decision_note=reason,
        )

    async def edit(
        self,
        user_id: str,
        card_id: str,
        payload_patch: dict,
    ) -> dict:
        """Edit the card's payload; status stays ``pending``."""
        if not isinstance(payload_patch, dict) or not payload_patch:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail="payload_patch must be a non-empty object",
            )
        card = await self.get(user_id, card_id)
        if card["status"] != "pending":
            raise HTTPException(
                status_code=http_status.HTTP_409_CONFLICT,
                detail=f"Cannot edit card in state {card['status']}",
            )

        new_payload = {**(card.get("payload") or {}), **payload_patch}
        resp = await (
            self._db.table("approval_cards")
            .update({"payload": new_payload})
            .eq("user_id", user_id)
            .eq("id", card_id)
            .execute()
        )
        rows = getattr(resp, "data", None) or []
        updated = rows[0] if rows else {**card, "payload": new_payload}

        await self._log.append(
            user_id=user_id,
            actor="user",
            action=self._describe_action(updated, verb="edited"),
            status="awaiting_approval",
            subject_path=_subject_path(updated),
        )
        return updated

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    async def _transition(
        self,
        user_id: str,
        card_id: str,
        new_status: str,
        decision_note: Optional[str],
    ) -> dict:
        card = await self.get(user_id, card_id)
        if card["status"] != "pending":
            raise HTTPException(
                status_code=http_status.HTTP_409_CONFLICT,
                detail=f"Card is already {card['status']}",
            )
        now = datetime.now(timezone.utc).isoformat()
        patch: dict[str, Any] = {
            "status": new_status,
            "decided_at": now,
            "decided_by": user_id,
        }
        if decision_note is not None:
            patch["decision_note"] = decision_note

        resp = await (
            self._db.table("approval_cards")
            .update(patch)
            .eq("user_id", user_id)
            .eq("id", card_id)
            .execute()
        )
        rows = getattr(resp, "data", None) or []
        updated = rows[0] if rows else {**card, **patch}

        verb = "approved" if new_status == "approved" else "rejected"
        await self._log.append(
            user_id=user_id,
            actor="user",
            action=self._describe_action(
                updated, verb=verb, decision_note=decision_note
            ),
            status="done",
            subject_path=_subject_path(updated),
            reasoning=decision_note,
        )

        # --- SPEC-052: execution dispatch for approvals ---
        if new_status == "approved":
            await self._execute_after_approve(updated, user_id)

        return updated

    # ------------------------------------------------------------------
    # Execution dispatch (SPEC-052)
    # ------------------------------------------------------------------

    async def _execute_after_approve(
        self, card: dict, user_id: str
    ) -> None:
        """Called after status='approved' is committed.

        Looks up the executor for the card type, runs it, and records the
        result. Idempotency guard: skips if ``executed_at`` is already set.
        """
        # Idempotency guard
        if card.get("executed_at") is not None:
            logger.warning(
                "Skipping execution for card %s — already executed at %s",
                card.get("id"),
                card["executed_at"],
            )
            return

        from .approval_executors.registry import EXECUTOR_REGISTRY
        from .approval_executors import ExecutionResult

        card_type = card.get("card_type", "")
        executor_cls = EXECUTOR_REGISTRY.get(card_type)

        if executor_cls is None:
            # No executor registered — approve as record only.
            await self._record_execution(
                card,
                user_id,
                ExecutionResult(
                    success=True,
                    activity_action=(
                        f"Approved {card_type}: {card.get('title', 'card')} "
                        f"— no executor registered"
                    ),
                ),
            )
            return

        try:
            executor = executor_cls()
            result = await executor.execute(card, user_id)
        except Exception as exc:
            logger.error(
                "Executor %s raised for card %s: %s",
                card_type,
                card.get("id"),
                exc,
            )
            result = ExecutionResult(
                success=False,
                error=f"Executor error: {exc}",
            )

        await self._record_execution(card, user_id, result)

    async def _record_execution(
        self, card: dict, user_id: str, result
    ) -> None:
        """Write ``executed_at`` + result/error to the card and emit activity_log."""
        from .approval_executors import ExecutionResult

        now = datetime.now(timezone.utc).isoformat()
        patch: dict[str, Any] = {"executed_at": now}
        if result.result:
            patch["execution_result"] = result.result
        if result.error:
            patch["execution_error"] = result.error

        await (
            self._db.table("approval_cards")
            .update(patch)
            .eq("id", card["id"])
            .execute()
        )

        action_text = result.activity_action or self._describe_execution(
            card, result
        )
        await self._log.append(
            user_id=user_id,
            actor="approval-executor",
            action=action_text,
            status="done" if result.success else "failed",
            subject_path=_subject_path(card),
            reasoning=result.error,
        )

    def _describe_execution(self, card: dict, result) -> str:
        """Fallback description for execution activity_log entries."""
        card_type = card.get("card_type", "card")
        title = card.get("title", "")
        if result.success:
            return f"Executed {card_type}: {title}"
        return f"Failed to execute {card_type}: {title}"

    # ------------------------------------------------------------------
    # Retry (SPEC-052)
    # ------------------------------------------------------------------

    async def retry(self, user_id: str, card_id: str) -> dict:
        """Retry execution of a failed card.

        Pre-conditions: status=approved, executed_at set, execution_error set.
        Clears execution columns and re-dispatches.
        """
        card = await self.get(user_id, card_id)

        if card.get("status") != "approved":
            raise HTTPException(
                status_code=http_status.HTTP_409_CONFLICT,
                detail=f"Card is {card.get('status')}, not approved",
            )
        if not card.get("executed_at"):
            raise HTTPException(
                status_code=http_status.HTTP_409_CONFLICT,
                detail="Card has not been executed yet",
            )
        if not card.get("execution_error"):
            raise HTTPException(
                status_code=http_status.HTTP_409_CONFLICT,
                detail="Card execution did not fail — no retry needed",
            )

        # Clear execution columns
        patch: dict[str, Any] = {
            "executed_at": None,
            "execution_result": None,
            "execution_error": None,
        }
        resp = await (
            self._db.table("approval_cards")
            .update(patch)
            .eq("id", card_id)
            .execute()
        )
        rows = getattr(resp, "data", None) or []
        updated = rows[0] if rows else {**card, **patch}

        # Re-dispatch execution
        await self._execute_after_approve(updated, user_id)

        # Re-fetch to get the execution results
        return await self.get(user_id, card_id)

    def _describe_action(
        self,
        card: dict,
        *,
        verb: str,
        decision_note: Optional[str] = None,
    ) -> str:
        """Human-readable line for the activity log."""
        title = card.get("title") or card.get("card_type", "approval")
        line = f"{verb.title()} {card.get('card_type', 'card')}: {title}"
        return line


def _subject_path(card: dict) -> Optional[str]:
    """Best-effort subject path for activity_log.

    For ``config_change`` / ``file_operation`` / ``workflow_proposal`` cards
    a payload path is meaningful; for email/outreach/calendar it's a no-op.
    """
    payload = card.get("payload") or {}
    for key in ("file_path", "filename", "target", "source", "thread_ref"):
        value = payload.get(key)
        if isinstance(value, str) and value:
            return value
    return None
