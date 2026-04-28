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

_CHANNEL_NOTES = {
    "web": "User is on the web app. Markdown supported.",
    "telegram": "User is on Telegram. Max 4096 chars, simple markdown, no tables.",
    "scheduled": "Automated scheduled run. No one is waiting. Be thorough and self-contained.",
    "heartbeat": (
        "Automated heartbeat. Check working memory + signals (calendar, tasks, email).\n"
        "Nothing needs attention → respond HEARTBEAT_OK\n"
        "Something does → state it and what you'd do, in 2-3 sentences."
    ),
    "session_open": "User just returned to the app. No message typed yet.",
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


def _collect_tool_guidance(tools: list, channel: str) -> str:
    """Gather per-tool behavioral guidance via classmethod prompt_section(channel).

    Walks the tools, calls prompt_section(channel) on each class that defines it,
    deduplicates, and returns a single "## Tool Guidance" block. Tools without
    prompt_section or returning None/empty for this channel are skipped.
    """
    seen: set[str] = set()
    sections: list[str] = []
    for tool in tools:
        fn = getattr(type(tool), "prompt_section", None)
        if fn is None:
            continue
        try:
            text = fn(channel)
        except Exception as exc:
            logger.debug("prompt_section failed for %s: %s", type(tool).__name__, exc)
            continue
        if not text:
            continue
        text = text.strip()
        if text in seen:
            continue
        seen.add(text)
        sections.append(text)
    if not sections:
        return ""
    return "## Tool Guidance\n" + "\n\n".join(sections)


async def _build_scope_context(scope: dict | None, vault_service=None, user_id: str = "") -> str:
    """Build a scope context string from the chat scope.

    SPEC-049 §"Technical Approach" §9 — injected as a prefix to the system
    prompt so the agent knows what the user is looking at.
    """
    if not scope:
        return ""

    scope_type = scope.get("type", "global")
    scope_path = scope.get("path")

    async def _read_and_truncate(label: str) -> str | None:
        if not (vault_service and user_id and scope_path):
            return None
        try:
            content = await vault_service.read_file(user_id, scope_path)
            if len(content) > 4000:
                content = content[:4000] + "\n... [truncated]"
            return f"{label}:\n```\n{content}\n```"
        except Exception:
            return None

    parts: list[str] = []
    if scope_type == "today":
        parts.append("The user is on the Today dashboard.")
    elif scope_type == "file" and scope_path:
        parts.append(f"The user is viewing the file: {scope_path}")
        snippet = await _read_and_truncate("File content")
        if snippet:
            parts.append(snippet)
    elif scope_type == "folder" and scope_path:
        parts.append(f"The user is browsing the folder: {scope_path}")
        if vault_service and user_id:
            try:
                entries = await vault_service.list_folder(user_id, scope_path)
                listing = "\n".join(f"- {e.type}: {e.name}" for e in entries)
                if listing:
                    parts.append(f"Folder contents:\n{listing}")
            except Exception:
                pass
    elif scope_type == "workflow" and scope_path:
        parts.append(f"The user is editing the workflow: {scope_path}")
        snippet = await _read_and_truncate("Workflow definition")
        if snippet:
            parts.append(snippet)
    else:
        return ""

    return "\n".join(parts)


def _build_system_prompt(
    soul: str | None = None,
    identity: dict | None = None,
    channel: str = "web",
    user_instructions: str | None = None,
    last_message_at: datetime | None = None,
    bootstrap_context: str | None = None,
    phase: str = "management",
    system_dir: Path | None = None,
    tool_guidance: str | None = None,
    scope_context: str | None = None,
) -> str:
    """Assemble the system prompt: soul + phase skill + runtime context.

    Memory (AGENTS.md) is handled separately by MemoryMiddleware.
    Skills are handled separately by SkillsMiddleware.
    """
    sections: list[str] = []

    # Identity and behavior
    if soul:
        sections.append(soul)

    # Phase-specific procedure (from skill files)
    if phase == "orientation" and system_dir:
        skill_path = system_dir / "skills" / "bootstrapping" / "SKILL.md"
        text = _read_system_file(skill_path)
        if text:
            sections.append(text)
    elif phase == "management" and system_dir:
        skill_path = system_dir / "skills" / "operating" / "SKILL.md"
        text = _read_system_file(skill_path)
        if text:
            sections.append(text)

    # Runtime context
    identity_text = _format_identity(identity)
    if identity_text:
        sections.append(identity_text)

    channel_note = _CHANNEL_NOTES.get(channel, _CHANNEL_NOTES["web"])
    sections.append(channel_note)

    if scope_context:
        sections.append(scope_context)

    now = datetime.now(timezone.utc)
    sections.append(now.strftime("Current time: %A, %B %d, %Y %I:%M %p UTC"))

    if user_instructions:
        sections.append(f"User instructions: {user_instructions[:2000]}")

    if tool_guidance:
        sections.append(tool_guidance)

    if channel == "session_open":
        _add_session_open_section(sections, user_instructions, last_message_at, bootstrap_context)

    return "\n\n".join(sections)


def _add_session_open_section(
    sections: list[str],
    user_instructions: str | None,
    last_message_at: datetime | None = None,
    bootstrap_context: str | None = None,
) -> None:
    """Append session_open runtime data. Behavioral guidance comes from soul + skills."""
    is_new_user = not user_instructions and last_message_at is None

    if is_new_user:
        sections.append("First session. No prior history with this user.")
        return

    # Time since last interaction
    if last_message_at:
        lm = last_message_at if last_message_at.tzinfo else last_message_at.replace(tzinfo=timezone.utc)
        elapsed_min = int((datetime.now(timezone.utc) - lm).total_seconds() / 60)
        if elapsed_min < 2:
            time_ctx = "Last interaction <2 min ago."
        elif elapsed_min < 60:
            time_ctx = f"Last interaction {elapsed_min} min ago."
        else:
            hrs = elapsed_min // 60
            time_ctx = f"Last interaction {hrs} hour{'s' if hrs > 1 else ''} ago."
    else:
        time_ctx = "No prior messages in this session."

    ctx = bootstrap_context or "(no signals available)"
    sections.append(
        f"{time_ctx}\n\n"
        f"Pre-fetched signals:\n{ctx}\n\n"
        "If something warrants a greeting, lead with it. Otherwise respond WAKEUP_SILENT."
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
# Phase detection — orientation vs. management
# ---------------------------------------------------------------------------

_AGENTS_MD_SECTIONS = [
    "## Who This Person Is",
    "## Life Domains",
    "## Key People",
    "## Active Plans",
    "## Open Threads",
    "## Observations",
]

_PLACEHOLDER_MARKER = "*("


def _detect_agent_phase(agents_md_content: str) -> str:
    """Detect whether the user is in orientation or management phase.

    Uses two strategies and takes the best signal:
    1. Header-based: counts known section headers with real (non-placeholder) content.
    2. Content-based: counts lines of real content regardless of header names.
       This handles old-format AGENTS.md files whose headers don't match the seed.

    Returns "management" if either strategy shows substantial content,
    "orientation" otherwise.
    """
    # Strategy 1: check known new-format headers
    populated = 0
    for i, header in enumerate(_AGENTS_MD_SECTIONS):
        header_pos = agents_md_content.find(header)
        if header_pos == -1:
            continue
        # Get content between this header and the next (or end of file)
        after_header = agents_md_content[header_pos + len(header):]
        next_header_pos = len(after_header)
        for next_h in _AGENTS_MD_SECTIONS[i + 1:]:
            pos = after_header.find(next_h)
            if pos != -1:
                next_header_pos = min(next_header_pos, pos)
                break
        section_content = after_header[:next_header_pos].strip()
        # A section is "populated" if it has content that isn't just a placeholder
        if section_content and not section_content.startswith(_PLACEHOLDER_MARKER):
            populated += 1

    if populated >= 4:
        return "management"

    # Strategy 2: content-line heuristic — works for any header format.
    # Strip headers, placeholder lines, blank lines, and count real content.
    content_lines = 0
    for line in agents_md_content.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            continue
        if stripped.startswith(_PLACEHOLDER_MARKER):
            continue
        content_lines += 1

    if content_lines > 10:
        return "management"

    return "orientation"


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
    bootstrap_context: str | None = None,
    last_message_at: datetime | None = None,
    scope: dict | None = None,
) -> Any:
    """Build or retrieve a cached CompiledStateGraph.

    Returns a LangGraph CompiledStateGraph created by create_deep_agent().
    Cached per (user_id, agent_name, channel) with 15-min TTL.

    session_open is never cached — bootstrap_context changes every invocation.
    """
    # session_open embeds runtime data (bootstrap_context, last_message_at)
    # in the system prompt, so it must be rebuilt fresh every time.
    skip_cache = channel == "session_open"

    cache_key = (user_id, agent_name, channel)

    if not skip_cache and cache_key in _agent_cache:
        logger.debug("Deep agent cache HIT: %s", cache_key)
        return _agent_cache[cache_key]

    lock = _agent_locks.setdefault(cache_key, asyncio.Lock())
    async with lock:
        if not skip_cache and cache_key in _agent_cache:
            return _agent_cache[cache_key]

        logger.info("Building deep agent for %s", cache_key)
        agent = await _build_agent(
            user_id, agent_name, session_id, channel,
            bootstrap_context=bootstrap_context,
            last_message_at=last_message_at,
            scope=scope,
        )
        if not skip_cache:
            _agent_cache[cache_key] = agent

    # Prune locks for cache keys that have expired from TTLCache
    stale = [k for k in _agent_locks if k not in _agent_cache]
    for k in stale:
        _agent_locks.pop(k, None)

    return agent


async def _build_agent(
    user_id: str,
    agent_name: str,
    session_id: str,
    channel: str,
    *,
    bootstrap_context: str | None = None,
    last_message_at: datetime | None = None,
    scope: dict | None = None,
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

    # Seed AGENTS.md for new users — load from file, fall back to constant
    agent_dir = system_dir / "agents" / agent_name
    agents_md_path = user_dir / "memory" / "AGENTS.md"
    if not agents_md_path.exists():
        agents_md_path.parent.mkdir(parents=True, exist_ok=True)
        seed_content = _read_system_file(agent_dir / "seed.md") or _SEED_AGENTS_MD
        agents_md_path.write_text(seed_content, encoding="utf-8")
        logger.info("Seeded AGENTS.md for user %s", user_id)

    # Try BwrapBackend (OS-level isolation), fall back to FilesystemBackend
    backend = _create_backend(system_dir, user_dir)

    # 5b. Detect agent phase from AGENTS.md content
    agents_md_content = agents_md_path.read_text(encoding="utf-8") if agents_md_path.exists() else ""
    phase = _detect_agent_phase(agents_md_content)
    if phase == "orientation":
        logger.info("User %s in orientation phase", user_id)

    # 6. Build system prompt — always-present identity + runtime context
    soul = agent_config.get("soul") or ""
    identity = agent_config.get("identity")

    tool_guidance = _collect_tool_guidance(instantiated_tools, channel)

    # SPEC-049: build scope context for injection into system prompt.
    # VaultService needs a StorageSync, but for scope context we only read
    # files from the local sandbox. We construct a lightweight VaultService
    # pointing at the same data_dir used by the sandbox backend.
    scope_context = ""
    if scope:
        try:
            from chatServer.services.vault_service import VaultService

            vault_svc = VaultService(storage_sync=None, data_dir=data_dir)
            scope_context = await _build_scope_context(scope, vault_service=vault_svc, user_id=user_id)
        except Exception as exc:
            logger.debug("Scope context build failed (non-fatal): %s", exc)

    system_prompt = _build_system_prompt(
        soul=soul,
        identity=identity,
        channel=channel,
        user_instructions=user_instructions,
        last_message_at=last_message_at,
        bootstrap_context=bootstrap_context,
        phase=phase,
        system_dir=system_dir,
        tool_guidance=tool_guidance,
        scope_context=scope_context,
    )

    # 7. Resolve model — Deep Agents uses "provider:model" format
    llm_config = agent_config.get("llm_config") or {}
    model_name = llm_config.get("model", settings.llm_default_model)
    default_prefix = "anthropic" if settings.llm_provider == "anthropic" else "openai"
    model = model_name if ":" in model_name else f"{default_prefix}:{model_name}"

    # ChatOpenAI drops reasoning_content from thinking models (DeepSeek, Kimi, etc.).
    # Use ChatOpenRouter which preserves it round-trip.
    if default_prefix == "openai":
        from langchain_openrouter import ChatOpenRouter
        init_kwargs: dict = {"model": model_name}
        if settings.llm_api_key:
            init_kwargs["api_key"] = settings.llm_api_key
        if settings.llm_base_url:
            init_kwargs["base_url"] = settings.llm_base_url
        model = ChatOpenRouter(**init_kwargs)

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
