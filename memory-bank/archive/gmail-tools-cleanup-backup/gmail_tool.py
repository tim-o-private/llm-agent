"""Gmail Tool for accessing Gmail API through OAuth tokens stored in Vault."""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import json

from langchain.tools import BaseTool
from pydantic import BaseModel, Field

try:
    from ..services.vault_token_service import VaultTokenService
    from ..services.gmail_service import GmailService
    from ..services.email_digest_service import EmailDigestService
    from ..database.connection import get_db_connection
except ImportError:
    from chatServer.services.vault_token_service import VaultTokenService
    from chatServer.services.gmail_service import GmailService
    from chatServer.services.email_digest_service import EmailDigestService
    from chatServer.database.connection import get_db_connection

logger = logging.getLogger(__name__)


class GmailSearchInput(BaseModel):
    """Input for Gmail search operation."""
    query: str = Field(description="Gmail search query (e.g., is:unread, newer_than:1d)")
    max_results: int = Field(default=20, description="Maximum number of emails to return")


class GmailGetMessageInput(BaseModel):
    """Input for Gmail get message operation."""
    message_id: str = Field(description="Gmail message ID to retrieve")


class GmailDigestInput(BaseModel):
    """Input for Gmail digest generation."""
    hours_back: int = Field(default=24, description="Hours to look back for emails")
    include_read: bool = Field(default=False, description="Whether to include read emails")


