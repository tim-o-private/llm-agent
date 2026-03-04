"""
Standalone tool executor for post-approval execution.

Resolves a tool by name, instantiates the BaseTool subclass with user context,
and calls _arun() directly -- bypassing the LangChain agent executor and the
approval wrapper.
"""

import importlib
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Memory tools require an MCP memory_client that doesn't exist outside
# the agent loop. Block them from post-approval execution.
_MEMORY_TOOL_TYPES = {
    "CreateMemoriesTool", "SearchMemoriesTool", "GetMemoriesTool",
    "DeleteMemoriesTool", "UpdateMemoriesTool", "SetProjectTool",
    "LinkMemoriesTool", "GetEntitiesTool", "SearchEntitiesTool",
    "GetContextTool",
}


class ToolExecutionError(Exception):
    """Raised when post-approval tool execution fails."""
    pass


class ToolExecutionService:
    """
    Executes tools by name outside the LangChain agent loop.

    Used by PendingActionsService after user approval. Instantiates tool
    classes from TOOL_REGISTRY with proper user context.
    """

    def __init__(self, db_client):
        self.db = db_client

    async def execute_tool(
        self,
        tool_name: str,
        tool_args: dict,
        user_id: str,
        agent_name: Optional[str] = None,
    ) -> str:
        """
        Execute a tool by name.

        1. Look up tool type + config from `tools` table by name
        2. Resolve Python class from TOOL_REGISTRY (with GmailTool dynamic import)
        3. Reject memory tools (need MCP client unavailable here)
        4. Instantiate with user context (no approval wrapper)
        5. Call _arun(**tool_args) directly
        """
        from src.core.agent_loader_db import TOOL_REGISTRY

        from ..config.settings import get_settings

        settings = get_settings()

        # Step 1: Resolve tool type from DB
        result = await self.db.table("tools") \
            .select("type, config") \
            .eq("name", tool_name) \
            .single() \
            .execute()

        if not result.data:
            raise ToolExecutionError(f"Tool '{tool_name}' not found in tools table")

        tool_type = result.data["type"]
        tool_config = result.data.get("config") or {}

        # Step 2: Reject memory tools -- they need memory_client (MCP)
        if tool_type in _MEMORY_TOOL_TYPES:
            raise ToolExecutionError(
                f"Tool '{tool_name}' (type {tool_type}) is a memory tool and cannot "
                f"be executed post-approval -- memory tools require an MCP client "
                f"that is only available inside the agent loop."
            )

        # Step 3: Resolve Python class
        tool_class = TOOL_REGISTRY.get(tool_type)

        if tool_class is None and tool_type == "GmailTool":
            # GmailTool uses dynamic import from config.tool_class
            # (same pattern as load_tools_from_db)
            gmail_class_name = tool_config.get("tool_class")
            if not gmail_class_name:
                raise ToolExecutionError(
                    f"GmailTool '{tool_name}' has no tool_class in config"
                )
            try:
                module = importlib.import_module("chatServer.tools.gmail_tools")
                tool_class = getattr(module, gmail_class_name)
            except (ImportError, AttributeError) as e:
                raise ToolExecutionError(
                    f"Failed to import Gmail tool class '{gmail_class_name}': {e}"
                ) from e
        elif tool_class is None:
            raise ToolExecutionError(
                f"Tool type '{tool_type}' for '{tool_name}' not in TOOL_REGISTRY"
            )

        # Step 4: Build constructor kwargs
        constructor_kwargs = {
            "user_id": user_id,
            "agent_name": agent_name,
            "supabase_url": settings.supabase_url,
            "supabase_key": settings.supabase_service_key,
            "name": tool_name,
            "description": f"Post-approval execution of {tool_name}",
        }

        # Merge tool-specific config (same pattern as load_tools_from_db)
        if tool_config:
            constructor_kwargs.update(tool_config)

        # Step 5: Instantiate and execute
        try:
            tool_instance = tool_class(**constructor_kwargs)
        except Exception as e:
            raise ToolExecutionError(
                f"Failed to instantiate tool '{tool_name}' (class {tool_class.__name__}): {e}"
            ) from e

        try:
            result = await tool_instance._arun(**tool_args)
            logger.info(f"Post-approval execution of '{tool_name}' succeeded for user {user_id}")
            return result
        except Exception as e:
            logger.error(f"Post-approval execution of '{tool_name}' failed: {e}")
            raise ToolExecutionError(
                f"Tool '{tool_name}' execution failed: {e}"
            ) from e
