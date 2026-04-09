"""Builder for Deep Agent (CompiledStateGraph) instances.

Builds a real create_deep_agent() graph backed by BwrapBackend.

Architecture
------------
    caller → build_deep_agent(user_id, agent_name, session_id, channel)
           → loads config, tools, approval wrapping, backend, channel prompt
           → create_deep_agent(model, tools, system_prompt, backend, skills)
           → returns CompiledStateGraph (LangGraph)

Callers use .ainvoke() / .astream() directly on the CompiledStateGraph.
"""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, Tuple

from cachetools import TTLCache

logger = logging.getLogger(__name__)


def extract_agent_response(result: dict) -> str:
    """Extract response text from a Deep Agent ainvoke() result.

    Handles both LangChain message objects (.content attr) and plain dicts.
    """
    messages = result.get("messages")
    if not messages:
        return ""
    last_msg = messages[-1]
    if hasattr(last_msg, "content"):
        return last_msg.content
    if isinstance(last_msg, dict):
        return last_msg.get("content", "")
    return ""

# ---------------------------------------------------------------------------
# Agent cache  (keyed on user_id + agent_name)
# ---------------------------------------------------------------------------

_agent_cache: TTLCache[Tuple[str, str], Any] = TTLCache(
    maxsize=100, ttl=900  # 15-min TTL
)
_agent_locks: Dict[Tuple[str, str], asyncio.Lock] = {}

# ---------------------------------------------------------------------------
# Channel-only system prompt  (AC-05: runtime sections only — soul/identity
# are skills loaded from BwrapBackend at invoke time)
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
    and channel guidance — those are loaded as skills from BwrapBackend.

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
# Backend construction
# ---------------------------------------------------------------------------


def _create_backend(system_dir, user_dir):
    """Create the best available sandbox backend.

    Tries BwrapBackend first (OS-level isolation). If bwrap isn't available
    (e.g., macOS, restricted Linux), falls back to CompositeBackend with
    FilesystemBackend (no isolation, but agent can still read/write skills).
    """
    import shutil

    if shutil.which("bwrap"):
        try:
            import subprocess

            # Quick smoke test — bwrap may exist but fail due to AppArmor/seccomp
            result = subprocess.run(  # noqa: S603, S607
                ["bwrap", "--unshare-all", "--die-with-parent",
                 "--ro-bind", "/usr", "/usr", "--", "true"],
                capture_output=True, timeout=5,
            )
            if result.returncode == 0:
                from chatServer.sandbox.bwrap_backend import BwrapBackend

                logger.info("Using BwrapBackend (OS-level sandbox)")
                return BwrapBackend(user_dir=user_dir, system_dir=system_dir)
        except Exception as exc:
            logger.warning("bwrap smoke test failed: %s", exc)

    # Fallback: CompositeBackend with FilesystemBackend for path routing.
    # Same /system/ and /user/ paths as bwrap — just no OS-level isolation.
    from deepagents.backends import CompositeBackend, FilesystemBackend

    logger.info(
        "bwrap unavailable — using FilesystemBackend (no sandbox isolation)"
    )
    return CompositeBackend(
        default=FilesystemBackend(root_dir=str(user_dir), virtual_mode=True),
        routes={
            "/system": FilesystemBackend(root_dir=str(system_dir), virtual_mode=True),
            "/user": FilesystemBackend(root_dir=str(user_dir), virtual_mode=True),
        },
    )


# ---------------------------------------------------------------------------
# Public builder
# ---------------------------------------------------------------------------


async def build_deep_agent(
    user_id: str,
    agent_name: str,
    session_id: str,
    channel: str = "web",
) -> Any:
    """Build or retrieve a cached CompiledStateGraph.

    Returns a LangGraph CompiledStateGraph created by create_deep_agent().
    Cached per (user_id, agent_name) with 15-min TTL.
    """
    cache_key = (user_id, agent_name)

    if cache_key in _agent_cache:
        logger.debug("Deep agent cache HIT: %s", cache_key)
        return _agent_cache[cache_key]

    lock = _agent_locks.setdefault(cache_key, asyncio.Lock())
    async with lock:
        if cache_key in _agent_cache:
            return _agent_cache[cache_key]

        logger.info("Building deep agent for %s", cache_key)
        agent = await _build_agent(user_id, agent_name, session_id, channel)
        _agent_cache[cache_key] = agent
        return agent


async def _build_agent(
    user_id: str,
    agent_name: str,
    session_id: str,
    channel: str,
) -> Any:
    """Load everything from DB and construct a CompiledStateGraph via create_deep_agent()."""
    from deepagents import create_deep_agent

    # Lazy imports to avoid circular dependencies
    from chatServer.services.agent_config_cache_service import get_cached_agent_config
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

    # 3. Instantiate tools (Deep Agents takes BaseTool directly — no bridge needed)
    instantiated_tools = load_tools_from_db(
        tools_data=tools_data,
        user_id=user_id,
        agent_name=agent_db_config["agent_name"],
        supabase_url=effective_supabase_url,
        supabase_key=effective_supabase_key,
        memory_client=memory_client,
    )

    # 4. Wrap tools with approval (same as existing builder — non-fatal on failure)
    supabase_client = None
    notification_service = None
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

    # 5. Create sandbox backend (AC-22)
    from pathlib import Path

    from chatServer.services.storage_sync import StorageSync

    data_dir = Path(os.getenv("SANDBOX_DATA_DIR", "/data"))
    system_dir = data_dir / "config" / "system"
    user_dir = data_dir / "sandboxes" / user_id

    # Ensure user dir exists
    user_dir.mkdir(parents=True, exist_ok=True)

    # Hydrate user dir from Storage if needed (AC-23)
    supabase_url = os.getenv("SUPABASE_URL", "")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    if supabase_url and supabase_key:
        sync = StorageSync(supabase_url=supabase_url, supabase_key=supabase_key, data_dir=data_dir)
        await sync.hydrate_user(user_id)

    # Try BwrapBackend (OS-level isolation), fall back to FilesystemBackend
    backend = _create_backend(system_dir, user_dir)

    # 6. Build channel-specific system prompt (runtime sections only — soul/identity
    #    come from skills loaded via the backend at invoke time)
    channel_prompt = _build_channel_prompt(
        channel=channel,
        memory_notes=memory_notes,
        user_instructions=user_instructions,
    )

    # 7. Resolve model — Deep Agents uses "provider:model" format
    llm_config = agent_db_config.get("llm_config") or {}
    model_name = llm_config.get("model", "claude-sonnet-4-20250514")
    model = model_name if ":" in model_name else f"anthropic:{model_name}"

    # 8. Build CompiledStateGraph via create_deep_agent
    agent = create_deep_agent(
        model=model,
        tools=instantiated_tools,        # BaseTool instances accepted natively
        system_prompt=channel_prompt,
        backend=backend,                  # BwrapBackend
        skills=["/system/skills/", "/user/skills/"],  # system (ro) + user (rw) skills
        checkpointer=None,                # TODO: add postgres checkpointer later
        name="clarity",
    )

    logger.info(
        "Built deep agent for '%s' (model=%s, %d tools, backend=BwrapBackend)",
        agent_name,
        model,
        len(instantiated_tools),
    )

    return agent
