"""Calendar tools with multi-account support and automatic token refresh.

Follows the gmail_tools.py multi-account pattern — CalendarToolProvider manages
per-connection credential fetching, tools aggregate across accounts.

Uses async SystemClient (A8/SPEC-017 compliant) for DB access.
"""

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Optional, Type

from google.oauth2.credentials import Credentials
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


def _get_calendar_service():
    """Lazy import to avoid circular dependency via chatServer.services.__init__."""
    from chatServer.services.calendar_service import CalendarService
    return CalendarService


class CalendarToolProvider:
    """Calendar tool provider with multi-account support and automatic token refresh."""

    def __init__(self, user_id: str, connection_id: str = None, context: str = "user"):
        """Initialize Calendar tool provider.

        Args:
            user_id: User ID for scoping
            connection_id: Specific connection UUID (for single-account mode)
            context: Execution context - "user" or "scheduler"
        """
        self.user_id = user_id
        self.connection_id = connection_id
        self.context = context
        self._credentials = None
        self._account_email = None
        self._token_data = None

    @property
    def account_email(self) -> Optional[str]:
        """Email address of the connected account."""
        return self._account_email

    @classmethod
    async def get_all_providers(cls, user_id: str, context: str = "user") -> list["CalendarToolProvider"]:
        """Get providers for ALL connected calendar accounts.

        Args:
            user_id: User ID
            context: Execution context

        Returns:
            List of CalendarToolProvider instances, one per connection.
        """
        connections = await cls._get_calendar_connections(user_id)
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
    ) -> "CalendarToolProvider":
        """Get provider for a specific account by email.

        Args:
            user_id: User ID
            account_email: Email address to look up
            context: Execution context

        Returns:
            CalendarToolProvider for the specified account.

        Raises:
            ValueError: If no connection found for the email.
        """
        connections = await cls._get_calendar_connections(user_id)
        for conn in connections:
            if conn.get("service_user_email") == account_email:
                provider = cls(user_id, conn["connection_id"], context)
                provider._account_email = account_email
                provider._token_data = conn
                return provider
        raise ValueError(
            f"No calendar connection found for {account_email}. "
            "Connected accounts: " + ", ".join(c.get("service_user_email", "?") for c in connections)
        )

    @classmethod
    async def _get_calendar_connections(cls, user_id: str) -> list:
        """Fetch all active Google Calendar connections for a user."""
        from chatServer.database.supabase_client import create_system_client
        system_client = await create_system_client()

        result = await system_client.rpc("get_oauth_tokens_for_scheduler", {
            "p_user_id": user_id,
            "p_service_name": "google_calendar",
        }).execute()

        if not result.data:
            return []

        data = result.data
        if isinstance(data, list):
            return data
        return [data]

    async def get_credentials(self) -> Credentials:
        """Get Google OAuth2 credentials with automatic token refresh."""
        if self._credentials is not None:
            return self._credentials

        if self._token_data is None:
            if self.connection_id:
                from chatServer.database.supabase_client import create_system_client
                system_client = await create_system_client()

                result = await system_client.rpc("get_oauth_tokens_for_scheduler", {
                    "p_user_id": self.user_id,
                    "p_service_name": "google_calendar",
                    "p_connection_id": self.connection_id,
                }).execute()

                if not result.data:
                    raise ValueError(
                        f"Calendar connection not found (id={self.connection_id}). "
                        "Please reconnect this account in Settings > Integrations."
                    )
                self._token_data = result.data
            else:
                connections = await self._get_calendar_connections(self.user_id)
                if not connections:
                    raise ValueError(
                        "Calendar not connected. Connect Google Calendar in "
                        "Settings > Integrations to enable this."
                    )
                self._token_data = connections[0]

        token_data = self._token_data
        access_token = token_data.get("access_token")
        refresh_token = token_data.get("refresh_token")
        self._account_email = token_data.get("service_user_email")

        if not access_token:
            raise ValueError(
                f"Calendar connection expired for {self._account_email}. "
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
            scopes=["https://www.googleapis.com/auth/calendar.readonly"],
        )

        # Check if token needs refresh
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
                logger.info(f"Refreshed calendar token for {self._account_email}")
            except Exception as e:
                logger.warning(f"Token refresh failed for {self._account_email}: {e}")
        elif needs_refresh and not refresh_token:
            logger.warning(
                f"Calendar token expired for {self._account_email} and no refresh token available. "
                "User needs to reconnect."
            )

        return self._credentials

    async def _update_stored_token(self, new_token: str, new_expiry) -> None:
        """Write a refreshed access token back to Vault."""
        if not self.connection_id:
            return

        try:
            from chatServer.database.supabase_client import create_system_client
            system_client = await create_system_client()

            conn = await system_client.table("external_api_connections").select(
                "user_id, service_name, service_user_id"
            ).eq("id", self.connection_id).execute()

            if conn.data and conn.data[0]:
                row = conn.data[0]
                service_user_id = row.get("service_user_id") or "default"
                secret_name = f"{row['user_id']}_{row['service_name']}_{service_user_id}_access"
                await system_client.rpc("store_secret", {
                    "p_secret": new_token,
                    "p_name": secret_name,
                    "p_description": f"Access token for {row['service_name']}",
                }).execute()

                update_data = {"updated_at": datetime.now(timezone.utc).isoformat()}
                if new_expiry:
                    if isinstance(new_expiry, datetime):
                        update_data["token_expires_at"] = new_expiry.isoformat()
                    else:
                        update_data["token_expires_at"] = str(new_expiry)

                await system_client.table("external_api_connections").update(
                    update_data
                ).eq("id", self.connection_id).execute()

        except Exception as e:
            logger.error(f"Failed to update stored token for connection {self.connection_id}: {e}")


