"""Integration tests for the orchestration-check workflow end-to-end.

Tests that the OrchestrationService correctly enforces rate limits,
rejection cooldowns, and consecutive rejection pauses when checking
whether proposals can be created — exercising the full service→DB
round-trip rather than unit-level mocks.

These tests use mocked DB clients (same pattern as other integration
tests in this directory) since a live Supabase instance is not
available in CI.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from chatServer.services.orchestration_service import OrchestrationService

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_db(rows_for_queries: list[list[dict]] | None = None):
    """Create a mock DB client that returns canned rows for sequential queries."""
    db = MagicMock()
    queue = list(rows_for_queries or [])

    def _table(name):
        q = MagicMock()

        def _chain(*_a, **_kw):
            return q

        q.select = _chain
        q.eq = _chain
        q.gt = _chain
        q.gte = _chain
        q.in_ = _chain
        q.order = _chain
        q.limit = _chain
        q.single = _chain

        # not_ is accessed as a PROPERTY (q.not_.is_(...)), not called
        not_obj = MagicMock()
        not_obj.is_ = _chain
        not_obj.eq = _chain
        q.not_ = not_obj

        async def _execute():
            data = queue.pop(0) if queue else []
            resp = MagicMock()
            resp.data = data
            resp.count = len(data)
            return resp

        q.execute = _execute
        return q

    db.table = _table
    return db


# ---------------------------------------------------------------------------
# Rate limits end-to-end
# ---------------------------------------------------------------------------


class TestRateLimitsEndToEnd:
    async def test_allows_proposal_under_limit(self):
        svc = OrchestrationService()
        # Query 1: consecutive rejections check (empty = no pause)
        # Query 2: user preferences for limits (empty = use defaults)
        # Query 3: daily count of workflow_proposal cards (1 existing, limit is 2)
        db = _make_db([
            [],  # no consecutive rejections
            [],  # no user-specific limits
            [{"id": "card-1"}],  # 1 card today (under default limit of 2)
        ])
        allowed, reason = await svc.can_propose("user-1", "workflow_proposal", db)
        assert allowed is True
        assert reason is None

    async def test_blocks_proposal_at_limit(self):
        svc = OrchestrationService()
        db = _make_db([
            [],  # no consecutive rejections
            [],  # no user-specific limits
            [{"id": "c1"}, {"id": "c2"}],  # 2 cards today (at default limit of 2)
        ])
        allowed, reason = await svc.can_propose("user-1", "workflow_proposal", db)
        assert allowed is False
        assert "limit" in reason.lower()

    async def test_config_change_higher_limit(self):
        svc = OrchestrationService()
        db = _make_db([
            [],
            [],
            [{"id": "c1"}, {"id": "c2"}, {"id": "c3"}],  # 3 cards (at default limit of 3)
        ])
        allowed, reason = await svc.can_propose("user-1", "config_change", db)
        assert allowed is False
        assert "limit" in reason.lower()


# ---------------------------------------------------------------------------
# Rejection cooldown end-to-end
# ---------------------------------------------------------------------------


class TestRejectionCooldownEndToEnd:
    async def test_similar_rejected_blocks_reproposal(self):
        svc = OrchestrationService()
        db = _make_db([
            [{"payload": {"pattern_observed": "standup notes"}, "rationale": "Detected standup pattern"}],
        ])
        is_similar = await svc.is_similar_rejected(
            "user-1", "standup notes", "_workflows/standup.flow.md", db
        )
        assert is_similar is True

    async def test_no_rejected_allows_proposal(self):
        svc = OrchestrationService()
        db = _make_db([
            [],  # no rejected cards
        ])
        is_similar = await svc.is_similar_rejected(
            "user-1", "new pattern", None, db
        )
        assert is_similar is False


# ---------------------------------------------------------------------------
# Consecutive rejection pause end-to-end
# ---------------------------------------------------------------------------


class TestConsecutiveRejectionPauseEndToEnd:
    async def test_five_rejections_triggers_pause(self):
        svc = OrchestrationService()
        now = datetime.now(timezone.utc).isoformat()
        db = _make_db([
            [
                {"status": "rejected", "decided_at": now},
                {"status": "rejected", "decided_at": now},
                {"status": "rejected", "decided_at": now},
                {"status": "rejected", "decided_at": now},
                {"status": "rejected", "decided_at": now},
            ],
        ])
        is_paused = await svc.check_consecutive_rejections("user-1", db)
        assert is_paused is True

    async def test_mixed_statuses_no_pause(self):
        svc = OrchestrationService()
        now = datetime.now(timezone.utc).isoformat()
        db = _make_db([
            [
                {"status": "rejected", "decided_at": now},
                {"status": "approved", "decided_at": now},
                {"status": "rejected", "decided_at": now},
                {"status": "rejected", "decided_at": now},
                {"status": "rejected", "decided_at": now},
            ],
        ])
        is_paused = await svc.check_consecutive_rejections("user-1", db)
        assert is_paused is False

    async def test_consecutive_pause_blocks_proposal(self):
        svc = OrchestrationService()
        now = datetime.now(timezone.utc).isoformat()
        db = _make_db([
            [
                {"status": "rejected", "decided_at": now},
                {"status": "rejected", "decided_at": now},
                {"status": "rejected", "decided_at": now},
                {"status": "rejected", "decided_at": now},
                {"status": "rejected", "decided_at": now},
            ],
        ])
        allowed, reason = await svc.can_propose("user-1", "workflow_proposal", db)
        assert allowed is False
        assert "consecutive" in reason.lower() or "pause" in reason.lower()
