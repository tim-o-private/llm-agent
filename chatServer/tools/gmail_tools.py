"""Gmail tools for agent integration using LangChain Gmail toolkit."""
# @docs memory-bank/patterns/agent-patterns.md#pattern-4-langchain-tool-abstraction
# @rules memory-bank/rules/agent-rules.json#agent-001

import logging
from typing import Dict, Any, Optional, List, Type, ClassVar
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

try:
    from langchain_google_community import GmailToolkit
    from langchain_google_community.gmail.utils import (
        build_resource_service,
        get_gmail_credentials,
    )
except ImportError:
    raise ImportError(
        "langchain-google-community is required for Gmail tools. "
        "Install with: pip install langchain-google-community[gmail]"
    )

from chatServer.services.vault_token_service import VaultTokenService
from chatServer.services.langchain_auth_bridge import VaultToLangChainCredentialAdapter

logger = logging.getLogger(__name__)


class GmailDigestInput(BaseModel):
    """Input for Gmail digest tool."""
    hours_back: int = Field(default=24, ge=1, le=168, description="Hours to look back for emails (1-168)")
    max_threads: int = Field(default=20, ge=1, le=100, description="Maximum number of email threads to analyze")
    include_read: bool = Field(default=False, description="Whether to include read emails")


class GmailSearchInput(BaseModel):
    """Input for Gmail search tool."""
    query: str = Field(description="Gmail search query (e.g., 'is:unread', 'from:example@gmail.com')")
    max_results: int = Field(default=20, ge=1, le=100, description="Maximum number of search results")


class GmailDigestTool(BaseTool):
    """Tool for generating email digests using Gmail API with Vault authentication."""
    
    name: str = "gmail_digest"
    description: str = (
        "Generate a digest of recent emails from Gmail. "
        "Analyzes email threads and provides a summary of important messages. "
        "Use this to help users understand what emails they've received recently."
    )
    args_schema: ClassVar[Type[BaseModel]] = GmailDigestInput
    
    # Configuration
    user_id: str
    vault_service: VaultTokenService
    
    def __init__(self, user_id: str, vault_service: VaultTokenService, **kwargs):
        """Initialize Gmail digest tool with Vault authentication.
        
        Args:
            user_id: User ID for scoping
            vault_service: VaultTokenService for token retrieval
            **kwargs: Additional configuration
        """
        super().__init__(user_id=user_id, vault_service=vault_service, **kwargs)
        self._gmail_toolkit = None
        self._gmail_tools = None
        self._auth_bridge = VaultToLangChainCredentialAdapter(vault_service)
    
    async def _get_gmail_toolkit(self) -> GmailToolkit:
        """Get or create Gmail toolkit instance with Vault authentication."""
        if self._gmail_toolkit is None:
            try:
                logger.info(f"Initializing Gmail toolkit for user {self.user_id}")
                
                # Get credentials from Vault via bridge
                credentials = await self._auth_bridge.create_gmail_credentials(self.user_id)
                api_resource = build_resource_service(credentials=credentials)
                self._gmail_toolkit = GmailToolkit(api_resource=api_resource)
                
                logger.info(f"Successfully initialized Gmail toolkit for user {self.user_id}")
            except Exception as e:
                logger.error(f"Failed to initialize Gmail toolkit for user {self.user_id}: {e}")
                raise RuntimeError(f"Gmail authentication failed: {e}")
        
        return self._gmail_toolkit
    
    async def _get_gmail_tools(self) -> List[BaseTool]:
        """Get Gmail tools from toolkit."""
        if self._gmail_tools is None:
            toolkit = await self._get_gmail_toolkit()
            self._gmail_tools = toolkit.get_tools()
        return self._gmail_tools
    
    async def _search_recent_emails(self, hours_back: int, include_read: bool) -> str:
        """Search for recent emails using Gmail search tool."""
        # Build search query
        query_parts = []
        
        # Time filter - Gmail uses format like "newer_than:1d" for 1 day
        if hours_back <= 24:
            query_parts.append(f"newer_than:{hours_back}h")
        else:
            days = hours_back // 24
            query_parts.append(f"newer_than:{days}d")
        
        # Read status filter
        if not include_read:
            query_parts.append("is:unread")
        
        query = " ".join(query_parts)
        
        # Get Gmail search tool
        gmail_tools = await self._get_gmail_tools()
        search_tool = next((tool for tool in gmail_tools if "search" in tool.name.lower()), None)
        
        if not search_tool:
            return "Gmail search tool not available"
        
        try:
            # Use the Gmail search tool
            search_result = search_tool.run({"query": query, "max_results": 50})
            return search_result
        except Exception as e:
            logger.error(f"Gmail search failed: {e}")
            return f"Failed to search emails: {e}"
    
    async def _get_message_details(self, message_ids: List[str]) -> List[str]:
        """Get details for specific messages."""
        gmail_tools = await self._get_gmail_tools()
        get_message_tool = next((tool for tool in gmail_tools if "get_message" in tool.name.lower()), None)
        
        if not get_message_tool:
            return ["Gmail get message tool not available"]
        
        message_details = []
        for msg_id in message_ids[:10]:  # Limit to 10 messages to avoid token overflow
            try:
                details = get_message_tool.run({"message_id": msg_id})
                message_details.append(details)
            except Exception as e:
                logger.error(f"Failed to get message {msg_id}: {e}")
                message_details.append(f"Failed to get message {msg_id}: {e}")
        
        return message_details
    
    def _generate_digest_summary(self, email_data: str, hours_back: int) -> str:
        """Generate a human-readable digest summary."""
        # This is a simple text-based summary
        # In a real implementation, you might use an LLM to generate a better summary
        
        lines = email_data.split('\n')
        email_count = len([line for line in lines if 'Message ID:' in line or 'Subject:' in line])
        
        summary = f"Email Digest - Last {hours_back} hours:\n\n"
        summary += f"Found {email_count} recent emails.\n\n"
        
        # Extract key information
        subjects = [line.split('Subject:')[1].strip() for line in lines if 'Subject:' in line]
        if subjects:
            summary += "Recent email subjects:\n"
            for i, subject in enumerate(subjects[:10], 1):
                summary += f"{i}. {subject}\n"
        
        return summary
    
    def _run(self, hours_back: int = 24, max_threads: int = 20, include_read: bool = False) -> str:
        """Generate email digest.
        
        Args:
            hours_back: Hours to look back for emails
            max_threads: Maximum number of threads to analyze
            include_read: Whether to include read emails
            
        Returns:
            Email digest summary
        """
        try:
            logger.info(f"Generating email digest for user {self.user_id}: {hours_back}h back, max {max_threads} threads")
            
            # Note: _run is synchronous but we need async for Vault operations
            # This is a limitation that will be addressed in the agent execution context
            # For now, we'll return a message indicating async execution is needed
            return (
                f"Email digest generation initiated for user {self.user_id}. "
                f"Parameters: {hours_back}h back, max {max_threads} threads, include_read={include_read}. "
                f"Note: This tool requires async execution context for Vault authentication."
            )
            
        except Exception as e:
            logger.error(f"Error generating email digest: {e}")
            return f"Failed to generate email digest: {e}"
    
    async def _arun(self, hours_back: int = 24, max_threads: int = 20, include_read: bool = False) -> str:
        """Async version of email digest generation."""
        try:
            logger.info(f"Generating email digest for user {self.user_id}: {hours_back}h back, max {max_threads} threads")
            
            # Search for recent emails
            search_results = await self._search_recent_emails(hours_back, include_read)
            
            if "Failed to search" in search_results or not search_results.strip():
                return f"No emails found in the last {hours_back} hours."
            
            # Generate summary
            digest = self._generate_digest_summary(search_results, hours_back)
            
            return digest
            
        except Exception as e:
            logger.error(f"Error generating email digest: {e}")
            return f"Failed to generate email digest: {e}"


