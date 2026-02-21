"""Tool for the agent to update user-specific standing instructions."""

import logging
import os
from typing import Type

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from supabase import Client as SupabaseClient
from supabase import create_client

logger = logging.getLogger(__name__)

MAX_INSTRUCTIONS_LENGTH = 2000


class UpdateInstructionsInput(BaseModel):
    """Input schema for UpdateInstructionsTool."""

    instructions: str = Field(
        ...,
        description=(
            "The complete updated instructions text. This REPLACES all existing instructions — "
            "include everything you want to keep."
        ),
    )


class UpdateInstructionsTool(BaseTool):
    """Update standing instructions for this user.

    Use when the user says things like 'always summarize emails in bullet points'
    or 'never send emails without asking me first'. This is a REPLACE operation —
    read existing instructions first, then write the full updated text.
    """

    name: str = "update_instructions"
    description: str = (
        "Update your standing instructions for this user. "
        "Use this when the user says things like 'always summarize emails in bullet points' "
        "or 'never send emails without asking me first'. "
        "This is a REPLACE operation — include all existing instructions you want to keep."
    )
    args_schema: Type[BaseModel] = UpdateInstructionsInput

    user_id: str = Field(..., description="User ID for scoping")
    agent_name: str = Field(..., description="Agent name for scoping")
    supabase_url: str = Field(default="", description="Supabase URL")
    supabase_key: str = Field(default="", description="Supabase service key")

    @classmethod
    def prompt_section(cls, channel: str) -> str | None:
        """Return behavioral guidance for the agent prompt, or None to omit."""
        if channel in ("web", "telegram"):
            return "Instructions: When the user says 'always do X' or 'never do Y', use update_instructions to persist the preference. This is a full replace — include existing instructions you want to keep."
        else:
            return None

    def _get_client(self) -> SupabaseClient:
        url = self.supabase_url or os.getenv("SUPABASE_URL", "")
        key = self.supabase_key or os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
        if not url or not key:
            raise RuntimeError("Supabase configuration missing for update_instructions tool.")
        return create_client(url, key)

    def _run(self, instructions: str) -> str:
        """Synchronous run — not used in async context."""
        return "update_instructions requires async execution. Use _arun."

    async def _arun(self, instructions: str) -> str:
        """Upsert user instructions into user_agent_prompt_customizations."""
        truncated = False
        if len(instructions) > MAX_INSTRUCTIONS_LENGTH:
            instructions = instructions[:MAX_INSTRUCTIONS_LENGTH]
            truncated = True
            logger.warning(
                f"Instructions for user={self.user_id}, agent={self.agent_name} "
                f"truncated to {MAX_INSTRUCTIONS_LENGTH} characters."
            )

        try:
            client = self._get_client()
            client.table("user_agent_prompt_customizations").upsert(
                {
                    "user_id": self.user_id,
                    "agent_name": self.agent_name,
                    "instructions": instructions,
                },
                on_conflict="user_id,agent_name",
            ).execute()

            if not instructions:
                msg = "Custom instructions cleared."
            else:
                msg = "Instructions updated successfully."
            if truncated:
                msg += f" (Note: truncated to {MAX_INSTRUCTIONS_LENGTH} characters.)"

            logger.info(f"Updated instructions for user={self.user_id}, agent={self.agent_name}")
            return msg

        except Exception as e:
            logger.error(f"Failed to update instructions for user={self.user_id}, agent={self.agent_name}: {e}")
            return f"Failed to update instructions: {e}"
