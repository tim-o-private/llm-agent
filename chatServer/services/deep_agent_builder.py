"""Builder for DeepAgentWrapper instances.

Mirrors conversation_handler_builder.py but produces a DeepAgentWrapper
(the Deep Agents interface shim) instead of a ConversationHandler.

Architecture
------------
Until the langchain 1.x migration unlocks the real deepagents package,
DeepAgentWrapper bridges the Deep Agent interface over ConversationHandler:

    caller → DeepAgentWrapper.ainvoke/astream
           → loads skills from ClarityBackend (Supabase Storage)
           → builds full system prompt (channel prompt + skill content)
           → delegates to ConversationHandler

When deepagents becomes installable, DeepAgentWrapper.ainvoke/astream is
replaced by a real create_deep_agent() call. The builder's external API
(build_deep_agent signature, return type interface) stays unchanged.
"""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, AsyncIterator, Dict, Tuple

from cachetools import TTLCache

if TYPE_CHECKING:
    from .conversation_handler import ConversationHandler

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Agent cache  (same pattern as conversation_handler_builder.py)
# ---------------------------------------------------------------------------

_agent_cache: TTLCache[Tuple[str, str], "DeepAgentWrapper"] = TTLCache(
    maxsize=100, ttl=900  # 15-min TTL
)
_agent_locks: Dict[Tuple[str, str], asyncio.Lock] = {}

# ---------------------------------------------------------------------------
# Channel-only system prompt  (AC-05: runtime sections only — soul/identity
# are skills loaded from ClarityBackend at invoke time)
# ---------------------------------------------------------------------------

_CHANNEL_PROMPT_INTRO = (
    "You are operating via the Clarity platform. "
    "Your behavioral guidelines, personality, and domain expertise are loaded "
    "from your skill library — see the skill sections prepended above.\n\n"
)

_CHANNEL_HEADERS = {
    "web": "User is on the web app. Markdown formatting is supported.",
    "telegram": (
        "User is on Telegram. Keep responses concise — under 4096 characters. "
        "Use simple markdown (bold, italic, code). No tables or complex formatting."
    ),
    "scheduled": (
        "This is an automated scheduled run. No one is waiting for a response.\n"
        "- Do the work described thoroughly.\n"
        "- Use all available tools to gather information before composing your response.\n"
        "- Don't ask follow-up questions — make reasonable assumptions.\n"
        "- Your response will be delivered as a notification, so make it self-contained."
    ),
    "heartbeat": (
        "This is an automated heartbeat check. No one is waiting.\n"
        "Check each area using your tools, then decide if anything needs the user's attention.\n"
        "- If everything is fine, respond with exactly: HEARTBEAT_OK\n"
        "- If something needs attention, report ONLY what needs action — no filler.\n"
        "- Never fabricate. If a tool fails, skip that check and note it."
    ),
    "session_open": (
        "The user just returned to the app. You are deciding whether to initiate — "
        "no user message has been sent yet."
    ),
}


def _build_channel_prompt(
    channel: str,
    memory_notes: str | None = None,
    user_instructions: str | None = None,
    last_message_at: datetime | None = None,
    bootstrap_context: str | None = None,
) -> str:
    """Assemble the runtime-only system prompt sections.

    Deliberately excludes soul, identity, operating model, interaction learning,
    and channel guidance — those are loaded as skills from ClarityBackend.

    This function handles ONLY:
    - A brief framing line
    - Channel-specific runtime mode
    - Current time
    - Memory notes (user-specific, not skill-level)
    - User custom instructions
    - Session/onboarding flow
    """
    sections: list[str] = []

    # Channel mode
    channel_text = _CHANNEL_HEADERS.get(channel, _CHANNEL_HEADERS["web"])
    sections.append(f"## Channel\n{channel_text}")

    # Current time
    now = datetime.now(timezone.utc)
    time_str = now.strftime("%A, %B %d, %Y %I:%M %p (UTC)")
    sections.append(f"## Current Time\n{time_str}")

    # Memory notes
    if memory_notes:
        sections.append(f"## What You Know\n{memory_notes[:4000]}")

    # User instructions
    if user_instructions:
        instr = user_instructions[:2000]
        sections.append(f"## User Instructions\n{instr}")

    # Session/onboarding sections (only for interactive channels)
    if channel == "session_open":
        _add_session_open_section(
            sections, memory_notes, user_instructions, last_message_at, bootstrap_context
        )
    elif channel in ("web", "telegram") and not memory_notes and not user_instructions:
        sections.append(
            "## Onboarding\n"
            "This appears to be your first interaction. Introduce yourself briefly, "
            "then ask one concrete open-ended question to start learning about this person. "
            "Do NOT call get_tasks, get_reminders, or search_gmail — there's nothing yet."
        )

    return "\n\n".join(sections)


