"""Task tools for agent integration.

Provides GetTasksTool, GetTaskTool, CreateTaskTool, UpdateTaskTool, DeleteTaskTool
for LangChain agents. Follows the BaseTool pattern established by reminder_tools.py.
"""

import logging
from typing import Optional, Type

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

PRIORITY_LABELS = {1: "LOW", 2: "MED", 3: "MED", 4: "HIGH", 5: "URGENT"}


def _format_task_line(task: dict, index: int) -> str:
    """Format a single task as a readable line."""
    priority = PRIORITY_LABELS.get(task.get("priority", 2), "MED")
    status = task.get("status", "pending")
    title = task.get("title", "Untitled")

    parts = [f"{index}. [{priority}] {title}"]

    due = task.get("due_date")
    if due:
        parts.append(f"(due: {due})")

    parts.append(f"— {status}")

    subtask_count = task.get("subtask_count", 0)
    if subtask_count > 0:
        completed = task.get("subtasks_completed", 0)
        parts.append(f"\n   └─ {subtask_count} subtask(s) ({completed} completed)")

    return " ".join(parts)


def _format_task_detail(task: dict) -> str:
    """Format a task with full detail including subtasks."""
    priority = PRIORITY_LABELS.get(task.get("priority", 2), "MED")
    lines = [
        f"Task: {task.get('title', 'Untitled')}",
        f"ID: {task['id']}",
        f"Status: {task.get('status', 'pending')} | Priority: {priority}",
    ]

    if task.get("due_date"):
        lines.append(f"Due: {task['due_date']}")
    if task.get("category"):
        lines.append(f"Category: {task['category']}")
    if task.get("description"):
        lines.append(f"Description: {task['description']}")
    if task.get("notes"):
        lines.append(f"Notes: {task['notes']}")
    if task.get("motivation"):
        lines.append(f"Motivation: {task['motivation']}")

    subtasks = task.get("subtasks", [])
    if subtasks:
        lines.append(f"\nSubtasks ({len(subtasks)}):")
        for i, st in enumerate(subtasks, 1):
            check = "x" if st.get("status") == "completed" else " "
            lines.append(f"  [{check}] {i}. {st.get('title', 'Untitled')} — {st.get('status', 'pending')}")

    return "\n".join(lines)


async def _get_task_service():
    """Get a TaskService instance with the shared async Supabase client."""
    from ..database.supabase_client import get_supabase_client
    from ..services.task_service import TaskService

    db = await get_supabase_client()
    return TaskService(db)


# --- GetTasksTool ---


class GetTasksInput(BaseModel):
    """Input schema for get_tasks tool."""

    status: Optional[str] = Field(
        default=None,
        description="Filter by status: 'pending', 'planning', 'in_progress', 'completed', 'skipped', 'deferred'",
    )
    due_date: Optional[str] = Field(
        default=None,
        description="Filter: ISO date (YYYY-MM-DD), returns tasks due on or before this date",
    )
    include_completed: bool = Field(
        default=False,
        description="Include completed/skipped tasks (excluded by default)",
    )
    include_subtasks: bool = Field(
        default=False,
        description="Include subtasks inline (default: top-level only)",
    )
    limit: int = Field(default=20, ge=1, le=50, description="Max tasks to return (1-50)")


class GetTasksTool(BaseTool):
    """List user's tasks with optional filters."""

    name: str = "get_tasks"
    description: str = (
        "List the user's tasks. By default shows top-level pending/in-progress tasks. "
        "Use filters to narrow results by status, due date, or to include completed tasks and subtasks."
    )
    args_schema: Type[BaseModel] = GetTasksInput

    user_id: str
    agent_name: Optional[str] = None
    supabase_url: Optional[str] = None
    supabase_key: Optional[str] = None

    def _run(self, **kwargs) -> str:
        return "get_tasks requires async execution. Use _arun."

    async def _arun(
        self,
        status: Optional[str] = None,
        due_date: Optional[str] = None,
        include_completed: bool = False,
        include_subtasks: bool = False,
        limit: int = 20,
    ) -> str:
        try:
            service = await _get_task_service()
            tasks = await service.list_tasks(
                user_id=self.user_id,
                status=status,
                due_date=due_date,
                include_completed=include_completed,
                include_subtasks=include_subtasks,
                limit=limit,
            )

            if not tasks:
                if status:
                    return f"No tasks found with status '{status}'."
                return "No tasks found."

            lines = [f"You have {len(tasks)} task(s):\n"]
            for i, task in enumerate(tasks, 1):
                lines.append(_format_task_line(task, i))

            return "\n".join(lines)

        except Exception as e:
            logger.error(f"get_tasks failed for user {self.user_id}: {e}")
            return f"Failed to list tasks: {e}"


