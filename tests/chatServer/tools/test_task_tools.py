"""Tests for agent task tools."""

from unittest.mock import AsyncMock, patch

import pytest

from chatServer.tools.task_tools import (
    CreateTasksTool,
    DeleteTasksTool,
    GetTasksTool,
    UpdateTasksTool,
    _format_task_detail,
    _format_task_line,
)


@pytest.fixture
def mock_task_service():
    """Create a mock TaskService."""
    service = AsyncMock()
    return service


@pytest.fixture
def tool_kwargs():
    """Common kwargs for tool instantiation."""
    return {
        "user_id": "test-user-id",
        "agent_name": "assistant",
        "supabase_url": "https://test.supabase.co",
        "supabase_key": "test-key",
    }


# --- Formatting tests ---


def test_format_task_line_basic():
    task = {"id": "t1", "title": "Do stuff", "priority": 4, "status": "pending"}
    result = _format_task_line(task, 1)
    assert "1. [HIGH] Do stuff" in result
    assert "pending" in result
    assert "[id: t1]" in result


def test_format_task_line_with_due_date():
    task = {"id": "t1", "title": "Due task", "priority": 2, "status": "in_progress", "due_date": "2026-02-20"}
    result = _format_task_line(task, 1)
    assert "(due: 2026-02-20)" in result


def test_format_task_line_with_subtasks():
    task = {
        "id": "t1",
        "title": "Parent",
        "priority": 3,
        "status": "pending",
        "subtask_count": 3,
        "subtasks_completed": 1,
    }
    result = _format_task_line(task, 1)
    assert "3 subtask(s) (1 completed)" in result


def test_format_task_detail():
    task = {
        "id": "t1",
        "title": "Main Task",
        "priority": 5,
        "status": "in_progress",
        "due_date": "2026-03-01",
        "category": "work",
        "description": "Important thing",
        "notes": "Some notes",
        "subtasks": [
            {"title": "Sub 1", "status": "completed"},
            {"title": "Sub 2", "status": "pending"},
        ],
    }
    result = _format_task_detail(task)
    assert "Main Task" in result
    assert "URGENT" in result
    assert "Due: 2026-03-01" in result
    assert "Category: work" in result
    assert "[x] 1. Sub 1" in result
    assert "[ ] 2. Sub 2" in result


# --- GetTasksTool (list mode) ---


@pytest.mark.asyncio
async def test_get_tasks_returns_formatted_list(mock_task_service, tool_kwargs):
    mock_task_service.list_tasks.return_value = [
        {"id": "t1", "title": "Task A", "priority": 3, "status": "pending"},
        {"id": "t2", "title": "Task B", "priority": 1, "status": "in_progress", "due_date": "2026-02-21"},
    ]

    tool = GetTasksTool(**tool_kwargs)
    with patch("chatServer.tools.task_tools._get_task_service", return_value=mock_task_service):
        result = await tool._arun()

    assert "2 task(s)" in result
    assert "Task A" in result
    assert "Task B" in result
    mock_task_service.list_tasks.assert_called_once()


@pytest.mark.asyncio
async def test_get_tasks_empty(mock_task_service, tool_kwargs):
    mock_task_service.list_tasks.return_value = []

    tool = GetTasksTool(**tool_kwargs)
    with patch("chatServer.tools.task_tools._get_task_service", return_value=mock_task_service):
        result = await tool._arun()

    assert "No tasks found" in result


@pytest.mark.asyncio
async def test_get_tasks_with_status_filter(mock_task_service, tool_kwargs):
    mock_task_service.list_tasks.return_value = []

    tool = GetTasksTool(**tool_kwargs)
    with patch("chatServer.tools.task_tools._get_task_service", return_value=mock_task_service):
        result = await tool._arun(status="completed")

    assert "No tasks found with status 'completed'" in result
    mock_task_service.list_tasks.assert_called_once_with(
        user_id="test-user-id",
        status="completed",
        due_date=None,
        include_completed=False,
        include_subtasks=False,
        limit=20,
    )


@pytest.mark.asyncio
async def test_get_tasks_error_handling(mock_task_service, tool_kwargs):
    mock_task_service.list_tasks.side_effect = Exception("DB error")

    tool = GetTasksTool(**tool_kwargs)
    with patch("chatServer.tools.task_tools._get_task_service", return_value=mock_task_service):
        result = await tool._arun()

    assert "Failed to get tasks" in result


# --- GetTasksTool (single task by ID) ---


@pytest.mark.asyncio
async def test_get_tasks_by_id_found(mock_task_service, tool_kwargs):
    mock_task_service.get_task.return_value = {
        "id": "t1",
        "title": "My Task",
        "priority": 3,
        "status": "pending",
        "subtasks": [],
    }

    tool = GetTasksTool(**tool_kwargs)
    with patch("chatServer.tools.task_tools._get_task_service", return_value=mock_task_service):
        result = await tool._arun(id="t1")

    assert "My Task" in result
    assert "t1" in result
    mock_task_service.get_task.assert_called_once_with(user_id="test-user-id", task_id="t1")


@pytest.mark.asyncio
async def test_get_tasks_by_id_not_found(mock_task_service, tool_kwargs):
    mock_task_service.get_task.return_value = None

    tool = GetTasksTool(**tool_kwargs)
    with patch("chatServer.tools.task_tools._get_task_service", return_value=mock_task_service):
        result = await tool._arun(id="bad-id")

    assert "not found" in result


# --- CreateTasksTool ---