class GmailTool(BaseTool):
    """Gmail tool for accessing Gmail API with OAuth tokens from Vault."""
    
    name: str = "gmail_tool"
    description: str = "Access Gmail API for searching, reading, and generating email digests"
    
    # Tool configuration from database - compatible with existing agent loading system
    # Making all fields optional with defaults to work with the agent loader
    operation: Optional[str] = Field(default="search", description="Gmail operation to perform")
    user_id: Optional[str] = Field(default=None, description="User ID for OAuth token retrieval")
    agent_name: Optional[str] = Field(default=None, description="Agent name for context")
    supabase_url: Optional[str] = Field(default=None, description="Supabase URL")
    supabase_key: Optional[str] = Field(default=None, description="Supabase key")
    
    def __init__(self, operation: str = None, user_id: str = None, agent_name: str = None, 
                 supabase_url: str = None, supabase_key: str = None, 
                 name: str = None, description: str = None, **kwargs):
        """Initialize Gmail tool with operation and user context.
        
        Args:
            operation: Gmail operation to perform (from config)
            user_id: User ID for OAuth token retrieval
            agent_name: Agent name for context
            supabase_url: Supabase URL
            supabase_key: Supabase key
            name: Tool name (from database)
            description: Tool description (from database)
            **kwargs: Additional config parameters from database
        """
        # Extract operation from kwargs if not provided directly
        operation = operation or kwargs.get('operation', 'search')
        
        # Use provided name/description or defaults
        tool_name = name or f"gmail_{operation}"
        tool_description = description or f"Gmail {operation} operation"
        
        # Initialize the parent BaseTool first
        super().__init__(name=tool_name, description=tool_description, **kwargs)
        
        # Set instance attributes after parent initialization
        self.operation = operation
        self.user_id = user_id
        self.agent_name = agent_name
        self.supabase_url = supabase_url
        self.supabase_key = supabase_key
    
    async def _get_gmail_service(self) -> GmailService:
        """Get Gmail service with user's OAuth tokens."""
        try:
            # Get database connection for vault token service
            async for db_conn in get_db_connection():
                # Get vault token service
                vault_service = VaultTokenService(db_conn, context="user")
                
                # Get user's Gmail tokens
                access_token, refresh_token = await vault_service.get_tokens(
                    self.user_id, 'gmail'
                )
                
                # Create Gmail service
                gmail_service = GmailService()
                
                # Set tokens (this would need to be implemented in GmailService)
                gmail_service.set_user_tokens(self.user_id, access_token, refresh_token)
                
                return gmail_service
                
        except Exception as e:
            logger.error(f"Failed to get Gmail service for user {self.user_id}: {e}")
            raise Exception(f"Gmail authentication failed: {e}")
    
    def _run(self, **kwargs) -> str:
        """Synchronous run method (not implemented for async tool)."""
        raise NotImplementedError("Use async version _arun")
    
    async def _arun(self, **kwargs) -> str:
        """Execute Gmail operation asynchronously."""
        try:
            logger.info(f"Executing Gmail operation '{self.operation}' for user {self.user_id}")
            
            if self.operation == "search":
                # Extract search parameters
                query = kwargs.get('query', 'is:unread')
                max_results = kwargs.get('max_results', 20)
                return await self._search_emails(query=query, max_results=max_results)
                
            elif self.operation == "get_message":
                # Extract message ID
                message_id = kwargs.get('message_id')
                if not message_id:
                    return "Error: message_id is required for get_message operation"
                return await self._get_message(message_id=message_id)
                
            elif self.operation == "generate_digest":
                # Extract digest parameters - handle various parameter names the LLM might use
                hours_back = kwargs.get('hours_back', kwargs.get('time_period', 24))
                include_read = kwargs.get('include_read', not kwargs.get('exclude_read', True))
                
                # Handle string time periods like "last 24 hours"
                if isinstance(hours_back, str):
                    if "24" in hours_back or "day" in hours_back.lower():
                        hours_back = 24
                    elif "12" in hours_back:
                        hours_back = 12
                    elif "48" in hours_back or "2 day" in hours_back.lower():
                        hours_back = 48
                    else:
                        hours_back = 24  # default
                
                return await self._generate_digest(hours_back=hours_back, include_read=include_read)
                
            else:
                raise ValueError(f"Unknown Gmail operation: {self.operation}")
                
        except Exception as e:
            logger.error(f"Gmail tool operation failed: {e}")
            return f"Error: {str(e)}"
    
    async def _search_emails(self, query: str, max_results: int = 20) -> str:
        """Search Gmail messages."""
        try:
            gmail_service = await self._get_gmail_service()
            
            # Search for messages
            result = await gmail_service.get_messages(
                self.user_id, 
                query=query, 
                max_results=max_results
            )
            
            if not result or 'messages' not in result:
                return "No messages found matching the search criteria."
            
            messages = result['messages']
            
            # Format results
            formatted_results = []
            for msg in messages[:max_results]:
                # Get message details
                message_detail = await gmail_service.get_message(self.user_id, msg['id'])
                if message_detail:
                    headers = message_detail.get('payload', {}).get('headers', [])
                    subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
                    sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown Sender')
                    date = next((h['value'] for h in headers if h['name'] == 'Date'), 'Unknown Date')
                    
                    formatted_results.append({
                        'id': msg['id'],
                        'subject': subject,
                        'from': sender,
                        'date': date,
                        'thread_id': msg.get('threadId')
                    })
            
            return json.dumps({
                'total_found': len(messages),
                'returned': len(formatted_results),
                'messages': formatted_results
            }, indent=2)
            
        except Exception as e:
            logger.error(f"Gmail search failed: {e}")
            return f"Search failed: {str(e)}"
    
    async def _get_message(self, message_id: str) -> str:
        """Get detailed Gmail message content."""
        try:
            gmail_service = await self._get_gmail_service()
            
            # Get message details
            message = await gmail_service.get_message(self.user_id, message_id)
            
            if not message:
                return f"Message {message_id} not found."
            
            # Extract message details
            headers = message.get('payload', {}).get('headers', [])
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
            sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown Sender')
            date = next((h['value'] for h in headers if h['name'] == 'Date'), 'Unknown Date')
            
            # Extract body (simplified - would need more robust parsing)
            body = ""
            payload = message.get('payload', {})
            if 'parts' in payload:
                for part in payload['parts']:
                    if part.get('mimeType') == 'text/plain':
                        body_data = part.get('body', {}).get('data', '')
                        if body_data:
                            import base64
                            body = base64.urlsafe_b64decode(body_data).decode('utf-8')
                            break
            elif payload.get('mimeType') == 'text/plain':
                body_data = payload.get('body', {}).get('data', '')
                if body_data:
                    import base64
                    body = base64.urlsafe_b64decode(body_data).decode('utf-8')
            
            return json.dumps({
                'id': message_id,
                'subject': subject,
                'from': sender,
                'date': date,
                'body': body[:1000] + "..." if len(body) > 1000 else body,
                'labels': message.get('labelIds', []),
                'thread_id': message.get('threadId')
            }, indent=2)
            
        except Exception as e:
            logger.error(f"Get message failed: {e}")
            return f"Failed to get message: {str(e)}"
    
    async def _generate_digest(self, hours_back: int = 24, include_read: bool = False) -> str:
        """Generate AI-powered email digest."""
        try:
            # Get database connection for email digest service
            async for db_conn in get_db_connection():
                # Create email digest service
                digest_service = EmailDigestService()
                
                # Generate digest
                digest_result = await digest_service.generate_digest(
                    user_id=self.user_id,
                    hours_back=hours_back,
                    include_read=include_read
                )
                
                return json.dumps(digest_result, indent=2, default=str)
                
        except Exception as e:
            logger.error(f"Email digest generation failed: {e}")
            return f"Digest generation failed: {str(e)}"


def create_gmail_tool(operation: str, user_id: str, **config) -> GmailTool:
    """Factory function to create Gmail tool instances."""
    return GmailTool(
        operation=operation,
        user_id=user_id,
        **config
    ) 