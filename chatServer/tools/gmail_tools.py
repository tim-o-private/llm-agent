"""Gmail tools with multi-account support and automatic token refresh.

TODO: SPEC-017 — gmail_tools uses sync Supabase client (create_client).
Migrate to async UserScopedClient when sync wrapper is available.
"""

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Type

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

logger = logging.getLogger(__name__)


class GmailToolProvider:
    """Gmail tool provider with multi-account support and automatic token refresh."""

    def __init__(self, user_id: str, connection_id: str = None, context: str = "user"):
        """Initialize Gmail tool provider.

        Args:
            user_id: User ID for scoping
            connection_id: Specific connection UUID (for single-account mode)
            context: Execution context - "user" or "scheduler"
        """
        self.user_id = user_id
        self.connection_id = connection_id
        self.context = context
        self._toolkit = None
        self._credentials = None
        self._account_email = None
        self._token_data = None

    @property
    def account_email(self) -> Optional[str]:
        """Email address of the connected account."""
        return self._account_email

    @classmethod
    async def get_all_providers(cls, user_id: str, context: str = "user") -> list["GmailToolProvider"]:
        """Get providers for ALL connected Gmail accounts.

        Args:
            user_id: User ID
            context: Execution context

        Returns:
            List of GmailToolProvider instances, one per connection.
        """
        connections = await cls._get_gmail_connections(user_id)
        providers = []
        for conn in connections:
            provider = cls(user_id, conn["connection_id"], context)
            provider._account_email = conn.get("service_user_email")
            provider._token_data = conn
            providers.append(provider)
        return providers

    @classmethod
    async def get_provider_for_account(
        cls, user_id: str, account_email: str, context: str = "user"
    ) -> "GmailToolProvider":
        """Get provider for a specific account by email.

        Args:
            user_id: User ID
            account_email: Email address to look up
            context: Execution context

        Returns:
            GmailToolProvider for the specified account.

        Raises:
            ValueError: If no connection found for the email.
        """
        connections = await cls._get_gmail_connections(user_id)
        for conn in connections:
            if conn.get("service_user_email") == account_email:
                provider = cls(user_id, conn["connection_id"], context)
                provider._account_email = account_email
                provider._token_data = conn
                return provider
        raise ValueError(
            f"No Gmail connection found for {account_email}. "
            "Connected accounts: " + ", ".join(c.get("service_user_email", "?") for c in connections)
        )

    @classmethod
    async def _get_gmail_connections(cls, user_id: str) -> list:
        """Fetch all active Gmail connections for a user."""
        from supabase import create_client

        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

        if not supabase_url or not supabase_key:
            raise RuntimeError("Supabase configuration missing")

        supabase = create_client(supabase_url, supabase_key)

        # Use scheduler RPC (no connection_id = returns array of all)
        result = supabase.rpc("get_oauth_tokens_for_scheduler", {
            "p_user_id": user_id,
            "p_service_name": "gmail",
        }).execute()

        if not result.data:
            return []

        # Result is a JSON array of connections
        data = result.data
        if isinstance(data, list):
            return data
        # Single result (backward compat) — wrap in list
        return [data]

    async def _get_google_credentials(self) -> Credentials:
        """Get Google OAuth2 credentials with automatic token refresh."""
        if self._credentials is not None:
            return self._credentials

        # Get token data if not already loaded
        if self._token_data is None:
            if self.connection_id:
                from supabase import create_client

                supabase_url = os.getenv("SUPABASE_URL")
                supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
                supabase = create_client(supabase_url, supabase_key)

                result = supabase.rpc("get_oauth_tokens_for_scheduler", {
                    "p_user_id": self.user_id,
                    "p_service_name": "gmail",
                    "p_connection_id": self.connection_id,
                }).execute()

                if not result.data:
                    raise ValueError(
                        f"Gmail connection not found (id={self.connection_id}). "
                        "Please reconnect this account in Settings > Integrations."
                    )
                self._token_data = result.data
            else:
                # Legacy single-account mode
                connections = await self._get_gmail_connections(self.user_id)
                if not connections:
                    raise ValueError(
                        "Gmail not connected. Please connect your Gmail account:\n"
                        "1. Go to Settings > Integrations\n"
                        "2. Click 'Connect Gmail'\n"
                        "3. Complete the OAuth authorization flow"
                    )
                self._token_data = connections[0]

        token_data = self._token_data
        access_token = token_data.get("access_token")
        refresh_token = token_data.get("refresh_token")
        self._account_email = token_data.get("service_user_email")

        if not access_token:
            raise ValueError(
                f"Gmail connection expired for {self._account_email}. "
                "Please reconnect this account in Settings > Integrations."
            )

        client_id = os.getenv("GOOGLE_CLIENT_ID")
        client_secret = os.getenv("GOOGLE_CLIENT_SECRET")

        if not client_id or not client_secret:
            raise RuntimeError(
                "Google OAuth configuration missing (GOOGLE_CLIENT_ID/GOOGLE_CLIENT_SECRET)"
            )

        self._credentials = Credentials(
            token=access_token,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=client_id,
            client_secret=client_secret,
            scopes=["https://www.googleapis.com/auth/gmail.readonly"],
        )

        # Check if token needs refresh (expired or within 5-min buffer)
        expires_at_str = token_data.get("expires_at")
        needs_refresh = False

        if expires_at_str:
            try:
                if isinstance(expires_at_str, str):
                    expires_at = datetime.fromisoformat(expires_at_str.replace("Z", "+00:00"))
                else:
                    expires_at = expires_at_str
                buffer = timedelta(minutes=5)
                if datetime.now(timezone.utc) + buffer > expires_at:
                    needs_refresh = True
            except (ValueError, TypeError):
                pass

        if self._credentials.expired:
            needs_refresh = True

        if needs_refresh and refresh_token:
            try:
                from google.auth.transport.requests import Request as GoogleAuthRequest

                self._credentials.refresh(GoogleAuthRequest())
                await self._update_stored_token(
                    self._credentials.token,
                    self._credentials.expiry,
                )
                logger.info(f"Refreshed Gmail token for {self._account_email}")
            except Exception as e:
                logger.warning(f"Token refresh failed for {self._account_email}: {e}")
                # Continue with existing token — it may still work
        elif needs_refresh and not refresh_token:
            logger.warning(
                f"Gmail token expired for {self._account_email} and no refresh token available. "
                "User needs to reconnect."
            )

        return self._credentials

    async def _update_stored_token(self, new_token: str, new_expiry) -> None:
        """Write a refreshed access token back to Vault."""
        if not self.connection_id:
            return

        try:
            from supabase import create_client

            supabase_url = os.getenv("SUPABASE_URL")
            supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
            supabase = create_client(supabase_url, supabase_key)

            # Get connection details to reconstruct the vault secret name
            conn = supabase.table("external_api_connections").select(
                "user_id, service_name, service_user_id"
            ).eq("id", self.connection_id).execute()

            if conn.data and conn.data[0]:
                row = conn.data[0]
                service_user_id = row.get("service_user_id") or "default"
                secret_name = f"{row['user_id']}_{row['service_name']}_{service_user_id}_access"
                # store_secret upserts by name — updates if exists, creates if not
                supabase.rpc("store_secret", {
                    "p_secret": new_token,
                    "p_name": secret_name,
                    "p_description": f"Access token for {row['service_name']}",
                }).execute()

                # Update expires_at on the connection record
                update_data = {"updated_at": datetime.now(timezone.utc).isoformat()}
                if new_expiry:
                    if isinstance(new_expiry, datetime):
                        update_data["token_expires_at"] = new_expiry.isoformat()
                    else:
                        update_data["token_expires_at"] = str(new_expiry)

                supabase.table("external_api_connections").update(
                    update_data
                ).eq("id", self.connection_id).execute()

        except Exception as e:
            logger.error(f"Failed to update stored token for connection {self.connection_id}: {e}")

    async def get_gmail_tools(self) -> List[BaseTool]:
        """Get LangChain Gmail tools with Vault authentication."""
        if self._toolkit is None:
            credentials = await self._get_google_credentials()

            try:
                from langchain_google_community.gmail.utils import build_resource_service

                api_resource = build_resource_service(credentials=credentials)
                self._toolkit = GmailToolkit(api_resource=api_resource)
            except ImportError:
                from googleapiclient.discovery import build

                api_resource = build("gmail", "v1", credentials=credentials)
                self._toolkit = GmailToolkit(api_resource=api_resource)

            logger.info(
                f"Initialized Gmail toolkit for user {self.user_id} "
                f"account {self._account_email} (context: {self.context})"
            )

        return self._toolkit.get_tools()


