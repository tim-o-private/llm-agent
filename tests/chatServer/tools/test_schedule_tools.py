"""Unit tests for schedule tools."""

import sys
from contextlib import contextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from chatServer.tools.schedule_tools import (
    CreateSchedulesTool,
    DeleteSchedulesTool,
    GetSchedulesTool,
)


@pytest.fixture
def create_tool():
    return CreateSchedulesTool(
        user_id="user-123",
        agent_name="search_test_agent",
    )


@pytest.fixture
def delete_tool():
    return DeleteSchedulesTool(
        user_id="user-123",
        agent_name="search_test_agent",
    )


@pytest.fixture
def get_tool():
    return GetSchedulesTool(
        user_id="user-123",
        agent_name="search_test_agent",
    )


@contextmanager
def _patch_schedule_deps(mock_db, mock_service):
    """Patch the lazy imports used by schedule tools inside _arun via sys.modules."""
    mock_supabase_mod = MagicMock()
    mock_supabase_mod.get_supabase_client = AsyncMock(return_value=mock_db)
    mock_service_mod = MagicMock()
    mock_service_mod.ScheduleService = MagicMock(return_value=mock_service)
    mock_scoped_mod = MagicMock()
    mock_scoped_mod.UserScopedClient = MagicMock(return_value=mock_db)

    with patch.dict(sys.modules, {
        "chatServer.database.supabase_client": mock_supabase_mod,
        "chatServer.services.schedule_service": mock_service_mod,
        "chatServer.database.scoped_client": mock_scoped_mod,
    }):
        yield


# ---------------------------------------------------------------------------
# CreateSchedulesTool
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_schedules_success(create_tool):
    """Verify create_schedules calls ScheduleService for each entry and returns confirmation."""
    mock_db = MagicMock()
    mock_service = MagicMock()
    mock_service.create_schedule = AsyncMock(
        return_value={
            "id": "sched-1",
            "prompt": "Check email",
            "schedule_cron": "0 7 * * *",
            "agent_name": "search_test_agent",
        }
    )

    with _patch_schedule_deps(mock_db, mock_service):
        result = await create_tool._arun(
            schedules=[
                {"prompt": "Check email", "schedule_cron": "0 7 * * *", "agent_name": "search_test_agent"},
            ]
        )

    assert "Created" in result
    assert "Check email" in result
    mock_service.create_schedule.assert_awaited_once()
    call_kwargs = mock_service.create_schedule.call_args[1]
    assert call_kwargs["user_id"] == "user-123"
    assert call_kwargs["prompt"] == "Check email"
    assert call_kwargs["schedule_cron"] == "0 7 * * *"


@pytest.mark.asyncio
async def test_create_schedules_invalid_cron(create_tool):
    """Verify create_schedules rejects invalid cron without calling service."""
    mock_db = MagicMock()
    mock_service = MagicMock()
    mock_service.create_schedule = AsyncMock()

    with _patch_schedule_deps(mock_db, mock_service):
        result = await create_tool._arun(
            schedules=[
                {"prompt": "Check email", "schedule_cron": "not-valid-cron"},
            ]
        )
    assert "invalid cron expression" in result
    mock_service.create_schedule.assert_not_awaited()


@pytest.mark.asyncio
async def test_create_schedules_service_error(create_tool):
    """Verify create_schedules handles service errors gracefully."""
    mock_db = MagicMock()
    mock_service = MagicMock()
    mock_service.create_schedule = AsyncMock(side_effect=ValueError("Unknown agent: 'bad'"))

    with _patch_schedule_deps(mock_db, mock_service):
        result = await create_tool._arun(
            schedules=[
                {"prompt": "Check email", "schedule_cron": "0 7 * * *", "agent_name": "bad"},
            ]
        )

    assert "Error" in result
    assert "Unknown agent" in result


@pytest.mark.asyncio
async def test_create_schedules_multiple(create_tool):
    """Verify create_schedules handles multiple entries including mixed success/failure."""
    mock_db = MagicMock()
    mock_service = MagicMock()
    mock_service.create_schedule = AsyncMock(
        return_value={"id": "sched-1", "prompt": "test", "schedule_cron": "0 7 * * *", "agent_name": "search_test_agent"}  # noqa: E501
    )

    with _patch_schedule_deps(mock_db, mock_service):
        result = await create_tool._arun(
            schedules=[
                {"prompt": "Check email", "schedule_cron": "0 7 * * *"},
                {"prompt": "Bad cron", "schedule_cron": "invalid"},
            ]
        )

    assert "#1: Created" in result
    assert "#2: Error" in result


@pytest.mark.asyncio
async def test_create_schedules_sync_run(create_tool):
    """Verify sync _run returns async required message."""
    result = create_tool._run(schedules=[{"prompt": "test", "schedule_cron": "0 7 * * *"}])
    assert "requires async" in result


# ---------------------------------------------------------------------------
# DeleteSchedulesTool
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_schedules_success(delete_tool):
    """Verify delete_schedules calls service for each id and returns confirmation."""
    mock_db = MagicMock()
    mock_service = MagicMock()
    mock_service.delete_schedule = AsyncMock(return_value=True)

    with _patch_schedule_deps(mock_db, mock_service):
        result = await delete_tool._arun(ids=["sched-1"])

    assert "deleted" in result
    mock_service.delete_schedule.assert_awaited_once_with(
        schedule_id="sched-1", user_id="user-123"
    )


