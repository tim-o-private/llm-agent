"""Memory tools for agent long-term memory persistence."""

import logging
import os
from typing import Type

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from supabase import Client as SupabaseClient
from supabase import create_client

logger = logging.getLogger(__name__)

MAX_NOTES_LENGTH = 4000


class SaveMemoryInput(BaseModel):
    """Input schema for SaveMemoryTool."""

    notes: str = Field(
        ...,
        description="The memory notes to save. These replace any existing notes for this agent.",
    )


class SaveMemoryTool(BaseTool):
    """Save or update long-term memory notes for this user and agent."""

    name: str = "save_memory"
    description: str = (
        "Save or update your long-term memory notes. "
        "Use this to remember important information about the user across sessions, "
        "such as preferences, ongoing projects, key dates, or anything the user asks you to remember. "
        "Notes are scoped to this user and agent — other agents cannot see them. "
        "Maximum 4000 characters."
    )
    args_schema: Type[BaseModel] = SaveMemoryInput

    user_id: str = Field(..., description="User ID for scoping")
    agent_name: str = Field(..., description="Agent name for scoping")
    supabase_url: str = Field(default="", description="Supabase URL")
    supabase_key: str = Field(default="", description="Supabase service key")

    def _get_client(self) -> SupabaseClient:
        url = self.supabase_url or os.getenv("SUPABASE_URL", "")
        key = self.supabase_key or os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
        if not url or not key:
            raise RuntimeError("Supabase configuration missing for memory tool.")
        return create_client(url, key)

    def _run(self, notes: str) -> str:
        """Synchronous run — not used in async context."""
        return "save_memory requires async execution. Use _arun."

    async def _arun(self, notes: str) -> str:
        """Save or update long-term memory notes."""
        truncated = False
        if len(notes) > MAX_NOTES_LENGTH:
            notes = notes[:MAX_NOTES_LENGTH]
            truncated = True
            logger.warning(
                f"Memory notes for user={self.user_id}, agent={self.agent_name} "
                f"truncated to {MAX_NOTES_LENGTH} characters."
            )

        try:
            client = self._get_client()
            client.table("agent_long_term_memory").upsert(
                {
                    "user_id": self.user_id,
                    "agent_name": self.agent_name,
                    "notes": notes,
                },
                on_conflict="user_id,agent_name",
            ).execute()

            msg = "Memory notes saved successfully."
            if truncated:
                msg += f" (Note: truncated to {MAX_NOTES_LENGTH} characters.)"
            logger.info(f"Saved memory notes for user={self.user_id}, agent={self.agent_name}")
            return msg

        except Exception as e:
            logger.error(f"Failed to save memory notes for user={self.user_id}, agent={self.agent_name}: {e}")
            return f"Failed to save memory notes: {e}"


class ReadMemoryTool(BaseTool):
    """Read long-term memory notes for this user and agent."""

    name: str = "read_memory"
    description: str = (
        "Read your long-term memory notes for this user. "
        "Returns any previously saved notes about the user's preferences, ongoing projects, "
        "key dates, or other information you were asked to remember. "
        "Notes are scoped to this user and agent."
    )

    user_id: str = Field(..., description="User ID for scoping")
    agent_name: str = Field(..., description="Agent name for scoping")
    supabase_url: str = Field(default="", description="Supabase URL")
    supabase_key: str = Field(default="", description="Supabase service key")

    def _get_client(self) -> SupabaseClient:
        url = self.supabase_url or os.getenv("SUPABASE_URL", "")
        key = self.supabase_key or os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
        if not url or not key:
            raise RuntimeError("Supabase configuration missing for memory tool.")
        return create_client(url, key)

    def _run(self) -> str:
        """Synchronous run — not used in async context."""
        return "read_memory requires async execution. Use _arun."

    async def _arun(self) -> str:
        """Read long-term memory notes."""
        try:
            client = self._get_client()
            result = (
                client.table("agent_long_term_memory")
                .select("notes")
                .eq("user_id", self.user_id)
                .eq("agent_name", self.agent_name)
                .maybe_single()
                .execute()
            )

            if result.data and result.data.get("notes"):
                logger.info(f"Read memory notes for user={self.user_id}, agent={self.agent_name}")
                return result.data["notes"]

            logger.info(f"No memory notes found for user={self.user_id}, agent={self.agent_name}")
            return "(No memory notes yet.)"

        except Exception as e:
            logger.error(f"Failed to read memory notes for user={self.user_id}, agent={self.agent_name}: {e}")
            return f"Failed to read memory notes: {e}"