# --- Tool input schemas ---

class SearchCalendarInput(BaseModel):
    """Input schema for calendar search tool."""

    date_from: Optional[str] = Field(
        default=None,
        description="Start date/time in ISO format (e.g., '2026-03-04' or '2026-03-04T09:00:00'). Defaults to now.",
    )
    date_to: Optional[str] = Field(
        default=None,
        description="End date/time in ISO format. Defaults to end of today.",
    )
    query: Optional[str] = Field(
        default=None,
        description="Free-text search query to filter events (e.g., 'standup', 'dentist').",
    )
    max_results: int = Field(
        default=10, ge=1, le=25,
        description="Maximum number of events to return (1-25, default 10).",
    )
    account: Optional[str] = Field(
        default=None,
        description="Email address of a specific calendar account to search. Omit to search ALL connected calendars.",
    )


class GetCalendarEventInput(BaseModel):
    """Input schema for get calendar event tool."""

    event_id: str = Field(..., description="Google Calendar event ID to retrieve.")
    account: Optional[str] = Field(
        default=None,
        description="Email address of the calendar account this event belongs to.",
    )


# --- Base tool class ---

class BaseCalendarTool(BaseTool):
    """Base class for database-driven calendar tools."""

    user_id: str = Field(..., description="User ID for scoping")
    agent_name: str = Field(..., description="Agent name for context")
    supabase_url: str = Field(..., description="Supabase URL")
    supabase_key: str = Field(..., description="Supabase key")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)


# --- Search Calendar Tool ---

class SearchCalendarTool(BaseCalendarTool):
    """Search Google Calendar for events."""

    name: str = "search_calendar"
    description: str = (
        "Search your Google Calendar for events. Returns event titles, times, "
        "locations, and attendees. Defaults to today's events if no date range specified. "
        "Optionally specify an account email to search a specific calendar."
    )
    args_schema: Type[BaseModel] = SearchCalendarInput

    @classmethod
    def prompt_section(cls, channel: str) -> str | None:
        """Return behavioral guidance for the agent prompt."""
        if channel in ("web", "telegram"):
            return (
                "Calendar: Use search_calendar to check the user's schedule. "
                "Reference calendar events when giving advice about timing, scheduling, "
                "or priorities. Cross-reference attendees with email contacts when relevant. "
                "When the user asks 'what's on my calendar' or 'am I free tomorrow', use this tool. "
                "If the user has multiple calendar accounts, results are grouped by account."
            )
        elif channel == "heartbeat":
            return (
                "Calendar: Check today's upcoming events using search_calendar. "
                "Mention any events starting in the next 2 hours."
            )
        elif channel == "scheduled":
            return None
        else:
            return (
                "Calendar: Use search_calendar to check the user's schedule. "
                "When the user asks about meetings or availability, use this tool."
            )

    def _run(
        self,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        query: Optional[str] = None,
        max_results: int = 10,
        account: Optional[str] = None,
    ) -> str:
        return "Calendar search tool requires async execution. Use the async version (_arun)."

    async def _arun(
        self,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        query: Optional[str] = None,
        max_results: int = 10,
        account: Optional[str] = None,
    ) -> str:
        """Search calendar events, optionally across all accounts."""
        try:
            time_min = _parse_datetime(date_from) if date_from else None
            time_max = _parse_datetime(date_to) if date_to else None

            context = "scheduler" if "background" in self.agent_name.lower() else "user"

            if account:
                provider = await CalendarToolProvider.get_provider_for_account(
                    self.user_id, account, context
                )
                events = await self._search_single(provider, time_min, time_max, query, max_results)
                return self._format_events(events, account)
            else:
                providers = await CalendarToolProvider.get_all_providers(self.user_id, context)

                if not providers:
                    return (
                        "Calendar not connected. Connect Google Calendar in "
                        "Settings > Integrations to enable this."
                    )

                if len(providers) == 1:
                    events = await self._search_single(
                        providers[0], time_min, time_max, query, max_results
                    )
                    return self._format_events(events, providers[0].account_email)

                # Multi-account search
                all_results = []
                for provider in providers:
                    try:
                        events = await self._search_single(
                            provider, time_min, time_max, query, max_results
                        )
                        all_results.append({
                            "account": provider.account_email,
                            "events": events,
                        })
                    except Exception as e:
                        all_results.append({
                            "account": provider.account_email,
                            "error": str(e),
                        })

                return self._format_multi_results(all_results)

        except ValueError as e:
            # Connection not found, credentials expired, etc.
            return str(e)
        except Exception as e:
            logger.error(f"Calendar search failed for user {self.user_id}: {e}")
            return f"Calendar search failed: {str(e)}"

    async def _search_single(
        self,
        provider: CalendarToolProvider,
        time_min: Optional[datetime],
        time_max: Optional[datetime],
        query: Optional[str],
        max_results: int,
    ) -> list[dict]:
        """Execute search on a single account."""
        credentials = await provider.get_credentials()
        svc = _get_calendar_service()(credentials)
        return svc.list_events(
            time_min=time_min,
            time_max=time_max,
            max_results=max_results,
            query=query,
        )

    def _format_events(self, events: list[dict], account: str) -> str:
        """Format events for a single account."""
        if not events:
            return f"[{account}]\nNo events found for the specified date range."

        lines = [f"[{account}]"]
        for i, ev in enumerate(events, 1):
            start = ev.get("start", "")
            end = ev.get("end", "")
            title = ev.get("title", "(No title)")
            location = ev.get("location", "")
            attendees = ev.get("attendees", [])

            line = f"{i}. {title} | {start} - {end}"
            if location:
                line += f" | {location}"
            if attendees:
                names = [a.get("name") or a.get("email", "") for a in attendees[:5]]
                line += f" | with: {', '.join(names)}"
                if len(attendees) > 5:
                    line += f" (+{len(attendees) - 5} more)"
            lines.append(line)

        return "\n".join(lines)

    def _format_multi_results(self, all_results: list) -> str:
        """Format multi-account results grouped by account."""
        parts = []
        for item in all_results:
            account = item["account"]
            if "error" in item:
                parts.append(f"=== {account} (error) ===\n{item['error']}")
            else:
                events = item["events"]
                if not events:
                    parts.append(f"=== {account} ===\nNo events found.")
                else:
                    formatted = self._format_events(events, account)
                    parts.append(f"=== {account} ===\n{formatted}")
        return "\n\n".join(parts)


