"""Task tools for agent integration.

Provides GetTasksTool, CreateTasksTool, UpdateTasksTool, DeleteTasksTool
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
    parts.append(f"[id: {task.get('id', '?')}]")

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


async def _get_task_service(user_id: str):
    """Get a TaskService instance with a user-scoped Supabase client."""
    from ..database.scoped_client import UserScopedClient
    from ..database.supabase_client import get_supabase_client
    from ..services.task_service import TaskService

    raw_client = await get_supabase_client()
    db = UserScopedClient(raw_client, user_id)
    return TaskService(db)


# --- GetTasksTool ---


class GetTasksInput(BaseModel):
    """Input schema for get_tasks tool."""

    id: Optional[str] = Field(
        default=None,
        description="UUID of a specific task to retrieve with full detail. When provided, other filters are ignored.",
    )
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
    """List user's tasks with optional filters, or get a single task by ID."""

    name: str = "get_tasks"
    description: str = (
        "List the user's tasks, or get a single task by ID. "
        "By default shows top-level pending/in-progress tasks. "
        "Pass 'id' to get full detail on one task (including subtasks). "
        "Use filters to narrow results by status, due date, or to include completed tasks and subtasks."
    )
    args_schema: Type[BaseModel] = GetTasksInput

    user_id: str
    agent_name: Optional[str] = None
    supabase_url: Optional[str] = None
    supabase_key: Optional[str] = None

    @classmethod
    def prompt_section(cls, channel: str) -> str | None:
        """Return behavioral guidance for the agent prompt, or None to omit."""
        if channel in ("web", "telegram"):
            return "Tasks: Check get_tasks at conversation start to see what the user is working on. When they mention something actionable, use create_tasks. Update status as work progresses with update_tasks."  # noqa: E501
        elif channel == "heartbeat":
            return "Tasks: Call get_tasks to check for overdue or stale tasks. Report any that need attention."
        elif channel == "scheduled":
            return None
        else:
            return "Tasks: Check get_tasks at conversation start to see what the user is working on. When they mention something actionable, use create_tasks. Update status as work progresses with update_tasks."  # noqa: E501

    def _run(self, **kwargs) -> str:
        return "get_tasks requires async execution. Use _arun."

    async def _arun(
        self,
        id: Optional[str] = None,
        status: Optional[str] = None,
        due_date: Optional[str] = None,
        include_completed: bool = False,
        include_subtasks: bool = False,
        limit: int = 20,
    ) -> str:
        try:
            service = await _get_task_service(self.user_id)

            # Single task detail mode
            if id:
                task = await service.get_task(user_id=self.user_id, task_id=id)
                if not task:
                    return f"Task '{id}' not found."
                return _format_task_detail(task)

            # List mode
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
            return f"Failed to get tasks: {e}"


# --- CreateTasksTool ---


class CreateTasksInput(BaseModel):
    """Input schema for create_tasks tool."""

    tasks: list[dict] = Field(
        ...,
        description=(
            "List of tasks to create. Each dict can have: "
            "title (required, str), description (str), priority (int 1-5, default 2), "
            "due_date (YYYY-MM-DD), status ('pending' or 'planning', default 'pending'), "
            "parent_task_id (UUID of parent for subtasks), category (str). "
            "Single task = list with one item."
        ),
        min_length=1,
    )


class CreateTasksTool(BaseTool):
    """Create one or more tasks."""

    name: str = "create_tasks"
    description: str = (
        "Create one or more tasks for the user. Input is a list of task objects. "
        "Each task must have a 'title'. Optional: description, priority (1-5), due_date (YYYY-MM-DD), "
        "status ('pending'/'planning'), parent_task_id (for subtasks), category. "
        "For a single task, pass a list with one item."
    )
    args_schema: Type[BaseModel] = CreateTasksInput

    user_id: str
    agent_name: Optional[str] = None
    supabase_url: Optional[str] = None
    supabase_key: Optional[str] = None

    def _run(self, **kwargs) -> str:
        return "create_tasks requires async execution. Use _arun."

    async def _arun(self, tasks: list[dict]) -> str:
        try:
            service = await _get_task_service(self.user_id)
            results = await service.create_tasks(user_id=self.user_id, tasks=tasks)

            lines = []
            for result in results:
                if result.get("error"):
                    lines.append(f'Error: {result["error"]}')
                else:
                    title = result.get("title", "Untitled")
                    priority = PRIORITY_LABELS.get(result.get("priority", 2), "MED")
                    parts = [f'Created: "{title}" (priority: {priority.lower()}']
                    if result.get("due_date"):
                        parts.append(f", due: {result['due_date']}")
                    parts.append(f", status: {result.get('status', 'pending')})")
                    if result.get("parent_task_id"):
                        parts.append(f" [subtask of {result['parent_task_id']}]")
                    lines.append("".join(parts))

            return "\n".join(lines)

        except Exception as e:
            logger.error(f"create_tasks failed for user {self.user_id}: {e}")
            return f"Failed to create tasks: {e}"


