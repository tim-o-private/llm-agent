"""Progress tracking — writes workflow status messages to chat history.

Simplified approach: instead of a separate workflow_events table with
Postgres polling, we write progress as assistant messages to the active
chat session's message history. The user sees progress inline in their
conversation.
"""

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


class ProgressWriter:
    """Writes workflow progress messages to chat message history.

    Progress messages appear as assistant messages in the conversation,
    tagged with metadata for the frontend to render distinctly.
    """

    def __init__(
        self,
        pg_connection: Any,
        session_id: str,
        run_id: str,
        template_name: str,
    ):
        self._pg = pg_connection
        self._session_id = session_id
        self._run_id = run_id
        self._template_name = template_name

    async def step_started(self, step_name: str) -> None:
        """Record that a workflow step has started."""
        await self._write_progress(
            f"[Workflow '{self._template_name}'] Starting step: {step_name}",
            event_type="step_started",
            step_name=step_name,
        )

    async def step_completed(
        self, step_name: str, output_preview: Optional[str] = None
    ) -> None:
        """Record that a workflow step completed."""
        msg = f"[Workflow '{self._template_name}'] Completed step: {step_name}"
        if output_preview:
            # Truncate long outputs
            preview = output_preview[:500]
            if len(output_preview) > 500:
                preview += "..."
            msg += f"\n{preview}"
        await self._write_progress(
            msg,
            event_type="step_completed",
            step_name=step_name,
        )

    async def approval_required(
        self, step_name: str, description: str
    ) -> None:
        """Record that a step requires human approval."""
        await self._write_progress(
            f"[Workflow '{self._template_name}'] Approval needed for: {step_name}\n{description}",
            event_type="approval_required",
            step_name=step_name,
        )

    async def workflow_completed(self, summary: Optional[str] = None) -> None:
        """Record workflow completion."""
        msg = f"[Workflow '{self._template_name}'] Completed"
        if summary:
            msg += f"\n{summary}"
        await self._write_progress(msg, event_type="workflow_completed")

    async def workflow_failed(self, error: str) -> None:
        """Record workflow failure."""
        await self._write_progress(
            f"[Workflow '{self._template_name}'] Failed: {error}",
            event_type="workflow_failed",
        )

    async def _write_progress(
        self,
        message: str,
        event_type: str,
        step_name: Optional[str] = None,
    ) -> None:
        """Write a progress message to chat_message_history."""
        try:
            async with self._pg.cursor() as cur:
                await cur.execute(
                    """
                    INSERT INTO chat_message_history (session_id, message)
                    VALUES (%s, %s)
                    """,
                    (
                        self._session_id,
                        {
                            "type": "ai",
                            "data": {
                                "content": message,
                                "additional_kwargs": {
                                    "workflow_event": True,
                                    "event_type": event_type,
                                    "run_id": self._run_id,
                                    "template_name": self._template_name,
                                    "step_name": step_name,
                                },
                            },
                        },
                    ),
                )
        except Exception as e:
            logger.error(
                "Failed to write progress for run %s: %s",
                self._run_id, e, exc_info=True,
            )


class HumanGate:
    """Manages human approval gates for workflow steps.

    When a step has gate_policy: "human-required", this class creates
    a pending action and waits for user approval/rejection.
    """

    def __init__(self, pending_actions_service: Any, notification_service: Any):
        self._pending_actions = pending_actions_service
        self._notifications = notification_service

    async def request_approval(
        self,
        user_id: str,
        run_id: str,
        step_name: str,
        output_preview: str,
        template_name: str,
        session_id: Optional[str] = None,
    ) -> str:
        """Create a pending action for workflow gate approval.

        Returns the pending_action_id.
        """
        action_id = await self._pending_actions.queue_action(
            user_id=user_id,
            session_id=session_id or "",
            tool_name="workflow_gate",
            tool_args={
                "run_id": run_id,
                "step_name": step_name,
                "output_preview": output_preview[:1000],
            },
            context={
                "template_name": template_name,
                "current_step": step_name,
            },
        )

        # Notify user about the approval request
        await self._notifications.notify_user(
            user_id=user_id,
            title=f"Workflow approval needed: {step_name}",
            body=f"Workflow '{template_name}' needs your approval for step '{step_name}'.",
            category="workflow_gate",
            metadata={
                "run_id": run_id,
                "step_name": step_name,
                "pending_action_id": str(action_id),
            },
        )

        return str(action_id)
