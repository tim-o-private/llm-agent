"""Builder for ConversationHandler instances.

Loads agent config, tools, and system prompt from the database,
wraps tools with approval, and creates/caches ConversationHandler
instances per (user_id, agent_name).
"""

import asyncio
import logging
import os
from typing import Dict, Optional, Tuple

import anthropic
from cachetools import TTLCache

from ..database.supabase_client import create_user_scoped_client
from ..security.tool_wrapper import ApprovalContext, wrap_tools_with_approval
from ..services.audit_service import AuditService
from ..services.notification_service import NotificationService
from ..services.pending_actions import PendingActionsService
from .conversation_handler import ConversationHandler
from .langchain_tool_bridge import LangChainToolBridge

logger = logging.getLogger(__name__)

# Singleton Anthropic client  (AC-02)
_anthropic_client: Optional[anthropic.AsyncAnthropic] = None

# Handler cache: (user_id, agent_name) → ConversationHandler  (AC-31)
_handler_cache: TTLCache[Tuple[str, str], ConversationHandler] = TTLCache(
    maxsize=100, ttl=900
)
_handler_locks: Dict[Tuple[str, str], asyncio.Lock] = {}


def _get_anthropic_client() -> anthropic.AsyncAnthropic:
    """Get or create the singleton AsyncAnthropic client."""
    global _anthropic_client
    if _anthropic_client is None:
        _anthropic_client = anthropic.AsyncAnthropic()
    return _anthropic_client


async def build_conversation_handler(
    user_id: str,
    agent_name: str,
    session_id: str,
    channel: str = "web",
) -> ConversationHandler:
    """Build or retrieve a cached ConversationHandler.

    Parallels ``load_agent_executor_db_async`` but produces a
    ConversationHandler instead of a CustomizableAgentExecutor.
    Cached per (user_id, agent_name) with 15-min TTL (AC-31).
    """
    cache_key = (user_id, agent_name)

    if cache_key in _handler_cache:
        logger.debug("ConversationHandler cache HIT: %s", cache_key)
        return _handler_cache[cache_key]

    lock = _handler_locks.setdefault(cache_key, asyncio.Lock())
    async with lock:
        if cache_key in _handler_cache:
            return _handler_cache[cache_key]

        logger.info("Building ConversationHandler for %s", cache_key)
        handler = await _build_handler(
            user_id, agent_name, session_id, channel
        )
        _handler_cache[cache_key] = handler
        return handler


async def _build_handler(
    user_id: str,
    agent_name: str,
    session_id: str,
    channel: str,
) -> ConversationHandler:
    """Load everything from the DB and construct a ConversationHandler."""
    # Lazy imports to avoid circular deps at module level
    from chatServer.services.agent_config_cache_service import (
        get_cached_agent_config,
    )
    from chatServer.services.prompt_builder import build_agent_prompt
    from chatServer.services.tool_cache_service import (
        get_cached_tools_for_agent,
    )
    from chatServer.services.user_instructions_cache_service import (
        get_cached_user_instructions,
    )
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

    # 2. Parallel fetch: tools + instructions + memory
    cached_tools_data, user_instructions, memory_notes = await asyncio.gather(
        get_cached_tools_for_agent(str(agent_id)),
        get_cached_user_instructions(user_id, agent_name),
        _prefetch_memory_notes(memory_client),
    )

    # Transform cached tool data to expected format
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

    # 3. Instantiate tools
    instantiated_tools = load_tools_from_db(
        tools_data=tools_data,
        user_id=user_id,
        agent_name=agent_db_config["agent_name"],
        supabase_url=effective_supabase_url,
        supabase_key=effective_supabase_key,
        memory_client=memory_client,
    )

    # 4. Wrap tools with approval
    try:
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
    except Exception as e:
        logger.warning(
            "Failed to wrap tools with approval (non-fatal): %s", e
        )

    # 5. Convert tools via bridge
    tool_schemas, tool_executors = LangChainToolBridge.convert_tools(
        instantiated_tools
    )

    # 6. Build system prompt
    llm_config = agent_db_config.get("llm_config") or {}
    system_prompt = build_agent_prompt(
        soul=agent_db_config.get("soul") or "",
        identity=agent_db_config.get("identity"),
        channel=channel,
        user_instructions=user_instructions,
        tools=instantiated_tools,
        memory_notes=memory_notes,
        prompt_template=agent_db_config.get("prompt_template"),
    )

    # 7. Create handler
    model = llm_config.get("model", "claude-sonnet-4-20250514")
    handler = ConversationHandler(
        client=_get_anthropic_client(),
        model=model,
        system_prompt=system_prompt,
        tools=tool_schemas,
        tool_executors=tool_executors,
        max_tokens=llm_config.get("max_tokens", 4096),
        temperature=llm_config.get("temperature", 0.7),
    )

    logger.info(
        "Built ConversationHandler for '%s' (model=%s, %d tools)",
        agent_name,
        model,
        len(tool_schemas),
    )
    return handler
