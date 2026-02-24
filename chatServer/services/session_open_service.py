"""Session open service — handles proactive agent greeting on app return."""

import logging
from typing import Any, Dict

from langchain_core.messages import AIMessage

from src.core.agent_loader_db import load_agent_executor_db_async

from ..security.tool_wrapper import ApprovalContext, wrap_tools_with_approval
from ..services.audit_service import AuditService
from ..services.pending_actions import PendingActionsService

logger = logging.getLogger(__name__)


class SessionOpenService:
    """Handles session_open requests — agent decides whether to greet the user."""

    def __init__(self, db_client):
        self.db_client = db_client

    async def run(
        self,
        user_id: str,
        agent_name: str,
        session_id: str,
    ) -> Dict[str, Any]:
        supabase_client = self.db_client

        # 1. Check if user is new (no memory + no instructions)
        has_memory = await self._has_memory(supabase_client, user_id, agent_name)
        has_instructions = await self._has_instructions(supabase_client, user_id, agent_name)
        is_new_user = not has_memory and not has_instructions

        # 2. Get last message timestamp for this session (via direct pg, per A3)
        last_message_at = await self._get_last_message_at(session_id)

        # 2b. Deterministic silence: returning user seen < 5 min ago → skip agent entirely
        if not is_new_user and last_message_at is not None:
            from datetime import datetime
            from datetime import timezone as tz

            elapsed = datetime.now(tz.utc) - (
                last_message_at.astimezone(tz.utc)
                if last_message_at.tzinfo
                else last_message_at.replace(tzinfo=tz.utc)
            )
            if elapsed.total_seconds() < 300:  # 5 minutes
                logger.info(
                    "session_open: returning user seen %.0fs ago — silent (deterministic)",
                    elapsed.total_seconds(),
                )
                return {
                    "response": "WAKEUP_SILENT",
                    "is_new_user": False,
                    "silent": True,
                    "session_id": session_id,
                }

        # 3. Load agent with session_open channel
        agent_executor = await load_agent_executor_db_async(
            agent_name=agent_name,
            user_id=user_id,
            session_id=session_id,
            channel="session_open",
            last_message_at=last_message_at,
        )

        # 4. Wrap tools with approval system
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

        # 5. Build trigger prompt
        if is_new_user:
            trigger_prompt = "[SYSTEM: First session. No user message. Begin bootstrap.]"
        else:
            trigger_prompt = "[SYSTEM: User returned to app. No user message. Check tools and decide whether to greet.]"

        # 6. Invoke agent
        response = await agent_executor.ainvoke(
            {"input": trigger_prompt, "chat_history": []}
        )

        # 7. Normalize output (handle content block lists)
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

        # 8. Check for silent response — agent may include reasoning before WAKEUP_SILENT
        silent = "WAKEUP_SILENT" in output

        # 9. Persist AI message if not silent
        if not silent:
            await self._persist_ai_message(session_id, output)

        return {
            "response": output,
            "is_new_user": is_new_user,
            "silent": silent,
            "session_id": session_id,
        }

    async def _has_memory(self, supabase_client, user_id: str, agent_name: str) -> bool:
        """Check if user has any memories in min-memory."""
        try:
            import os

            mem_url = os.getenv("MEMORY_SERVER_URL", "")
            mem_key = os.getenv("MEMORY_SERVER_BACKEND_KEY", "")
            if not mem_url or not mem_key:
                return False
            from chatServer.services.memory_client import MemoryClient
            from src.core.agent_loader_db import _resolve_memory_user_id

            memory_user_id = await _resolve_memory_user_id(user_id)
            client = MemoryClient(base_url=mem_url, backend_key=mem_key, user_id=memory_user_id)
            result = await client.call_tool("search", {"query": "user preferences"})
            if isinstance(result, list) and len(result) > 0:
                return True
            if isinstance(result, dict) and (result.get("results") or result.get("memories")):
                return True
            return False
        except Exception as e:
            logger.warning("Failed to check min-memory for %s/%s: %s", user_id, agent_name, e)
            return False

    async def _has_instructions(self, supabase_client, user_id: str, agent_name: str) -> bool:
        try:
            resp = await supabase_client.table("user_agent_prompt_customizations").select("id").eq(
                "user_id", user_id
            ).eq("agent_name", agent_name).maybe_single().execute()
            return resp.data is not None
        except Exception as e:
            logger.warning(f"Failed to check instructions for {user_id}/{agent_name}: {e}")
            return False

    async def _get_last_message_at(self, session_id: str):
        """Get the timestamp of the most recent message in this session.

        Uses direct pg connection per A3 — chat_message_history is a
        LangChain framework table, not a user-CRUD table.
        """
        from datetime import timezone as tz

        from ..config.constants import CHAT_MESSAGE_HISTORY_TABLE_NAME
        from ..database.connection import get_db_connection

        try:
            async for conn in get_db_connection():
                async with conn.cursor() as cur:
                    await cur.execute(
                        f"SELECT created_at FROM {CHAT_MESSAGE_HISTORY_TABLE_NAME} "  # noqa: E501
                        "WHERE session_id = %s ORDER BY created_at DESC LIMIT 1",
                        (session_id,),
                    )
                    row = await cur.fetchone()
                    if row and row[0]:
                        ts = row[0]
                        if ts.tzinfo is None:
                            ts = ts.replace(tzinfo=tz.utc)
                        return ts
                    return None
        except Exception as e:
            logger.warning(f"Failed to get last message time for session {session_id}: {e}")
            return None

    async def _persist_ai_message(self, session_id: str, content: str) -> None:
        """Persist the AI's opening message to chat history."""
        from langchain_postgres import PostgresChatMessageHistory

        from ..config.constants import CHAT_MESSAGE_HISTORY_TABLE_NAME
        from ..database.connection import get_db_connection

        try:
            async for conn in get_db_connection():
                history = PostgresChatMessageHistory(
                    CHAT_MESSAGE_HISTORY_TABLE_NAME,
                    session_id,
                    async_connection=conn,
                )
                await history.aadd_messages([AIMessage(content=content)])
                break
        except Exception as e:
            logger.warning(f"Failed to persist session_open AI message: {e}")
