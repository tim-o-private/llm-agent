"""Unified Email Digest Service for both scheduled and on-demand execution."""

import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from chatServer.services.email_digest_storage_service import get_email_digest_storage_service
from src.core.agent_loader_db import load_agent_executor_db
from supabase import Client as SupabaseClient
from supabase import create_client

logger = logging.getLogger(__name__)


class EmailDigestService:
    """Unified service for email digest generation - used by both scheduled tasks and tools."""

    def __init__(self, user_id: str, context: str = "on-demand"):
        """Initialize the email digest service.

        Args:
            user_id: User ID for scoping
            context: Execution context - "on-demand" for assistant agent, "scheduled" for background tasks
        """
        self.user_id = user_id
        self.context = context
        self.storage_service = get_email_digest_storage_service()

    async def generate_digest(
        self,
        hours_back: int = 24,
        include_read: bool = False,
        custom_prompt: Optional[str] = None,
        store_result: bool = True
    ) -> Dict[str, Any]:
        """
        Unified entry point for email digest generation.
        Used by both BackgroundTaskService and EmailDigestTool.

        Args:
            hours_back: Hours to look back for emails
            include_read: Whether to include read emails
            custom_prompt: Optional custom prompt to override default
            store_result: Whether to store the result in database (default: True)

        Returns:
            Dict with success status, digest content, and metadata
        """
        generated_at = datetime.now(timezone.utc)

        try:
            logger.info(f"Generating email digest for user {self.user_id} (context: {self.context}, hours_back: {hours_back})")

            # Load the email_digest_agent from database
            # This automatically loads the agent's system prompt and Gmail tools
            try:
                agent_executor = load_agent_executor_db(
                    agent_name="email_digest_agent",
                    user_id=self.user_id,
                    session_id=f"email_digest_{self.context}_{generated_at.strftime('%Y%m%d_%H%M%S')}"
                )

                logger.info(f"Successfully loaded email_digest_agent for user {self.user_id}")

            except Exception as e:
                logger.error(f"Failed to load email_digest_agent for user {self.user_id}: {e}")
                raise RuntimeError(f"Could not load email digest agent: {e}")

            # Create prompt for the agent
            if custom_prompt:
                prompt = custom_prompt
            else:
                read_filter = "including read emails" if include_read else "only unread emails"
                prompt = (
                    f"Please generate an email digest for the last {hours_back} hours, "
                    f"{read_filter}. Use your Gmail tools to search for recent emails and "
                    f"create a comprehensive summary. Focus on actionable items and important communications."
                )

            # Load LTM and prepend to prompt for context-aware prioritization (AC-5, AC-8)
            ltm_notes = await self._load_ltm(self.user_id, "email_digest_agent")
            if ltm_notes:
                prompt = f"User context (from memory):\n{ltm_notes}\n\n{prompt}"
                logger.info(f"Prepended LTM ({len(ltm_notes)} chars) to digest prompt")

            logger.info(f"Invoking email_digest_agent with prompt: {prompt[:100]}...")

            # Invoke the agent - it will use its Gmail tools to generate the digest
            result = await agent_executor.ainvoke({
                "input": prompt,
                "chat_history": []  # Fresh context for digest generation
            })

            # Extract the digest content from agent response
            digest_content = result.get("output", "")

            if not digest_content:
                logger.warning(f"email_digest_agent returned empty response for user {self.user_id}")
                digest_content = "No email digest could be generated at this time."

            # Extract email count from digest content if possible
            email_count = self._extract_email_count(digest_content)

            # Prepare result data
            result_data = {
                "success": True,
                "digest": digest_content,
                "generated_at": generated_at.isoformat(),
                "hours_back": hours_back,
                "include_read": include_read,
                "context": self.context,
                "email_count": email_count
            }

            # Store result if requested
            if store_result:
                storage_success = await self._store_digest_result({
                    "user_id": self.user_id,
                    "generated_at": generated_at,
                    "hours_back": hours_back,
                    "include_read": include_read,
                    "digest_content": digest_content,
                    "status": "success",
                    "context": self.context,
                    "email_count": email_count
                })

                if not storage_success:
                    logger.warning(f"Failed to store digest result for user {self.user_id}, but digest generation succeeded")

            logger.info(f"Successfully generated email digest for user {self.user_id} (context: {self.context})")
            return result_data

        except Exception as e:
            logger.error(f"Email digest generation failed for user {self.user_id}: {e}", exc_info=True)

            error_message = f"Failed to generate email digest: {str(e)}"

            # Prepare error result data
            error_result = {
                "success": False,
                "error": str(e),
                "digest": error_message,
                "generated_at": generated_at.isoformat(),
                "context": self.context,
                "hours_back": hours_back,
                "include_read": include_read
            }

            # Store error result if requested
            if store_result:
                await self._store_digest_result({
                    "user_id": self.user_id,
                    "generated_at": generated_at,
                    "hours_back": hours_back,
                    "include_read": include_read,
                    "digest_content": error_message,
                    "status": "error",
                    "context": self.context,
                    "email_count": None
                })

            return error_result

    async def _load_ltm(self, user_id: str, agent_name: str) -> Optional[str]:
        """Load long-term memory notes for user+agent from the database."""
        try:
            url = os.getenv("VITE_SUPABASE_URL", "")
            key = os.getenv("SUPABASE_SERVICE_KEY", "")
            if not url or not key:
                return None

            db: SupabaseClient = create_client(url, key)
            result = (
                db.table("agent_long_term_memory")
                .select("notes")
                .eq("user_id", user_id)
                .eq("agent_id", agent_name)
                .maybe_single()
                .execute()
            )
            if result.data and result.data.get("notes"):
                return result.data["notes"]
            return None
        except Exception as e:
            logger.warning(f"Failed to load LTM for {user_id}/{agent_name}: {e}")
            return None

    def _extract_email_count(self, digest_content: str) -> Optional[int]:
        """Extract email count from digest content if possible."""
        try:
            # Look for patterns like "20 unread emails found" or "Summary: 15 emails"
            import re

            patterns = [
                r'(\d+)\s+(?:unread\s+)?emails?\s+found',
                r'Summary:\s*(\d+)\s+(?:unread\s+)?emails?',
                r'(\d+)\s+(?:read\s+and\s+unread\s+)?emails?\s+found',
                r'total\s+of\s+(\d+)\s+(?:unread\s+)?emails?'
            ]

            for pattern in patterns:
                match = re.search(pattern, digest_content, re.IGNORECASE)
                if match:
                    count = int(match.group(1))
                    logger.debug(f"Extracted email count {count} from digest content")
                    return count

            logger.debug("Could not extract email count from digest content")
            return None

        except Exception as e:
            logger.warning(f"Failed to extract email count from digest: {e}")
            return None

    async def _store_digest_result(self, digest_data: Dict[str, Any]) -> bool:
        """Store digest result using the dedicated storage service."""
        try:
            return await self.storage_service.store_digest(digest_data)
        except Exception as e:
            logger.error(f"Failed to store digest result for user {digest_data.get('user_id', 'unknown')}: {e}")
            return False

    async def get_recent_digests(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent digests for this user."""
        try:
            return await self.storage_service.get_recent_digests(self.user_id, limit)
        except Exception as e:
            logger.error(f"Failed to get recent digests for user {self.user_id}: {e}")
            return []

    async def get_digest_stats(self) -> Dict[str, Any]:
        """Get digest statistics for this user."""
        try:
            return await self.storage_service.get_digest_stats(self.user_id)
        except Exception as e:
            logger.error(f"Failed to get digest stats for user {self.user_id}: {e}")
            return {}


# Factory function for creating service instances
def create_email_digest_service(user_id: str, context: str = "on-demand") -> EmailDigestService:
    """Create an EmailDigestService instance.

    Args:
        user_id: User ID for scoping
        context: Execution context - "scheduled" for background tasks, "on-demand" for user requests

    Returns:
        EmailDigestService instance
    """
    return EmailDigestService(user_id, context)
