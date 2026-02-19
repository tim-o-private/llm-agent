"""Tests for TaskService."""

from unittest.mock import AsyncMock, MagicMock, PropertyMock

import pytest

from chatServer.services.task_service import TaskService


def _make_chainable_mock():
    """Create a MagicMock that chains sync methods and has async execute().

    Supabase query builder uses sync chaining (table/select/eq/order/limit)
    with only execute() being async.
    """
    m = MagicMock()

    # All chain methods return the same mock
    chain_methods = [
        "table", "select", "insert", "update", "delete",
        "eq", "lte", "order", "limit", "maybe_single", "is_",
    ]
    for method in chain_methods:
        getattr(m, method).return_value = m

    # not_ is a property that returns an object with in_()
    not_mock = MagicMock()
    not_mock.in_.return_value = m
    type(m).not_ = PropertyMock(return_value=not_mock)

    # execute is the only async method
    m.execute = AsyncMock()

    return m


@pytest.fixture
def mock_db():
    return _make_chainable_mock()


@pytest.fixture
def service(mock_db):
    return TaskService(mock_db)


# --- list_tasks ---


@pytest.mark.asyncio
async def test_list_tasks_default_filters(service, mock_db):
    """Default: top-level, non-completed, non-deleted tasks."""
    mock_db.execute.return_value = MagicMock(
        data=[
            {"id": "t1", "title": "Task 1", "priority": 3, "status": "pending"},
            {"id": "t2", "title": "Task 2", "priority": 1, "status": "in_progress"},
        ],
        count=0,
    )

    tasks = await service.list_tasks(user_id="user-1")

    mock_db.table.assert_any_call("tasks")
    mock_db.eq.assert_any_call("user_id", "user-1")
    mock_db.eq.assert_any_call("deleted", False)
    mock_db.is_.assert_any_call("parent_task_id", "null")
    assert len(tasks) == 2


@pytest.mark.asyncio
async def test_list_tasks_with_status_filter(service, mock_db):
    """Filter by specific status."""
    mock_db.execute.return_value = MagicMock(
        data=[{"id": "t1", "title": "Done", "status": "completed"}], count=0
    )

    tasks = await service.list_tasks(user_id="user-1", status="completed")

    mock_db.eq.assert_any_call("status", "completed")
    assert len(tasks) == 1


@pytest.mark.asyncio
async def test_list_tasks_with_due_date_filter(service, mock_db):
    """Filter by due date."""
    mock_db.execute.return_value = MagicMock(data=[], count=0)

    await service.list_tasks(user_id="user-1", due_date="2026-02-20")

    mock_db.lte.assert_called_with("due_date", "2026-02-20")


@pytest.mark.asyncio
async def test_list_tasks_subtasks_of_parent(service, mock_db):
    """List subtasks of a specific parent."""
    mock_db.execute.return_value = MagicMock(data=[{"id": "st1", "title": "Subtask"}], count=0)

    tasks = await service.list_tasks(user_id="user-1", parent_task_id="parent-id")

    mock_db.eq.assert_any_call("parent_task_id", "parent-id")
    assert len(tasks) == 1


@pytest.mark.asyncio
async def test_list_tasks_empty_result(service, mock_db):
    """Returns empty list when no tasks found."""
    mock_db.execute.return_value = MagicMock(data=[], count=0)

    tasks = await service.list_tasks(user_id="user-1")
    assert tasks == []


# --- get_task ---


@pytest.mark.asyncio
async def test_get_task_found(service, mock_db):
    """Get task with subtasks."""
    mock_db.execute.side_effect = [
        MagicMock(data={"id": "t1", "title": "Main Task", "status": "pending"}),
        MagicMock(data=[{"id": "st1", "title": "Sub 1"}, {"id": "st2", "title": "Sub 2"}]),
    ]

    task = await service.get_task(user_id="user-1", task_id="t1")

    assert task is not None
    assert task["title"] == "Main Task"
    assert len(task["subtasks"]) == 2


@pytest.mark.asyncio
async def test_get_task_not_found(service, mock_db):
    """Returns None when task doesn't exist."""
    mock_db.execute.return_value = MagicMock(data=None)

    task = await service.get_task(user_id="user-1", task_id="nonexistent")
    assert task is None


# --- create_task ---


@pytest.mark.asyncio
async def test_create_task_top_level(service, mock_db):
    """Create a top-level task with auto position."""
    mock_db.execute.side_effect = [
        MagicMock(data=[{"position": 5}]),  # max position query
        MagicMock(data=[{"id": "new-id", "title": "New Task", "position": 6}]),  # insert
    ]

    task = await service.create_task(user_id="user-1", title="New Task", priority=3)

    assert task["id"] == "new-id"
    mock_db.insert.assert_called_once()
    call_args = mock_db.insert.call_args[0][0]
    assert call_args["title"] == "New Task"
    assert call_args["position"] == 6
    assert call_args["priority"] == 3


