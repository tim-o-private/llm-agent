"""Session open service — handles proactive agent greeting on app return."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict

from .bootstrap_context_service import BootstrapContextService

logger = logging.getLogger(__name__)

# Per-session lock to prevent concurrent session_open processing.
# React double-mount / rapid re-init can fire multiple calls before
# the first one persists its greeting, causing duplicate messages.
_session_locks: Dict[str, asyncio.Lock] = {}


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
        # Serialize concurrent session_open calls for the same session.
        # Without this, React double-mount fires two calls simultaneously,
        # both see no messages, and both invoke the agent → duplicate greetings.
        if session_id not in _session_locks:
            _session_locks[session_id] = asyncio.Lock()
        async with _session_locks[session_id]:
            return await self._run_locked(user_id, agent_name, session_id)

    async def _run_locked(
        self,
        user_id: str,
        agent_name: str,
        session_id: str,
    ) -> Dict[str, Any]:
        supabase_client = self.db_client

        # 1. Get last message timestamp FIRST — chat history is the strongest
        # signal for whether this user is new or returning.
        last_message_at = await self._get_last_message_at(session_id)

        # 2. Check if user is new.  Chat history overrides memory/instructions
        # checks, which are fragile (memory MCP may be down, user may not have
        # saved instructions yet but has been chatting for weeks).
        if last_message_at is not None:
            is_new_user = False
        else:
            has_memory = await self._has_memory(supabase_client, user_id, agent_name)
            has_instructions = await self._has_instructions(supabase_client, user_id, agent_name)
            is_new_user = not has_memory and not has_instructions

        # 2b. Dedup: if ANY message exists within 30s, always go silent.
        # Prevents duplicate greetings from React double-mount or rapid re-init.
        if last_message_at is not None:
            from datetime import datetime
            from datetime import timezone as tz

            elapsed = datetime.now(tz.utc) - (
                last_message_at.astimezone(tz.utc)
                if last_message_at.tzinfo
                else last_message_at.replace(tzinfo=tz.utc)
            )
            if elapsed.total_seconds() < 30:
                logger.info(
                    "session_open: recent message %.0fs ago — silent (dedup)",
                    elapsed.total_seconds(),
                )
                return {
                    "response": "WAKEUP_SILENT",
                    "is_new_user": is_new_user,
                    "silent": True,
                    "session_id": session_id,
                }

        # 2c. Deterministic silence: returning user seen < 5 min ago → skip agent entirely.
        # Exception: skip silence if user is in orientation phase (needs bootstrapping
        # even if they have old chat history).
        if not is_new_user and last_message_at is not None:
            from datetime import datetime
            from datetime import timezone as tz

            elapsed = datetime.now(tz.utc) - (
                last_message_at.astimezone(tz.utc)
                if last_message_at.tzinfo
                else last_message_at.replace(tzinfo=tz.utc)
            )
            if elapsed.total_seconds() < 300:  # 5 minutes
                # Check if user still needs bootstrapping before going silent
                in_orientation = self._is_orientation_phase(user_id)
                if not in_orientation:
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
                logger.info(
                    "session_open: returning user seen %.0fs ago but in orientation — proceeding",
                    elapsed.total_seconds(),
                )

        # 3. Pre-compute context for returning users (non-LLM, direct DB)
        bootstrap_context = None
        if not is_new_user:
            ctx_service = BootstrapContextService(supabase_client)
            ctx = await ctx_service.gather(user_id)
            bootstrap_context = ctx.render()

        # 4. Build trigger prompt
        if is_new_user:
            trigger_prompt = "[SYSTEM: First session. No user message. Begin bootstrap.]"
        else:
            trigger_prompt = "[SYSTEM: User returned to app. No user message. Check tools and decide whether to greet.]"  # noqa: E501

        try:
            output = await self._invoke_agent(
                user_id, agent_name, session_id, trigger_prompt,
                bootstrap_context=bootstrap_context,
                last_message_at=last_message_at,
            )
        except Exception as e:
            error_name = type(e).__name__
            logger.error(
                "session_open: agent invocation failed for user=%s: %s: %s",
                user_id, error_name, e,
            )
            return {
                "response": "",
                "is_new_user": is_new_user,
                "silent": True,
                "session_id": session_id,
            }

        # Handle empty output — agent may have burned all iterations on tool calls
        if not output or output.strip() == "" or output == "No text content in response.":
            logger.error(
                "session_open: agent returned empty output for user=%s session=%s",
                user_id, session_id,
            )
            return {
                "response": "",
                "is_new_user": is_new_user,
                "silent": True,
                "session_id": session_id,
            }

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

    async def _invoke_agent(
        self,
        user_id: str,
        agent_name: str,
        session_id: str,
        trigger_prompt: str,
        *,
        bootstrap_context: str | None = None,
        last_message_at: datetime | None = None,
    ) -> str:
        """Invoke the Deep Agent runtime for session_open."""
        from ..services.deep_agent_builder import build_deep_agent, extract_agent_response

        agent = await build_deep_agent(
            user_id=user_id,
            agent_name=agent_name,
            session_id=session_id,
            channel="session_open",
            bootstrap_context=bootstrap_context,
            last_message_at=last_message_at,
        )

        # AC-32: empty history for session_open
        messages = [{"role": "user", "content": trigger_prompt}]
        config = {"configurable": {"thread_id": session_id}}
        result = await agent.ainvoke({"messages": messages}, config=config)
        return extract_agent_response(result)

    async def _persist_ai_message(self, session_id: str, content: str) -> None:
        """Persist AI opening message."""
        from ..database.connection import get_database_manager
        from ..services.message_history_adapter import MessageHistoryAdapter

        try:
            db_manager = get_database_manager()
            await db_manager.ensure_initialized()
            async with db_manager.pool.connection() as pg_conn:
                await MessageHistoryAdapter.save_messages(
                    session_id=session_id,
                    messages=[{"role": "assistant", "content": content}],
                    pg_connection=pg_conn,
                )
        except Exception as e:
            logger.warning(f"Failed to persist session_open AI message: {e}")

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
            return resp is not None and resp.data is not None
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

    def _is_orientation_phase(self, user_id: str) -> bool:
        """Check if user is in orientation phase (AGENTS.md empty or freshly seeded)."""
        import os
        from pathlib import Path

        from .deep_agent_builder import _detect_agent_phase

        data_dir = Path(os.getenv("SANDBOX_DATA_DIR", "/data"))
        agents_md_path = data_dir / "sandboxes" / user_id / "memory" / "AGENTS.md"
        if not agents_md_path.exists():
            return True
        content = agents_md_path.read_text(encoding="utf-8")
        return _detect_agent_phase(content) == "orientation"

