"""Memory tools backed by min-memory MCP server.

Thin LangChain wrappers around MemoryClient.call_tool(). Each tool maps 1:1
to a min-memory MCP tool — no duplicated logic.
"""

import logging
from typing import Any, Type

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Base class — all memory tools share this pattern
# ---------------------------------------------------------------------------

class _MemoryToolBase(BaseTool):
    """Base for memory tools that delegate to MemoryClient."""

    memory_client: Any = Field(..., description="MemoryClient instance")
    user_id: str = Field(..., description="User ID for logging")
    agent_name: str = Field(..., description="Agent name for logging")

    # Subclasses set this to the min-memory MCP tool name
    _mcp_tool_name: str = ""

    @classmethod
    def prompt_section(cls, channel: str) -> str | None:
        return None

    def _run(self, **kwargs: Any) -> str:
        return f"{self.name} requires async execution."

    async def _call_mcp(self, args: dict[str, Any]) -> str:
        """Call min-memory and return result as string."""
        try:
            result = await self.memory_client.call_tool(self._mcp_tool_name, args)
            logger.info("%s for user=%s, agent=%s", self.name, self.user_id, self.agent_name)
            return str(result)
        except Exception as e:
            logger.error("Failed %s for user=%s, agent=%s: %s", self.name, self.user_id, self.agent_name, e)
            return f"Failed to {self.name}: {e}"


# ---------------------------------------------------------------------------
# Input schemas
# ---------------------------------------------------------------------------

class CreateMemoriesInput(BaseModel):
    text: str = Field(..., description="The memory text to store.")
    memory_type: str = Field(..., description="Type: core_identity, project_context, task_instruction, or episodic.")
    entity: str = Field(..., description="Entity this memory is about (e.g., user name, project name).")
    scope: str = Field(..., description="Scope: global, project, or task.")
    tags: list[str] = Field(default_factory=list, description="Optional tags for categorization.")
    project: str = Field(default="", description="Project name (required when scope is project or task).")
    task_id: str = Field(default="", description="Task ID (required when scope is task).")


class SearchMemoriesInput(BaseModel):
    query: str = Field(..., description="What to search for — describe what you're looking for.")
    limit: int = Field(default=10, description="Max number of memories to return.")
    memory_type: list[str] = Field(default_factory=list, description="Filter by memory types.")
    scope: str = Field(default="", description="Filter by scope: global, project, or task.")
    project: str = Field(default="", description="Filter by project name.")


class GetMemoriesInput(BaseModel):
    id: str = Field(..., description="The ID of the memory to fetch.")


class DeleteMemoriesInput(BaseModel):
    memory_id: str = Field(..., description="The ID of the memory to delete.")


class UpdateMemoriesInput(BaseModel):
    memory_id: str = Field(..., description="The ID of the memory to update.")
    text: str = Field(default="", description="New text content (re-embeds if changed).")
    memory_type: str = Field(
        default="", description="New type: core_identity, project_context, task_instruction, or episodic.",
    )
    scope: str = Field(default="", description="New scope: global, project, or task.")
    entity: str = Field(default="", description="New entity name.")
    project: str = Field(default="", description="New project name.")
    task_id: str = Field(default="", description="New task ID.")
    tags: list[str] = Field(default_factory=list, description="New tags (replaces existing).")
    status: str = Field(default="", description="New status.")
    priority: int | None = Field(default=None, description="New priority.")


class SetProjectInput(BaseModel):
    project: str = Field(..., description="Project name to validate or create.")


class LinkMemoriesInput(BaseModel):
    memory_id: str = Field(..., description="ID of the source memory.")
    related_id: str = Field(..., description="ID of the related memory.")
    relation_type: str = Field(..., description="Relationship: supports, contradicts, supersedes, refines, depends_on, implements, or example_of.")  # noqa: E501


class GetEntitiesInput(BaseModel):
    scope: str = Field(default="", description="Filter by scope.")
    project: str = Field(default="", description="Filter by project.")
    memory_type: str = Field(default="", description="Filter by memory type.")


