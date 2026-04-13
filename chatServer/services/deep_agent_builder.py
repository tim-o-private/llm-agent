"""Builder for Deep Agent (CompiledStateGraph) instances.

Builds a create_deep_agent() graph with:
- BwrapBackend (OS-level sandbox) or FilesystemBackend fallback
- AGENTS.md working memory via MemoryMiddleware (always loaded, agent-editable)
- Skills via SkillsMiddleware (on-demand, progressive disclosure)
- AsyncPostgresSaver checkpointer for conversation state persistence
- MemoryClient tools for semantic search (separate from AGENTS.md)

Architecture
------------
    caller → build_deep_agent(user_id, agent_name, session_id, channel)
           → loads config, tools, approval wrapping, backend, system prompt
           → create_deep_agent(model, tools, system_prompt, backend, skills, memory, checkpointer)
           → returns CompiledStateGraph (LangGraph)

Callers use .ainvoke() / .astream() with config={"configurable": {"thread_id": session_id}}.
"""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
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
# Agent cache  (keyed on user_id + agent_name + channel)
# ---------------------------------------------------------------------------

_agent_cache: TTLCache[Tuple[str, str, str], Any] = TTLCache(
    maxsize=100, ttl=900  # 15-min TTL
)
_agent_locks: Dict[Tuple[str, str, str], asyncio.Lock] = {}

# ---------------------------------------------------------------------------
# System prompt — always-present identity + runtime context
# ---------------------------------------------------------------------------

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
        "This is an automated heartbeat check. No one is waiting.\n\n"
        "Review your working memory for active plans and open threads.\n"
        "Then check signals: calendar (next 4 hours), email (unread from key people), overdue tasks.\n\n"
        "- If nothing needs the user's attention: respond exactly HEARTBEAT_OK\n"
        "- If something does: report what and why, in 2-3 sentences max. Be specific.\n"
        "- Target 3-5 proactive messages per day total. Silence is usually correct.\n"
        "- Never fabricate. If a tool fails, skip that check and note it."
    ),
    "session_open": (
        "The user just returned to the app. You are deciding whether to initiate — "
        "no user message has been sent yet."
    ),
}


def _format_identity(identity: dict | None) -> str:
    """Format identity dict into readable text."""
    if not identity:
        return ""
    parts = []
    if identity.get("name"):
        parts.append(f"Name: {identity['name']}")
    if identity.get("description"):
        parts.append(f"Description: {identity['description']}")
    if identity.get("vibe"):
        parts.append(f"Vibe: {identity['vibe']}")
    return "\n".join(parts)


def _read_system_file(path: Path) -> str:
    """Read a system config file, stripping YAML frontmatter."""
    if not path.exists():
        return ""
    text = path.read_text(encoding="utf-8")
    # Strip YAML frontmatter (--- ... ---)
    if text.startswith("---"):
        end = text.find("---", 3)
        if end != -1:
            text = text[end + 3:].strip()
    return text


def _build_system_prompt(
    soul: str | None = None,
    identity: dict | None = None,
    channel: str = "web",
    user_instructions: str | None = None,
    last_message_at: datetime | None = None,
    bootstrap_context: str | None = None,
) -> str:
    """Assemble the full system prompt with always-present identity + runtime context.

    Includes:
    - Soul (personality, values — includes operating model and safety guidelines)
    - Identity (name, description, vibe)
    - Channel-specific guidance
    - Current time
    - User custom instructions
    - Session/onboarding flow

    Memory (AGENTS.md) is handled separately by MemoryMiddleware.
    Skills are handled separately by SkillsMiddleware.
    """
    sections: list[str] = []

    # Soul — core personality (now includes operating model + safety guidelines)
    if soul:
        sections.append(f"## Soul\n{soul}")

    # Identity — name and metadata
    identity_text = _format_identity(identity)
    if identity_text:
        sections.append(f"## Identity\n{identity_text}")

    # Channel mode
    channel_text = _CHANNEL_HEADERS.get(channel, _CHANNEL_HEADERS["web"])
    sections.append(f"## Channel\n{channel_text}")

    # Current time
    now = datetime.now(timezone.utc)
    time_str = now.strftime("%A, %B %d, %Y %I:%M %p (UTC)")
    sections.append(f"## Current Time\n{time_str}")

    # User instructions
    if user_instructions:
        instr = user_instructions[:2000]
        sections.append(f"## User Instructions\n{instr}")

    # Workflow creation capabilities
    sections.append(
        "## Workflows\n"
        "Pre-built workflows are available at `/system/workflows/` (email-triage, morning-briefing, evening-briefing, draft-reply).\n"  # noqa: E501
        "These run automatically via scheduled tasks.\n\n"
        "You can create custom workflows by writing Markdown template files to `/user/workflows/`.\n"
        "Templates use YAML frontmatter + step definitions. Use `ls /system/workflows/` and "
        "`read_file` on any template to see the format."
    )

    # Session/onboarding sections (only for interactive channels)
    if channel == "session_open":
        _add_session_open_section(
            sections, user_instructions, last_message_at, bootstrap_context
        )
    elif channel in ("web", "telegram") and not user_instructions:
        # Onboarding hint — MemoryMiddleware handles the "has memory" check
        # via AGENTS.md content. If AGENTS.md is empty/new, agent will see
        # "(No memory loaded)" and know to introduce itself.
        pass

    return "\n\n".join(sections)


