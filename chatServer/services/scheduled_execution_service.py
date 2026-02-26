"""
Generalized scheduled agent execution service.

Loads any agent from the database, wraps tools with the approval system,
invokes the agent, and stores the result. Replaces the special-cased
execution logic in BackgroundTaskService._execute_scheduled_agent.

Pattern mirrors chatServer/services/chat.py:225-258 for approval wrapping.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from src.core.agent_loader_db import load_agent_executor_db_async

from ..database.supabase_client import create_user_scoped_client
from ..security.tool_wrapper import ApprovalContext, wrap_tools_with_approval
from ..services.audit_service import AuditService
from ..services.pending_actions import PendingActionsService

logger = logging.getLogger(__name__)

DEFAULT_SCHEDULED_MODEL = "claude-haiku-4-5-20251001"


class ScheduledExecutionService:
    """
    Executes scheduled agent runs with proper agent loading, approval wrapping,
    and result storage.

    Unlike the previous approach in BackgroundTaskService, this service:
    - Always loads agents from DB (never relies on executor cache)
    - Wraps all tools with the approval system
    - Stores results in agent_execution_results
    - Triggers notifications (via NotificationService, when available)
    """

    async def execute(self, schedule: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a scheduled agent run.

        Args:
            schedule: Dict with keys: id, user_id, agent_name, prompt, config

        Returns:
            Dict with success status, output content, and metadata
        """
        user_id = schedule["user_id"]
        agent_name = schedule["agent_name"]
        prompt = schedule["prompt"]
        config = schedule.get("config", {})
        schedule_id = schedule.get("id")

        session_id = f"scheduled_{agent_name}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
        start_time = datetime.now(timezone.utc)
        model_override = config.get("model_override")

        try:
            schedule_type = config.get("schedule_type", "scheduled")
            channel = "heartbeat" if schedule_type == "heartbeat" else "scheduled"

            logger.info(
                f"Executing scheduled agent '{agent_name}' for user {user_id} "
                f"(schedule {schedule_id}, channel={channel})"
            )

            # 1. Load agent from DB — always fresh, never rely on cache
            agent_executor = await load_agent_executor_db_async(
                agent_name=agent_name,
                user_id=user_id,
                session_id=session_id,
                channel=channel,
            )

            # 1b. Apply model override if specified in schedule config (AC-14, AC-16)
            model_used = self._get_model_name(agent_executor)
            if model_override:
                self._apply_model_override(agent_executor, model_override)
                model_used = model_override
                logger.info(f"Applied model override '{model_override}' for scheduled run")

            # 2. Create chat_sessions row for this scheduled run
            supabase_client = await create_user_scoped_client(user_id)
            await supabase_client.table("chat_sessions").insert(
                {
                    "user_id": user_id,
                    "session_id": session_id,
                    "channel": "scheduled",
                    "agent_name": agent_name,
                    "is_active": True,
                }
            ).execute()

            # 3. Wrap tools with approval system (mirrors chat.py:225-245)
            audit_service = AuditService(supabase_client)
            pending_actions_service = PendingActionsService(
                db_client=supabase_client,
                audit_service=audit_service,
            )
            approval_context = ApprovalContext(
                user_id=user_id,
                session_id=session_id,
                agent_name=agent_name,
                db_client=supabase_client,
                pending_actions_service=pending_actions_service,
                audit_service=audit_service,
            )
            if hasattr(agent_executor, "tools") and agent_executor.tools:
                wrap_tools_with_approval(agent_executor.tools, approval_context)
                logger.info(
                    f"Wrapped {len(agent_executor.tools)} tools with approval "
                    f"for scheduled run of '{agent_name}'"
                )

            # 4. Build effective prompt (heartbeat gets checklist formatting)
            if schedule_type == "heartbeat":
                effective_prompt = self._build_heartbeat_prompt(
                    prompt, config.get("heartbeat_checklist", [])
                )
            else:
                effective_prompt = prompt

            # 5. Invoke the agent
            response = await agent_executor.ainvoke(
                {
                    "input": effective_prompt,
                    "chat_history": [],  # Fresh context for scheduled runs
                }
            )

            # 6. Normalize output (handle content block lists from newer langchain-anthropic)
            output = response.get("output", "")
            if isinstance(output, list):
                output = (
                    "".join(
                        block.get("text", "")
                        for block in output
                        if isinstance(block, dict) and block.get("type") == "text"
                    )
                    or "No text content in response."
                )

            # 7. Detect HEARTBEAT_OK suppression
            is_heartbeat_ok = (
                schedule_type == "heartbeat" and output.strip().startswith("HEARTBEAT_OK")
            )

            # 8. Count pending actions created during this run
            pending_count = await pending_actions_service.get_pending_count(user_id)

            # 9. Build execution metadata with token usage (AC-15)
            duration_ms = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)
            execution_metadata = self._build_execution_metadata(
                agent_executor=agent_executor,
                model_used=model_used,
            )

            # 10. Store result (always, for audit trail)
            result_status = "heartbeat_ok" if is_heartbeat_ok else "success"
            await self._store_result(
                supabase_client=supabase_client,
                user_id=user_id,
                schedule_id=schedule_id,
                agent_name=agent_name,
                prompt=prompt,
                result_content=output,
                status=result_status,
                pending_actions_created=pending_count,
                duration_ms=duration_ms,
                metadata=execution_metadata,
            )

            # 11. Notify user (skip when HEARTBEAT_OK or caller handles its own notification)
            skip_notification = config.get("skip_notification", False)
            if is_heartbeat_ok:
                logger.info(
                    f"Heartbeat OK for '{agent_name}' — suppressing notification"
                )
            elif skip_notification:
                logger.info(
                    f"Notification suppressed for '{agent_name}' (caller handles notification)"
                )
            else:
                await self._notify_user(
                    supabase_client=supabase_client,
                    user_id=user_id,
                    agent_name=agent_name,
                    result_content=output,
                    pending_count=pending_count,
                    config=config,
                )

            # 12. Mark session inactive after completion
            await supabase_client.table("chat_sessions").update(
                {"is_active": False}
            ).eq("session_id", session_id).execute()

            logger.info(
                f"Scheduled agent '{agent_name}' completed for user {user_id} "
                f"({duration_ms}ms, {pending_count} pending actions)"
            )

            return {
                "success": True,
                "output": output,
                "pending_actions_created": pending_count,
                "duration_ms": duration_ms,
            }

        except Exception as e:
            duration_ms = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)
            logger.error(
                f"Scheduled agent '{agent_name}' failed for user {user_id}: {e}",
                exc_info=True,
            )

            # Store error result
            try:
                supabase_client = await create_user_scoped_client(user_id)
                await self._store_result(
                    supabase_client=supabase_client,
                    user_id=user_id,
                    schedule_id=schedule_id,
                    agent_name=agent_name,
                    prompt=prompt,
                    result_content=str(e),
                    status="error",
                    pending_actions_created=0,
                    duration_ms=duration_ms,
                )
            except Exception as store_err:
                logger.error(f"Failed to store error result: {store_err}")

            return {
                "success": False,
                "error": str(e),
                "duration_ms": duration_ms,
            }

    def _get_model_name(self, agent_executor) -> str:
        """Extract the model name from the agent executor's LLM chain."""
        try:
            agent = getattr(agent_executor, "agent", None)
            if agent and hasattr(agent, "middle"):
                for step in agent.middle:
                    if hasattr(step, "model"):
                        return step.model
                    if hasattr(step, "model_name"):
                        return step.model_name
            # Fallback: check if the bound LLM has a model attribute
            if agent and hasattr(agent, "last"):
                last = agent.last
                if hasattr(last, "bound") and hasattr(last.bound, "model"):
                    return last.bound.model
        except Exception:
            pass
        return "unknown"

    def _apply_model_override(self, agent_executor, model_override: str) -> None:
        """Override the model on the agent executor's LLM instance."""
        try:
            agent = getattr(agent_executor, "agent", None)
            if agent and hasattr(agent, "middle"):
                for step in agent.middle:
                    if hasattr(step, "model"):
                        step.model = model_override
                        return
            # Try the bound LLM path
            if agent and hasattr(agent, "last"):
                last = agent.last
                if hasattr(last, "bound") and hasattr(last.bound, "model"):
                    last.bound.model = model_override
                    return
            logger.warning(f"Could not apply model override '{model_override}' — LLM not found in chain")
        except Exception as e:
            logger.warning(f"Failed to apply model override: {e}")

    def _build_heartbeat_prompt(
        self, original_prompt: str, checklist: list[str]
    ) -> str:
        """Build a structured heartbeat prompt from the original prompt and checklist items.

        If no checklist is provided, falls back to the original prompt unchanged.
        """
        if not checklist:
            return original_prompt

        items = "\n".join(f"- {item}" for item in checklist)
        return (
            f"{original_prompt}\n\n"
            f"## Heartbeat Checklist\n"
            f"Check each item below using your tools:\n{items}\n\n"
            f"If nothing needs attention, respond with exactly: HEARTBEAT_OK\n"
            f"Otherwise, report only what needs action."
        )

    def _build_execution_metadata(
        self,
        agent_executor,
        model_used: str,
    ) -> Dict[str, Any]:
        """Build metadata dict with model and token usage info (AC-15)."""
        metadata: Dict[str, Any] = {"model": model_used}
        try:
            # LangChain AgentExecutor may have callback-based token tracking
            # Try to extract from the LLM's usage metadata if available
            agent = getattr(agent_executor, "agent", None)
            if agent and hasattr(agent, "middle"):
                for step in agent.middle:
                    usage = getattr(step, "_last_usage_metadata", None)
                    if usage:
                        metadata["input_tokens"] = usage.get("input_tokens", 0)
                        metadata["output_tokens"] = usage.get("output_tokens", 0)
        except Exception as e:
            logger.debug(f"Could not extract token usage: {e}")
        return metadata

    async def _store_result(
        self,
        supabase_client,
        user_id: str,
        schedule_id: Optional[str],
        agent_name: str,
        prompt: str,
        result_content: str,
        status: str,
        pending_actions_created: int,
        duration_ms: int,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Store execution result in agent_execution_results table."""
        try:
            data = {
                "user_id": user_id,
                "agent_name": agent_name,
                "prompt": prompt,
                "result_content": result_content[:50000] if result_content else None,
                "status": status,
                "pending_actions_created": pending_actions_created,
                "execution_duration_ms": duration_ms,
                "metadata": metadata or {},
            }
            if schedule_id:
                data["schedule_id"] = str(schedule_id)

            try:
                await supabase_client.table("agent_execution_results").insert(data).execute()
            except Exception as insert_err:
                # FK violation if schedule was deleted — retry without schedule_id
                if "23503" in str(insert_err) and "schedule_id" in str(insert_err):
                    logger.warning(f"Schedule {schedule_id} not found, storing result without FK")
                    data.pop("schedule_id", None)
                    await supabase_client.table("agent_execution_results").insert(data).execute()
                else:
                    raise
            logger.debug(f"Stored execution result for '{agent_name}' (status: {status})")

        except Exception as e:
            logger.error(f"Failed to store execution result: {e}", exc_info=True)

    async def _notify_user(
        self,
        supabase_client,
        user_id: str,
        agent_name: str,
        result_content: str,
        pending_count: int,
        config: Dict[str, Any],
    ) -> None:
        """Notify the user about the execution result via NotificationService."""
        try:
            from ..services.notification_service import NotificationService

            notification_service = NotificationService(supabase_client)
            channels = config.get("notify_channels")  # e.g., ["telegram", "web"] or None

            # Truncate result for notification body
            body = result_content[:2000] if result_content else "Agent completed with no output."
            if pending_count > 0:
                body += f"\n\n_{pending_count} action{'s' if pending_count != 1 else ''} pending your approval._"

            schedule_type = config.get("schedule_type", "scheduled")
            notification_type = "agent_only" if schedule_type == "heartbeat" else "notify"
            category = "heartbeat" if schedule_type == "heartbeat" else "agent_result"

            await notification_service.notify_user(
                user_id=user_id,
                title=f"{agent_name} run completed",
                body=body,
                category=category,
                metadata={"agent_name": agent_name, "pending_actions": pending_count},
                channels=channels,
                type=notification_type,
            )

            # Also send a separate approval notification if there are pending actions
            if pending_count > 0:
                await notification_service.notify_pending_actions(
                    user_id=user_id,
                    pending_count=pending_count,
                    agent_name=agent_name,
                )

        except Exception as e:
            logger.warning(f"Failed to send notification (non-fatal): {e}")