# Database-driven tool classes
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
        """Get Gmail tool provider (legacy single-account)."""
        if self._provider is None:
            context = "scheduler" if "background" in self.agent_name.lower() else "user"
            self._provider = GmailToolProvider(self.user_id, context=context)
        return self._provider


class GmailSearchInput(BaseModel):
    """Input schema for Gmail search tool."""

    query: str = Field(
        ...,
        description=(
            "Gmail search query using Gmail search syntax "
            "(e.g., 'is:unread', 'from:example@gmail.com', 'newer_than:2d')"
        ),
    )
    max_results: int = Field(default=10, ge=1, le=50, description="Maximum results (1-50)")
    account: Optional[str] = Field(
        default=None,
        description="Email address of the account to search. Omit to search ALL connected accounts.",
    )


class SearchGmailTool(BaseGmailTool):
    """Search Gmail messages using Gmail search syntax."""

    name: str = "search_gmail"
    description: str = (
        "Search Gmail messages using Gmail search syntax. "
        "Examples: is:unread, from:example@gmail.com, subject:meeting, newer_than:2d. "
        "Returns message IDs, subjects, and basic metadata. "
        "Use the 'account' parameter to search a specific Gmail account, "
        "or omit it to search all connected accounts."
    )
    args_schema: Type[BaseModel] = GmailSearchInput

    @classmethod
    def prompt_section(cls, channel: str) -> str | None:
        """Return behavioral guidance for the agent prompt, or None to omit."""
        if channel in ("web", "telegram"):
            return "Gmail: Use search_gmail and get_gmail for email tasks. When the user asks about email, use the tools — don't ask clarifying questions first."  # noqa: E501
        elif channel == "heartbeat":
            return "Gmail: Check for important unread emails using search_gmail with 'is:unread newer_than:1d'. Report subjects and senders of anything urgent. Skip newsletters and automated notifications."  # noqa: E501
        elif channel == "scheduled":
            return None
        else:
            return "Gmail: Use search_gmail and get_gmail for email tasks. When the user asks about email, use the tools — don't ask clarifying questions first."  # noqa: E501

    def _run(self, query: str, max_results: int = 10, account: Optional[str] = None) -> str:
        return "Gmail search tool requires async execution. Use the async version (_arun)."

    async def _arun(self, query: str, max_results: int = 10, account: Optional[str] = None) -> str:
        """Search Gmail messages, optionally across all accounts."""
        try:
            context = "scheduler" if "background" in self.agent_name.lower() else "user"

            if account:
                # Single account search
                provider = await GmailToolProvider.get_provider_for_account(
                    self.user_id, account, context
                )
                result = await self._search_single(provider, query, max_results)
                return self._format_results(result, account)
            else:
                # Search all accounts
                providers = await GmailToolProvider.get_all_providers(self.user_id, context)

                if not providers:
                    return "No Gmail accounts connected. Please connect Gmail in Settings > Integrations."

                if len(providers) == 1:
                    result = await self._search_single(providers[0], query, max_results)
                    return self._format_results(result, providers[0].account_email)

                # Multi-account search
                all_results = []
                for provider in providers:
                    try:
                        result = await self._search_single(provider, query, max_results)
                        all_results.append({
                            "account": provider.account_email,
                            "results": result,
                        })
                    except Exception as e:
                        all_results.append({
                            "account": provider.account_email,
                            "error": str(e),
                        })

                return self._format_multi_results(all_results)

        except Exception as e:
            logger.error(f"Gmail search failed for user {self.user_id}: {e}")
            return f"Gmail search failed: {str(e)}"

    async def _search_single(self, provider: GmailToolProvider, query: str, max_results: int) -> str:
        """Execute search on a single account."""
        gmail_tools = await provider.get_gmail_tools()
        search_tool = next((t for t in gmail_tools if "search" in t.name.lower()), None)
        if not search_tool:
            return "Gmail search tool not available."
        return await search_tool.arun({"query": query, "max_results": max_results})

    def _format_results(self, results: str, account: str) -> str:
        """Format single-account results with account tag."""
        return f"[{account}]\n{results}"

    def _format_multi_results(self, all_results: list) -> str:
        """Format multi-account results grouped by account."""
        parts = []
        for item in all_results:
            account = item["account"]
            if "error" in item:
                parts.append(f"=== {account} (error) ===\n{item['error']}")
            else:
                parts.append(f"=== {account} ===\n{item['results']}")
        return "\n\n".join(parts)


