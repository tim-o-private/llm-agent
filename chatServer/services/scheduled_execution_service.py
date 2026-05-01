"""
Generalized scheduled agent execution service.

Loads any agent from the database, wraps tools with the approval system,
invokes the agent, and stores the result. Replaces the special-cased
execution logic in BackgroundTaskService._execute_scheduled_agent.

Pattern mirrors chatServer/services/chat.py:225-258 for approval wrapping.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from chatServer.config.settings import get_settings

from ..database.supabase_client import create_user_scoped_client
from ..services.audit_service import AuditService
from ..services.pending_actions import PendingActionsService

logger = logging.getLogger(__name__)

DEFAULT_SCHEDULED_MODEL = get_settings().llm_default_model


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

        start_time = datetime.now(timezone.utc)
        model_override = config.get("model_override")

        try:
            schedule_type = config.get("schedule_type", "scheduled")
            channel = "heartbeat" if schedule_type == "heartbeat" else "scheduled"

            supabase_client = await create_user_scoped_client(user_id)

            # Use the user's main chat thread so output appears in web + Telegram
            session_id = await self._resolve_main_thread(supabase_client, user_id, agent_name)

            logger.info(
                f"Executing scheduled agent '{agent_name}' for user {user_id} "
                f"(schedule {schedule_id}, channel={channel}, thread={session_id})"
            )

            # Build effective prompt (heartbeat gets a structured checklist)
            if schedule_type == "heartbeat":
                effective_prompt = self._build_heartbeat_prompt(
                    prompt, config.get("heartbeat_checklist", [])
                )
            else:
                effective_prompt = prompt

            if model_override:
                logger.warning(f"Model override '{model_override}' requested but not supported by Deep Agent runtime")  # noqa: E501

            output, model_used = await self._execute_agent(
                user_id=user_id,
                agent_name=agent_name,
                session_id=session_id,
                channel=channel,
                prompt=effective_prompt,
                )
            pending_actions_service = PendingActionsService(
                db_client=supabase_client,
                audit_service=AuditService(supabase_client),
            )

            # 7. Detect HEARTBEAT_OK suppression
            is_heartbeat_ok = (
                schedule_type == "heartbeat" and output.strip().startswith("HEARTBEAT_OK")
            )

            # 7b. Defer non-OK heartbeat findings when briefings are enabled
            if schedule_type == "heartbeat" and not is_heartbeat_ok:
                try:
                    from chatServer.services.briefing_service import BriefingService

                    briefing_svc = BriefingService(supabase_client)
                    prefs = await briefing_svc.get_user_preferences(user_id)

                    if prefs.get("morning_briefing_enabled"):
                        # Defer to next briefing instead of notifying immediately
                        await supabase_client.table("deferred_observations").insert({
                            "user_id": user_id,
                            "content": output,
                            "source": "heartbeat",
                        }).execute()
                        logger.info(f"Deferred heartbeat finding for {user_id} to next briefing")
                        # Touch session updated_at for recency tracking
                        await supabase_client.table("chat_sessions").update(
                            {"updated_at": datetime.now(timezone.utc).isoformat()}
                        ).eq("session_id", session_id).execute()

                        # Still store the execution result for audit
                        duration_ms = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)  # noqa: E501
                        pending_count = await pending_actions_service.get_pending_count(user_id)
                        await self._store_result(
                            supabase_client=supabase_client,
                            user_id=user_id,
                            schedule_id=schedule_id,
                            agent_name=agent_name,
                            prompt=prompt,
                            result_content=output,
                            status="deferred",
                            pending_actions_created=pending_count,
                            duration_ms=duration_ms,
                        )

                        return {
                            "success": True,
                            "output": output,
                            "deferred": True,
                            "pending_actions_created": pending_count,
                            "duration_ms": duration_ms,
                        }
                except Exception as e:
                    logger.warning(f"Failed to check briefing deferral, delivering immediately: {e}")
                # Fall through to normal notification if briefings disabled or check failed

            # 8. Count pending actions created during this run
            pending_count = await pending_actions_service.get_pending_count(user_id)

            # 9. Build execution metadata with token usage (AC-15)
            duration_ms = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)
            execution_metadata: Dict[str, Any] = {"model": model_used}

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

            # 11. Persist output to main thread + notify via Telegram
            skip_notification = config.get("skip_notification", False)
            if is_heartbeat_ok:
                logger.info(
                    f"Heartbeat OK for '{agent_name}' — suppressing notification"
                )
            else:
                # Persist as chat message so it appears in web UI
                await self._persist_to_thread(session_id, output)

                if not skip_notification:
                    await self._notify_user(
                        supabase_client=supabase_client,
                        user_id=user_id,
                        agent_name=agent_name,
                        result_content=output,
                        pending_count=pending_count,
                        config=config,
                    )

            # Touch session updated_at (don't deactivate — it's the main thread)
            await supabase_client.table("chat_sessions").update(
                {"updated_at": datetime.now(timezone.utc).isoformat()}
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

    async def _execute_agent(
        self,
        user_id: str,
        agent_name: str,
        session_id: str,
        channel: str,
        prompt: str,
    ) -> tuple[str, str]:
        """Invoke the Deep Agent runtime for scheduled runs.

        Returns (response_text, model_name).
        """
        from ..services.deep_agent_builder import (  # noqa: E501
            build_deep_agent,
            extract_agent_response,
            sync_user_files_after_invocation,
        )

        agent = await build_deep_agent(
            user_id=user_id,
            agent_name=agent_name,
            session_id=session_id,
            channel=channel,
        )

        messages = [{"role": "user", "content": prompt}]
        config = {"configurable": {"thread_id": session_id}}
        result = await agent.ainvoke({"messages": messages}, config=config)

        # Fire-and-forget sync of user changes to durable storage
        asyncio.create_task(sync_user_files_after_invocation(user_id))

        return extract_agent_response(result), "default"


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

        except Exception as e:
            logger.warning(f"Failed to send notification (non-fatal): {e}")

    async def _resolve_main_thread(
        self, supabase_client, user_id: str, agent_name: str
    ) -> str:
        """Find or create the user's main chat thread.

        Looks for the most recent chat_sessions row with a chat_id.
        If none exists, creates one. Returns the chat_id (used as
        session_id / thread_id for the agent).
        """
        import uuid

        result = (
            await supabase_client.table("chat_sessions")
            .select("chat_id")
            .eq("user_id", user_id)
            .not_.is_("chat_id", "null")
            .order("updated_at", desc=True)
            .limit(1)
            .execute()
        )

        if result.data and result.data[0].get("chat_id"):
            chat_id = str(result.data[0]["chat_id"])
            logger.info(f"Scheduled run using main thread {chat_id} for user {user_id}")
            return chat_id

        chat_id = str(uuid.uuid4())
        await supabase_client.table("chat_sessions").insert(
            {
                "user_id": user_id,
                "chat_id": chat_id,
                "session_id": chat_id,
                "channel": "scheduled",
                "agent_name": agent_name,
                "is_active": True,
            }
        ).execute()
        logger.info(f"Created main thread {chat_id} for user {user_id}")
        return chat_id

    async def _persist_to_thread(self, session_id: str, content: str) -> None:
        """Persist agent output as a chat message in the main thread."""
        try:
            from ..database.connection import get_database_manager
            from ..services.message_history_adapter import MessageHistoryAdapter

            db_manager = get_database_manager()
            await db_manager.ensure_initialized()
            async with db_manager.pool.connection() as pg_conn:
                await MessageHistoryAdapter.save_messages(
                    session_id=session_id,
                    messages=[{"role": "assistant", "content": content}],
                    pg_connection=pg_conn,
                )
        except Exception as e:
            logger.warning(f"Failed to persist scheduled output to thread (non-fatal): {e}")
