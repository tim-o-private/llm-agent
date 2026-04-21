"""ApprovalService — state machine + edit path for approval_cards.

Stage 1 (per SPEC-045) contract:

- approve / reject flip ``status`` and record ``decided_at`` / ``decided_by``.
- Edit mutates the JSONB ``payload`` and leaves status=pending.
- Every transition emits an ``activity_log`` row via ``ActivityLogService``.
- No outbound effects — no email send, no calendar insert, no workflow write.

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
        return updated

    def _describe_action(
        self,
        card: dict,
        *,
        verb: str,
        decision_note: Optional[str] = None,
    ) -> str:
        """Human-readable line for the activity log.

        Always ends with "Stage 1 no-op, not sent" for approvals of card
        types that would trigger an outbound effect in later stages — this
        makes the S7 log screen reflect the contract explicitly.
        """
        title = card.get("title") or card.get("card_type", "approval")
        outbound_types = {"email_draft", "outreach", "calendar_hold"}
        suffix = ""
        if verb == "approved" and card.get("card_type") in outbound_types:
            suffix = " — Stage 1 no-op, not sent"
        line = f"{verb.title()} {card.get('card_type', 'card')}: {title}{suffix}"
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


def validate_card_type(card_type: str) -> None:
    """Raise ``HTTPException(400)`` if ``card_type`` is not a recognized shape."""
    if card_type not in _VALID_CARD_TYPES:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown card_type: {card_type}",
        )
