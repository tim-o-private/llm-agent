"""OrchestrationService — rate limits, rejection cooldown, and proposal gating.

Enforces noise-prevention constraints from SPEC-054 §6:
- Per-type daily rate limits (AC-16)
- 30-day cooldown on rejected similar proposals (AC-17)
- Consecutive-rejection pause (AC-18)

All checks read from the ``approval_cards`` table via a user-scoped DB client.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

logger = logging.getLogger(__name__)

# Defaults — can be overridden per-user via user_preferences.orchestration_limits
DAILY_LIMITS: dict[str, int] = {
    "workflow_proposal": 2,
    "config_change": 3,
    "thread_creation": 3,
}

REJECTION_COOLDOWN_DAYS = 30
CONSECUTIVE_REJECTION_PAUSE_THRESHOLD = 5
CONSECUTIVE_REJECTION_PAUSE_DAYS = 7


class OrchestrationService:
    """Proposal rate-limiting and rejection-cooldown enforcement."""

    async def can_propose(
        self,
        user_id: str,
        card_type: str,
        db: Any,
    ) -> tuple[bool, str | None]:
        """Check whether a proposal of ``card_type`` is allowed right now.

        Returns ``(True, None)`` if allowed, or ``(False, reason)`` if blocked.

        Checks (in order):
        1. Consecutive-rejection pause (5+ rejections → 7-day pause)
        2. Daily rate limit for this card_type
        """
        # 1. Check consecutive-rejection pause
        if await self.check_consecutive_rejections(user_id, db):
            return False, (
                "Proposals paused — 5 or more consecutive rejections in the "
                "recent history. Proposals resume automatically after 7 days."
            )

        # 2. Check daily rate limit
        limit = await self._get_limit(user_id, card_type, db)
        today_start = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        resp = await (
            db.table("approval_cards")
            .select("id", count="exact")
            .eq("user_id", user_id)
            .eq("card_type", card_type)
            .gte("created_at", today_start.isoformat())
            .execute()
        )
        count = resp.count if resp.count is not None else len(resp.data or [])
        if count >= limit:
            return False, (
                f"Daily limit reached: {count}/{limit} {card_type} "
                f"proposals today."
            )

        return True, None

    async def is_similar_rejected(
        self,
        user_id: str,
        pattern_description: str,
        target_path: str | None,
        db: Any,
    ) -> bool:
        """Check if a similar proposal was rejected in the last 30 days.

        Uses simple substring + path matching (not embedding-based).
        Returns True if a similar rejected proposal is found.
        """
        cutoff = (
            datetime.now(timezone.utc)
            - timedelta(days=REJECTION_COOLDOWN_DAYS)
        ).isoformat()

        resp = await (
            db.table("approval_cards")
            .select("payload, rationale")
            .eq("user_id", user_id)
            .eq("status", "rejected")
            .gte("created_at", cutoff)
            .execute()
        )

        if not resp.data:
            return False

        # Normalize for substring matching
        pattern_lower = pattern_description.lower()

        for card in resp.data:
            payload = card.get("payload") or {}
            rationale = (card.get("rationale") or "").lower()

            # Path match: same target file
            if target_path and payload.get("file_path") == target_path:
                return True

            # Substring match in rationale or pattern_observed
            observed = (payload.get("pattern_observed") or "").lower()
            if pattern_lower and (
                pattern_lower in rationale or pattern_lower in observed
            ):
                return True

        return False

    async def check_consecutive_rejections(
        self,
        user_id: str,
        db: Any,
    ) -> bool:
        """Return True if the last 5+ decisions were all rejections
        and the most recent rejection was within the pause window."""
        resp = await (
            db.table("approval_cards")
            .select("status, decided_at")
            .eq("user_id", user_id)
            .in_("card_type", ["workflow_proposal", "config_change"])
            .not_.is_("decided_at", "null")
            .order("decided_at", desc=True)
            .limit(CONSECUTIVE_REJECTION_PAUSE_THRESHOLD)
            .execute()
        )

        cards = resp.data or []
        if len(cards) < CONSECUTIVE_REJECTION_PAUSE_THRESHOLD:
            return False

        # All must be rejected
        if not all(c.get("status") == "rejected" for c in cards):
            return False

        # The most recent rejection must be within the pause window
        latest_decided = cards[0].get("decided_at", "")
        if not latest_decided:
            return False

        try:
            decided_dt = datetime.fromisoformat(
                latest_decided.replace("Z", "+00:00")
            )
        except (ValueError, TypeError):
            return False

        pause_cutoff = datetime.now(timezone.utc) - timedelta(
            days=CONSECUTIVE_REJECTION_PAUSE_DAYS
        )
        return decided_dt > pause_cutoff

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _get_limit(
        self, user_id: str, card_type: str, db: Any
    ) -> int:
        """Return the daily limit for ``card_type``, respecting user overrides."""
        default = DAILY_LIMITS.get(card_type, 3)
        try:
            resp = await (
                db.table("user_preferences")
                .select("orchestration_limits")
                .eq("user_id", user_id)
                .execute()
            )
            if resp.data and resp.data[0].get("orchestration_limits"):
                limits = resp.data[0]["orchestration_limits"]
                return limits.get(card_type, default)
        except Exception:
            logger.debug(
                "Could not read orchestration_limits for %s, using default",
                user_id,
            )
        return default
