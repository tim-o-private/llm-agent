"""Tests for agent task tools."""

from unittest.mock import AsyncMock, patch

import pytest

from chatServer.tools.task_tools import (
    CreateTaskTool,
    DeleteTaskTool,
    GetTasksTool,
    GetTaskTool,
    UpdateTaskTool,
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


# --- GetTasksTool ---


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

    assert "Failed to list tasks" in result


# --- GetTaskTool ---


@pytest.mark.asyncio
async def test_get_task_found(mock_task_service, tool_kwargs):
    mock_task_service.get_task.return_value = {
        "id": "t1",
        "title": "My Task",
        "priority": 3,
        "status": "pending",
        "subtasks": [],
    }

    tool = GetTaskTool(**tool_kwargs)
    with patch("chatServer.tools.task_tools._get_task_service", return_value=mock_task_service):
        result = await tool._arun(task_id="t1")

    assert "My Task" in result
    assert "t1" in result


@pytest.mark.asyncio
async def test_get_task_not_found(mock_task_service, tool_kwargs):
    mock_task_service.get_task.return_value = None

    tool = GetTaskTool(**tool_kwargs)
    with patch("chatServer.tools.task_tools._get_task_service", return_value=mock_task_service):
        result = await tool._arun(task_id="bad-id")

    assert "not found" in result


# --- CreateTaskTool ---


@pytest.mark.asyncio
async def test_create_task_basic(mock_task_service, tool_kwargs):
    mock_task_service.create_task.return_value = {"id": "new-1", "title": "Buy groceries"}

    tool = CreateTaskTool(**tool_kwargs)
    with patch("chatServer.tools.task_tools._get_task_service", return_value=mock_task_service):
        result = await tool._arun(title="Buy groceries")

    assert 'Created task: "Buy groceries"' in result
    assert "status: pending" in result


@pytest.mark.asyncio
async def test_create_task_with_all_fields(mock_task_service, tool_kwargs):
    mock_task_service.create_task.return_value = {"id": "new-2", "title": "Review PR"}

    tool = CreateTaskTool(**tool_kwargs)
    with patch("chatServer.tools.task_tools._get_task_service", return_value=mock_task_service):
        result = await tool._arun(
            title="Review PR",
            priority=4,
            due_date="2026-02-25",
            status="planning",
            category="work",
        )

    assert "Review PR" in result
    assert "due: 2026-02-25" in result
    assert "high" in result


@pytest.mark.asyncio
async def test_create_subtask(mock_task_service, tool_kwargs):
    mock_task_service.create_task.return_value = {
        "id": "sub-1",
        "title": "Step 1",
        "parent_task_id": "parent-1",
    }

    tool = CreateTaskTool(**tool_kwargs)
    with patch("chatServer.tools.task_tools._get_task_service", return_value=mock_task_service):
        result = await tool._arun(title="Step 1", parent_task_id="parent-1")

    assert "[subtask of parent-1]" in result


@pytest.mark.asyncio
async def test_create_task_validation_error(mock_task_service, tool_kwargs):
    mock_task_service.create_task.side_effect = ValueError("Initial status must be 'pending' or 'planning'")

    tool = CreateTaskTool(**tool_kwargs)
    with patch("chatServer.tools.task_tools._get_task_service", return_value=mock_task_service):
        result = await tool._arun(title="Bad", status="completed")

    assert "Error:" in result


# --- UpdateTaskTool ---


@pytest.mark.asyncio
async def test_update_task_status(mock_task_service, tool_kwargs):
    mock_task_service.update_task.return_value = {"id": "t1", "title": "Done Task", "status": "completed"}

    tool = UpdateTaskTool(**tool_kwargs)
    with patch("chatServer.tools.task_tools._get_task_service", return_value=mock_task_service):
        result = await tool._arun(task_id="t1", status="completed")

    assert 'Updated "Done Task"' in result
    assert "status → completed ✓" in result


@pytest.mark.asyncio
async def test_update_task_multiple_fields(mock_task_service, tool_kwargs):
    mock_task_service.update_task.return_value = {"id": "t1", "title": "New Title"}

    tool = UpdateTaskTool(**tool_kwargs)
    with patch("chatServer.tools.task_tools._get_task_service", return_value=mock_task_service):
        result = await tool._arun(task_id="t1", title="New Title", priority=5)

    assert "New Title" in result
    assert "URGENT" in result


@pytest.mark.asyncio
async def test_update_task_not_found(mock_task_service, tool_kwargs):
    mock_task_service.update_task.return_value = None

    tool = UpdateTaskTool(**tool_kwargs)
    with patch("chatServer.tools.task_tools._get_task_service", return_value=mock_task_service):
        result = await tool._arun(task_id="bad-id", title="X")

    assert "not found" in result


# --- DeleteTaskTool ---


@pytest.mark.asyncio
async def test_delete_task_success(mock_task_service, tool_kwargs):
    mock_task_service.delete_task.return_value = {"id": "t1", "title": "Old Task"}

    tool = DeleteTaskTool(**tool_kwargs)
    with patch("chatServer.tools.task_tools._get_task_service", return_value=mock_task_service):
        result = await tool._arun(task_id="t1")

    assert 'Deleted task: "Old Task"' in result


@pytest.mark.asyncio
async def test_delete_task_not_found(mock_task_service, tool_kwargs):
    mock_task_service.delete_task.return_value = None

    tool = DeleteTaskTool(**tool_kwargs)
    with patch("chatServer.tools.task_tools._get_task_service", return_value=mock_task_service):
        result = await tool._arun(task_id="bad-id")

    assert "not found" in result
