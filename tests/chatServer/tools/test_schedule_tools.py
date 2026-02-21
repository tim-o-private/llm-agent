"""Unit tests for schedule tools."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from chatServer.tools.schedule_tools import (
    CreateScheduleTool,
    DeleteScheduleTool,
    ListSchedulesTool,
)


@pytest.fixture
def create_tool():
    return CreateScheduleTool(
        user_id="user-123",
        agent_name="assistant",
    )


@pytest.fixture
def delete_tool():
    return DeleteScheduleTool(
        user_id="user-123",
        agent_name="assistant",
    )


@pytest.fixture
def list_tool():
    return ListSchedulesTool(
        user_id="user-123",
        agent_name="assistant",
    )


def _patch_schedule_deps(mock_db, mock_service):
    """Context manager tuple that patches the lazy imports used by schedule tools."""
    return (
        patch(
            "chatServer.database.supabase_client.get_supabase_client",
            new_callable=AsyncMock,
            return_value=mock_db,
        ),
        patch(
            "chatServer.services.schedule_service.ScheduleService",
            return_value=mock_service,
        ),
    )


# ---------------------------------------------------------------------------
# CreateScheduleTool
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_schedule_success(create_tool):
    """Verify create_schedule calls ScheduleService and returns confirmation."""
    mock_db = MagicMock()
    mock_service = MagicMock()
    mock_service.create_schedule = AsyncMock(
        return_value={
            "id": "sched-1",
            "prompt": "Check email",
            "schedule_cron": "0 7 * * *",
            "agent_name": "assistant",
        }
    )

    p1, p2 = _patch_schedule_deps(mock_db, mock_service)
    with p1, p2:
        result = await create_tool._arun(
            prompt="Check email",
            schedule_cron="0 7 * * *",
            agent_name="assistant",
        )

    assert "Schedule created" in result
    assert "Check email" in result
    mock_service.create_schedule.assert_awaited_once()
    call_kwargs = mock_service.create_schedule.call_args[1]
    assert call_kwargs["user_id"] == "user-123"
    assert call_kwargs["prompt"] == "Check email"
    assert call_kwargs["schedule_cron"] == "0 7 * * *"


@pytest.mark.asyncio
async def test_create_schedule_invalid_cron(create_tool):
    """Verify create_schedule rejects invalid cron without calling service."""
    result = await create_tool._arun(
        prompt="Check email",
        schedule_cron="not-valid-cron",
    )
    assert "invalid cron expression" in result


@pytest.mark.asyncio
async def test_create_schedule_service_error(create_tool):
    """Verify create_schedule handles service errors gracefully."""
    mock_db = MagicMock()
    mock_service = MagicMock()
    mock_service.create_schedule = AsyncMock(side_effect=ValueError("Unknown agent: 'bad'"))

    p1, p2 = _patch_schedule_deps(mock_db, mock_service)
    with p1, p2:
        result = await create_tool._arun(
            prompt="Check email",
            schedule_cron="0 7 * * *",
            agent_name="bad",
        )

    assert "Error" in result
    assert "Unknown agent" in result


@pytest.mark.asyncio
async def test_create_schedule_sync_run(create_tool):
    """Verify sync _run returns async required message."""
    result = create_tool._run(prompt="test", schedule_cron="0 7 * * *")
    assert "requires async" in result


# ---------------------------------------------------------------------------
# DeleteScheduleTool
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_schedule_success(delete_tool):
    """Verify delete_schedule calls service and returns confirmation."""
    mock_db = MagicMock()
    mock_service = MagicMock()
    mock_service.delete_schedule = AsyncMock(return_value=True)

    p1, p2 = _patch_schedule_deps(mock_db, mock_service)
    with p1, p2:
        result = await delete_tool._arun(schedule_id="sched-1")

    assert "deleted successfully" in result
    mock_service.delete_schedule.assert_awaited_once_with(
        schedule_id="sched-1", user_id="user-123"
    )


@pytest.mark.asyncio
async def test_delete_schedule_not_found(delete_tool):
    """Verify delete_schedule returns not-found message."""
    mock_db = MagicMock()
    mock_service = MagicMock()
    mock_service.delete_schedule = AsyncMock(return_value=False)

    p1, p2 = _patch_schedule_deps(mock_db, mock_service)
    with p1, p2:
        result = await delete_tool._arun(schedule_id="sched-missing")

    assert "not found" in result


@pytest.mark.asyncio
async def test_delete_schedule_sync_run(delete_tool):
    """Verify sync _run returns async required message."""
    result = delete_tool._run(schedule_id="sched-1")
    assert "requires async" in result


# ---------------------------------------------------------------------------
# ListSchedulesTool
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_schedules_returns_formatted(list_tool):
    """Verify list_schedules returns formatted schedule list with next run."""
    mock_db = MagicMock()
    mock_service = MagicMock()
    mock_service.list_schedules = AsyncMock(
        return_value=[
            {
                "id": "s1",
                "prompt": "Check email",
                "schedule_cron": "0 7 * * *",
                "agent_name": "assistant",
                "active": True,
            },
            {
                "id": "s2",
                "prompt": "Weekly report",
                "schedule_cron": "0 9 * * 1",
                "agent_name": "assistant",
                "active": True,
            },
        ]
    )

    p1, p2 = _patch_schedule_deps(mock_db, mock_service)
    with p1, p2:
        result = await list_tool._arun(active_only=True)

    assert "2 schedule(s)" in result
    assert "Check email" in result
    assert "Weekly report" in result
    assert "0 7 * * *" in result
    mock_service.list_schedules.assert_awaited_once_with(user_id="user-123", active_only=True)


@pytest.mark.asyncio
async def test_list_schedules_empty(list_tool):
    """Verify list_schedules shows empty message when no schedules."""
    mock_db = MagicMock()
    mock_service = MagicMock()
    mock_service.list_schedules = AsyncMock(return_value=[])

    p1, p2 = _patch_schedule_deps(mock_db, mock_service)
    with p1, p2:
        result = await list_tool._arun()

    assert "no active schedules" in result


@pytest.mark.asyncio
async def test_list_schedules_sync_run(list_tool):
    """Verify sync _run returns async required message."""
    result = list_tool._run()
    assert "requires async" in result
