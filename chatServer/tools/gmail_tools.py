"""Simplified Gmail tools using pure LangChain Gmail toolkit with Vault authentication."""

import logging
from typing import List, Optional, Dict, Any, Type
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

try:
    from langchain_google_community import GmailToolkit
    from google.oauth2.credentials import Credentials
except ImportError:
    raise ImportError(
        "langchain-google-community is required for Gmail tools. "
        "Install with: pip install langchain-google-community[gmail]"
    )

try:
    from ..services.vault_token_service import VaultTokenService
    from ..database.connection import get_db_connection
except ImportError:
    from chatServer.services.vault_token_service import VaultTokenService
    from chatServer.database.connection import get_db_connection

import os

logger = logging.getLogger(__name__)


class GmailToolProvider:
    """Simplified Gmail tool provider using pure LangChain toolkit with Vault authentication."""
    
    def __init__(self, user_id: str, context: str = "user"):
        """Initialize Gmail tool provider.
        
        Args:
            user_id: User ID for scoping
            context: Execution context - "user" for UI operations, "scheduler" for background tasks
        """
        self.user_id = user_id
        self.context = context
        self._toolkit = None
        self._credentials = None
    
    async def _get_google_credentials(self) -> Credentials:
        """Get Google OAuth2 credentials from Vault."""
        if self._credentials is None:
            try:
                # Get database connection
                async for db_conn in get_db_connection():
                    # Create VaultTokenService with appropriate context
                    vault_service = VaultTokenService(db_conn, context=self.context)
                    
                    # Get tokens from vault
                    access_token, refresh_token = await vault_service.get_tokens(self.user_id, "gmail")
                    
                    # Get Google OAuth client credentials from environment
                    client_id = os.getenv('GOOGLE_CLIENT_ID')
                    client_secret = os.getenv('GOOGLE_CLIENT_SECRET')
                    
                    if not client_id or not client_secret:
                        raise RuntimeError(
                            "Google OAuth configuration missing. Please contact support - "
                            "GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET environment variables required"
                        )
                    
                    # Create Google credentials object
                    self._credentials = Credentials(
                        token=access_token,
                        refresh_token=refresh_token,
                        token_uri="https://oauth2.googleapis.com/token",
                        client_id=client_id,
                        client_secret=client_secret,
                        scopes=['https://www.googleapis.com/auth/gmail.readonly']
                    )
                    
                    logger.info(f"Successfully created Google credentials for user {self.user_id} (context: {self.context})")
                    break
                    
            except ValueError as e:
                # User hasn't completed OAuth flow
                logger.warning(f"Gmail OAuth not configured for user {self.user_id}: {e}")
                raise RuntimeError(
                    "Gmail not connected. Please connect your Gmail account in Settings > Integrations. "
                    "You'll need to complete the OAuth flow to allow access to your Gmail."
                )
            except Exception as e:
                logger.error(f"Failed to create Google credentials for user {self.user_id}: {e}")
                raise RuntimeError(f"Gmail authentication failed: {e}")
        
        return self._credentials
    
    async def get_gmail_tools(self) -> List[BaseTool]:
        """Get LangChain Gmail tools with Vault authentication."""
        if self._toolkit is None:
            try:
                logger.info(f"Initializing Gmail toolkit for user {self.user_id} (context: {self.context})")
                
                # Get credentials from Vault
                credentials = await self._get_google_credentials()
                
                # Create LangChain Gmail toolkit directly
                self._toolkit = GmailToolkit(credentials=credentials)
                
                logger.info(f"Successfully initialized Gmail toolkit for user {self.user_id} (context: {self.context})")
                
            except Exception as e:
                logger.error(f"Failed to initialize Gmail toolkit for user {self.user_id}: {e}")
                raise
        
        return self._toolkit.get_tools()