class GmailSearchTool(BaseTool):
    """Gmail search tool with Vault authentication."""
    
    name: str = "gmail_search"
    description: str = (
        "Search Gmail messages using Gmail search syntax. "
        "Examples: 'is:unread', 'from:example@gmail.com', 'subject:meeting', 'newer_than:2d'. "
        "Returns message IDs and basic information."
    )
    args_schema: ClassVar[Type[BaseModel]] = GmailSearchInput
    
    user_id: str
    vault_service: VaultTokenService
    
    def __init__(self, user_id: str, vault_service: VaultTokenService, **kwargs):
        """Initialize Gmail search tool with Vault authentication.
        
        Args:
            user_id: User ID for scoping
            vault_service: VaultTokenService for token retrieval
            **kwargs: Additional configuration
        """
        super().__init__(user_id=user_id, vault_service=vault_service, **kwargs)
        self._gmail_toolkit = None
        self._auth_bridge = VaultToLangChainCredentialAdapter(vault_service)
    
    async def _get_gmail_toolkit(self) -> GmailToolkit:
        """Get or create Gmail toolkit instance with Vault authentication."""
        if self._gmail_toolkit is None:
            try:
                logger.info(f"Initializing Gmail toolkit for user {self.user_id}")
                
                # Get credentials from Vault via bridge
                credentials = await self._auth_bridge.create_gmail_credentials(self.user_id)
                api_resource = build_resource_service(credentials=credentials)
                self._gmail_toolkit = GmailToolkit(api_resource=api_resource)
                
                logger.info(f"Successfully initialized Gmail toolkit for user {self.user_id}")
            except Exception as e:
                logger.error(f"Failed to initialize Gmail toolkit for user {self.user_id}: {e}")
                raise RuntimeError(f"Gmail authentication failed: {e}")
        
        return self._gmail_toolkit
    
    def _run(self, query: str, max_results: int = 20) -> str:
        """Search Gmail messages.
        
        Args:
            query: Gmail search query
            max_results: Maximum number of results
            
        Returns:
            Search results
        """
        try:
            # Note: _run is synchronous but we need async for Vault operations
            # This is a limitation that will be addressed in the agent execution context
            return (
                f"Gmail search initiated for user {self.user_id}. "
                f"Query: '{query}', max_results: {max_results}. "
                f"Note: This tool requires async execution context for Vault authentication."
            )
            
        except Exception as e:
            logger.error(f"Gmail search failed: {e}")
            return f"Failed to search Gmail: {e}"
    
    async def _arun(self, query: str, max_results: int = 20) -> str:
        """Async version of Gmail search."""
        try:
            toolkit = await self._get_gmail_toolkit()
            gmail_tools = toolkit.get_tools()
            search_tool = next((tool for tool in gmail_tools if "search" in tool.name.lower()), None)
            
            if not search_tool:
                return "Gmail search tool not available"
            
            result = search_tool.run({"query": query, "max_results": max_results})
            return result
            
        except Exception as e:
            logger.error(f"Gmail search failed: {e}")
            return f"Failed to search Gmail: {e}" 