@pytest.mark.asyncio
async def test_create_tasks_single(mock_task_service, tool_kwargs):
    mock_task_service.create_tasks.return_value = [
        {"id": "new-1", "title": "Buy groceries", "priority": 2, "status": "pending"},
    ]

    tool = CreateTasksTool(**tool_kwargs)
    with patch("chatServer.tools.task_tools._get_task_service", return_value=mock_task_service):
        result = await tool._arun(tasks=[{"title": "Buy groceries"}])

    assert 'Created: "Buy groceries"' in result
    assert "status: pending" in result


@pytest.mark.asyncio
async def test_create_tasks_batch(mock_task_service, tool_kwargs):
    mock_task_service.create_tasks.return_value = [
        {"id": "new-1", "title": "Task A", "priority": 2, "status": "pending"},
        {"id": "new-2", "title": "Task B", "priority": 4, "status": "planning", "due_date": "2026-03-01"},
    ]

    tool = CreateTasksTool(**tool_kwargs)
    with patch("chatServer.tools.task_tools._get_task_service", return_value=mock_task_service):
        result = await tool._arun(tasks=[
            {"title": "Task A"},
            {"title": "Task B", "priority": 4, "due_date": "2026-03-01", "status": "planning"},
        ])

    assert "Task A" in result
    assert "Task B" in result
    assert "due: 2026-03-01" in result


@pytest.mark.asyncio
async def test_create_tasks_with_error(mock_task_service, tool_kwargs):
    mock_task_service.create_tasks.return_value = [
        {"id": "new-1", "title": "Good", "priority": 2, "status": "pending"},
        {"error": "Missing required field 'title'"},
    ]

    tool = CreateTasksTool(**tool_kwargs)
    with patch("chatServer.tools.task_tools._get_task_service", return_value=mock_task_service):
        result = await tool._arun(tasks=[{"title": "Good"}, {}])

    assert "Good" in result
    assert "Error:" in result


@pytest.mark.asyncio
async def test_create_tasks_subtask(mock_task_service, tool_kwargs):
    mock_task_service.create_tasks.return_value = [
        {"id": "sub-1", "title": "Step 1", "priority": 2, "status": "pending", "parent_task_id": "parent-1"},
    ]

    tool = CreateTasksTool(**tool_kwargs)
    with patch("chatServer.tools.task_tools._get_task_service", return_value=mock_task_service):
        result = await tool._arun(tasks=[{"title": "Step 1", "parent_task_id": "parent-1"}])

    assert "[subtask of parent-1]" in result


# --- UpdateTasksTool ---


@pytest.mark.asyncio
async def test_update_tasks_single(mock_task_service, tool_kwargs):
    mock_task_service.update_tasks.return_value = [
        {"id": "t1", "title": "Done Task", "changes": ["status → completed ✓"]},
    ]

    tool = UpdateTasksTool(**tool_kwargs)
    with patch("chatServer.tools.task_tools._get_task_service", return_value=mock_task_service):
        result = await tool._arun(tasks=[{"id": "t1", "status": "completed"}])

    assert 'Updated "Done Task"' in result
    assert "status → completed ✓" in result


@pytest.mark.asyncio
async def test_update_tasks_batch(mock_task_service, tool_kwargs):
    mock_task_service.update_tasks.return_value = [
        {"id": "t1", "title": "Task A", "changes": ["status → completed ✓"]},
        {"id": "t2", "title": "Task B", "changes": ['title → "New Title"', "priority → URGENT"]},
    ]

    tool = UpdateTasksTool(**tool_kwargs)
    with patch("chatServer.tools.task_tools._get_task_service", return_value=mock_task_service):
        result = await tool._arun(tasks=[
            {"id": "t1", "status": "completed"},
            {"id": "t2", "title": "New Title", "priority": 5},
        ])

    assert "Task A" in result
    assert "Task B" in result


@pytest.mark.asyncio
async def test_update_tasks_not_found(mock_task_service, tool_kwargs):
    mock_task_service.update_tasks.return_value = [
        {"id": "bad-id", "error": "Task 'bad-id' not found."},
    ]

    tool = UpdateTasksTool(**tool_kwargs)
    with patch("chatServer.tools.task_tools._get_task_service", return_value=mock_task_service):
        result = await tool._arun(tasks=[{"id": "bad-id", "title": "X"}])

    assert "not found" in result


# --- DeleteTasksTool ---


@pytest.mark.asyncio
async def test_delete_tasks_single(mock_task_service, tool_kwargs):
    mock_task_service.delete_tasks.return_value = [
        {"id": "t1", "title": "Old Task"},
    ]

    tool = DeleteTasksTool(**tool_kwargs)
    with patch("chatServer.tools.task_tools._get_task_service", return_value=mock_task_service):
        result = await tool._arun(ids=["t1"])

    assert 'Deleted: "Old Task"' in result


@pytest.mark.asyncio
async def test_delete_tasks_batch(mock_task_service, tool_kwargs):
    mock_task_service.delete_tasks.return_value = [
        {"id": "t1", "title": "Task A"},
        {"id": "t2", "title": "Task B"},
    ]

    tool = DeleteTasksTool(**tool_kwargs)
    with patch("chatServer.tools.task_tools._get_task_service", return_value=mock_task_service):
        result = await tool._arun(ids=["t1", "t2"])

    assert "Task A" in result
    assert "Task B" in result


@pytest.mark.asyncio
async def test_delete_tasks_not_found(mock_task_service, tool_kwargs):
    mock_task_service.delete_tasks.return_value = [
        {"id": "bad-id", "error": "Task 'bad-id' not found."},
    ]

    tool = DeleteTasksTool(**tool_kwargs)
    with patch("chatServer.tools.task_tools._get_task_service", return_value=mock_task_service):
        result = await tool._arun(ids=["bad-id"])

    assert "not found" in result