# --- UpdateTasksTool ---


class UpdateTasksInput(BaseModel):
    """Input schema for update_tasks tool."""

    tasks: list[dict] = Field(
        ...,
        description=(
            "List of task updates. Each dict must have 'id' (UUID) plus fields to update: "
            "title, description, status (pending/planning/in_progress/completed/skipped/deferred), "
            "priority (int 1-5), due_date (YYYY-MM-DD or empty string to clear), "
            "notes (str), completion_note (str). Only provided fields are changed. "
            "Single update = list with one item."
        ),
        min_length=1,
    )


class UpdateTasksTool(BaseTool):
    """Update one or more tasks."""

    name: str = "update_tasks"
    description: str = (
        "Update one or more tasks. Input is a list of objects, each with 'id' and fields to change. "
        "To mark complete, set status to 'completed'. To clear due date, pass empty string. "
        "For a single update, pass a list with one item."
    )
    args_schema: Type[BaseModel] = UpdateTasksInput

    user_id: str
    agent_name: Optional[str] = None
    supabase_url: Optional[str] = None
    supabase_key: Optional[str] = None

    def _run(self, **kwargs) -> str:
        return "update_tasks requires async execution. Use _arun."

    async def _arun(self, tasks: list[dict]) -> str:
        try:
            service = await _get_task_service(self.user_id)
            results = await service.update_tasks(user_id=self.user_id, tasks=tasks)

            lines = []
            for result in results:
                if result.get("error"):
                    task_id = result.get("id", "?")
                    lines.append(f"Error ({task_id}): {result['error']}")
                else:
                    task_title = result.get("title", result.get("id", "?"))
                    changes = result.get("changes", [])
                    lines.append(f'Updated "{task_title}": {", ".join(changes)}')

            return "\n".join(lines)

        except Exception as e:
            logger.error(f"update_tasks failed for user {self.user_id}: {e}")
            return f"Failed to update tasks: {e}"


# --- DeleteTasksTool ---


class DeleteTasksInput(BaseModel):
    """Input schema for delete_tasks tool."""

    ids: list[str] = Field(
        ...,
        description="List of task UUIDs to delete (soft-delete). Single delete = list with one ID.",
        min_length=1,
    )


class DeleteTasksTool(BaseTool):
    """Soft-delete one or more tasks and their subtasks."""

    name: str = "delete_tasks"
    description: str = (
        "Delete one or more tasks and all their subtasks. This is a soft delete (can be undone). "
        "Use this when the user explicitly asks to remove tasks. "
        "For a single delete, pass a list with one ID."
    )
    args_schema: Type[BaseModel] = DeleteTasksInput

    user_id: str
    agent_name: Optional[str] = None
    supabase_url: Optional[str] = None
    supabase_key: Optional[str] = None

    def _run(self, **kwargs) -> str:
        return "delete_tasks requires async execution. Use _arun."

    async def _arun(self, ids: list[str]) -> str:
        try:
            service = await _get_task_service(self.user_id)
            results = await service.delete_tasks(user_id=self.user_id, task_ids=ids)

            lines = []
            for result in results:
                if result.get("error"):
                    task_id = result.get("id", "?")
                    lines.append(f"Error ({task_id}): {result['error']}")
                else:
                    lines.append(f'Deleted: "{result.get("title", result.get("id", "?"))}"')

            return "\n".join(lines)

        except Exception as e:
            logger.error(f"delete_tasks failed for user {self.user_id}: {e}")
            return f"Failed to delete tasks: {e}"
