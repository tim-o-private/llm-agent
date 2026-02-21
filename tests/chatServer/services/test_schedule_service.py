"""Unit tests for ScheduleService."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from chatServer.services.schedule_service import ScheduleService


@pytest.fixture
def db_client():
    """Create a mock Supabase db client with method chaining support."""
    return MagicMock()


@pytest.fixture
def service(db_client):
    return ScheduleService(db_client)


def _setup_insert_chain(db_client, data=None):
    """Set up mock chain for table(...).insert(...).execute()."""
    if data is None:
        data = [
            {
                "id": "sched-1",
                "user_id": "user-1",
                "agent_name": "assistant",
                "schedule_cron": "0 7 * * *",
                "prompt": "Check email",
                "active": True,
                "config": {},
            }
        ]
    mock_execute = AsyncMock(return_value=MagicMock(data=data))
    db_client.table.return_value.insert.return_value.execute = mock_execute
    return mock_execute


def _setup_select_chain(db_client, data=None):
    """Set up mock chain for table(...).select(...).eq(...).order(...).execute()."""
    if data is None:
        data = []
    mock_execute = AsyncMock(return_value=MagicMock(data=data))
    chain = db_client.table.return_value.select.return_value
    chain.eq.return_value = chain
    chain.order.return_value = chain
    chain.limit.return_value = chain
    chain.maybe_single.return_value = chain
    chain.execute = mock_execute
    return mock_execute


def _setup_update_chain(db_client, data=None):
    """Set up mock chain for table(...).update(...).eq(...).execute()."""
    if data is None:
        data = []
    mock_execute = AsyncMock(return_value=MagicMock(data=data))
    chain = db_client.table.return_value.update.return_value
    chain.eq.return_value = chain
    chain.execute = mock_execute
    return mock_execute


def _setup_agent_validation(db_client, exists=True):
    """Set up mock chain for agent_configurations lookup."""
    agent_data = {"id": "agent-uuid-1"} if exists else None
    mock_execute = AsyncMock(return_value=MagicMock(data=agent_data))
    chain = db_client.table.return_value.select.return_value
    chain.eq.return_value = chain
    chain.maybe_single.return_value = chain
    chain.execute = mock_execute
    return mock_execute


# ---------------------------------------------------------------------------
# create_schedule
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_schedule_success(service, db_client):
    """Verify create_schedule inserts a row and returns it."""
    # First call: agent_configurations lookup; second call: insert
    call_count = 0  # noqa: F841
    agent_data = {"id": "agent-uuid-1"}
    schedule_data = [
        {
            "id": "sched-1",
            "user_id": "user-1",
            "agent_name": "assistant",
            "schedule_cron": "0 7 * * *",
            "prompt": "Check email",
            "active": True,
            "config": {},
        }
    ]

    # Set up agent validation (select chain)
    agent_execute = AsyncMock(return_value=MagicMock(data=agent_data))
    select_chain = db_client.table.return_value.select.return_value
    select_chain.eq.return_value = select_chain
    select_chain.maybe_single.return_value = select_chain
    select_chain.execute = agent_execute

    # Set up insert chain
    insert_execute = AsyncMock(return_value=MagicMock(data=schedule_data))
    db_client.table.return_value.insert.return_value.execute = insert_execute

    result = await service.create_schedule(
        user_id="user-1",
        agent_name="assistant",
        schedule_cron="0 7 * * *",
        prompt="Check email",
    )

    assert result["id"] == "sched-1"
    assert result["schedule_cron"] == "0 7 * * *"
    insert_execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_schedule_invalid_cron(service, db_client):
    """Verify create_schedule rejects invalid cron expressions."""
    with pytest.raises(ValueError, match="Invalid cron expression"):
        await service.create_schedule(
            user_id="user-1",
            agent_name="assistant",
            schedule_cron="not-a-cron",
            prompt="Check email",
        )


@pytest.mark.asyncio
async def test_create_schedule_empty_prompt(service, db_client):
    """Verify create_schedule rejects empty prompts."""
    with pytest.raises(ValueError, match="prompt is required"):
        await service.create_schedule(
            user_id="user-1",
            agent_name="assistant",
            schedule_cron="0 7 * * *",
            prompt="",
        )


@pytest.mark.asyncio
async def test_create_schedule_unknown_agent(service, db_client):
    """Verify create_schedule rejects unknown agent names."""
    _setup_agent_validation(db_client, exists=False)

    with pytest.raises(ValueError, match="Unknown agent"):
        await service.create_schedule(
            user_id="user-1",
            agent_name="nonexistent_agent",
            schedule_cron="0 7 * * *",
            prompt="Check email",
        )


# ---------------------------------------------------------------------------
# delete_schedule
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_schedule_soft_deletes(service, db_client):
    """Verify delete_schedule sets active=false (soft delete) scoped by user_id."""
    _setup_update_chain(db_client, data=[{"id": "sched-1", "active": False}])

    result = await service.delete_schedule(schedule_id="sched-1", user_id="user-1")

    assert result is True
    db_client.table.assert_called_with("agent_schedules")

    # Verify it used update with active=False (soft delete, not hard delete)
    update_call = db_client.table.return_value.update.call_args[0][0]
    assert update_call["active"] is False
    assert "updated_at" in update_call

    # Verify eq calls include both id and user_id
    eq_calls = [call.args for call in db_client.table.return_value.update.return_value.eq.call_args_list]
    assert ("id", "sched-1") in eq_calls
    assert ("user_id", "user-1") in eq_calls


@pytest.mark.asyncio
async def test_delete_schedule_not_found(service, db_client):
    """Verify delete_schedule returns False when no rows matched."""
    _setup_update_chain(db_client, data=[])

    result = await service.delete_schedule(schedule_id="sched-missing", user_id="user-1")

    assert result is False


# ---------------------------------------------------------------------------
# list_schedules
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_schedules_active_only(service, db_client):
    """Verify list_schedules returns active schedules ordered by created_at."""
    schedules = [
        {"id": "s1", "prompt": "Daily report", "schedule_cron": "0 7 * * *", "active": True},
        {"id": "s2", "prompt": "Weekly review", "schedule_cron": "0 9 * * 1", "active": True},
    ]
    _setup_select_chain(db_client, data=schedules)

    result = await service.list_schedules(user_id="user-1", active_only=True)

    assert len(result) == 2
    assert result[0]["id"] == "s1"


@pytest.mark.asyncio
async def test_list_schedules_empty(service, db_client):
    """Verify list_schedules returns empty list when no schedules exist."""
    _setup_select_chain(db_client, data=[])

    result = await service.list_schedules(user_id="user-1")

    assert result == []