def _add_session_open_section(
    sections: list[str],
    memory_notes: str | None,
    user_instructions: str | None,
    last_message_at: datetime | None,
    bootstrap_context: str | None,
) -> None:
    """Append the session_open decision block to sections."""
    is_new_user = not memory_notes and not user_instructions and last_message_at is None
    if is_new_user:
        sections.append(
            "## Session Open\n"
            "This is the first time meeting this user. No message typed yet — you are initiating.\n\n"
            "1. Introduce yourself in one sentence.\n"
            "2. Ask one concrete open-ended question to start learning about them.\n"
            "3. Do NOT call get_tasks, get_reminders, or search_gmail — nothing to find yet."
        )
        return

    # Returning user — format time context
    if last_message_at:
        elapsed = datetime.now(timezone.utc) - last_message_at.replace(
            tzinfo=timezone.utc
        ) if not last_message_at.tzinfo else datetime.now(timezone.utc) - last_message_at
        minutes = int(elapsed.total_seconds() / 60)
        if minutes < 2:
            time_ctx = "Your last interaction was less than 2 minutes ago."
        elif minutes < 60:
            time_ctx = f"Your last interaction was {minutes} minutes ago."
        else:
            hours = minutes // 60
            time_ctx = f"Your last interaction was {hours} hour{'s' if hours > 1 else ''} ago."
    else:
        time_ctx = "This is the first time opening this session."

    ctx = bootstrap_context or "(no bootstrap context)"
    sections.append(
        f"## Session Open\n{time_ctx}\n"
        "No message typed yet — decide whether to initiate.\n\n"
        f"Context from your tools (pre-fetched):\n{ctx}\n\n"
        "Decision rules:\n"
        "- If nothing needs attention and <30 min since last message: respond WAKEUP_SILENT\n"
        "- Otherwise: greet with a brief (2-4 sentence) summary of what needs attention.\n"
        "Don't re-call tools to fetch what's already in the context above."
    )


# ---------------------------------------------------------------------------
# DeepAgentWrapper  (TEMPORARY SHIM — see module docstring)
# ---------------------------------------------------------------------------


