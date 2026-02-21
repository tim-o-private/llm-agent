"""Email Digest Agent using existing agent framework."""
# @docs memory-bank/patterns/agent-patterns.md#pattern-5-agent-configuration-pattern
# @rules memory-bank/rules/agent-rules.json#agent-003

# DEPRECATION NOTICE:
# This file is largely redundant with the database-driven agent system.
# The email_digest_agent is now configured in the agent_configurations table
# with tools assigned via the agent_tools table. The EmailDigestService
# uses load_agent_executor_db() to get the properly configured agent.
#
# This class is kept for backward compatibility and testing purposes only.

import logging
from datetime import datetime
from typing import Any, Dict, Optional

from ..services.email_digest_service import EmailDigestService

logger = logging.getLogger(__name__)


class EmailDigestAgent:
    """DEPRECATED: Agent specialized for email digest generation and management.

    This class is deprecated in favor of the database-driven agent system.
    Use EmailDigestService directly which loads the email_digest_agent from the database.
    """

    def __init__(self, user_id: str, session_id: str, config_loader: Optional[Any] = None):
        """Initialize Email Digest Agent.

        Args:
            user_id: User ID for scoping
            session_id: Session ID for memory
            config_loader: Optional config loader instance (deprecated)
        """
        self.user_id = user_id
        self.session_id = session_id
        self.agent_name = "email_digest_agent"

        logger.warning(
            "EmailDigestAgent is deprecated. Use EmailDigestService directly. "
            "The email_digest_agent is now configured in the database."
        )

    async def generate_digest(self, hours_back: int = 24, max_threads: int = 20, include_read: bool = False) -> str:
        """Generate email digest using the EmailDigestService.

        DEPRECATED: Use EmailDigestService directly.

        Args:
            hours_back: Hours to look back for emails
            max_threads: Maximum number of threads to analyze (ignored, for compatibility)
            include_read: Whether to include read emails

        Returns:
            Email digest summary
        """
        logger.warning("EmailDigestAgent.generate_digest() is deprecated. Use EmailDigestService directly.")

        try:
            # Delegate to EmailDigestService
            service = EmailDigestService(self.user_id, context="on-demand")
            result = await service.generate_digest(
                hours_back=hours_back,
                include_read=include_read
            )

            if result.get("success"):
                return result["digest"]
            else:
                return result["digest"]  # Contains error message

        except Exception as e:
            logger.error(f"Error generating email digest: {e}")
            return f"Failed to generate email digest: {e}"

    async def search_emails(self, query: str, max_results: int = 20) -> str:
        """Search emails using the EmailDigestService.

        DEPRECATED: Use EmailDigestService with custom prompt.

        Args:
            query: Gmail search query
            max_results: Maximum number of results

        Returns:
            Search results summary
        """
        logger.warning("EmailDigestAgent.search_emails() is deprecated. Use EmailDigestService with custom prompt.")

        try:
            # Delegate to EmailDigestService with custom prompt
            service = EmailDigestService(self.user_id, context="on-demand")
            custom_prompt = f"Search my Gmail for: {query}. Show up to {max_results} results. Provide a clear summary of the search results."  # noqa: E501

            result = await service.generate_digest(
                hours_back=168,  # Search last week by default
                include_read=True,  # Include read emails for search
                custom_prompt=custom_prompt
            )

            if result.get("success"):
                return result["digest"]
            else:
                return result["digest"]  # Contains error message

        except Exception as e:
            logger.error(f"Error searching emails: {e}")
            return f"Failed to search emails: {e}"

    def get_agent_info(self) -> Dict[str, Any]:
        """Get information about the agent."""
        return {
            "agent_name": self.agent_name,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "status": "deprecated",
            "message": "This class is deprecated. Use EmailDigestService with database-driven email_digest_agent."
        }


async def create_email_digest_agent(user_id: str, session_id: str = None) -> EmailDigestAgent:
    """DEPRECATED: Factory function to create an email digest agent.

    Use EmailDigestService directly instead.

    Args:
        user_id: User ID for context
        session_id: Session ID for memory (optional, will generate if not provided)

    Returns:
        Deprecated EmailDigestAgent instance
    """
    logger.warning("create_email_digest_agent() is deprecated. Use EmailDigestService directly.")

    if not session_id:
        session_id = f"email_digest_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    return EmailDigestAgent(user_id, session_id)
