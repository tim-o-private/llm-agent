"""Tool resolver service — unified tool resolution for chat agents and workflows."""

import logging
from typing import Any, Callable

logger = logging.getLogger(__name__)


def _build_executor(tool: Any) -> Callable:
    """Build an async executor closure for a BaseTool instance."""

    async def _executor(input_dict: dict) -> str:
        return await tool._arun(**input_dict)

    return _executor


class ToolResolverService:
    """Unified tool resolution path for both chat agents and workflows."""

    async def resolve_for_agent(
        self, user_id: str, agent_name: str
    ) -> tuple[list[dict], dict[str, Callable], list[Any]]:
        """Resolve tools for a given user and agent.

        Fetches granted tools from the database, instantiates them via
        ``load_tools_from_db``, and converts them into workflow engine format.

        Args:
            user_id: The user ID.
            agent_name: The agent name.

        Returns:
            Tuple of (tool_schemas, tool_executors, instantiated_tools).
        """
        from ..config.settings import get_settings
        from ..database.connection import get_database_manager

        # 1. Fetch tools from DB
        db_manager = get_database_manager()
        tools_data: list[dict] = []

        try:
            async for conn in db_manager.get_connection():
                async with conn.cursor() as cur:
                    await cur.execute(
                        """
                        SELECT
                            t.name,
                            t.description,
                            t.type,
                            t.config,
                            at.status
                        FROM agent_tools at
                        JOIN tools t ON at.tool_id = t.id
                        JOIN agent_configurations ac ON at.agent_id = ac.id
                        WHERE ac.agent_name = %s
                        AND at.is_active = true
                        AND at.is_deleted = false
                        AND (at.status = 'granted' OR at.status IS NULL)
                        AND t.is_active = true
                        AND t.is_deleted = false
                        """,
                        (agent_name,),
                    )
                    rows = await cur.fetchall()
                    for row in rows:
                        tools_data.append({
                            "name": row[0],
                            "description": row[1],
                            "type": row[2],
                            "config": row[3],
                            "status": row[4],
                        })
        except Exception as e:
            logger.error("Failed to fetch tools for agent %s: %s", agent_name, e)
            return [], {}, []

        if not tools_data:
            return [], {}, []

        # 2. Instantiate tools
        settings = get_settings()
        from src.core.agent_loader_db import load_tools_from_db

        instantiated_tools = load_tools_from_db(
            tools_data=tools_data,
            user_id=user_id,
            agent_name=agent_name,
            supabase_url=settings.supabase_url or "",
            supabase_key=settings.supabase_service_key or "",
            memory_client=None,
        )

        # 3. Convert to workflow engine format
        tool_schemas: list[dict] = []
        tool_executors: dict[str, Callable] = {}

        for tool in instantiated_tools:
            if not getattr(tool, "name", None):
                continue

            schema: dict = {"type": "object", "properties": {}, "required": []}
            if getattr(tool, "args_schema", None):
                try:
                    schema = tool.args_schema.model_json_schema()
                except Exception:
                    logger.warning(
                        "Failed to get schema for tool '%s'", tool.name, exc_info=True
                    )

            tool_schemas.append({
                "name": tool.name,
                "description": getattr(tool, "description", ""),
                "input_schema": {
                    "type": "object",
                    "properties": schema.get("properties", {}),
                    "required": schema.get("required", []),
                },
            })

            tool_executors[tool.name] = _build_executor(tool)

        return tool_schemas, tool_executors, instantiated_tools


async def resolve_tools_for_agent(
    user_id: str, agent_name: str
) -> tuple[list[dict], dict[str, Callable], list[Any]]:
    """Convenience function to resolve tools for an agent.

    Args:
        user_id: The user ID.
        agent_name: The agent name.

    Returns:
        Tuple of (tool_schemas, tool_executors, instantiated_tools).
    """
    service = ToolResolverService()
    return await service.resolve_for_agent(user_id, agent_name)