class SearchEntitiesInput(BaseModel):
    query: str = Field(..., description="Entity name to search for.")
    limit: int = Field(default=5, description="Max results.")


class EmptyInput(BaseModel):
    """No arguments required."""
    pass


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

class CreateMemoriesTool(_MemoryToolBase):
    """Store a memory about the user or a project."""

    name: str = "create_memories"
    description: str = (
        "Store a memory. Use proactively when you learn something — preferences, "
        "habits, projects, decisions, or communication style. Don't wait to be asked."
    )
    args_schema: Type[BaseModel] = CreateMemoriesInput
    _mcp_tool_name: str = "store_memory"

    @classmethod
    def prompt_section(cls, channel: str) -> str | None:
        if channel in ("web", "telegram"):
            return (
                "Memory recording guide:\n"
                "- memory_type 'core_identity': user facts, preferences, personality traits, "
                "communication style\n"
                "- memory_type 'project_context': life domains, ongoing projects, work context, "
                "relationships between entities\n"
                "- memory_type 'episodic': specific events, decisions, feedback, corrections\n"
                "- Create entities for people, organizations, and projects the user mentions\n"
                "- Record priority signals: what the user reacts to, dismisses, or corrects\n"
                "- Use search_memories before answering questions about the user's preferences "
                "or history"
            )
        return None

    async def _arun(self, text: str, memory_type: str, entity: str, scope: str,
                    tags: list[str] | None = None, project: str = "", task_id: str = "") -> str:
        args: dict[str, Any] = {"text": text, "memory_type": memory_type, "entity": entity, "scope": scope}
        if tags:
            args["tags"] = tags
        if project:
            args["project"] = project
        if task_id:
            args["task_id"] = task_id
        return await self._call_mcp(args)


class SearchMemoriesTool(_MemoryToolBase):
    """Search memories relevant to a query with optional filtering."""

    name: str = "search_memories"
    description: str = (
        "Search memories relevant to a query. Returns semantically similar memories "
        "with hierarchical context (merges global + project scopes). Use before answering "
        "questions about preferences, past decisions, or projects. "
        "Provide scope/type filters for hierarchical recall, or just a query for basic search."
    )
    args_schema: Type[BaseModel] = SearchMemoriesInput
    _mcp_tool_name: str = "retrieve_context"

    async def _arun(self, query: str, limit: int = 10, memory_type: list[str] | None = None,
                    scope: str = "", project: str = "") -> str:
        args: dict[str, Any] = {"query": query, "limit": limit}
        if memory_type:
            args["memory_type"] = memory_type
        if scope:
            args["scope"] = scope
        if project:
            args["project"] = project
        return await self._call_mcp(args)


class GetMemoriesTool(_MemoryToolBase):
    """Fetch a specific memory by ID."""

    name: str = "get_memories"
    description: str = "Fetch a specific memory by its ID. Use after search to get full details."
    args_schema: Type[BaseModel] = GetMemoriesInput
    _mcp_tool_name: str = "fetch"

    async def _arun(self, id: str) -> str:
        return await self._call_mcp({"id": id})


class DeleteMemoriesTool(_MemoryToolBase):
    """Soft-delete a memory by ID."""

    name: str = "delete_memories"
    description: str = (
        "Delete a memory. Use when the user asks you to forget something "
        "or when information is outdated."
    )
    args_schema: Type[BaseModel] = DeleteMemoriesInput
    _mcp_tool_name: str = "delete_memory"

    async def _arun(self, memory_id: str) -> str:
        return await self._call_mcp({"memory_id": memory_id})