# --- GetTaskTool ---


class GetTaskInput(BaseModel):
    """Input schema for get_task tool."""

    task_id: str = Field(..., description="UUID of the task to retrieve")


class GetTaskTool(BaseTool):
    """Get a single task with its subtasks."""

    name: str = "get_task"
    description: str = "Get detailed information about a specific task by its ID, including all subtasks."
    args_schema: Type[BaseModel] = GetTaskInput

    user_id: str
    agent_name: Optional[str] = None
    supabase_url: Optional[str] = None
    supabase_key: Optional[str] = None

    def _run(self, **kwargs) -> str:
        return "get_task requires async execution. Use _arun."

    async def _arun(self, task_id: str) -> str:
        try:
            service = await _get_task_service()
            task = await service.get_task(user_id=self.user_id, task_id=task_id)

            if not task:
                return f"Task '{task_id}' not found."

            return _format_task_detail(task)

        except Exception as e:
            logger.error(f"get_task failed for user {self.user_id}: {e}")
            return f"Failed to get task: {e}"


# --- CreateTaskTool ---


class CreateTaskInput(BaseModel):
    """Input schema for create_task tool."""

    title: str = Field(..., description="Task title", min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, description="Longer description or notes")
    priority: int = Field(default=2, ge=1, le=5, description="1=lowest, 5=highest")
    due_date: Optional[str] = Field(default=None, description="Due date as YYYY-MM-DD")
    status: str = Field(default="pending", description="Initial status: 'pending' or 'planning'")
    parent_task_id: Optional[str] = Field(
        default=None,
        description="UUID of parent task to create this as a subtask",
    )
    category: Optional[str] = Field(default=None, description="Category label")


class CreateTaskTool(BaseTool):
    """Create a task or subtask."""

    name: str = "create_task"
    description: str = (
        "Create a new task for the user. Set parent_task_id to create a subtask under an existing task. "
        "Priority: 1=lowest, 5=highest. Default status is 'pending'."
    )
    args_schema: Type[BaseModel] = CreateTaskInput

    user_id: str
    agent_name: Optional[str] = None
    supabase_url: Optional[str] = None
    supabase_key: Optional[str] = None

    def _run(self, **kwargs) -> str:
        return "create_task requires async execution. Use _arun."

    async def _arun(
        self,
        title: str,
        description: Optional[str] = None,
        priority: int = 2,
        due_date: Optional[str] = None,
        status: str = "pending",
        parent_task_id: Optional[str] = None,
        category: Optional[str] = None,
    ) -> str:
        try:
            service = await _get_task_service()
            await service.create_task(
                user_id=self.user_id,
                title=title,
                description=description,
                priority=priority,
                due_date=due_date,
                status=status,
                parent_task_id=parent_task_id,
                category=category,
            )

            priority_label = PRIORITY_LABELS.get(priority, "MED")
            parts = [f'Created task: "{title}" (priority: {priority_label.lower()}']
            if due_date:
                parts.append(f", due: {due_date}")
            parts.append(f", status: {status})")
            if parent_task_id:
                parts.append(f" [subtask of {parent_task_id}]")

            return "".join(parts)

        except ValueError as e:
            return f"Error: {e}"
        except Exception as e:
            logger.error(f"create_task failed for user {self.user_id}: {e}")
            return f"Failed to create task: {e}"