@pytest.mark.asyncio
async def test_create_task_first_task(service, mock_db):
    """First task gets position 0."""
    mock_db.execute.side_effect = [
        MagicMock(data=[]),  # no existing tasks
        MagicMock(data=[{"id": "first", "title": "First", "position": 0}]),
    ]

    await service.create_task(user_id="user-1", title="First")

    call_args = mock_db.insert.call_args[0][0]
    assert call_args["position"] == 0


@pytest.mark.asyncio
async def test_create_subtask(service, mock_db):
    """Create a subtask with parent validation and position calc."""
    mock_db.execute.side_effect = [
        MagicMock(data={"id": "parent-1"}),  # parent exists
        MagicMock(data=[{"subtask_position": 2}]),  # max subtask position
        MagicMock(data=[{"id": "sub-1", "parent_task_id": "parent-1", "subtask_position": 3}]),
    ]

    task = await service.create_task(
        user_id="user-1",
        title="Sub Task",
        parent_task_id="parent-1",
    )

    assert task["parent_task_id"] == "parent-1"
    call_args = mock_db.insert.call_args[0][0]
    assert call_args["subtask_position"] == 3
    assert call_args["parent_task_id"] == "parent-1"


@pytest.mark.asyncio
async def test_create_subtask_parent_not_found(service, mock_db):
    """Error when parent task doesn't exist."""
    mock_db.execute.return_value = MagicMock(data=None)

    with pytest.raises(ValueError, match="Parent task .* not found"):
        await service.create_task(user_id="user-1", title="Orphan", parent_task_id="bad-id")


@pytest.mark.asyncio
async def test_create_task_invalid_status(service, mock_db):
    """Error on invalid initial status."""
    with pytest.raises(ValueError, match="Initial status must be"):
        await service.create_task(user_id="user-1", title="Bad", status="completed")


@pytest.mark.asyncio
async def test_create_task_invalid_date(service, mock_db):
    """Error on invalid date format."""
    with pytest.raises(ValueError, match="Invalid due_date format"):
        await service.create_task(user_id="user-1", title="Bad", due_date="not-a-date")


# --- update_task ---


@pytest.mark.asyncio
async def test_update_task_status_completed(service, mock_db):
    """Updating status to completed sets completed=true."""
    mock_db.execute.return_value = MagicMock(
        data=[{"id": "t1", "title": "Done", "status": "completed", "completed": True}]
    )

    task = await service.update_task(user_id="user-1", task_id="t1", status="completed")

    assert task is not None
    call_args = mock_db.update.call_args[0][0]
    assert call_args["status"] == "completed"
    assert call_args["completed"] is True


@pytest.mark.asyncio
async def test_update_task_status_pending(service, mock_db):
    """Updating status to pending sets completed=false."""
    mock_db.execute.return_value = MagicMock(
        data=[{"id": "t1", "title": "Reopened", "status": "pending", "completed": False}]
    )

    await service.update_task(user_id="user-1", task_id="t1", status="pending")

    call_args = mock_db.update.call_args[0][0]
    assert call_args["completed"] is False


@pytest.mark.asyncio
async def test_update_task_not_found(service, mock_db):
    """Returns None when task doesn't exist."""
    mock_db.execute.return_value = MagicMock(data=[])

    task = await service.update_task(user_id="user-1", task_id="nonexistent", title="X")
    assert task is None


@pytest.mark.asyncio
async def test_update_task_invalid_status(service, mock_db):
    """Error on invalid status value."""
    with pytest.raises(ValueError, match="Invalid status"):
        await service.update_task(user_id="user-1", task_id="t1", status="invalid")


@pytest.mark.asyncio
async def test_update_task_no_fields(service, mock_db):
    """Error when no fields provided."""
    with pytest.raises(ValueError, match="No fields to update"):
        await service.update_task(user_id="user-1", task_id="t1")


@pytest.mark.asyncio
async def test_update_task_clear_due_date(service, mock_db):
    """Empty string clears due_date."""
    mock_db.execute.return_value = MagicMock(data=[{"id": "t1", "title": "T", "due_date": None}])

    await service.update_task(user_id="user-1", task_id="t1", due_date="")

    call_args = mock_db.update.call_args[0][0]
    assert call_args["due_date"] is None


# --- delete_task ---


@pytest.mark.asyncio
async def test_delete_task_cascades(service, mock_db):
    """Delete soft-deletes task and subtasks."""
    mock_db.execute.side_effect = [
        MagicMock(data=[]),  # subtask soft-delete
        MagicMock(data=[{"id": "t1", "title": "Deleted", "deleted": True}]),  # task soft-delete
    ]

    task = await service.delete_task(user_id="user-1", task_id="t1")

    assert task is not None
    assert task["deleted"] is True
    # Verify update was called twice (subtasks + task)
    assert mock_db.update.call_count == 2


@pytest.mark.asyncio
async def test_delete_task_not_found(service, mock_db):
    """Returns None when task doesn't exist."""
    mock_db.execute.side_effect = [
        MagicMock(data=[]),  # subtask query (no subtasks)
        MagicMock(data=[]),  # task not found
    ]

    task = await service.delete_task(user_id="user-1", task_id="nonexistent")
    assert task is None
