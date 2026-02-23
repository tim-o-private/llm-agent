"""Memory tools backed by min-memory MCP server."""

import logging
from typing import Any, Type

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# --- Input schemas ---

class StoreMemoryInput(BaseModel):
    """Input schema for StoreMemoryTool."""

    text: str = Field(..., description="The memory text to store.")
    memory_type: str = Field(
        ...,
        description="Type of memory: core_identity, project_context, task_instruction, or episodic.",
    )
    entity: str = Field(..., description="The entity this memory is about (e.g., user name, project name).")
    scope: str = Field(..., description="Scope: global, project, or task.")
    tags: list[str] = Field(default_factory=list, description="Optional tags for categorization.")


class RecallMemoryInput(BaseModel):
    """Input schema for RecallMemoryTool."""

    query: str = Field(..., description="What to recall — describe what you're looking for.")
    limit: int = Field(default=10, description="Max number of memories to return.")
    memory_type: list[str] = Field(default_factory=list, description="Filter by memory types.")


class SearchMemoryInput(BaseModel):
    """Input schema for SearchMemoryTool."""

    query: str = Field(..., description="Search query to find relevant memories.")


# --- Tools ---

class StoreMemoryTool(BaseTool):
    """Store a memory observation about the user."""

    name: str = "store_memory"
    description: str = (
        "Store a memory about the user. Use this proactively when you learn something "
        "about the user — preferences, habits, projects, important dates, or communication style. "
        "Don't wait to be asked."
    )
    args_schema: Type[BaseModel] = StoreMemoryInput

    memory_client: Any = Field(..., description="MemoryClient instance")
    user_id: str = Field(..., description="User ID for logging")
    agent_name: str = Field(..., description="Agent name for logging")

    @classmethod
    def prompt_section(cls, channel: str) -> str | None:
        """Return behavioral guidance for the agent prompt, or None to omit."""
        if channel in ("web", "telegram"):
            return (
                "Memory: Proactively observe and record. When you learn something about the user "
                "— from their messages, email patterns, task habits, or tone — call store_memory. "
                "Don't wait to be asked. Use recall before answering questions about the user's "
                "preferences, past decisions, or projects."
            )
        return None

    def _run(self, **kwargs: Any) -> str:
        return "store_memory requires async execution."

    async def _arun(self, text: str, memory_type: str, entity: str, scope: str, tags: list[str] | None = None) -> str:
        args: dict[str, Any] = {
            "text": text,
            "memory_type": memory_type,
            "entity": entity,
            "scope": scope,
        }
        if tags:
            args["tags"] = tags

        try:
            result = await self.memory_client.call_tool("store_memory", args)
            logger.info("Stored memory for user=%s, agent=%s", self.user_id, self.agent_name)
            return f"Memory stored. {result.get('message', '')}"
        except Exception as e:
            logger.error("Failed to store memory for user=%s, agent=%s: %s", self.user_id, self.agent_name, e)
            return f"Failed to store memory: {e}"


class RecallMemoryTool(BaseTool):
    """Recall memories relevant to a query."""

    name: str = "recall"
    description: str = (
        "Recall memories about the user relevant to a query. Use this before answering questions "
        "about the user's preferences, past decisions, projects, or anything previously discussed."
    )
    args_schema: Type[BaseModel] = RecallMemoryInput

    memory_client: Any = Field(..., description="MemoryClient instance")
    user_id: str = Field(..., description="User ID for logging")
    agent_name: str = Field(..., description="Agent name for logging")

    @classmethod
    def prompt_section(cls, channel: str) -> str | None:
        return None

    def _run(self, **kwargs: Any) -> str:
        return "recall requires async execution."

    async def _arun(self, query: str, limit: int = 10, memory_type: list[str] | None = None) -> str:
        args: dict[str, Any] = {"query": query, "limit": limit}
        if memory_type:
            args["memory_type"] = memory_type

        try:
            result = await self.memory_client.call_tool("retrieve_context", args)
            logger.info("Recalled memories for user=%s, agent=%s", self.user_id, self.agent_name)
            return str(result)
        except Exception as e:
            logger.error("Failed to recall memories for user=%s, agent=%s: %s", self.user_id, self.agent_name, e)
            return f"Failed to recall memories: {e}"


class SearchMemoryTool(BaseTool):
    """Search for specific memories by keyword."""

    name: str = "search_memory"
    description: str = (
        "Search for memories matching a query. Returns matching memories ranked by relevance."
    )
    args_schema: Type[BaseModel] = SearchMemoryInput

    memory_client: Any = Field(..., description="MemoryClient instance")
    user_id: str = Field(..., description="User ID for logging")
    agent_name: str = Field(..., description="Agent name for logging")

    @classmethod
    def prompt_section(cls, channel: str) -> str | None:
        return None

    def _run(self, **kwargs: Any) -> str:
        return "search_memory requires async execution."

    async def _arun(self, query: str) -> str:
        try:
            result = await self.memory_client.call_tool("search", {"query": query})
            logger.info("Searched memories for user=%s, agent=%s", self.user_id, self.agent_name)
            return str(result)
        except Exception as e:
            logger.error("Failed to search memories for user=%s, agent=%s: %s", self.user_id, self.agent_name, e)
            return f"Failed to search memories: {e}"