# --- UpdateTaskTool ---


class UpdateTaskInput(BaseModel):
    """Input schema for update_task tool."""

    task_id: str = Field(..., description="UUID of the task to update")
    title: Optional[str] = Field(default=None, description="New title")
    description: Optional[str] = Field(default=None, description="New description")
    status: Optional[str] = Field(
        default=None,
        description="New status: 'pending', 'planning', 'in_progress', 'completed', 'skipped', 'deferred'",
    )
    priority: Optional[int] = Field(default=None, ge=1, le=5, description="New priority (1-5)")
    due_date: Optional[str] = Field(default=None, description="New due date (YYYY-MM-DD) or empty string to clear")
    notes: Optional[str] = Field(default=None, description="Additional notes")
    completion_note: Optional[str] = Field(
        default=None,
        description="Note on how/why the task was completed",
    )


class UpdateTaskTool(BaseTool):
    """Update task fields."""

    name: str = "update_task"
    description: str = (
        "Update a task's fields. Only provided fields are changed. "
        "To mark a task complete, set status to 'completed'. "
        "To clear a due date, pass an empty string for due_date."
    )
    args_schema: Type[BaseModel] = UpdateTaskInput

    user_id: str
    agent_name: Optional[str] = None
    supabase_url: Optional[str] = None
    supabase_key: Optional[str] = None

    def _run(self, **kwargs) -> str:
        return "update_task requires async execution. Use _arun."

    async def _arun(
        self,
        task_id: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        status: Optional[str] = None,
        priority: Optional[int] = None,
        due_date: Optional[str] = None,
        notes: Optional[str] = None,
        completion_note: Optional[str] = None,
    ) -> str:
        try:
            service = await _get_task_service()
            task = await service.update_task(
                user_id=self.user_id,
                task_id=task_id,
                title=title,
                description=description,
                status=status,
                priority=priority,
                due_date=due_date,
                notes=notes,
                completion_note=completion_note,
            )

            if not task:
                return f"Task '{task_id}' not found."

            changes = []
            if title is not None:
                changes.append(f"title → \"{title}\"")
            if status is not None:
                mark = " ✓" if status == "completed" else ""
                changes.append(f"status → {status}{mark}")
            if priority is not None:
                changes.append(f"priority → {PRIORITY_LABELS.get(priority, str(priority))}")
            if due_date is not None:
                changes.append(f"due → {due_date or 'cleared'}")
            if description is not None:
                changes.append("description updated")
            if notes is not None:
                changes.append("notes updated")
            if completion_note is not None:
                changes.append("completion note added")

            task_title = task.get("title", task_id)
            return f'Updated "{task_title}": {", ".join(changes)}'

        except ValueError as e:
            return f"Error: {e}"
        except Exception as e:
            logger.error(f"update_task failed for user {self.user_id}: {e}")
            return f"Failed to update task: {e}"


# --- DeleteTaskTool ---


class DeleteTaskInput(BaseModel):
    """Input schema for delete_task tool."""

    task_id: str = Field(..., description="UUID of the task to delete")


class DeleteTaskTool(BaseTool):
    """Soft-delete a task and its subtasks."""

    name: str = "delete_task"
    description: str = (
        "Delete a task and all its subtasks. This is a soft delete (can be undone). "
        "Use this when the user explicitly asks to remove a task."
    )
    args_schema: Type[BaseModel] = DeleteTaskInput

    user_id: str
    agent_name: Optional[str] = None
    supabase_url: Optional[str] = None
    supabase_key: Optional[str] = None

    def _run(self, **kwargs) -> str:
        return "delete_task requires async execution. Use _arun."

    async def _arun(self, task_id: str) -> str:
        try:
            service = await _get_task_service()
            task = await service.delete_task(user_id=self.user_id, task_id=task_id)

            if not task:
                return f"Task '{task_id}' not found."

            return f'Deleted task: "{task.get("title", task_id)}"'

        except Exception as e:
            logger.error(f"delete_task failed for user {self.user_id}: {e}")
            return f"Failed to delete task: {e}"
