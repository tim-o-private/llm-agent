"""WorkflowRunManager — start, monitor, cancel, resume workflow runs.

Coordinates graph compilation, background execution, and state tracking
via the workflow_runs table.
"""

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Coroutine, Optional

from .builder import GraphBuilder
from .checkpointer import get_workflow_checkpointer
from .engine import AnthropicEngine
from .models import (
    MissingParameterError,
    WorkflowRunRecord,
    WorkflowRunStatus,
)
from .registry import get_template_registry

logger = logging.getLogger(__name__)


class WorkflowRunManager:
    """Manages workflow run lifecycle: start, monitor, cancel, resume."""

    def __init__(
        self,
        db_client: Any,
        anthropic_client: Any,
        tool_schemas: list[dict],
        tool_executors: dict[str, Callable[..., Coroutine[Any, Any, str]]],
    ):
        self._db = db_client
        self._anthropic_client = anthropic_client
        self._tool_schemas = tool_schemas
        self._tool_executors = tool_executors
        self._active_tasks: dict[str, asyncio.Task] = {}
        self._builder = GraphBuilder()

    async def start_run(
        self,
        user_id: str,
        template_name: str,
        parameters: Optional[dict] = None,
    ) -> str:
        """Start a new workflow run.

        Validates the template and parameters, creates a run record,
        compiles the graph, and launches background execution.

        Returns:
            run_id (UUID string)

        Raises:
            TemplateNotFoundError: If template doesn't exist.
            MissingParameterError: If required parameters are missing.
        """
        parameters = parameters or {}
        registry = get_template_registry()
        template = await registry.get_template(template_name, user_id)

        # Validate required parameters
        missing = [
            p.name for p in template.parameters
            if p.required and p.name not in parameters
        ]
        if missing:
            raise MissingParameterError(missing)

        # Create run record
        run_id = str(uuid.uuid4())
        thread_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()

        await self._db.table("workflow_runs").insert({
            "id": run_id,
            "user_id": user_id,
            "template_name": template_name,
            "thread_id": thread_id,
            "status": WorkflowRunStatus.running.value,
            "parameters": parameters,
            "step_outputs": {},
            "current_step": "",
            "started_at": now,
            "created_at": now,
        }).execute()

        # Build engine and graph
        engine = AnthropicEngine(
            client=self._anthropic_client,
            tool_schemas=self._tool_schemas,
            tool_executors=self._tool_executors,
            user_id=user_id,
        )

        checkpointer = get_workflow_checkpointer()
        compiled, interrupt_nodes = self._builder.build(
            template, engine, checkpointer=checkpointer.saver,
        )

        # Launch background execution
        task = asyncio.create_task(
            self._execute_run(
                run_id=run_id,
                user_id=user_id,
                thread_id=thread_id,
                compiled=compiled,
                parameters=parameters,
                has_gates=bool(interrupt_nodes),
            ),
            name=f"workflow-{run_id}",
        )
        self._active_tasks[run_id] = task

        logger.info(
            "Started workflow run %s (template=%s, user=%s)",
            run_id, template_name, user_id,
        )
        return run_id

    async def get_run_status(self, run_id: str) -> Optional[WorkflowRunRecord]:
        """Get the current status of a workflow run."""
        result = await self._db.table("workflow_runs").select("*").eq(
            "id", run_id
        ).execute()
        if not result.data:
            return None
        row = result.data[0]
        return WorkflowRunRecord(
            id=row["id"],
            user_id=row["user_id"],
            template_name=row["template_name"],
            thread_id=row["thread_id"],
            status=WorkflowRunStatus(row["status"]),
            parameters=row.get("parameters", {}),
            step_outputs=row.get("step_outputs", {}),
            current_step=row.get("current_step", ""),
            error=row.get("error"),
            started_at=row.get("started_at"),
            completed_at=row.get("completed_at"),
            created_at=row.get("created_at"),
        )

    async def list_runs(
        self,
        user_id: str,
        status_filter: Optional[str] = None,
    ) -> list[WorkflowRunRecord]:
        """List workflow runs for a user."""
        query = self._db.table("workflow_runs").select("*").eq(
            "user_id", user_id
        ).order("created_at", desc=True)

        if status_filter:
            query = query.eq("status", status_filter)

        result = await query.execute()
        return [
            WorkflowRunRecord(
                id=row["id"],
                user_id=row["user_id"],
                template_name=row["template_name"],
                thread_id=row["thread_id"],
                status=WorkflowRunStatus(row["status"]),
                parameters=row.get("parameters", {}),
                step_outputs=row.get("step_outputs", {}),
                current_step=row.get("current_step", ""),
                error=row.get("error"),
                started_at=row.get("started_at"),
                completed_at=row.get("completed_at"),
                created_at=row.get("created_at"),
            )
            for row in result.data
        ]

    async def cancel_run(self, run_id: str) -> bool:
        """Cancel a running workflow.

        Returns True if the run was cancelled, False if not found or already done.
        """
        task = self._active_tasks.pop(run_id, None)
        if task and not task.done():
            task.cancel()

        now = datetime.now(timezone.utc).isoformat()
        result = await self._db.table("workflow_runs").update({
            "status": WorkflowRunStatus.cancelled.value,
            "completed_at": now,
        }).eq("id", run_id).in_(
            "status", ["running", "waiting_for_approval", "pending"]
        ).execute()

        cancelled = bool(result.data)
        if cancelled:
            logger.info("Cancelled workflow run %s", run_id)
        return cancelled

    async def resume_run(
        self, run_id: str, approval_data: Optional[dict] = None
    ) -> bool:
        """Resume a workflow run after human gate approval.

        Returns True if resumed, False if not found or not waiting.
        """
        record = await self.get_run_status(run_id)
        if not record or record.status != WorkflowRunStatus.waiting_for_approval:
            return False

        # Update state and re-invoke the graph
        # (Detailed resume logic will be in FU-5 with human gate integration)
        await self._db.table("workflow_runs").update({
            "status": WorkflowRunStatus.running.value,
        }).eq("id", run_id).execute()

        logger.info("Resumed workflow run %s", run_id)
        return True

    async def _execute_run(
        self,
        run_id: str,
        user_id: str,
        thread_id: str,
        compiled: Any,
        parameters: dict,
        has_gates: bool,
    ) -> None:
        """Background task that executes the workflow graph."""
        try:
            config = {"configurable": {"thread_id": thread_id}}
            initial_state = {
                "messages": [],
                "step_outputs": {},
                "parameters": parameters,
                "current_step": "",
                "status": "running",
                "approval": None,
            }

            result = await compiled.ainvoke(initial_state, config)

            # Update run record with results
            now = datetime.now(timezone.utc).isoformat()
            step_outputs = result.get("step_outputs", {})
            final_step = result.get("current_step", "")
            status = result.get("status", "completed")

            if status == "waiting_for_approval":
                await self._db.table("workflow_runs").update({
                    "status": WorkflowRunStatus.waiting_for_approval.value,
                    "step_outputs": step_outputs,
                    "current_step": final_step,
                }).eq("id", run_id).execute()
            else:
                await self._db.table("workflow_runs").update({
                    "status": WorkflowRunStatus.completed.value,
                    "step_outputs": step_outputs,
                    "current_step": final_step,
                    "completed_at": now,
                }).eq("id", run_id).execute()

            logger.info("Workflow run %s completed", run_id)

        except asyncio.CancelledError:
            logger.info("Workflow run %s cancelled", run_id)
            raise

        except Exception as e:
            logger.error(
                "Workflow run %s failed: %s", run_id, e, exc_info=True
            )
            now = datetime.now(timezone.utc).isoformat()
            try:
                await self._db.table("workflow_runs").update({
                    "status": WorkflowRunStatus.failed.value,
                    "error": str(e),
                    "completed_at": now,
                }).eq("id", run_id).execute()
            except Exception:
                logger.error("Failed to update run status for %s", run_id)

        finally:
            self._active_tasks.pop(run_id, None)
