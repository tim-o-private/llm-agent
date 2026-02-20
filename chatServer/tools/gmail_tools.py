"""Simplified Gmail tools using pure LangChain Gmail toolkit with Vault authentication."""

import logging
from typing import List, Type

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

try:
    from google.oauth2.credentials import Credentials
    from langchain_google_community import GmailToolkit
except ImportError:
    raise ImportError(
        "langchain-google-community is required for Gmail tools. "
        "Install with: pip install langchain-google-community[gmail]"
    )

from ..database.connection import get_db_connection
from ..services.vault_token_service import VaultTokenService


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
                # Use Supabase client instead of connection pool for better compatibility
                import os

                from supabase import create_client

                supabase_url = os.getenv("SUPABASE_URL")
                supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

                if not supabase_url or not supabase_key:
                    raise RuntimeError("Supabase configuration missing. Please contact support.")

                supabase = create_client(supabase_url, supabase_key)

                # Get tokens using Supabase RPC function directly
                if self.context == "scheduler":
                    # Scheduler context - use scheduler-specific function
                    result = supabase.rpc("get_oauth_tokens_for_scheduler", {
                        "p_user_id": self.user_id,
                        "p_service_name": "gmail"
                    }).execute()
                else:
                    # User context - use scheduler function as well since we're calling from service context
                    # The regular get_oauth_tokens requires user authentication context which we don't have
                    result = supabase.rpc("get_oauth_tokens_for_scheduler", {
                        "p_user_id": self.user_id,
                        "p_service_name": "gmail"
                    }).execute()

                if not result.data:
                    # Provide clear user guidance
                    raise ValueError(
                        "Gmail not connected. Please connect your Gmail account:\n"
                        "1. Go to Settings > Integrations\n"
                        "2. Click 'Connect Gmail'\n"
                        "3. Complete the OAuth authorization flow\n"
                        "4. Try your request again"
                    )

                token_data = result.data
                access_token = token_data.get('access_token')
                refresh_token = token_data.get('refresh_token')

                if not access_token:
                    raise ValueError(
                        "Gmail connection expired. Please reconnect your Gmail account:\n"
                        "1. Go to Settings > Integrations\n"
                        "2. Disconnect and reconnect Gmail\n"
                        "3. Complete the OAuth authorization flow\n"
                        "4. Try your request again"
                    )

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

            except ValueError as e:
                # User-friendly OAuth guidance
                logger.warning(f"Gmail OAuth not configured for user {self.user_id}: {e}")
                raise RuntimeError(str(e))
            except Exception as e:
                logger.error(f"Failed to create Google credentials for user {self.user_id}: {e}")
                # Check if it's an authentication error from Supabase
                if "Authentication required" in str(e) or "P0001" in str(e):
                    raise RuntimeError(
                        "Gmail not connected. Please connect your Gmail account:\n"
                        "1. Go to Settings > Integrations\n"
                        "2. Click 'Connect Gmail'\n"
                        "3. Complete the OAuth authorization flow\n"
                        "4. Try your request again"
                    )
                else:
                    raise RuntimeError(f"Gmail authentication failed: {e}")

        return self._credentials

    async def get_gmail_tools(self) -> List[BaseTool]:
        """Get LangChain Gmail tools with Vault authentication."""
        if self._toolkit is None:
            try:
                logger.info(f"Initializing Gmail toolkit for user {self.user_id} (context: {self.context})")

                # Get credentials from Vault
                credentials = await self._get_google_credentials()

                # Create Gmail API resource using LangChain's build_resource_service
                # This is the proper way according to LangChain documentation
                try:
                    from langchain_google_community.gmail.utils import build_resource_service

                    # Build the Gmail API resource with our OAuth2 credentials
                    api_resource = build_resource_service(credentials=credentials)

                    # Create LangChain Gmail toolkit with the API resource
                    self._toolkit = GmailToolkit(api_resource=api_resource)

                except ImportError:
                    # Fallback: try direct Google API client creation
                    logger.warning("LangChain Gmail utils not available, using direct Google API client")
                    from googleapiclient.discovery import build

                    # Build Gmail service directly
                    api_resource = build('gmail', 'v1', credentials=credentials)

                    # Create toolkit with the service
                    self._toolkit = GmailToolkit(api_resource=api_resource)

                logger.info(f"Successfully initialized Gmail toolkit for user {self.user_id} (context: {self.context})")

            except Exception as e:
                logger.error(f"Failed to initialize Gmail toolkit for user {self.user_id}: {e}")
                raise RuntimeError(f"Gmail toolkit initialization failed: {e}")

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

    def _run(self, query: str, max_results: int = 10) -> str:
        """Synchronous run method (not used in async context)."""
        return (
            f"Gmail search tool requires async execution. "
            f"Parameters: query='{query}', max_results={max_results}. "
            f"Please use the async version (_arun) for proper execution."
        )

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

    def _run(self, message_id: str) -> str:
        """Synchronous run method (not used in async context)."""
        return (
            f"Gmail get message tool requires async execution. "
            f"Parameters: message_id='{message_id}'. "
            f"Please use the async version (_arun) for proper execution."
        )

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

    def _run(self, hours_back: int = 24, include_read: bool = False, max_emails: int = 20) -> str:
        """Synchronous run method (not used in async context)."""
        return (
            f"Gmail digest tool requires async execution. "
            f"Parameters: hours_back={hours_back}, include_read={include_read}, max_emails={max_emails}. "
            f"Please use the async version (_arun) for proper execution."
        )

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
            # Handle structured data from LangChain Gmail toolkit
            if isinstance(search_results, list):
                # LangChain Gmail toolkit returns list of dictionaries
                emails = search_results
                email_count = len(emails)

                # Extract information from structured data
                subjects = []
                senders = []
                snippets = []

                for email in emails:
                    if isinstance(email, dict):
                        # Extract subject
                        subject = email.get('subject', 'No Subject')
                        subjects.append(subject)

                        # Extract sender
                        sender = email.get('sender', 'Unknown Sender')
                        senders.append(sender)

                        # Extract snippet for preview
                        snippet = email.get('snippet', '')
                        if snippet:
                            # Truncate snippet to reasonable length
                            snippet = snippet[:100] + '...' if len(snippet) > 100 else snippet
                            snippets.append(snippet)

            else:
                # Fallback: try to parse as text (legacy format)
                lines = search_results.split('\n') if search_results else []

                # Count emails and extract key information
                email_count = 0
                subjects = []
                senders = []

                for line in lines:
                    line = str(line).strip()
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

                # If no structured data found, count the lines as emails
                if email_count == 0 and lines:
                    email_count = len([line for line in lines if line.strip()])

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
                digest += "\n"

            # Add email previews if available
            if 'snippets' in locals() and snippets:
                digest += "📝 **Email Previews:**\n"
                for i, snippet in enumerate(snippets[:3], 1):  # Show up to 3 previews
                    digest += f"{i}. {snippet}\n"
                if len(snippets) > 3:
                    digest += f"... and {len(snippets) - 3} more emails\n"
                digest += "\n"

            digest += f"🔍 **Search Query:** {hours_back}h back, {read_status} emails"

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