def _add_session_open_section(
    sections: list[str],
    user_instructions: str | None,
    last_message_at: datetime | None = None,
    bootstrap_context: str | None = None,
) -> None:
    """Append the session_open decision block to sections."""
    is_new_user = not user_instructions and last_message_at is None
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
        elapsed = datetime.now(timezone.utc) - last_message_at.replace(  # noqa: E501
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
        "- Reference your working memory for active plans and open threads.\n"
        "- If nothing needs attention and <30 min since last message: respond WAKEUP_SILENT\n"
        "- Otherwise: lead with what matters — active plans, upcoming deadlines, things needing follow-up.\n"
        "Don't re-call tools to fetch what's already in the context above."
    )


# ---------------------------------------------------------------------------
# AGENTS.md seed content for new users
# ---------------------------------------------------------------------------

_SEED_AGENTS_MD = """\
# Agent Memory

Your working memory. Read it every session. Rewrite sections to stay current — \
don't append forever. Keep under 100 lines.

## Who This Person Is
*(Name, role, what they care about, how they communicate. Learn through conversation.)*

## Life Domains
*(Work, family, health, home, finances, interests — which are active, what matters in each.)*

## Key People
*(Name → relationship, context, what matters about them.)*

## Active Plans
*(Goals the user is working toward. For each: goal, current status, next step, blockers. \
Use parent tasks with subtasks to track these — reference task IDs here. \
Remove completed plans.)*

## Open Threads
*(Things needing follow-up: emails awaiting replies, decisions pending, promises made. \
Include dates and deadlines.)*

## Observations
*(Patterns: preferences, triggers, recurring struggles, what works. Priority signals: \
what the user responds to quickly, what they dismiss, what stresses them.)*
"""


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
                 "--ro-bind", "/usr", "/usr",
                 "--ro-bind", "/lib", "/lib",
                 "--ro-bind", "/lib64", "/lib64",
                 "--", "/usr/bin/true"],
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
    Cached per (user_id, agent_name, channel) with 15-min TTL.
    """
    cache_key = (user_id, agent_name, channel)

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
    """Load config from files and construct a CompiledStateGraph via create_deep_agent()."""
    from deepagents import create_deep_agent

    # Lazy imports to avoid circular dependencies
    from chatServer.config.settings import get_settings
    from chatServer.services.agent_config_loader import get_agent_config_loader
    from chatServer.services.user_instructions_cache_service import get_cached_user_instructions
    from src.core.agent_loader_db import (
        _resolve_memory_user_id,
        load_tools_from_db,
    )

    settings = get_settings()
    effective_supabase_url = settings.supabase_url
    effective_supabase_key = settings.supabase_service_key

    # Memory client (for semantic search tool — separate from AGENTS.md working memory)
    memory_client = None
    mem_url = os.getenv("MEMORY_SERVER_URL", "")
    mem_key = os.getenv("MEMORY_SERVER_BACKEND_KEY", "")
    if mem_url and mem_key:
        from chatServer.services.memory_client import MemoryClient

        memory_user_id = await _resolve_memory_user_id(user_id)
        memory_client = MemoryClient(
            base_url=mem_url, backend_key=mem_key, user_id=memory_user_id
        )

    # 1. Agent config from files (YAML + soul.md)
    loader = get_agent_config_loader()
    agent_config = loader.load(agent_name)

    # 2. Tools from file config + user instructions from DB
    tools_data = agent_config["tools"]
    user_instructions = await get_cached_user_instructions(user_id, agent_name)

    # 3. Instantiate tools (Deep Agents takes BaseTool directly)
    instantiated_tools = load_tools_from_db(
        tools_data=tools_data,
        user_id=user_id,
        agent_name=agent_config["agent_name"],
        supabase_url=effective_supabase_url,
        supabase_key=effective_supabase_key,
        memory_client=memory_client,
    )

    # 4. Wrap tools with approval (non-fatal on failure)
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

    # 5. Create sandbox backend
    from chatServer.services.storage_sync import StorageSync

    data_dir = Path(os.getenv("SANDBOX_DATA_DIR", "/data"))
    system_dir = data_dir / "config" / "system"
    user_dir = data_dir / "sandboxes" / user_id

    # Ensure user dir exists
    user_dir.mkdir(parents=True, exist_ok=True)

    # Hydrate user dir from Storage if needed
    if settings.supabase_url and settings.supabase_service_key:
        sync = StorageSync(supabase_url=settings.supabase_url, supabase_key=settings.supabase_service_key, data_dir=data_dir)  # noqa: E501
        await sync.hydrate_user(user_id)

    # Seed AGENTS.md for new users
    agents_md_path = user_dir / "memory" / "AGENTS.md"
    if not agents_md_path.exists():
        agents_md_path.parent.mkdir(parents=True, exist_ok=True)
        agents_md_path.write_text(_SEED_AGENTS_MD, encoding="utf-8")
        logger.info("Seeded AGENTS.md for user %s", user_id)

    # Try BwrapBackend (OS-level isolation), fall back to FilesystemBackend
    backend = _create_backend(system_dir, user_dir)

    # 6. Build system prompt — always-present identity + runtime context
    soul = agent_config.get("soul") or ""
    identity = agent_config.get("identity")

    system_prompt = _build_system_prompt(
        soul=soul,
        identity=identity,
        channel=channel,
        user_instructions=user_instructions,
    )

    # 7. Resolve model — Deep Agents uses "provider:model" format
    llm_config = agent_config.get("llm_config") or {}
    model_name = llm_config.get("model", "claude-sonnet-4-20250514")
    model = model_name if ":" in model_name else f"anthropic:{model_name}"

    # 8. Resolve checkpointer (if initialized)
    checkpointer = None
    try:
        from chatServer.workflows.checkpointer import get_workflow_checkpointer
        cp = get_workflow_checkpointer()
        if cp.is_ready:
            checkpointer = cp.saver
    except RuntimeError:
        logger.debug("WorkflowCheckpointer not initialized — running without checkpointer")

    # 9. Build CompiledStateGraph via create_deep_agent
    agent = create_deep_agent(
        model=model,
        tools=instantiated_tools,
        system_prompt=system_prompt,
        backend=backend,
        skills=["/system/skills/", "/user/skills/"],
        memory=["/user/memory/AGENTS.md"],
        checkpointer=checkpointer,
        name=agent_config.get("agent_name", "clarity"),
        subagents=agent_config.get("subagents", []),
    )

    logger.info(
        "Built deep agent for '%s' (model=%s, %d tools, checkpointer=%s)",
        agent_name,
        model,
        len(instantiated_tools),
        "postgres" if checkpointer else "none",
    )

    return agent


# ---------------------------------------------------------------------------
# Post-invocation file sync
# ---------------------------------------------------------------------------


async def sync_user_files_after_invocation(user_id: str) -> None:
    """Fire-and-forget sync of user-modified files to Supabase Storage.

    Called after agent invocation to persist any changes the agent made
    to AGENTS.md or user skills back to durable storage.
    """
    try:
        from chatServer.config.settings import get_settings
        from chatServer.services.storage_sync import StorageSync

        settings = get_settings()
        data_dir = Path(os.getenv("SANDBOX_DATA_DIR", "/data"))
        supabase_url = settings.supabase_url
        supabase_key = settings.supabase_service_key

        if not supabase_url or not supabase_key:
            return

        sync = StorageSync(
            supabase_url=supabase_url,
            supabase_key=supabase_key,
            data_dir=data_dir,
        )

        # Sync key user files that the agent may have modified
        user_dir = data_dir / "sandboxes" / user_id
        memory_file = user_dir / "memory" / "AGENTS.md"

        if memory_file.exists():
            await sync.sync_file(user_id, "memory/AGENTS.md")

        # Sync any user skills
        skills_dir = user_dir / "skills"
        if skills_dir.exists():
            for skill_dir in skills_dir.iterdir():
                if skill_dir.is_dir():
                    skill_file = skill_dir / "SKILL.md"
                    if skill_file.exists():
                        await sync.sync_file(user_id, f"skills/{skill_dir.name}/SKILL.md")

        # Sync any user workflows
        workflows_dir = user_dir / "workflows"
        if workflows_dir.exists():
            for wf_file in workflows_dir.glob("*.md"):
                await sync.sync_file(user_id, f"workflows/{wf_file.name}")

    except Exception as e:
        logger.warning(f"Post-invocation sync failed for user {user_id} (non-fatal): {e}")