class UpdateMemoriesTool(_MemoryToolBase):
    """Update an existing memory's text and/or metadata."""

    name: str = "update_memories"
    description: str = (
        "Update an existing memory's text and/or metadata fields. "
        "Only provided fields are changed."
    )
    args_schema: Type[BaseModel] = UpdateMemoriesInput
    _mcp_tool_name: str = "update_memory"

    async def _arun(self, memory_id: str, text: str = "", memory_type: str = "",
                    scope: str = "", entity: str = "", project: str = "",
                    task_id: str = "", tags: list[str] | None = None,
                    status: str = "", priority: int | None = None) -> str:
        args: dict[str, Any] = {"memory_id": memory_id}
        if text:
            args["text"] = text
        if memory_type:
            args["memory_type"] = memory_type
        if scope:
            args["scope"] = scope
        if entity:
            args["entity"] = entity
        if project:
            args["project"] = project
        if task_id:
            args["task_id"] = task_id
        if tags:
            args["tags"] = tags
        if status:
            args["status"] = status
        if priority is not None:
            args["priority"] = priority
        return await self._call_mcp(args)


class SetProjectTool(_MemoryToolBase):
    """Validate or create a project scope."""

    name: str = "set_project"
    description: str = "Validate a project exists in memory or create it. Returns project summary with memory counts."
    args_schema: Type[BaseModel] = SetProjectInput
    _mcp_tool_name: str = "set_project"

    async def _arun(self, project: str) -> str:
        return await self._call_mcp({"project": project})


class LinkMemoriesTool(_MemoryToolBase):
    """Create a relationship between two memories."""

    name: str = "link_memories"
    description: str = (
        "Link two memories with a relationship (supports, contradicts, supersedes, "
        "refines, depends_on, implements, example_of). Use to connect related decisions or facts."
    )
    args_schema: Type[BaseModel] = LinkMemoriesInput
    _mcp_tool_name: str = "link_memories"

    async def _arun(self, memory_id: str, related_id: str, relation_type: str) -> str:
        return await self._call_mcp({"memory_id": memory_id, "related_id": related_id, "relation_type": relation_type})


class GetEntitiesTool(_MemoryToolBase):
    """List all known entities."""

    name: str = "get_entities"
    description: str = "List all entities in memory with optional filtering by scope, project, or memory type."
    args_schema: Type[BaseModel] = GetEntitiesInput
    _mcp_tool_name: str = "list_entities"

    async def _arun(self, scope: str = "", project: str = "", memory_type: str = "") -> str:
        args: dict[str, Any] = {}
        if scope:
            args["scope"] = scope
        if project:
            args["project"] = project
        if memory_type:
            args["memory_type"] = memory_type
        return await self._call_mcp(args)


class SearchEntitiesTool(_MemoryToolBase):
    """Fuzzy search for entity names."""

    name: str = "search_entities"
    description: str = "Search for entities by name. Use before storing to avoid creating duplicate entities."
    args_schema: Type[BaseModel] = SearchEntitiesInput
    _mcp_tool_name: str = "search_entities"

    async def _arun(self, query: str, limit: int = 5) -> str:
        return await self._call_mcp({"query": query, "limit": limit})


class GetContextTool(_MemoryToolBase):
    """Get environment context info."""

    name: str = "get_context"
    description: str = "Get environment context: current user identity, active project, and metadata."
    args_schema: Type[BaseModel] = EmptyInput
    _mcp_tool_name: str = "get_context_info"

    async def _arun(self) -> str:
        return await self._call_mcp({})


# ---------------------------------------------------------------------------
# Backward-compat aliases (old names → new classes)
# ---------------------------------------------------------------------------
StoreMemoryTool = CreateMemoriesTool
RecallMemoryTool = SearchMemoriesTool
SearchMemoryTool = SearchMemoriesTool
FetchMemoryTool = GetMemoriesTool
DeleteMemoryTool = DeleteMemoriesTool
UpdateMemoryTool = UpdateMemoriesTool
ListEntitiesTool = GetEntitiesTool
GetContextInfoTool = GetContextTool

# Old input schema aliases
StoreMemoryInput = CreateMemoriesInput
RecallInput = SearchMemoriesInput
SearchMemoryInput = SearchMemoriesInput
FetchMemoryInput = GetMemoriesInput
DeleteMemoryInput = DeleteMemoriesInput
UpdateMemoryInput = UpdateMemoriesInput
ListEntitiesInput = GetEntitiesInput