# Database-driven tool classes that work with the agent_loader_db system
class BaseGmailTool(BaseTool):
    """Base class for database-driven Gmail tools."""
    
    user_id: str = Field(..., description="User ID for scoping")
    agent_name: str = Field(..., description="Agent name for context")
    supabase_url: str = Field(..., description="Supabase URL")
    supabase_key: str = Field(..., description="Supabase key")
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._provider = None
    
    async def _get_provider(self) -> GmailToolProvider:
        """Get Gmail tool provider with appropriate context."""
        if self._provider is None:
            # Determine context based on agent name or other factors
            context = "scheduler" if "background" in self.agent_name.lower() else "user"
            self._provider = GmailToolProvider(self.user_id, context=context)
        return self._provider


class GmailSearchInput(BaseModel):
    """Input schema for Gmail search tool."""
    query: str = Field(..., description="Gmail search query using Gmail search syntax (e.g., 'is:unread', 'from:example@gmail.com', 'newer_than:2d')")
    max_results: int = Field(default=10, ge=1, le=50, description="Maximum number of results to return (1-50)")


class GmailSearchTool(BaseGmailTool):
    """Search Gmail messages using Gmail search syntax."""
    
    name: str = "gmail_search"
    description: str = (
        "Search Gmail messages using Gmail search syntax. "
        "Examples: is:unread, from:example@gmail.com, subject:meeting, newer_than:2d. "
        "Returns message IDs, subjects, and basic metadata."
    )
    args_schema: Type[BaseModel] = GmailSearchInput
    
    async def _arun(self, query: str, max_results: int = 10) -> str:
        """Search Gmail messages."""
        try:
            provider = await self._get_provider()
            gmail_tools = await provider.get_gmail_tools()
            
            # Find the search tool from LangChain Gmail toolkit
            search_tool = None
            for tool in gmail_tools:
                if "search" in tool.name.lower():
                    search_tool = tool
                    break
            
            if not search_tool:
                return "Gmail search tool not available. Please check your Gmail connection."
            
            # Execute search with LangChain tool
            search_params = {"query": query, "max_results": max_results}
            result = await search_tool.arun(search_params)
            
            logger.info(f"Gmail search completed for user {self.user_id}: query='{query}', max_results={max_results}")
            return result
            
        except Exception as e:
            logger.error(f"Gmail search failed for user {self.user_id}: {e}")
            return f"Gmail search failed: {str(e)}"


class GmailGetMessageInput(BaseModel):
    """Input schema for Gmail get message tool."""
    message_id: str = Field(..., description="Gmail message ID to retrieve")


class GmailGetMessageTool(BaseGmailTool):
    """Get detailed Gmail message content by ID."""
    
    name: str = "gmail_get_message"
    description: str = (
        "Get detailed Gmail message content by ID. "
        "Retrieves full message content including body, headers, and attachments info."
    )
    args_schema: Type[BaseModel] = GmailGetMessageInput
    
    async def _arun(self, message_id: str) -> str:
        """Get Gmail message by ID."""
        try:
            provider = await self._get_provider()
            gmail_tools = await provider.get_gmail_tools()
            
            # Find the get message tool from LangChain Gmail toolkit
            get_tool = None
            for tool in gmail_tools:
                if "get" in tool.name.lower() and "message" in tool.name.lower():
                    get_tool = tool
                    break
            
            if not get_tool:
                return "Gmail get message tool not available. Please check your Gmail connection."
            
            # Execute get message with LangChain tool
            result = await get_tool.arun({"message_id": message_id})
            
            logger.info(f"Gmail get message completed for user {self.user_id}: message_id={message_id}")
            return result
            
        except Exception as e:
            logger.error(f"Gmail get message failed for user {self.user_id}: {e}")
            return f"Gmail get message failed: {str(e)}"


class GmailDigestInput(BaseModel):
    """Input schema for Gmail digest tool."""
    hours_back: int = Field(default=24, ge=1, le=168, description="Hours to look back for emails (1-168)")
    include_read: bool = Field(default=False, description="Whether to include read emails in the digest")
    max_emails: int = Field(default=20, ge=1, le=50, description="Maximum number of emails to analyze (1-50)")