@pytest.mark.asyncio
async def test_delete_schedules_not_found(delete_tool):
    """Verify delete_schedules returns not-found message."""
    mock_db = MagicMock()
    mock_service = MagicMock()
    mock_service.delete_schedule = AsyncMock(return_value=False)

    with _patch_schedule_deps(mock_db, mock_service):
        result = await delete_tool._arun(ids=["sched-missing"])

    assert "not found" in result


@pytest.mark.asyncio
async def test_delete_schedules_multiple(delete_tool):
    """Verify delete_schedules handles multiple ids."""
    mock_db = MagicMock()
    mock_service = MagicMock()
    mock_service.delete_schedule = AsyncMock(side_effect=[True, False])

    with _patch_schedule_deps(mock_db, mock_service):
        result = await delete_tool._arun(ids=["sched-1", "sched-2"])

    assert "sched-1: deleted" in result
    assert "sched-2: not found" in result


@pytest.mark.asyncio
async def test_delete_schedules_sync_run(delete_tool):
    """Verify sync _run returns async required message."""
    result = delete_tool._run(ids=["sched-1"])
    assert "requires async" in result


# ---------------------------------------------------------------------------
# GetSchedulesTool
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_schedules_returns_formatted(get_tool):
    """Verify get_schedules returns formatted schedule list with next run."""
    mock_db = MagicMock()
    mock_service = MagicMock()
    mock_service.list_schedules = AsyncMock(
        return_value=[
            {
                "id": "s1",
                "prompt": "Check email",
                "schedule_cron": "0 7 * * *",
                "agent_name": "search_test_agent",
                "active": True,
            },
            {
                "id": "s2",
                "prompt": "Weekly report",
                "schedule_cron": "0 9 * * 1",
                "agent_name": "search_test_agent",
                "active": True,
            },
        ]
    )

    with _patch_schedule_deps(mock_db, mock_service):
        result = await get_tool._arun(active_only=True)

    assert "2 schedule(s)" in result
    assert "Check email" in result
    assert "Weekly report" in result
    assert "0 7 * * *" in result
    mock_service.list_schedules.assert_awaited_once_with(user_id="user-123", active_only=True)


@pytest.mark.asyncio
async def test_get_schedules_empty(get_tool):
    """Verify get_schedules shows empty message when no schedules."""
    mock_db = MagicMock()
    mock_service = MagicMock()
    mock_service.list_schedules = AsyncMock(return_value=[])

    with _patch_schedule_deps(mock_db, mock_service):
        result = await get_tool._arun()

    assert "no active schedules" in result


@pytest.mark.asyncio
async def test_get_schedules_by_id(get_tool):
    """Verify get_schedules with id param fetches a single schedule."""
    mock_db = MagicMock()

    # Build the chained mock for db.table(...).select(...).eq(...).eq(...).maybe_single().execute()
    mock_execute = AsyncMock(return_value=MagicMock(data={
        "id": "s1",
        "prompt": "Check email",
        "schedule_cron": "0 7 * * *",
        "agent_name": "search_test_agent",
        "active": True,
    }))
    mock_maybe_single = MagicMock()
    mock_maybe_single.execute = mock_execute
    mock_eq2 = MagicMock()
    mock_eq2.maybe_single.return_value = mock_maybe_single
    mock_eq1 = MagicMock()
    mock_eq1.eq.return_value = mock_eq2
    mock_select = MagicMock()
    mock_select.eq.return_value = mock_eq1
    mock_table = MagicMock()
    mock_table.select.return_value = mock_select
    mock_db.table.return_value = mock_table

    mock_supabase_mod = MagicMock()
    mock_supabase_mod.get_supabase_client = AsyncMock(return_value=mock_db)
    mock_scoped_mod = MagicMock()
    mock_scoped_mod.UserScopedClient = MagicMock(return_value=mock_db)

    with patch.dict(sys.modules, {
        "chatServer.database.supabase_client": mock_supabase_mod,
        "chatServer.database.scoped_client": mock_scoped_mod,
    }):
        result = await get_tool._arun(id="s1")

    assert "1 schedule(s)" in result
    assert "Check email" in result


@pytest.mark.asyncio
async def test_get_schedules_by_id_not_found(get_tool):
    """Verify get_schedules with id returns not-found when schedule missing."""
    mock_db = MagicMock()

    mock_execute = AsyncMock(return_value=MagicMock(data=None))
    mock_maybe_single = MagicMock()
    mock_maybe_single.execute = mock_execute
    mock_eq2 = MagicMock()
    mock_eq2.maybe_single.return_value = mock_maybe_single
    mock_eq1 = MagicMock()
    mock_eq1.eq.return_value = mock_eq2
    mock_select = MagicMock()
    mock_select.eq.return_value = mock_eq1
    mock_table = MagicMock()
    mock_table.select.return_value = mock_select
    mock_db.table.return_value = mock_table

    mock_supabase_mod = MagicMock()
    mock_supabase_mod.get_supabase_client = AsyncMock(return_value=mock_db)
    mock_scoped_mod = MagicMock()
    mock_scoped_mod.UserScopedClient = MagicMock(return_value=mock_db)

    with patch.dict(sys.modules, {
        "chatServer.database.supabase_client": mock_supabase_mod,
        "chatServer.database.scoped_client": mock_scoped_mod,
    }):
        result = await get_tool._arun(id="nonexistent")

    assert "not found" in result


@pytest.mark.asyncio
async def test_get_schedules_sync_run(get_tool):
    """Verify sync _run returns async required message."""
    result = get_tool._run()
    assert "requires async" in result
