"""Task service for agent tool integration.

Encapsulates business logic for task CRUD operations including
subtask management, position calculation, and status transitions.
"""

import logging
from datetime import date
from typing import Optional

logger = logging.getLogger(__name__)


class TaskService:
    def __init__(self, db_client):
        self.db = db_client

    async def list_tasks(
        self,
        user_id: str,
        status: Optional[str] = None,
        due_date: Optional[str] = None,
        include_completed: bool = False,
        include_subtasks: bool = False,
        parent_task_id: Optional[str] = None,
        limit: int = 20,
    ) -> list[dict]:
        """List tasks for a user with optional filters.

        Args:
            user_id: The user's ID.
            status: Filter by specific status.
            due_date: Filter tasks due on or before this ISO date.
            include_completed: Include completed/skipped/deferred tasks.
            include_subtasks: If True, include subtasks inline. If False, top-level only.
            parent_task_id: If set, return subtasks of this parent.
            limit: Max results (1-50).
        """
        query = self.db.table("tasks").select("*").eq("user_id", user_id).eq("deleted", False)

        if parent_task_id:
            query = query.eq("parent_task_id", parent_task_id)
            query = query.order("subtask_position", desc=False)
        elif not include_subtasks:
            query = query.is_("parent_task_id", "null")
            query = query.order("position", desc=False)
        else:
            query = query.order("position", desc=False)

        if status:
            query = query.eq("status", status)
        elif not include_completed:
            query = query.not_.in_("status", ["completed", "skipped"])

        if due_date:
            query = query.lte("due_date", due_date)

        query = query.limit(limit)
        result = await query.execute()
        tasks = result.data or []

        # Attach subtask counts for top-level tasks
        if not parent_task_id and not include_subtasks:
            for task in tasks:
                count_result = (
                    await self.db.table("tasks")
                    .select("id", count="exact")
                    .eq("parent_task_id", task["id"])
                    .eq("deleted", False)
                    .execute()
                )
                task["subtask_count"] = count_result.count or 0

                # Count completed subtasks
                completed_result = (
                    await self.db.table("tasks")
                    .select("id", count="exact")
                    .eq("parent_task_id", task["id"])
                    .eq("deleted", False)
                    .eq("status", "completed")
                    .execute()
                )
                task["subtasks_completed"] = completed_result.count or 0

        return tasks

    async def get_task(self, user_id: str, task_id: str) -> Optional[dict]:
        """Get a single task by ID, including its subtasks.

        Returns None if not found.
        """
        result = (
            await self.db.table("tasks")
            .select("*")
            .eq("id", task_id)
            .eq("user_id", user_id)
            .eq("deleted", False)
            .maybe_single()
            .execute()
        )

        task = result.data
        if not task:
            return None

        # Fetch subtasks
        subtasks_result = (
            await self.db.table("tasks")
            .select("*")
            .eq("parent_task_id", task_id)
            .eq("user_id", user_id)
            .eq("deleted", False)
            .order("subtask_position", desc=False)
            .execute()
        )
        task["subtasks"] = subtasks_result.data or []

        return task

    async def create_task(
        self,
        user_id: str,
        title: str,
        description: Optional[str] = None,
        priority: int = 2,
        due_date: Optional[str] = None,
        status: str = "pending",
        parent_task_id: Optional[str] = None,
        category: Optional[str] = None,
    ) -> dict:
        """Create a task or subtask.

        Auto-calculates position/subtask_position as max+1 among siblings.
        Validates parent exists if parent_task_id is provided.
        """
        if status not in ("pending", "planning"):
            raise ValueError(f"Initial status must be 'pending' or 'planning', got '{status}'")

        # Validate due_date format if provided
        if due_date:
            try:
                date.fromisoformat(due_date)
            except ValueError:
                raise ValueError(f"Invalid due_date format: '{due_date}'. Use YYYY-MM-DD.")

        data = {
            "user_id": user_id,
            "title": title,
            "status": status,
            "priority": priority,
            "completed": False,
        }

        if description:
            data["description"] = description
        if due_date:
            data["due_date"] = due_date
        if category:
            data["category"] = category

        if parent_task_id:
            # Validate parent exists and belongs to user
            parent = (
                await self.db.table("tasks")
                .select("id")
                .eq("id", parent_task_id)
                .eq("user_id", user_id)
                .eq("deleted", False)
                .maybe_single()
                .execute()
            )
            if not parent.data:
                raise ValueError(f"Parent task '{parent_task_id}' not found.")

            data["parent_task_id"] = parent_task_id

            # Calculate next subtask_position
            max_pos_result = (
                await self.db.table("tasks")
                .select("subtask_position")
                .eq("parent_task_id", parent_task_id)
                .eq("user_id", user_id)
                .eq("deleted", False)
                .order("subtask_position", desc=True)
                .limit(1)
                .execute()
            )
            if max_pos_result.data and max_pos_result.data[0].get("subtask_position") is not None:
                data["subtask_position"] = max_pos_result.data[0]["subtask_position"] + 1
            else:
                data["subtask_position"] = 0
        else:
            # Calculate next top-level position
            max_pos_result = (
                await self.db.table("tasks")
                .select("position")
                .eq("user_id", user_id)
                .is_("parent_task_id", "null")
                .eq("deleted", False)
                .order("position", desc=True)
                .limit(1)
                .execute()
            )
            if max_pos_result.data and max_pos_result.data[0].get("position") is not None:
                data["position"] = max_pos_result.data[0]["position"] + 1
            else:
                data["position"] = 0

        result = await self.db.table("tasks").insert(data).execute()
        return result.data[0]

    async def update_task(
        self,
        user_id: str,
        task_id: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        status: Optional[str] = None,
        priority: Optional[int] = None,
        due_date: Optional[str] = None,
        notes: Optional[str] = None,
        completion_note: Optional[str] = None,
    ) -> Optional[dict]:
        """Update a task's fields.

        Returns the updated task, or None if not found.
        Sets `completed = true` when status changes to 'completed'.
        """
        valid_statuses = {"pending", "planning", "in_progress", "completed", "skipped", "deferred"}
        if status and status not in valid_statuses:
            raise ValueError(f"Invalid status '{status}'. Must be one of: {', '.join(sorted(valid_statuses))}")

        if due_date is not None and due_date != "":
            try:
                date.fromisoformat(due_date)
            except ValueError:
                raise ValueError(f"Invalid due_date format: '{due_date}'. Use YYYY-MM-DD.")

        updates = {}
        if title is not None:
            updates["title"] = title
        if description is not None:
            updates["description"] = description
        if status is not None:
            updates["status"] = status
            updates["completed"] = status == "completed"
        if priority is not None:
            updates["priority"] = priority
        if due_date is not None:
            updates["due_date"] = due_date if due_date != "" else None
        if notes is not None:
            updates["notes"] = notes
        if completion_note is not None:
            updates["completion_note"] = completion_note

        if not updates:
            raise ValueError("No fields to update.")

        result = (
            await self.db.table("tasks")
            .update(updates)
            .eq("id", task_id)
            .eq("user_id", user_id)
            .eq("deleted", False)
            .execute()
        )

        if not result.data:
            return None
        return result.data[0]

    async def delete_task(self, user_id: str, task_id: str) -> Optional[dict]:
        """Soft-delete a task and its subtasks.

        Returns the deleted task, or None if not found.
        """
        # Soft-delete subtasks first
        await (
            self.db.table("tasks")
            .update({"deleted": True})
            .eq("parent_task_id", task_id)
            .eq("user_id", user_id)
            .execute()
        )

        # Soft-delete the task itself
        result = (
            await self.db.table("tasks")
            .update({"deleted": True})
            .eq("id", task_id)
            .eq("user_id", user_id)
            .eq("deleted", False)
            .execute()
        )

        if not result.data:
            return None
        return result.data[0]
