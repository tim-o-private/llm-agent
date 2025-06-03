"""Unified Email Digest Service for both scheduled and on-demand execution."""

import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from src.core.agent_loader_db import load_agent_executor_db
from chatServer.database.connection import get_database_manager

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
    
    async def generate_digest(
        self, 
        hours_back: int = 24, 
        include_read: bool = False,
        custom_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Unified entry point for email digest generation.
        Used by both BackgroundTaskService and EmailDigestTool.
        
        Args:
            hours_back: Hours to look back for emails
            include_read: Whether to include read emails
            custom_prompt: Optional custom prompt to override default
            
        Returns:
            Dict with success status, digest content, and metadata
        """
        try:
            logger.info(f"Generating email digest for user {self.user_id} (context: {self.context}, hours_back: {hours_back})")
            
            # Load the email_digest_agent from database
            # This automatically loads the agent's system prompt and Gmail tools
            try:
                agent_executor = load_agent_executor_db(
                    agent_name="email_digest_agent",
                    user_id=self.user_id,
                    session_id=f"email_digest_{self.context}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
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
            
            # Store result for scheduled digests
            if self.context == "scheduled":
                await self._store_digest_result({
                    "user_id": self.user_id,
                    "generated_at": datetime.now(timezone.utc),
                    "hours_back": hours_back,
                    "include_read": include_read,
                    "digest_content": digest_content,
                    "status": "success"
                })
            
            logger.info(f"Successfully generated email digest for user {self.user_id} (context: {self.context})")
            
            return {
                "success": True,
                "digest": digest_content,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "hours_back": hours_back,
                "include_read": include_read,
                "context": self.context
            }
            
        except Exception as e:
            logger.error(f"Email digest generation failed for user {self.user_id}: {e}", exc_info=True)
            
            error_message = f"Failed to generate email digest: {str(e)}"
            
            # Store error result for scheduled digests
            if self.context == "scheduled":
                await self._store_digest_result({
                    "user_id": self.user_id,
                    "generated_at": datetime.now(timezone.utc),
                    "hours_back": hours_back,
                    "include_read": include_read,
                    "digest_content": error_message,
                    "status": "error"
                })
            
            return {
                "success": False,
                "error": str(e),
                "digest": error_message,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "context": self.context
            }
    
    async def _store_digest_result(self, digest_data: Dict[str, Any]) -> None:
        """Store digest result in the email_digests table for scheduled executions."""
        try:
            db_manager = get_database_manager()
            async with db_manager.pool.connection() as conn:
                async with conn.cursor() as cur:
                    await cur.execute("""
                        INSERT INTO email_digests 
                        (user_id, generated_at, hours_back, include_read, digest_content, status)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """, (
                        digest_data["user_id"],
                        digest_data["generated_at"],
                        digest_data["hours_back"],
                        digest_data["include_read"],
                        digest_data["digest_content"],
                        digest_data["status"]
                    ))
                    
            logger.info(f"Stored digest result for user {digest_data['user_id']} with status {digest_data['status']}")
            
        except Exception as e:
            logger.error(f"Failed to store digest result for user {digest_data['user_id']}: {e}")
            # Don't re-raise - storage failure shouldn't break digest generation


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