# --- Get Calendar Event Tool ---

class GetCalendarEventTool(BaseCalendarTool):
    """Get full details for a specific calendar event."""

    name: str = "get_calendar_event"
    description: str = (
        "Get full details for a specific calendar event by ID. "
        "Returns description, attendees, conferencing info, and location."
    )
    args_schema: Type[BaseModel] = GetCalendarEventInput

    def _run(self, event_id: str, account: Optional[str] = None) -> str:
        return "Get calendar event tool requires async execution. Use the async version (_arun)."

    async def _arun(self, event_id: str, account: Optional[str] = None) -> str:
        """Get full event details from a specific account."""
        try:
            context = "scheduler" if "background" in self.agent_name.lower() else "user"

            if account:
                provider = await CalendarToolProvider.get_provider_for_account(
                    self.user_id, account, context
                )
            else:
                providers = await CalendarToolProvider.get_all_providers(self.user_id, context)
                if not providers:
                    return (
                        "Calendar not connected. Connect Google Calendar in "
                        "Settings > Integrations to enable this."
                    )
                # Try each provider until event is found
                for provider in providers:
                    try:
                        credentials = await provider.get_credentials()
                        svc = _get_calendar_service()(credentials)
                        event = svc.get_event(event_id)
                        return self._format_event_detail(event, provider.account_email)
                    except Exception:
                        continue
                return f"Event {event_id} not found in any connected calendar account."

            credentials = await provider.get_credentials()
            svc = _get_calendar_service()(credentials)
            event = svc.get_event(event_id)
            return self._format_event_detail(event, account)

        except ValueError as e:
            return str(e)
        except Exception as e:
            logger.error(f"Get calendar event failed for user {self.user_id}: {e}")
            return f"Failed to get calendar event: {str(e)}"

    def _format_event_detail(self, event: dict, account: str) -> str:
        """Format full event details."""
        lines = [f"[{account}]"]
        lines.append(f"Title: {event.get('title', '(No title)')}")
        lines.append(f"Start: {event.get('start', '')}")
        lines.append(f"End: {event.get('end', '')}")
        lines.append(f"Status: {event.get('status', '')}")

        if event.get("location"):
            lines.append(f"Location: {event['location']}")
        if event.get("description"):
            lines.append(f"Description: {event['description']}")
        if event.get("hangout_link"):
            lines.append(f"Video call: {event['hangout_link']}")
        if event.get("html_link"):
            lines.append(f"Link: {event['html_link']}")
        if event.get("creator"):
            lines.append(f"Creator: {event['creator']}")
        if event.get("organizer"):
            lines.append(f"Organizer: {event['organizer']}")

        attendees = event.get("attendees", [])
        if attendees:
            lines.append("Attendees:")
            for a in attendees:
                name = a.get("name") or a.get("email", "")
                response = a.get("response", "")
                lines.append(f"  - {name} ({response})")

        return "\n".join(lines)


# --- Helper ---

def _parse_datetime(value: str) -> datetime:
    """Parse ISO datetime string, handling date-only format."""
    try:
        dt = datetime.fromisoformat(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        raise ValueError(f"Invalid date/time format: {value}. Use ISO format (e.g., '2026-03-04T09:00:00').")
