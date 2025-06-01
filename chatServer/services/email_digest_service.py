"""Email digest service for generating AI-powered email summaries."""
# @docs memory-bank/patterns/api-patterns.md#pattern-3-service-layer-pattern
# @rules memory-bank/rules/api-rules.json#api-003

import logging
from datetime import datetime
from typing import List, Optional
from supabase import AsyncClient

try:
    from .gmail_service import GmailService
    from ..models.external_api import EmailDigestRequest, EmailDigestResponse, EmailThread
    from ..config.constants import DEFAULT_LOG_LEVEL
except ImportError:
    from chatServer.services.gmail_service import GmailService
    from chatServer.models.external_api import EmailDigestRequest, EmailDigestResponse, EmailThread
    from chatServer.config.constants import DEFAULT_LOG_LEVEL

# Import LLM interface from the existing core
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../../src'))

try:
    from core.llm_interface import LLMInterface
    from utils.config_loader import ConfigLoader
except ImportError:
    # Fallback for when running from different context
    from src.core.llm_interface import LLMInterface
    from src.utils.config_loader import ConfigLoader

logger = logging.getLogger(__name__)


class EmailDigestService:
    """Service for generating AI-powered email digests."""
    
    def __init__(self, db_client: AsyncClient):
        """Initialize email digest service.
        
        Args:
            db_client: Supabase client for database operations
        """
        self.db_client = db_client
        self.gmail_service = GmailService(db_client)
        
        # Initialize LLM interface using existing infrastructure
        try:
            config = ConfigLoader()
            self.llm_interface = LLMInterface(config)
        except Exception as e:
            logger.error(f"Failed to initialize LLM interface: {e}")
            self.llm_interface = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.gmail_service.__aenter__()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.gmail_service.__aexit__(exc_type, exc_val, exc_tb)
    
    def _format_thread_for_summary(self, thread: EmailThread) -> str:
        """Format an email thread for LLM summarization.
        
        Args:
            thread: Email thread to format
            
        Returns:
            Formatted thread text
        """
        formatted = f"Thread: {thread.subject}\n"
        formatted += f"Participants: {', '.join(thread.participants)}\n"
        formatted += f"Messages: {thread.message_count}\n"
        formatted += f"Last message: {thread.last_message_date.strftime('%Y-%m-%d %H:%M')}\n"
        formatted += f"Unread: {'Yes' if thread.is_unread else 'No'}\n\n"
        
        # Add message content (limit to avoid token overflow)
        for i, message in enumerate(thread.messages[-3:]):  # Last 3 messages
            formatted += f"Message {i+1} ({message.date.strftime('%Y-%m-%d %H:%M')}):\n"
            formatted += f"From: {message.sender}\n"
            formatted += f"To: {message.recipient}\n"
            # Truncate long messages
            body = message.body[:500] + "..." if len(message.body) > 500 else message.body
            formatted += f"Content: {body}\n\n"
        
        return formatted
    
    def _create_digest_prompt(self, threads: List[EmailThread], time_period_hours: int) -> str:
        """Create a prompt for email digest generation.
        
        Args:
            threads: List of email threads
            time_period_hours: Time period for the digest
            
        Returns:
            Formatted prompt for LLM
        """
        prompt = f"""You are an AI assistant helping to create an email digest. Please analyze the following email threads from the last {time_period_hours} hours and create a concise, actionable summary.

Focus on:
1. Important emails that require action or response
2. Key information or updates
3. Urgent or time-sensitive matters
4. Overall themes or patterns

Email threads to analyze:

"""
        
        for i, thread in enumerate(threads, 1):
            prompt += f"--- Thread {i} ---\n"
            prompt += self._format_thread_for_summary(thread)
            prompt += "\n"
        
        prompt += """
Please provide:
1. A brief overall summary (2-3 sentences)
2. Action items or emails requiring response (if any)
3. Important information or updates (if any)
4. Any urgent or time-sensitive matters (if any)

Keep the summary concise but informative. Focus on what the user needs to know and do."""
        
        return prompt
    
    async def _generate_summary_with_llm(self, threads: List[EmailThread], time_period_hours: int) -> str:
        """Generate email summary using LLM.
        
        Args:
            threads: List of email threads
            time_period_hours: Time period for the digest
            
        Returns:
            Generated summary text
        """
        if not self.llm_interface:
            logger.error("LLM interface not available")
            return self._generate_fallback_summary(threads, time_period_hours)
        
        try:
            prompt = self._create_digest_prompt(threads, time_period_hours)
            
            # Use the existing LLM interface
            response = await self.llm_interface.llm.ainvoke(prompt)
            
            if hasattr(response, 'content'):
                return response.content
            else:
                return str(response)
                
        except Exception as e:
            logger.error(f"Error generating LLM summary: {e}")
            return self._generate_fallback_summary(threads, time_period_hours)
    
    def _generate_fallback_summary(self, threads: List[EmailThread], time_period_hours: int) -> str:
        """Generate a fallback summary when LLM is not available.
        
        Args:
            threads: List of email threads
            time_period_hours: Time period for the digest
            
        Returns:
            Fallback summary text
        """
        if not threads:
            return f"No emails received in the last {time_period_hours} hours."
        
        unread_count = sum(1 for thread in threads if thread.is_unread)
        
        summary = f"Email Digest - Last {time_period_hours} hours:\n\n"
        summary += f"Total threads: {len(threads)}\n"
        summary += f"Unread threads: {unread_count}\n\n"
        
        if unread_count > 0:
            summary += "Unread threads:\n"
            for thread in threads:
                if thread.is_unread:
                    summary += f"- {thread.subject} ({thread.message_count} messages)\n"
                    summary += f"  From: {', '.join(thread.participants)}\n"
                    summary += f"  Last: {thread.last_message_date.strftime('%Y-%m-%d %H:%M')}\n\n"
        
        return summary
    
    def _identify_important_threads(self, threads: List[EmailThread]) -> List[EmailThread]:
        """Identify important threads based on simple heuristics.
        
        Args:
            threads: List of email threads
            
        Returns:
            List of important threads
        """
        important_threads = []
        
        # Keywords that might indicate importance
        important_keywords = [
            'urgent', 'asap', 'important', 'deadline', 'meeting', 'call',
            'action required', 'please respond', 'time sensitive', 'priority'
        ]
        
        for thread in threads:
            # Unread threads are potentially important
            if thread.is_unread:
                important_threads.append(thread)
                continue
            
            # Check for important keywords in subject
            subject_lower = thread.subject.lower()
            if any(keyword in subject_lower for keyword in important_keywords):
                important_threads.append(thread)
                continue
            
            # Threads with multiple recent messages might be important
            if thread.message_count > 2:
                important_threads.append(thread)
        
        # Limit to top 10 most important
        return important_threads[:10]
    
    async def generate_digest(self, user_id: str, request: EmailDigestRequest) -> Optional[EmailDigestResponse]:
        """Generate an email digest for a user.
        
        Args:
            user_id: User ID
            request: Email digest request parameters
            
        Returns:
            Email digest response or None if failed
        """
        try:
            # Check if user has Gmail connection
            connection = await self.gmail_service.get_connection(user_id)
            if not connection:
                logger.error(f"No Gmail connection found for user {user_id}")
                return None
            
            # Get email threads
            threads = await self.gmail_service.get_email_threads(user_id, request)
            
            if not threads:
                # Return empty digest
                return EmailDigestResponse(
                    summary=f"No emails found in the last {request.hours_back} hours.",
                    thread_count=0,
                    unread_count=0,
                    important_threads=[],
                    generated_at=datetime.now(),
                    time_period_hours=request.hours_back
                )
            
            # Identify important threads
            important_threads = self._identify_important_threads(threads)
            
            # Generate AI summary
            summary = await self._generate_summary_with_llm(threads, request.hours_back)
            
            # Count unread threads
            unread_count = sum(1 for thread in threads if thread.is_unread)
            
            return EmailDigestResponse(
                summary=summary,
                thread_count=len(threads),
                unread_count=unread_count,
                important_threads=important_threads,
                generated_at=datetime.now(),
                time_period_hours=request.hours_back
            )
            
        except Exception as e:
            logger.error(f"Error generating email digest for user {user_id}: {e}")
            return None
    
    async def test_gmail_connection(self, user_id: str) -> bool:
        """Test Gmail connection for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            True if connection is working, False otherwise
        """
        return await self.gmail_service.test_connection(user_id) 