"""Unit tests for OrchestrationService — rate limits, rejection cooldown, consecutive pause."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest

from chatServer.services.orchestration_service import (
    CONSECUTIVE_REJECTION_PAUSE_DAYS,
    CONSECUTIVE_REJECTION_PAUSE_THRESHOLD,
    OrchestrationService,
)

USER = "user-test"


class _FakeQuery:
    """Minimal chainable fake for Supabase queries."""

    def __init__(self, parent, *, count_val=None):
        self._parent = parent
        self._count_val = count_val

    def select(self, *args, **kwargs):
        return self

    def eq(self, *args, **kwargs):
        return self

    def in_(self, *args, **kwargs):
        return self

    def gte(self, *args, **kwargs):
        return self

    @property
    def not_(self):
        return _NotHelper(self)

    def order(self, *args, **kwargs):
        return self

    def limit(self, *args, **kwargs):
        return self

    async def execute(self):
        rows = self._parent.next_rows()
        count = self._count_val if self._count_val is not None else len(rows)
        return MagicMock(data=rows, count=count)


class _NotHelper:
    def __init__(self, query):
        self._query = query

    def is_(self, *args, **kwargs):
        return self._query


class FakeDb:
    """Fake DB client for testing OrchestrationService."""

    def __init__(self):
        self._row_queue: list[list[dict]] = []

    def queue_rows(self, rows: list[dict]):
        self._row_queue.append(rows)

    def next_rows(self) -> list[dict]:
        if self._row_queue:
            return self._row_queue.pop(0)
        return []

    def table(self, _name):
        return _FakeQuery(self)


@pytest.fixture
def db():
    return FakeDb()


@pytest.fixture
def service():
    return OrchestrationService()


# ---------------------------------------------------------------------------
# can_propose — rate limits
# ---------------------------------------------------------------------------


class TestCanPropose:
    @pytest.mark.asyncio
    async def test_allowed_when_under_limit(self, service, db):
        # consecutive rejections check → no data
        db.queue_rows([])
        # daily count → 0 (no cards today)
        db.queue_rows([])
        # user prefs → no overrides
        db.queue_rows([])

        allowed, reason = await service.can_propose(USER, "workflow_proposal", db)
        assert allowed is True
        assert reason is None

    @pytest.mark.asyncio
    async def test_blocked_at_daily_limit(self, service, db):
        # consecutive rejections check → fewer than 5
        db.queue_rows([{"status": "approved", "decided_at": "2026-04-21T10:00:00Z"}])
        # _get_limit queries user_preferences → no overrides (uses default=2)
        db.queue_rows([])
        # daily count query → 2 cards today (at limit)
        db.queue_rows([{"id": "1"}, {"id": "2"}])

        allowed, reason = await service.can_propose(USER, "workflow_proposal", db)
        assert allowed is False
        assert "Daily limit" in reason

    @pytest.mark.asyncio
    async def test_consecutive_rejections_pause(self, service, db):
        """5 consecutive rejections should pause proposals."""
        recent = datetime.now(timezone.utc).isoformat()
        rejection_cards = [
            {"status": "rejected", "decided_at": recent}
            for _ in range(CONSECUTIVE_REJECTION_PAUSE_THRESHOLD)
        ]
        db.queue_rows(rejection_cards)

        allowed, reason = await service.can_propose(USER, "workflow_proposal", db)
        assert allowed is False
        assert "paused" in reason.lower()


# ---------------------------------------------------------------------------
# is_similar_rejected
# ---------------------------------------------------------------------------


class TestIsSimilarRejected:
    @pytest.mark.asyncio
    async def test_no_rejections(self, service, db):
        db.queue_rows([])
        result = await service.is_similar_rejected(
            USER, "standup notes", "_workflows/standup.flow.md", db
        )
        assert result is False

    @pytest.mark.asyncio
    async def test_path_match(self, service, db):
        db.queue_rows([{
            "payload": {"file_path": "_workflows/standup.flow.md"},
            "rationale": "some rationale",
        }])
        result = await service.is_similar_rejected(
            USER, "different description", "_workflows/standup.flow.md", db
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_pattern_substring_match(self, service, db):
        db.queue_rows([{
            "payload": {"pattern_observed": "User captures standup notes regularly"},
            "rationale": "Detected standup notes pattern",
        }])
        result = await service.is_similar_rejected(
            USER, "standup notes", None, db
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_no_match(self, service, db):
        db.queue_rows([{
            "payload": {"pattern_observed": "User sends weekly reports"},
            "rationale": "Weekly report pattern",
        }])
        result = await service.is_similar_rejected(
            USER, "standup notes", None, db
        )
        assert result is False


# ---------------------------------------------------------------------------
# check_consecutive_rejections
# ---------------------------------------------------------------------------


class TestConsecutiveRejections:
    @pytest.mark.asyncio
    async def test_not_enough_decisions(self, service, db):
        db.queue_rows([
            {"status": "rejected", "decided_at": datetime.now(timezone.utc).isoformat()},
        ])
        result = await service.check_consecutive_rejections(USER, db)
        assert result is False

    @pytest.mark.asyncio
    async def test_mixed_decisions(self, service, db):
        recent = datetime.now(timezone.utc).isoformat()
        db.queue_rows([
            {"status": "rejected", "decided_at": recent},
            {"status": "rejected", "decided_at": recent},
            {"status": "approved", "decided_at": recent},  # breaks streak
            {"status": "rejected", "decided_at": recent},
            {"status": "rejected", "decided_at": recent},
        ])
        result = await service.check_consecutive_rejections(USER, db)
        assert result is False

    @pytest.mark.asyncio
    async def test_all_rejections_within_pause_window(self, service, db):
        recent = datetime.now(timezone.utc).isoformat()
        db.queue_rows([
            {"status": "rejected", "decided_at": recent}
            for _ in range(CONSECUTIVE_REJECTION_PAUSE_THRESHOLD)
        ])
        result = await service.check_consecutive_rejections(USER, db)
        assert result is True

    @pytest.mark.asyncio
    async def test_old_rejections_outside_pause_window(self, service, db):
        old = (
            datetime.now(timezone.utc)
            - timedelta(days=CONSECUTIVE_REJECTION_PAUSE_DAYS + 1)
        ).isoformat()
        db.queue_rows([
            {"status": "rejected", "decided_at": old}
            for _ in range(CONSECUTIVE_REJECTION_PAUSE_THRESHOLD)
        ])
        result = await service.check_consecutive_rejections(USER, db)
        assert result is False
