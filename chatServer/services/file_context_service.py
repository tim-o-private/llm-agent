"""FileContextService -- backlinks, suggest card CRUD, and file context composition.

Reads use the user-scoped client (RLS enforced). Suggest card status updates
use the user-scoped client (UPDATE policy on user_id). Activity log inserts
go through a system client acquired internally via ``create_system_client``
(service_role INSERT policy, per A8).

See SPEC-047 ACs 20-22.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import HTTPException, status

logger = logging.getLogger(__name__)


class FileContextService:
    """Compose file context: backlinks, suggest cards, and activity."""

    def __init__(
        self,
        vault_service: Any,
        user_client: Optional[Any] = None,
    ):
        self._vault = vault_service
        self._user = user_client

    # ------------------------------------------------------------------
    # Backlinks (delegates to VaultService)
    # ------------------------------------------------------------------

    async def get_backlinks(
        self, user_id: str, rel_path: str
    ) -> list[dict[str, str]]:
        """Return backlinks for a file by delegating to VaultService."""
        return await self._vault.find_backlinks(user_id, rel_path)

    # ------------------------------------------------------------------
    # File context (AC-21)
    # ------------------------------------------------------------------

    async def get_file_context(
        self, user_id: str, rel_path: str
    ) -> dict:
        """Return ``{summary, suggest_cards, activity}`` for a file.

        Stage 1: summary is always ``null`` (client computes it).
        """
        if self._user is None:
            raise RuntimeError("user_client required for get_file_context")

        # Fetch pending suggest cards for this file.
        sc_resp = await (
            self._user.table("suggest_cards")
            .select("*")
            .eq("user_id", user_id)
            .eq("file_path", rel_path)
            .eq("status", "pending")
            .order("created_at", desc=False)
            .execute()
        )
        suggest_cards = list(getattr(sc_resp, "data", None) or [])

        # Fetch recent activity for this file path.
        act_resp = await (
            self._user.table("activity_log")
            .select("*")
            .eq("user_id", user_id)
            .eq("subject_path", rel_path)
            .order("created_at", desc=True)
            .limit(20)
            .execute()
        )
        activity = list(getattr(act_resp, "data", None) or [])

        return {
            "summary": None,
            "suggest_cards": suggest_cards,
            "activity": activity,
        }

    # ------------------------------------------------------------------
    # Suggest card actions (AC-22)
    # ------------------------------------------------------------------

    async def accept_suggest_card(
        self, user_id: str, card_id: str
    ) -> dict:
        """Mark a suggest card as accepted; return its text payload.

        Returns ``{text, target_line}`` so the client can insert the
        suggested text into the editor.
        """
        if self._user is None:
            raise RuntimeError("user_client required for accept_suggest_card")

        # Fetch the card first to get its payload and verify ownership.
        fetch_resp = await (
            self._user.table("suggest_cards")
            .select("*")
            .eq("user_id", user_id)
            .eq("id", card_id)
            .limit(1)
            .execute()
        )
        rows = getattr(fetch_resp, "data", None) or []
        if not rows:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Suggest card not found",
            )

        card = rows[0]
        if card["status"] != "pending":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Card already {card['status']}",
            )

        # Update status.
        now = datetime.now(timezone.utc).isoformat()
        await (
            self._user.table("suggest_cards")
            .update({"status": "accepted", "decided_at": now})
            .eq("user_id", user_id)
            .eq("id", card_id)
            .execute()
        )

        # Emit activity log entry (best-effort, via system client).
        await self._emit_activity(
            user_id=user_id,
            actor="user",
            action=f"Accepted suggestion: {card['body'][:80]}",
            subject_path=card.get("file_path"),
        )

        return {
            "text": card.get("suggested_text"),
            "target_line": card.get("target_line", 0),
        }

    async def dismiss_suggest_card(
        self, user_id: str, card_id: str
    ) -> None:
        """Mark a suggest card as dismissed."""
        if self._user is None:
            raise RuntimeError("user_client required for dismiss_suggest_card")

        # Fetch the card to verify ownership and current status.
        fetch_resp = await (
            self._user.table("suggest_cards")
            .select("*")
            .eq("user_id", user_id)
            .eq("id", card_id)
            .limit(1)
            .execute()
        )
        rows = getattr(fetch_resp, "data", None) or []
        if not rows:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Suggest card not found",
            )

        card = rows[0]
        if card["status"] != "pending":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Card already {card['status']}",
            )

        now = datetime.now(timezone.utc).isoformat()
        await (
            self._user.table("suggest_cards")
            .update({"status": "dismissed", "decided_at": now})
            .eq("user_id", user_id)
            .eq("id", card_id)
            .execute()
        )

        # Emit activity log entry (best-effort, via system client).
        await self._emit_activity(
            user_id=user_id,
            actor="user",
            action=f"Dismissed suggestion: {card['body'][:80]}",
            subject_path=card.get("file_path"),
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _emit_activity(
        self,
        *,
        user_id: str,
        actor: str,
        action: str,
        subject_path: str | None = None,
    ) -> None:
        """Append an activity_log entry via a system client (best-effort).

        Acquires the system client internally -- activity_log INSERT requires
        service_role per RLS policy.
        """
        try:
            from ..database.supabase_client import create_system_client

            system = await create_system_client()
            payload: dict[str, Any] = {
                "user_id": user_id,
                "actor": actor,
                "action": action,
                "status": "done",
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            if subject_path is not None:
                payload["subject_path"] = subject_path
            await system.table("activity_log").insert(payload).execute()
        except Exception:
            logger.warning(
                "Failed to emit activity_log for %s", action, exc_info=True
            )