class GmailGetMessageInput(BaseModel):
    """Input schema for Gmail get message tool."""

    message_id: str = Field(..., description="Gmail message ID to retrieve")
    account: str = Field(
        ...,
        description="Email address of the account this message belongs to",
    )


class GetGmailTool(BaseGmailTool):
    """Get detailed Gmail message content by ID."""

    name: str = "get_gmail"
    description: str = (
        "Get detailed Gmail message content by ID. "
        "Requires the 'account' parameter to specify which Gmail account the message is from."
    )
    args_schema: Type[BaseModel] = GmailGetMessageInput

    def _run(self, message_id: str, account: str = "") -> str:
        return "Gmail get message tool requires async execution. Use the async version (_arun)."

    async def _arun(self, message_id: str, account: str = "") -> str:
        """Get Gmail message by ID from a specific account."""
        try:
            if not account:
                return "Error: 'account' parameter is required. Specify the email address of the Gmail account."

            context = "scheduler" if "background" in self.agent_name.lower() else "user"
            provider = await GmailToolProvider.get_provider_for_account(
                self.user_id, account, context
            )
            gmail_tools = await provider.get_gmail_tools()

            get_tool = next(
                (t for t in gmail_tools if "get" in t.name.lower() and "message" in t.name.lower()),
                None,
            )
            if not get_tool:
                return "Gmail get message tool not available."

            result = await get_tool.arun({"message_id": message_id})
            return f"[{account}]\n{result}"

        except Exception as e:
            logger.error(f"Gmail get message failed for user {self.user_id}: {e}")
            return f"Gmail get message failed: {str(e)}"


# Backward-compat aliases (old names → new classes)
GmailSearchTool = SearchGmailTool
GmailGetMessageTool = GetGmailTool


# Factory functions for backward compatibility
def create_gmail_tool_provider(user_id: str, context: str = "user") -> GmailToolProvider:
    """Create a Gmail tool provider instance."""
    return GmailToolProvider(user_id, context)


async def get_gmail_tools_for_user(user_id: str, context: str = "user") -> List[BaseTool]:
    """Get Gmail tools for a specific user."""
    provider = GmailToolProvider(user_id, context)
    return await provider.get_gmail_tools()
