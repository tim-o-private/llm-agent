"""Email Digest Tool for assistant agent integration."""

import logging
from typing import Optional, Type

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class EmailDigestInput(BaseModel):
    """Input schema for email digest tool."""
    hours_back: int = Field(
        default=24,
        ge=1,
        le=168,
        description="Hours to look back for emails (1-168 hours, default 24)"
    )
    include_read: bool = Field(
        default=False,
        description="Whether to include read emails in the digest (default False)"
    )


class EmailDigestTool(BaseTool):
    """Tool that calls the unified EmailDigestService for on-demand email digest generation."""

    name: str = "email_digest"
    description: str = (
        "Generate a digest of recent emails from Gmail. "
        "Use this when the user asks about emails, inbox summary, recent messages, or email digest. "
        "Provides a summary of email subjects, senders, and counts from the specified time period."
    )
    args_schema: Type[BaseModel] = EmailDigestInput

    # User context for scoping
    user_id: str
    # Optional parameters provided by agent loader (not used by this tool)
    agent_name: Optional[str] = None
    supabase_url: Optional[str] = None
    supabase_key: Optional[str] = None

    @classmethod
    def prompt_section(cls, channel: str) -> str | None:
        """Return behavioral guidance for the agent prompt, or None to omit."""
        if channel in ("web", "telegram"):
            return "Email Digest: Use email_digest for comprehensive email summaries. Prefer this over manual gmail_search when the user wants an overview of recent email activity."  # noqa: E501
        elif channel == "scheduled":
            return "Email Digest: Generate the digest using email_digest. Include the full summary in your response for notification delivery."  # noqa: E501
        else:
            return None

    def __init__(self, user_id: str, agent_name: Optional[str] = None,
                 supabase_url: Optional[str] = None, supabase_key: Optional[str] = None, **kwargs):
        """Initialize email digest tool.

        Args:
            user_id: User ID for scoping
            agent_name: Agent name (provided by loader, not used)
            supabase_url: Supabase URL (provided by loader, not used)
            supabase_key: Supabase key (provided by loader, not used)
            **kwargs: Additional tool configuration
        """
        super().__init__(user_id=user_id, agent_name=agent_name,
                        supabase_url=supabase_url, supabase_key=supabase_key, **kwargs)

    def _run(self, hours_back: int = 24, include_read: bool = False) -> str:
        """Synchronous run method (not used in async context)."""
        return (
            f"Email digest tool requires async execution. "
            f"Parameters: hours_back={hours_back}, include_read={include_read}. "
            f"Please use the async version (_arun) for proper execution."
        )

    async def _arun(self, hours_back: int = 24, include_read: bool = False) -> str:
        """Generate email digest by calling unified service.

        Args:
            hours_back: Hours to look back for emails (1-168)
            include_read: Whether to include read emails

        Returns:
            Email digest summary as formatted string
        """
        try:
            logger.info(f"Generating email digest for user {self.user_id}: {hours_back}h back, include_read={include_read}")  # noqa: E501

            # Lazy import to avoid circular dependency
            from ..services.email_digest_service import EmailDigestService

            # Create EmailDigestService for on-demand execution
            service = EmailDigestService(self.user_id, context="on-demand")

            # Generate digest using unified service
            # Note: context is already set in service constructor, don't pass it again
            result = await service.generate_digest(
                hours_back=hours_back,
                include_read=include_read
            )

            # Return the digest content
            if result.get("success"):
                logger.info(f"Successfully generated email digest for user {self.user_id}")
                return result["digest"]
            else:
                logger.error(f"Email digest generation failed for user {self.user_id}: {result.get('error')}")
                return result["digest"]  # Contains error message

        except Exception as e:
            logger.error(f"Email digest tool execution failed for user {self.user_id}: {e}")
            return f"⚠️ Failed to generate email digest: {e}"


# Factory function for creating tool instances
def create_email_digest_tool(user_id: str, **kwargs) -> EmailDigestTool:
    """Create an EmailDigestTool instance.

    Args:
        user_id: User ID for scoping
        **kwargs: Additional tool configuration

    Returns:
        EmailDigestTool instance
    """
    return EmailDigestTool(user_id=user_id, **kwargs)