class GmailDigestTool(BaseGmailTool):
    """Generate a digest of recent emails from Gmail."""
    
    name: str = "gmail_digest"
    description: str = (
        "Generate a digest of recent emails from Gmail. "
        "Analyzes email threads and provides a summary of important messages. "
        "Use this to create comprehensive email summaries."
    )
    args_schema: Type[BaseModel] = GmailDigestInput
    
    async def _arun(self, hours_back: int = 24, include_read: bool = False, max_emails: int = 20) -> str:
        """Generate Gmail digest."""
        try:
            provider = await self._get_provider()
            gmail_tools = await provider.get_gmail_tools()
            
            # Find the search tool to get recent emails
            search_tool = None
            for tool in gmail_tools:
                if "search" in tool.name.lower():
                    search_tool = tool
                    break
            
            if not search_tool:
                return "Gmail search tool not available. Please check your Gmail connection."
            
            # Build search query for recent emails
            query = f"newer_than:{hours_back}h"
            if not include_read:
                query += " is:unread"
            
            # Search for recent emails
            search_result = await search_tool.arun({"query": query, "max_results": max_emails})
            
            # Create digest summary
            if not search_result or "No messages found" in search_result:
                read_status = "read and unread" if include_read else "unread"
                return f"📭 No {read_status} emails found in the last {hours_back} hours."
            
            # Parse and summarize the results
            digest = self._create_digest_summary(search_result, hours_back, include_read)
            
            logger.info(f"Gmail digest completed for user {self.user_id}: hours_back={hours_back}, include_read={include_read}")
            return digest
            
        except Exception as e:
            logger.error(f"Gmail digest failed for user {self.user_id}: {e}")
            return f"Gmail digest failed: {str(e)}"
    
    def _create_digest_summary(self, search_results: str, hours_back: int, include_read: bool) -> str:
        """Create a human-readable digest summary from search results."""
        try:
            # Parse search results to extract email information
            lines = search_results.split('\n') if search_results else []
            
            # Count emails and extract key information
            email_count = 0
            subjects = []
            senders = []
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # Look for subject lines
                if 'Subject:' in line:
                    subject = line.split('Subject:')[1].strip()
                    subjects.append(subject)
                    email_count += 1
                
                # Look for sender information
                elif 'From:' in line:
                    sender = line.split('From:')[1].strip()
                    senders.append(sender)
            
            # Create digest summary
            read_status = "read and unread" if include_read else "unread"
            
            digest = f"📧 **Email Digest - Last {hours_back} Hours**\n\n"
            digest += f"📊 **Summary:** {email_count} {read_status} emails found\n\n"
            
            if subjects:
                digest += "📋 **Recent Email Subjects:**\n"
                for i, subject in enumerate(subjects[:10], 1):  # Show up to 10 subjects
                    digest += f"{i}. {subject}\n"
                
                if len(subjects) > 10:
                    digest += f"... and {len(subjects) - 10} more emails\n"
                digest += "\n"
            
            if senders:
                # Count unique senders
                unique_senders = list(set(senders))
                digest += f"👥 **Senders:** {len(unique_senders)} unique senders\n"
                for sender in unique_senders[:5]:  # Show up to 5 senders
                    digest += f"• {sender}\n"
                
                if len(unique_senders) > 5:
                    digest += f"• ... and {len(unique_senders) - 5} more senders\n"
            
            digest += f"\n🔍 **Search Query:** {hours_back}h back, {read_status} emails"
            
            return digest
            
        except Exception as e:
            logger.error(f"Failed to create digest summary: {e}")
            return f"📧 Email digest generated but summary formatting failed: {str(e)}"


# Factory functions for backward compatibility
def create_gmail_tool_provider(user_id: str, context: str = "user") -> GmailToolProvider:
    """Create a Gmail tool provider instance.
    
    Args:
        user_id: User ID for scoping
        context: Execution context - "user" for UI operations, "scheduler" for background tasks
        
    Returns:
        GmailToolProvider instance
    """
    return GmailToolProvider(user_id, context)


async def get_gmail_tools_for_user(user_id: str, context: str = "user") -> List[BaseTool]:
    """Get Gmail tools for a specific user.
    
    Args:
        user_id: User ID for scoping
        context: Execution context - "user" for UI operations, "scheduler" for background tasks
        
    Returns:
        List of LangChain Gmail tools
    """
    provider = GmailToolProvider(user_id, context)
    return await provider.get_gmail_tools() 