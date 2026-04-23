"""Unit tests for ActivityLogService extended methods (SPEC-050 FU-1).

Tests for list_paginated, count, count_since, get_counts_with_last_viewed,
and mark_viewed.  Existing append/list_recent tests live in
test_activity_log_service.py and are not duplicated here.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from chatServer.services.activity_log_service import ActivityLogService

USER_A = "user-a"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_entry(idx: int, **overrides) -> dict:
    """Build a fake activity_log row."""
    base = {
        "id": f"entry-{idx}",
        "user_id": USER_A,
        "actor": f"actor-{idx}",
        "action": f"Did thing {idx}",
        "status": "done",
        "created_at": f"2026-04-21T00:{idx:02d}:00+00:00",
    }
    base.update(overrides)
    return base


def _user_client_returning(rows: list[dict], *, count: int | None = None):
    """Return a mock user client whose chained query returns *rows*.

    Supports chained methods: table().select().eq().order().limit().execute(),
    as well as lt(), in_(), or_(), gt().
    """
    chain = MagicMock()
    # Every chainable method returns *chain* so calls can be stacked
    for method in (
        "select", "eq", "order", "limit", "lt", "in_", "or_", "gt",
    ):
        getattr(chain, method).return_value = chain

    resp = MagicMock(data=rows, count=count)
    chain.execute = AsyncMock(return_value=resp)

    client = MagicMock()
    client.table.return_value = chain
    return client, chain


# ---------------------------------------------------------------------------
# list_paginated
# ---------------------------------------------------------------------------


class TestListPaginated:
    @pytest.mark.asyncio
    async def test_returns_entries_desc(self):
        rows = [_make_entry(3), _make_entry(2), _make_entry(1)]
        client, _ = _user_client_returning(rows)
        svc = ActivityLogService(system_client=None, user_client=client)

        items, has_more = await svc.list_paginated(USER_A, limit=50)
        assert len(items) == 3
        assert not has_more

    @pytest.mark.asyncio
    async def test_has_more_true_when_extra_row(self):
        # limit=2, but service fetches limit+1=3 rows to detect overflow
        rows = [_make_entry(3), _make_entry(2), _make_entry(1)]
        client, _ = _user_client_returning(rows)
        svc = ActivityLogService(system_client=None, user_client=client)

        items, has_more = await svc.list_paginated(USER_A, limit=2)
        assert len(items) == 2
        assert has_more

    @pytest.mark.asyncio
    async def test_has_more_false_at_end(self):
        rows = [_make_entry(1)]
        client, _ = _user_client_returning(rows)
        svc = ActivityLogService(system_client=None, user_client=client)

        items, has_more = await svc.list_paginated(USER_A, limit=50)
        assert len(items) == 1
        assert not has_more

    @pytest.mark.asyncio
    async def test_before_cursor_calls_lt(self):
        client, chain = _user_client_returning([])
        svc = ActivityLogService(system_client=None, user_client=client)

        await svc.list_paginated(USER_A, before="2026-04-21T00:05:00+00:00")
        chain.lt.assert_called_once_with("created_at", "2026-04-21T00:05:00+00:00")

    @pytest.mark.asyncio
    async def test_workflow_run_id_filter(self):
        client, chain = _user_client_returning([])
        svc = ActivityLogService(system_client=None, user_client=client)

        await svc.list_paginated(USER_A, workflow_run_id="run-1")
        chain.eq.assert_any_call("workflow_run_id", "run-1")

    @pytest.mark.asyncio
    async def test_status_filter(self):
        client, chain = _user_client_returning([])
        svc = ActivityLogService(system_client=None, user_client=client)

        await svc.list_paginated(USER_A, status=["done", "failed"])
        chain.in_.assert_called_once_with("status", ["done", "failed"])

    @pytest.mark.asyncio
    async def test_search_q(self):
        client, chain = _user_client_returning([])
        svc = ActivityLogService(system_client=None, user_client=client)

        await svc.list_paginated(USER_A, q="regenerate")
        chain.or_.assert_called_once_with(
            "action.ilike.%regenerate%,actor.ilike.%regenerate%"
        )

    @pytest.mark.asyncio
    async def test_combined_filters(self):
        """All filters compose via AND (separate chained calls)."""
        client, chain = _user_client_returning([])
        svc = ActivityLogService(system_client=None, user_client=client)

        await svc.list_paginated(
            USER_A,
            before="2026-04-21T00:05:00+00:00",
            workflow_run_id="run-1",
            status=["done"],
            q="hello",
        )
        chain.lt.assert_called_once()
        chain.eq.assert_any_call("workflow_run_id", "run-1")
        chain.in_.assert_called_once()
        chain.or_.assert_called_once()

    @pytest.mark.asyncio
    async def test_requires_user_client(self):
        svc = ActivityLogService(system_client=MagicMock(), user_client=None)
        with pytest.raises(RuntimeError):
            await svc.list_paginated(USER_A)


# ---------------------------------------------------------------------------
# count
# ---------------------------------------------------------------------------


class TestCount:
    @pytest.mark.asyncio
    async def test_returns_exact_count(self):
        client, _ = _user_client_returning([], count=42)
        svc = ActivityLogService(system_client=None, user_client=client)

        result = await svc.count(USER_A)
        assert result == 42

    @pytest.mark.asyncio
    async def test_falls_back_to_data_length(self):
        rows = [{"id": "1"}, {"id": "2"}]
        client, _ = _user_client_returning(rows, count=None)
        svc = ActivityLogService(system_client=None, user_client=client)

        result = await svc.count(USER_A)
        assert result == 2

    @pytest.mark.asyncio
    async def test_requires_user_client(self):
        svc = ActivityLogService(system_client=MagicMock(), user_client=None)
        with pytest.raises(RuntimeError):
            await svc.count(USER_A)


# ---------------------------------------------------------------------------
# count_since
# ---------------------------------------------------------------------------


class TestCountSince:
    @pytest.mark.asyncio
    async def test_with_timestamp(self):
        client, chain = _user_client_returning([], count=5)
        svc = ActivityLogService(system_client=None, user_client=client)

        result = await svc.count_since(USER_A, "2026-04-21T00:00:00+00:00")
        assert result == 5
        chain.gt.assert_called_once_with(
            "created_at", "2026-04-21T00:00:00+00:00"
        )

    @pytest.mark.asyncio
    async def test_none_returns_total(self):
        """When since is None, gt() is not called — returns total count."""
        client, chain = _user_client_returning([], count=10)
        svc = ActivityLogService(system_client=None, user_client=client)

        result = await svc.count_since(USER_A, None)
        assert result == 10
        chain.gt.assert_not_called()

    @pytest.mark.asyncio
    async def test_requires_user_client(self):
        svc = ActivityLogService(system_client=MagicMock(), user_client=None)
        with pytest.raises(RuntimeError):
            await svc.count_since(USER_A, None)


# ---------------------------------------------------------------------------
# get_counts_with_last_viewed
# ---------------------------------------------------------------------------


class TestGetCountsWithLastViewed:
    @pytest.mark.asyncio
    async def test_returns_total_and_since_last_viewed(self):
        """Integrates count + user_preferences read + count_since."""
        # We need the client to return different data for different tables.
        # Simplest: patch the service methods directly.
        client = MagicMock()
        svc = ActivityLogService(system_client=None, user_client=client)
        svc.count = AsyncMock(return_value=25)
        svc.count_since = AsyncMock(return_value=3)

        # Mock user_preferences read
        prefs_chain = MagicMock()
        for m in ("select", "eq", "limit"):
            getattr(prefs_chain, m).return_value = prefs_chain
        prefs_chain.execute = AsyncMock(
            return_value=MagicMock(
                data=[{"last_activity_viewed_at": "2026-04-21T00:00:00+00:00"}]
            )
        )
        client.table.return_value = prefs_chain

        result = await svc.get_counts_with_last_viewed(USER_A)
        assert result == {"total": 25, "since_last_viewed": 3}
        svc.count_since.assert_awaited_once_with(
            USER_A, "2026-04-21T00:00:00+00:00"
        )

    @pytest.mark.asyncio
    async def test_never_viewed_passes_none(self):
        """When no user_preferences row exists, since is None."""
        client = MagicMock()
        svc = ActivityLogService(system_client=None, user_client=client)
        svc.count = AsyncMock(return_value=10)
        svc.count_since = AsyncMock(return_value=10)

        prefs_chain = MagicMock()
        for m in ("select", "eq", "limit"):
            getattr(prefs_chain, m).return_value = prefs_chain
        prefs_chain.execute = AsyncMock(
            return_value=MagicMock(data=[])
        )
        client.table.return_value = prefs_chain

        result = await svc.get_counts_with_last_viewed(USER_A)
        assert result == {"total": 10, "since_last_viewed": 10}
        svc.count_since.assert_awaited_once_with(USER_A, None)


# ---------------------------------------------------------------------------
# mark_viewed
# ---------------------------------------------------------------------------


class TestMarkViewed:
    @pytest.mark.asyncio
    async def test_upserts_and_returns_timestamp(self):
        client = MagicMock()
        chain = MagicMock()
        chain.upsert.return_value = chain
        chain.execute = AsyncMock(return_value=MagicMock(data=[]))
        client.table.return_value = chain

        svc = ActivityLogService(system_client=None, user_client=client)
        result = await svc.mark_viewed(USER_A)

        assert isinstance(result, str)
        client.table.assert_called_with("user_preferences")
        chain.upsert.assert_called_once()
        # Verify the upserted payload contains both fields
        call_args = chain.upsert.call_args
        payload = call_args[0][0]
        assert payload["user_id"] == USER_A
        assert "last_activity_viewed_at" in payload

    @pytest.mark.asyncio
    async def test_requires_user_client(self):
        svc = ActivityLogService(system_client=MagicMock(), user_client=None)
        with pytest.raises(RuntimeError):
            await svc.mark_viewed(USER_A)