class DeepAgentWrapper:
    """Temporary shim implementing the Deep Agent interface over ConversationHandler.

    TODO: Replace with real create_deep_agent() call once langchain 1.x migration
    is complete and deepagents>=0.5.0 can be installed without breaking AgentExecutor.

    External interface (stable):
        await agent.ainvoke({"messages": [...]}) → {"messages": [...]}
        async for event in agent.astream({"messages": [...]}, stream_mode=..., version="v2"):
            ...

    The wrapper:
    1. Loads skill content from ClarityBackend at each invocation.
    2. Builds the full system prompt = skills content + channel prompt.
    3. Delegates the actual LLM call to ConversationHandler.
    """

    def __init__(
        self,
        handler: "ConversationHandler",
        channel_prompt: str,
        backend: Any | None = None,
    ) -> None:
        self._handler = handler
        self._channel_prompt = channel_prompt
        self._backend = backend

    async def _build_full_prompt(self) -> str:
        """Load skill SKILL.md files and prepend them to the channel prompt."""
        if self._backend is None:
            return self._channel_prompt

        skill_sections: list[str] = []
        try:
            glob_result = self._backend.glob("SKILL.md", "/skills/")
            skill_paths = (
                [e["path"] for e in glob_result.matches]
                if glob_result.matches
                else []
            )
            for path in sorted(skill_paths):
                read_result = self._backend.read(path)
                if read_result.error or not read_result.file_data:
                    continue
                raw = read_result.file_data.get("content", "")
                if raw:
                    # Strip YAML frontmatter before inserting as a prompt section
                    content = _strip_frontmatter(raw).strip()
                    if content:
                        skill_sections.append(content)
        except Exception as exc:
            logger.warning("Failed to load skills from backend: %s", exc)

        if skill_sections:
            skills_block = "\n\n---\n\n".join(skill_sections)
            return f"{skills_block}\n\n---\n\n{self._channel_prompt}"
        return self._channel_prompt

    async def ainvoke(
        self,
        input: dict[str, Any],
        config: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Run the agent non-streaming. Returns {"messages": [...]}."""
        messages = input.get("messages", [])
        # Normalise to Anthropic format  (Deep Agents uses role/content dicts)
        anthropic_messages = [_normalise_message(m) for m in messages]

        full_prompt = await self._build_full_prompt()
        self._handler.system_prompt = full_prompt

        result = await self._handler.run(anthropic_messages)
        return {
            "messages": anthropic_messages
            + [{"role": "assistant", "content": result.response_text}]
        }

    async def astream(
        self,
        input: dict[str, Any],
        stream_mode: list[str] | str | None = None,
        config: dict[str, Any] | None = None,
        version: str = "v2",
        subgraphs: bool = False,
    ) -> AsyncIterator[dict[str, Any]]:
        """Run the agent with streaming. Yields event dicts."""
        messages = input.get("messages", [])
        anthropic_messages = [_normalise_message(m) for m in messages]

        full_prompt = await self._build_full_prompt()
        self._handler.system_prompt = full_prompt

        async for event in self._handler.run_stream(anthropic_messages):
            # Translate StreamEvent to a dict consumers expect
            yield {"type": event.type, "event": event}


def _normalise_message(msg: dict[str, Any]) -> dict[str, Any]:
    """Ensure message has the minimal role/content structure."""
    if isinstance(msg, dict) and "role" in msg:
        return msg
    return {"role": "user", "content": str(msg)}


def _strip_frontmatter(content: str) -> str:
    """Remove YAML frontmatter (---...---) from a SKILL.md string."""
    stripped = content.strip()
    if not stripped.startswith("---"):
        return content
    end = stripped.find("---", 3)
    if end == -1:
        return content
    return stripped[end + 3 :].lstrip("\n")


# ---------------------------------------------------------------------------
# Public builder
# ---------------------------------------------------------------------------


async def build_deep_agent(
    user_id: str,
    agent_name: str,
    session_id: str,
    channel: str = "web",
) -> DeepAgentWrapper:
    """Build or retrieve a cached DeepAgentWrapper.

    Mirrors build_conversation_handler() but returns a DeepAgentWrapper
    instead of a ConversationHandler.  Cached per (user_id, agent_name)
    with 15-min TTL.
    """
    cache_key = (user_id, agent_name)

    if cache_key in _agent_cache:
        logger.debug("DeepAgentWrapper cache HIT: %s", cache_key)
        return _agent_cache[cache_key]

    lock = _agent_locks.setdefault(cache_key, asyncio.Lock())
    async with lock:
        if cache_key in _agent_cache:
            return _agent_cache[cache_key]

        logger.info("Building DeepAgentWrapper for %s", cache_key)
        agent = await _build_agent(user_id, agent_name, session_id, channel)
        _agent_cache[cache_key] = agent
        return agent


async def _build_agent(
    user_id: str,
    agent_name: str,
    session_id: str,
    channel: str,
) -> DeepAgentWrapper:
    """Load everything from DB and construct a DeepAgentWrapper."""
    # Lazy imports — same pattern as conversation_handler_builder.py
    from chatServer.services.agent_config_cache_service import get_cached_agent_config
    from chatServer.services.conversation_handler import ConversationHandler
    from chatServer.services.conversation_handler_builder import _get_anthropic_client
    from chatServer.services.tool_cache_service import get_cached_tools_for_agent
    from chatServer.services.user_instructions_cache_service import get_cached_user_instructions
    from src.core.agent_loader_db import (
        _fetch_agent_config_from_db_async,
        _prefetch_memory_notes,
        _resolve_memory_user_id,
        load_tools_from_db,
    )

    effective_supabase_url = os.getenv("SUPABASE_URL")
    effective_supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

    # Memory client
    memory_client = None
    mem_url = os.getenv("MEMORY_SERVER_URL", "")
    mem_key = os.getenv("MEMORY_SERVER_BACKEND_KEY", "")
    if mem_url and mem_key:
        from chatServer.services.memory_client import MemoryClient

        memory_user_id = await _resolve_memory_user_id(user_id)
        memory_client = MemoryClient(
            base_url=mem_url, backend_key=mem_key, user_id=memory_user_id
        )

    # 1. Agent config
    agent_db_config = await get_cached_agent_config(agent_name)
    if not agent_db_config:
        agent_db_config = await _fetch_agent_config_from_db_async(agent_name)
    if not agent_db_config:
        raise ValueError(f"Agent '{agent_name}' not found in DB")

    agent_id = agent_db_config.get("id")
    if not agent_id:
        raise ValueError(f"Agent '{agent_name}' has no ID")

    # 2. Parallel fetch: tools + instructions + memory  (mirrors builder lines 138-142)
    cached_tools_data, user_instructions, memory_notes = await asyncio.gather(
        get_cached_tools_for_agent(str(agent_id)),
        get_cached_user_instructions(user_id, agent_name),
        _prefetch_memory_notes(memory_client),
    )

    tools_data = [
        {
            "name": tc["name"],
            "type": tc.get("type", "CRUDTool"),
            "description": tc.get("description", ""),
            "config": tc.get("config", {}),
            "is_active": tc.get("is_active", True),
        }
        for tc in cached_tools_data
    ]

    # 3. Instantiate tools (no LangChainToolBridge — Deep Agents takes BaseTool directly)
    instantiated_tools = load_tools_from_db(
        tools_data=tools_data,
        user_id=user_id,
        agent_name=agent_db_config["agent_name"],
        supabase_url=effective_supabase_url,
        supabase_key=effective_supabase_key,
        memory_client=memory_client,
    )

    # 4. Wrap tools with approval (same as existing builder — non-fatal on failure)
    tool_schemas: list[dict] = []
    tool_executors: dict = {}
    try:
        from chatServer.database.supabase_client import create_user_scoped_client
        from chatServer.security.tool_wrapper import ApprovalContext, wrap_tools_with_approval
        from chatServer.services.audit_service import AuditService
        from chatServer.services.notification_service import NotificationService
        from chatServer.services.pending_actions import PendingActionsService

        supabase_client = await create_user_scoped_client(user_id)
        audit_service = AuditService(supabase_client)
        pending_actions_service = PendingActionsService(
            db_client=supabase_client,
            audit_service=audit_service,
        )
        notification_service = NotificationService(supabase_client)
        approval_context = ApprovalContext(
            user_id=user_id,
            session_id=session_id,
            agent_name=agent_name,
            db_client=supabase_client,
            pending_actions_service=pending_actions_service,
            audit_service=audit_service,
            notification_service=notification_service,
        )
        wrap_tools_with_approval(instantiated_tools, approval_context)
    except Exception as exc:
        logger.warning("Failed to wrap tools with approval (non-fatal): %s", exc)

    # Convert to ConversationHandler format via bridge
    from chatServer.services.langchain_tool_bridge import LangChainToolBridge
    tool_schemas, tool_executors = LangChainToolBridge.convert_tools(instantiated_tools)

    # 5. Create ClarityBackend  (AC-22: fall back gracefully on ConfigService failure)
    backend = None
    try:
        from chatServer.sandbox.security_boundary import SecurityBoundary
        from chatServer.services.config_service import get_config_service
        from chatServer.services.deep_agent_backend import ClarityBackend

        backend = ClarityBackend(
            config_service=get_config_service(),
            user_id=user_id,
            security_boundary=SecurityBoundary(),
        )
    except Exception as exc:
        logger.warning(
            "ClarityBackend unavailable (ConfigService not initialized?): %s — "
            "skills will not be loaded from storage",
            exc,
        )

    # 6. Build channel-specific system prompt (runtime sections only — soul/identity
    #    come from skills loaded via the backend at invoke time)
    channel_prompt = _build_channel_prompt(
        channel=channel,
        memory_notes=memory_notes,
        user_instructions=user_instructions,
    )

    # 7. Create ConversationHandler (the actual LLM engine)
    llm_config = agent_db_config.get("llm_config") or {}
    model = llm_config.get("model", "claude-sonnet-4-20250514")
    client = _get_anthropic_client()

    handler = ConversationHandler(
        client=client,
        model=model,
        system_prompt=channel_prompt,  # overwritten at ainvoke time with full prompt
        tools=tool_schemas,
        tool_executors=tool_executors,
        max_tokens=llm_config.get("max_tokens", 4096),
        temperature=llm_config.get("temperature", 0.7),
        session_id=session_id,
        user_id=user_id,
    )

    # Wire dispatch_workflow executor (same as existing builder)
    try:
        from chatServer.workflows.dispatch import dispatch_workflow as _real_dispatch_workflow

        async def _dispatch_executor(args: dict) -> str:
            return await _real_dispatch_workflow(
                args=args,
                user_id=user_id,
                db_client=supabase_client,
                anthropic_client=client,
                tool_schemas=tool_schemas,
                tool_executors=tool_executors,
            )

        handler.tool_executors["dispatch_workflow"] = _dispatch_executor
    except Exception as exc:
        logger.debug("dispatch_workflow executor not wired: %s", exc)

    logger.info(
        "Built DeepAgentWrapper for '%s' (model=%s, %d tools, backend=%s)",
        agent_name,
        model,
        len(tool_schemas),
        "ClarityBackend" if backend else "None (fallback)",
    )

    return DeepAgentWrapper(
        handler=handler,
        channel_prompt=channel_prompt,
        backend=backend,
    )
