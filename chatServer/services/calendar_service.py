"""Read-only Google Calendar API wrapper.

Provides list_events and get_event methods using google-api-python-client.
Follows the same sync-in-async pattern as Gmail tools (API calls are brief <1s).
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)


class CalendarService:
    """Read-only Google Calendar API wrapper."""

    def __init__(self, credentials: Credentials):
        self.service = build("calendar", "v3", credentials=credentials)

    def list_events(
        self,
        time_min: Optional[datetime] = None,
        time_max: Optional[datetime] = None,
        max_results: int = 10,
        query: Optional[str] = None,
    ) -> list[dict]:
        """List calendar events in a time range.

        Args:
            time_min: Start of range (default: now)
            time_max: End of range (default: end of today)
            max_results: Max events to return (1-25)
            query: Optional free-text search filter

        Returns:
            List of normalized event dicts.
        """
        if time_min is None:
            time_min = datetime.now(timezone.utc)
        if time_max is None:
            time_max = time_min.replace(hour=23, minute=59, second=59)

        kwargs = {
            "calendarId": "primary",
            "timeMin": time_min.isoformat(),
            "timeMax": time_max.isoformat(),
            "maxResults": min(max_results, 25),
            "singleEvents": True,
            "orderBy": "startTime",
        }
        if query:
            kwargs["q"] = query

        result = self.service.events().list(**kwargs).execute()
        events = result.get("items", [])
        return [self._normalize_event(e) for e in events]

    def get_event(self, event_id: str) -> dict:
        """Get full details for a single event."""
        event = self.service.events().get(
            calendarId="primary", eventId=event_id
        ).execute()
        return self._normalize_event(event, full=True)

    def _normalize_event(self, event: dict, full: bool = False) -> dict:
        """Normalize a Google Calendar event to a consistent format.

        Handles both dateTime (timed events) and date (all-day events).
        """
        start = event.get("start", {})
        end = event.get("end", {})
        normalized = {
            "id": event.get("id", ""),
            "title": event.get("summary", "(No title)"),
            "start": start.get("dateTime", start.get("date", "")),
            "end": end.get("dateTime", end.get("date", "")),
            "location": event.get("location", ""),
            "status": event.get("status", ""),
            "attendees": [
                {
                    "email": a.get("email", ""),
                    "name": a.get("displayName", ""),
                    "response": a.get("responseStatus", ""),
                }
                for a in event.get("attendees", [])
            ],
        }
        if full:
            normalized["description"] = event.get("description", "")
            normalized["hangout_link"] = event.get("hangoutLink", "")
            normalized["html_link"] = event.get("htmlLink", "")
            normalized["creator"] = event.get("creator", {}).get("email", "")
            normalized["organizer"] = event.get("organizer", {}).get("email", "")
        return normalized
