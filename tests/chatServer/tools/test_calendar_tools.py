"""Unit tests for calendar tools."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from chatServer.tools.calendar_tools import (
    CalendarToolProvider,
    GetCalendarEventTool,
    SearchCalendarTool,
)

# --- Fixtures ---

@pytest.fixture
def tool_kwargs():
    """Common kwargs for tool instantiation."""
    return {
        "user_id": "test-user-123",
        "agent_name": "assistant",
        "supabase_url": "https://test.supabase.co",
        "supabase_key": "test-key",
    }


@pytest.fixture
def search_tool(tool_kwargs):
    return SearchCalendarTool(**tool_kwargs)


@pytest.fixture
def get_event_tool(tool_kwargs):
    return GetCalendarEventTool(**tool_kwargs)


def _make_provider(account_email="user@test.com", events=None):
    """Create a mock CalendarToolProvider."""
    provider = MagicMock()
    provider.account_email = account_email
    provider._account_email = account_email
    mock_creds = MagicMock()
    provider.get_credentials = AsyncMock(return_value=mock_creds)
    return provider


def _make_event(event_id="evt1", title="Team Standup", start="2026-03-04T09:00:00-05:00", end="2026-03-04T09:30:00-05:00", location="", attendees=None):  # noqa: E501
    """Create a normalized event dict."""
    return {
        "id": event_id,
        "title": title,
        "start": start,
        "end": end,
        "location": location,
        "status": "confirmed",
        "attendees": attendees or [],
    }


# --- SearchCalendarTool tests ---

class TestSearchCalendarTool:
    """Tests for SearchCalendarTool."""

    @pytest.mark.asyncio
    async def test_search_happy_path(self, search_tool):
        """AC-02, AC-15: search_calendar returns formatted output."""
        provider = _make_provider("user@test.com")
        events = [
            _make_event("evt1", "Team Standup", "2026-03-04T09:00:00-05:00", "2026-03-04T09:30:00-05:00"),
            _make_event("evt2", "Lunch", "2026-03-04T12:00:00-05:00", "2026-03-04T13:00:00-05:00"),
        ]

        with patch.object(CalendarToolProvider, "get_all_providers", new_callable=AsyncMock, return_value=[provider]):
            with patch("chatServer.tools.calendar_tools.CalendarService") as MockSvc:
                MockSvc.return_value.list_events.return_value = events
                result = await search_tool._arun()

        assert "[user@test.com]" in result
        assert "Team Standup" in result
        assert "Lunch" in result

    @pytest.mark.asyncio
    async def test_search_no_connection(self, search_tool):
        """AC-06, AC-15: No connection returns helpful message."""
        with patch.object(CalendarToolProvider, "get_all_providers", new_callable=AsyncMock, return_value=[]):
            result = await search_tool._arun()

        assert "Calendar not connected" in result
        assert "Settings > Integrations" in result

    @pytest.mark.asyncio
    async def test_search_multi_account_aggregation(self, search_tool):
        """AC-15: Multi-account results grouped by account."""
        provider1 = _make_provider("work@test.com")
        provider2 = _make_provider("personal@test.com")
        events1 = [_make_event("evt1", "Work Meeting")]
        events2 = [_make_event("evt2", "Dentist")]

        with patch.object(CalendarToolProvider, "get_all_providers", new_callable=AsyncMock, return_value=[provider1, provider2]):  # noqa: E501
            with patch("chatServer.tools.calendar_tools.CalendarService") as MockSvc:
                MockSvc.return_value.list_events.side_effect = [events1, events2]
                result = await search_tool._arun()

        assert "work@test.com" in result
        assert "personal@test.com" in result
        assert "Work Meeting" in result
        assert "Dentist" in result

    @pytest.mark.asyncio
    async def test_search_specific_account(self, search_tool):
        """AC-15: Searching a specific account by email."""
        provider = _make_provider("work@test.com")
        events = [_make_event("evt1", "Work Meeting")]

        with patch.object(CalendarToolProvider, "get_provider_for_account", new_callable=AsyncMock, return_value=provider):  # noqa: E501
            with patch("chatServer.tools.calendar_tools.CalendarService") as MockSvc:
                MockSvc.return_value.list_events.return_value = events
                result = await search_tool._arun(account="work@test.com")

        assert "work@test.com" in result
        assert "Work Meeting" in result

    @pytest.mark.asyncio
    async def test_search_empty_calendar(self, search_tool):
        """AC-15: Empty calendar returns no-events message."""
        provider = _make_provider("user@test.com")

        with patch.object(CalendarToolProvider, "get_all_providers", new_callable=AsyncMock, return_value=[provider]):
            with patch("chatServer.tools.calendar_tools.CalendarService") as MockSvc:
                MockSvc.return_value.list_events.return_value = []
                result = await search_tool._arun()

        assert "No events found" in result

    @pytest.mark.asyncio
    async def test_search_expired_credentials(self, search_tool):
        """AC-07, AC-15: Expired credentials returns reconnect message."""
        with patch.object(
            CalendarToolProvider, "get_all_providers", new_callable=AsyncMock,
            side_effect=ValueError("Calendar connection expired for user@test.com. Please reconnect this account in Settings > Integrations.")  # noqa: E501
        ):
            result = await search_tool._arun()

        assert "expired" in result.lower() or "reconnect" in result.lower()


# --- GetCalendarEventTool tests ---

class TestGetCalendarEventTool:
    """Tests for GetCalendarEventTool."""

    @pytest.mark.asyncio
    async def test_get_event_happy_path(self, get_event_tool):
        """AC-03, AC-15: get_calendar_event returns full details."""
        provider = _make_provider("user@test.com")
        event = {
            "id": "evt1",
            "title": "Team Standup",
            "start": "2026-03-04T09:00:00-05:00",
            "end": "2026-03-04T09:30:00-05:00",
            "location": "Room 42",
            "status": "confirmed",
            "description": "Daily sync",
            "hangout_link": "https://meet.google.com/abc",
            "html_link": "https://calendar.google.com/event?eid=abc",
            "creator": "bob@test.com",
            "organizer": "bob@test.com",
            "attendees": [
                {"email": "alice@test.com", "name": "Alice", "response": "accepted"},
            ],
        }

        with patch.object(CalendarToolProvider, "get_provider_for_account", new_callable=AsyncMock, return_value=provider):  # noqa: E501
            with patch("chatServer.tools.calendar_tools.CalendarService") as MockSvc:
                MockSvc.return_value.get_event.return_value = event
                result = await get_event_tool._arun(event_id="evt1", account="user@test.com")

        assert "Team Standup" in result
        assert "Room 42" in result
        assert "Daily sync" in result
        assert "meet.google.com" in result
        assert "Alice" in result

    @pytest.mark.asyncio
    async def test_get_event_no_connection(self, get_event_tool):
        """AC-06: No calendar connection returns helpful message."""
        with patch.object(CalendarToolProvider, "get_all_providers", new_callable=AsyncMock, return_value=[]):
            result = await get_event_tool._arun(event_id="evt1")

        assert "Calendar not connected" in result


# --- CalendarToolProvider tests ---

class TestCalendarToolProvider:
    """Tests for CalendarToolProvider."""

    @pytest.mark.asyncio
    async def test_get_all_providers_returns_multiple(self):
        """AC-07b, AC-15: get_all_providers returns one provider per connection."""
        connections = [
            {"connection_id": "conn1", "service_user_email": "work@test.com", "access_token": "tok1"},
            {"connection_id": "conn2", "service_user_email": "personal@test.com", "access_token": "tok2"},
        ]
        with patch.object(CalendarToolProvider, "_get_calendar_connections", new_callable=AsyncMock, return_value=connections):  # noqa: E501
            providers = await CalendarToolProvider.get_all_providers("user-123")

        assert len(providers) == 2
        assert providers[0].account_email == "work@test.com"
        assert providers[1].account_email == "personal@test.com"

    @pytest.mark.asyncio
    async def test_get_provider_for_account_finds_correct(self):
        """AC-07b, AC-15: get_provider_for_account returns correct provider."""
        connections = [
            {"connection_id": "conn1", "service_user_email": "work@test.com", "access_token": "tok1"},
            {"connection_id": "conn2", "service_user_email": "personal@test.com", "access_token": "tok2"},
        ]
        with patch.object(CalendarToolProvider, "_get_calendar_connections", new_callable=AsyncMock, return_value=connections):  # noqa: E501
            provider = await CalendarToolProvider.get_provider_for_account("user-123", "personal@test.com")

        assert provider.account_email == "personal@test.com"
        assert provider.connection_id == "conn2"

    @pytest.mark.asyncio
    async def test_get_provider_for_account_not_found(self):
        """AC-07b: Raises ValueError when account not found."""
        connections = [
            {"connection_id": "conn1", "service_user_email": "work@test.com", "access_token": "tok1"},
        ]
        with patch.object(CalendarToolProvider, "_get_calendar_connections", new_callable=AsyncMock, return_value=connections):  # noqa: E501
            with pytest.raises(ValueError, match="No calendar connection found"):
                await CalendarToolProvider.get_provider_for_account("user-123", "unknown@test.com")


# --- prompt_section tests ---

class TestPromptSection:
    """Tests for tool prompt_section methods."""

    def test_search_calendar_prompt_section_web(self):
        """AC-13: prompt_section returns guidance for web channel."""
        result = SearchCalendarTool.prompt_section("web")
        assert result is not None
        assert "search_calendar" in result
        assert "schedule" in result.lower()

    def test_search_calendar_prompt_section_heartbeat(self):
        """AC-13: prompt_section returns heartbeat guidance."""
        result = SearchCalendarTool.prompt_section("heartbeat")
        assert result is not None
        assert "upcoming events" in result.lower()

    def test_search_calendar_prompt_section_scheduled_none(self):
        """AC-13: prompt_section returns None for scheduled channel."""
        result = SearchCalendarTool.prompt_section("scheduled")
        assert result is None
