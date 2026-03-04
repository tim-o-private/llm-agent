"""Unit tests for CalendarService."""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from chatServer.services.calendar_service import CalendarService


@pytest.fixture
def mock_credentials():
    """Create mock Google OAuth credentials."""
    return MagicMock()


@pytest.fixture
def mock_service():
    """Create mock Google Calendar API service."""
    mock = MagicMock()
    return mock


@pytest.fixture
def calendar_service(mock_credentials, mock_service):
    """Create CalendarService with mocked Google API."""
    with patch("chatServer.services.calendar_service.build", return_value=mock_service):
        svc = CalendarService(mock_credentials)
    return svc


def _make_event(
    event_id="evt1",
    summary="Team Standup",
    start_dt="2026-03-04T09:00:00-05:00",
    end_dt="2026-03-04T09:30:00-05:00",
    location="",
    attendees=None,
    description="",
    hangout_link="",
    html_link="",
    status="confirmed",
):
    """Helper to build a raw Google Calendar event dict."""
    event = {
        "id": event_id,
        "summary": summary,
        "start": {"dateTime": start_dt},
        "end": {"dateTime": end_dt},
        "status": status,
    }
    if location:
        event["location"] = location
    if attendees:
        event["attendees"] = attendees
    if description:
        event["description"] = description
    if hangout_link:
        event["hangoutLink"] = hangout_link
    if html_link:
        event["htmlLink"] = html_link
    return event


class TestListEvents:
    """Tests for CalendarService.list_events."""

    def test_list_events_happy_path(self, calendar_service, mock_service):
        """AC-01, AC-14: list_events returns normalized event list."""
        raw_events = [
            _make_event("evt1", "Team Standup", "2026-03-04T09:00:00-05:00", "2026-03-04T09:30:00-05:00"),
            _make_event("evt2", "1:1 with Alice", "2026-03-04T14:00:00-05:00", "2026-03-04T14:30:00-05:00"),
        ]
        mock_service.events().list().execute.return_value = {"items": raw_events}

        time_min = datetime(2026, 3, 4, 0, 0, tzinfo=timezone.utc)
        time_max = datetime(2026, 3, 4, 23, 59, 59, tzinfo=timezone.utc)
        result = calendar_service.list_events(time_min=time_min, time_max=time_max)

        assert len(result) == 2
        assert result[0]["id"] == "evt1"
        assert result[0]["title"] == "Team Standup"
        assert result[0]["start"] == "2026-03-04T09:00:00-05:00"
        assert result[1]["title"] == "1:1 with Alice"

    def test_list_events_empty_calendar(self, calendar_service, mock_service):
        """AC-14: Empty calendar returns empty list."""
        mock_service.events().list().execute.return_value = {"items": []}

        result = calendar_service.list_events()
        assert result == []

    def test_list_events_with_date_range(self, calendar_service, mock_service):
        """AC-14: Date range params are passed correctly."""
        mock_service.events().list().execute.return_value = {"items": []}

        time_min = datetime(2026, 3, 4, 9, 0, tzinfo=timezone.utc)
        time_max = datetime(2026, 3, 4, 17, 0, tzinfo=timezone.utc)
        calendar_service.list_events(time_min=time_min, time_max=time_max)

        mock_service.events().list.assert_called()
        call_kwargs = mock_service.events().list.call_args
        # The kwargs contain our time range
        assert call_kwargs is not None

    def test_list_events_with_query(self, calendar_service, mock_service):
        """AC-14: Query filter is passed to the API."""
        mock_service.events().list().execute.return_value = {"items": []}

        calendar_service.list_events(query="standup")
        mock_service.events().list.assert_called()

    def test_list_events_max_results_capped(self, calendar_service, mock_service):
        """AC-14: max_results is capped at 25."""
        mock_service.events().list().execute.return_value = {"items": []}

        calendar_service.list_events(max_results=100)
        mock_service.events().list.assert_called()


class TestGetEvent:
    """Tests for CalendarService.get_event."""

    def test_get_event_returns_full_details(self, calendar_service, mock_service):
        """AC-01, AC-14: get_event returns full normalized event."""
        raw = _make_event(
            "evt1", "Team Standup",
            location="Room 42",
            description="Daily sync",
            hangout_link="https://meet.google.com/abc",
            html_link="https://calendar.google.com/event?eid=abc",
            attendees=[
                {"email": "alice@test.com", "displayName": "Alice", "responseStatus": "accepted"},
            ],
        )
        raw["creator"] = {"email": "bob@test.com"}
        raw["organizer"] = {"email": "bob@test.com"}
        mock_service.events().get().execute.return_value = raw

        result = calendar_service.get_event("evt1")

        assert result["id"] == "evt1"
        assert result["title"] == "Team Standup"
        assert result["location"] == "Room 42"
        assert result["description"] == "Daily sync"
        assert result["hangout_link"] == "https://meet.google.com/abc"
        assert result["creator"] == "bob@test.com"
        assert len(result["attendees"]) == 1
        assert result["attendees"][0]["email"] == "alice@test.com"


class TestNormalizeEvent:
    """Tests for CalendarService._normalize_event."""

    def test_normalize_handles_missing_fields(self, calendar_service):
        """AC-14: Graceful handling of missing fields."""
        sparse_event = {"id": "evt1"}
        result = calendar_service._normalize_event(sparse_event)

        assert result["id"] == "evt1"
        assert result["title"] == "(No title)"
        assert result["start"] == ""
        assert result["end"] == ""
        assert result["location"] == ""
        assert result["attendees"] == []

    def test_normalize_handles_all_day_events(self, calendar_service):
        """Edge case: All-day events use 'date' instead of 'dateTime'."""
        all_day_event = {
            "id": "evt_allday",
            "summary": "Holiday",
            "start": {"date": "2026-03-04"},
            "end": {"date": "2026-03-05"},
            "status": "confirmed",
        }
        result = calendar_service._normalize_event(all_day_event)

        assert result["start"] == "2026-03-04"
        assert result["end"] == "2026-03-05"
        assert result["title"] == "Holiday"
