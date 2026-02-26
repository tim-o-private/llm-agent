# SPEC-027: Google Calendar Integration

> **Status:** Draft
> **Author:** Tim + Claude (Product)
> **Created:** 2026-02-24
> **Updated:** 2026-02-24
> **PRD:** PRD-002 (Expand the World), Workstream 1

## Goal

Give the agent read-only access to the user's Google Calendar so it can reference today's schedule in conversation, cross-reference calendar events with email contacts, and provide calendar context in session_open bootstrap. This is an Inform-tier capability — the agent sees the calendar and tells the user what it notices. No event creation or modification.

## Prior Work

Significant groundwork already exists:

- **DB:** `external_api_connections.service_name` CHECK constraint already includes `google_calendar`
- **Models:** `ServiceName` enum in `chatServer/models/external_api.py` includes `GOOGLE_CALENDAR`
- **Auth:** `VaultToLangChainCredentialAdapter.fetch_or_refresh_calendar_credentials()` exists in `chatServer/services/langchain_auth_bridge.py` — fetches `google.oauth2.credentials.Credentials` with `calendar.readonly` scope
- **Frontend:** `Integrations.tsx` has a "Coming Soon" placeholder for Google Calendar

What's missing: calendar tools, calendar service, OAuth scope in the frontend OAuth flow, and prompt/bootstrap integration.

## Acceptance Criteria

### Backend: Calendar Service & Tools

- [ ] **AC-01:** A `CalendarService` class in `chatServer/services/calendar_service.py` provides `list_events(credentials, time_min, time_max, max_results)` and `get_event(credentials, event_id)` methods. Uses the Google Calendar API via `google-api-python-client`. [A1, A6]
- [ ] **AC-02:** Agent has a `search_calendar` tool that accepts optional date range and query parameters, returns a formatted list of events (title, start/end time, location, attendees). Default range: today. [A6, A10]
- [ ] **AC-03:** Agent has a `get_calendar_event` tool that accepts an event ID and returns full event details including description, attendees, location, and conferencing info. [A6, A10]
- [ ] **AC-04:** Both tools are registered in `agent_tools` with type `SearchCalendarTool` and `GetCalendarEventTool`, linked to the `assistant` agent. [A6]
- [ ] **AC-05:** Both tools have approval tier `AUTO_APPROVE` (read-only). [A6]
- [ ] **AC-06:** Tools gracefully handle missing calendar connection: return "Calendar not connected. Connect Google Calendar in Settings > Integrations to enable this." [A6]
- [ ] **AC-07:** Tools handle expired/invalid credentials by attempting refresh via the existing `VaultToLangChainCredentialAdapter` flow. If refresh fails, return a user-friendly reconnect message. [A6]
- [ ] **AC-08:** `google-api-python-client` is listed in both `requirements.txt` files (may already be present via Gmail dependency — verify, don't duplicate). [Cross-domain gotcha #1]

### Frontend: Calendar OAuth Flow

- [ ] **AC-09:** The Integrations page replaces the "Coming Soon" Calendar placeholder with a functional connect/disconnect flow, reusing the Gmail OAuth pattern. [F1]
- [ ] **AC-10:** The OAuth consent URL includes `https://www.googleapis.com/auth/calendar.readonly` scope. Calendar is a separate connection from Gmail (separate `external_api_connections` row with `service_name='google_calendar'`). [A3]
- [ ] **AC-11:** After connecting, the Calendar card shows connected state with the Google account email and a disconnect button. [F1]

### Prompt Integration

- [ ] **AC-12:** `prompt_builder.py` session_open bootstrap context includes today's calendar events (if calendar is connected). Format: event count + next 3 events with times. Fetched during pre-computation alongside task/reminder/email counts. [A14]
- [ ] **AC-13:** Calendar tool `prompt_section()` provides behavioral guidance: use calendar context to inform advice, cross-reference attendees with email contacts, mention upcoming events when relevant. [A6]

### Testing

- [ ] **AC-14:** Unit tests cover: `CalendarService.list_events` happy path, empty calendar, credential error, date range filtering. [A6]
- [ ] **AC-15:** Unit tests cover: `search_calendar` tool formatted output, no-connection error, `get_calendar_event` tool output. [A6]
- [ ] **AC-16:** Frontend test: Calendar connect/disconnect flow renders correctly. [F1]

## Scope

### Files to Create

| File | Purpose |
|------|---------|
| `chatServer/services/calendar_service.py` | Service wrapping Google Calendar API |
| `chatServer/tools/calendar_tools.py` | `SearchCalendarTool` and `GetCalendarEventTool` BaseTool subclasses |
| `tests/chatServer/services/test_calendar_service.py` | Unit tests for CalendarService |
| `tests/chatServer/tools/test_calendar_tools.py` | Unit tests for calendar tools |
| `supabase/migrations/2026MMDD000001_register_calendar_tools.sql` | DB registration migration |

### Files to Modify

| File | Change |
|------|--------|
| `src/core/agent_loader_db.py` | Add `SearchCalendarTool`, `GetCalendarEventTool` to `TOOL_REGISTRY` |
| `chatServer/security/approval_tiers.py` | Add `search_calendar`, `get_calendar_event` entries |
| `chatServer/services/prompt_builder.py` | Add calendar context to session_open pre-computation |
| `webApp/src/pages/Settings/Integrations.tsx` | Replace "Coming Soon" with functional Calendar OAuth flow |

### Out of Scope

- Creating, modifying, or deleting calendar events (Act-tier, future SPEC)
- RSVP management
- Multiple calendar support within one Google account (process primary calendar only for MVP)
- Non-Google calendar providers (Outlook, iCal)
- Recurring event pattern analysis (future — briefings SPEC may address)
- Calendar-based scheduling suggestions

## Technical Approach

### 1. CalendarService (`chatServer/services/calendar_service.py`)

Thin service wrapping the Google Calendar API. Follows the same pattern as Gmail tools' direct API usage.

```python
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
        """Normalize a Google Calendar event to a consistent format."""
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
                {"email": a.get("email", ""), "name": a.get("displayName", ""), "response": a.get("responseStatus", "")}
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
```

Note: `googleapiclient` methods are synchronous. Like Gmail tools, we call them from `_arun` directly. The API calls are brief (<1s typical).

### 2. Calendar Tools (`chatServer/tools/calendar_tools.py`)

Two tools following the `gmail_tools.py` pattern for credential fetching.

```python
class SearchCalendarTool(BaseTool):
    name: str = "search_calendar"
    description: str = (
        "Search your Google Calendar for events. Returns event titles, times, "
        "locations, and attendees. Defaults to today's events if no date range specified."
    )
    # ... args_schema with optional date_from, date_to, query, max_results

    @classmethod
    def prompt_section(cls, channel: str) -> str | None:
        return (
            "Calendar: Use search_calendar to check the user's schedule. "
            "Reference calendar events when giving advice about timing, scheduling, "
            "or priorities. Cross-reference attendees with email contacts when relevant. "
            "When the user asks 'what's on my calendar' or 'am I free tomorrow', use this tool."
        )

class GetCalendarEventTool(BaseTool):
    name: str = "get_calendar_event"
    description: str = (
        "Get full details for a specific calendar event by ID. "
        "Returns description, attendees, conferencing info, and location."
    )
    # ... args_schema with event_id
```

Credential fetching uses `VaultToLangChainCredentialAdapter.fetch_or_refresh_calendar_credentials()` — already implemented.

### 3. Frontend OAuth Flow

The Integrations page already has the Gmail connect pattern. Calendar reuses it:

- Same Google OAuth redirect URL, different scope (`calendar.readonly`)
- Stores as separate `external_api_connections` row with `service_name='google_calendar'`
- Frontend calls `POST /api/external/connections` with `service_name: "google_calendar"` after OAuth callback

The Google OAuth consent screen may need `calendar.readonly` scope added in the Google Cloud Console. This is a manual configuration step, not code.

### 4. Session Open Bootstrap

In `prompt_builder.py`, the `_compute_section_values()` method already pre-fetches task counts, reminder counts, and email summaries. Add calendar:

```python
# In _compute_section_values or the pre-computation step:
calendar_summary = ""
try:
    # Check if user has calendar connected
    # If yes, fetch today's events (3 max for bootstrap context)
    calendar_summary = f"Today's calendar: {event_count} events. Next: {next_events_summary}"
except Exception:
    pass  # Calendar not connected or error — skip silently
```

### 5. DB Registration (Migration)

```sql
ALTER TYPE agent_tool_type ADD VALUE IF NOT EXISTS 'SearchCalendarTool';
ALTER TYPE agent_tool_type ADD VALUE IF NOT EXISTS 'GetCalendarEventTool';

INSERT INTO agent_tools (agent_id, tool_name, type, tool_config, is_active, "order")
SELECT ac.id, 'search_calendar', 'SearchCalendarTool'::agent_tool_type,
    '{}'::jsonb, true,
    (SELECT COALESCE(MAX("order"), 0) + 1 FROM agent_tools WHERE agent_id = ac.id)
FROM agent_configurations ac WHERE ac.agent_name = 'assistant';

INSERT INTO agent_tools (agent_id, tool_name, type, tool_config, is_active, "order")
SELECT ac.id, 'get_calendar_event', 'GetCalendarEventTool'::agent_tool_type,
    '{}'::jsonb, true,
    (SELECT COALESCE(MAX("order"), 0) + 1 FROM agent_tools WHERE agent_id = ac.id)
FROM agent_configurations ac WHERE ac.agent_name = 'assistant';
```

### Dependencies

- `google-api-python-client` (likely already installed for Gmail — verify)
- No new database tables
- Google Cloud Console: add `calendar.readonly` scope to OAuth consent screen (manual step)
- New env vars: none (uses existing `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`)

## Testing Requirements

### Unit Tests (required)

**`tests/chatServer/services/test_calendar_service.py`:**
- Test `list_events` returns normalized event list (mock Google API)
- Test `list_events` with empty calendar returns empty list
- Test `list_events` with date range passes correct params
- Test `list_events` with query filter
- Test `get_event` returns full event details
- Test `_normalize_event` handles missing fields gracefully

**`tests/chatServer/tools/test_calendar_tools.py`:**
- Test `search_calendar` `_arun` happy path returns formatted output
- Test `search_calendar` without calendar connection returns helpful message
- Test `search_calendar` with expired credentials returns reconnect message
- Test `get_calendar_event` `_arun` happy path
- Test `prompt_section` returns guidance string

### AC-to-Test Mapping

| AC | Test Type | Test Function |
|----|-----------|---------------|
| AC-01 | Unit | `test_list_events`, `test_get_event` |
| AC-02 | Unit | `test_search_calendar_formatted_output` |
| AC-03 | Unit | `test_get_calendar_event_output` |
| AC-05 | Unit | `test_approval_tier_auto_approve` |
| AC-06 | Unit | `test_no_connection_message` |
| AC-07 | Unit | `test_expired_credentials_message` |
| AC-13 | Unit | `test_prompt_section_content` |
| AC-14 | Unit | All CalendarService tests |
| AC-15 | Unit | All calendar tool tests |

### Manual Verification (UAT)

- [ ] Connect Google Calendar in Settings > Integrations
- [ ] Ask agent: "What's on my calendar today?"
- [ ] Verify agent uses `search_calendar` and returns formatted events
- [ ] Ask agent: "Tell me about my 3pm meeting" — verify it fetches event details
- [ ] Start new session — verify session_open mentions calendar context
- [ ] Disconnect Calendar — verify agent handles missing connection gracefully
- [ ] Ask agent about scheduling — verify it references calendar proactively

## Edge Cases

- **No calendar connected:** Tool returns helpful message pointing to Settings. Not an error.
- **Empty calendar:** Tool returns "No events found for [date range]." Not an error.
- **All-day events:** `start` field uses `date` key instead of `dateTime`. Normalization handles both.
- **Expired credentials:** Auth bridge handles refresh automatically. If refresh fails, tool returns reconnect message.
- **Timezone handling:** Google Calendar API returns events in the calendar's timezone. The tool passes times as-is; the agent interprets them in conversation context. Future: consider user timezone in prompt context.
- **Multi-calendar accounts:** MVP processes only the `primary` calendar. Users with multiple Google accounts would connect each separately (same pattern as multi-Gmail from SPEC-008).
- **Rate limiting:** Google Calendar API has generous quota (1M queries/day). Not a concern.

## Functional Units (for PR Breakdown)

1. **FU-1: DB + Dependencies** (single branch, `feat/SPEC-027-calendar`)
   - Migration: register `SearchCalendarTool` and `GetCalendarEventTool`
   - Verify `google-api-python-client` is in both `requirements.txt`
   - Add approval tier entries
   - Assigned to: database-dev

2. **FU-2: Service + Tools + Tests**
   - Create `chatServer/services/calendar_service.py`
   - Create `chatServer/tools/calendar_tools.py`
   - Modify `src/core/agent_loader_db.py`: add to `TOOL_REGISTRY`
   - Create tests for service and tools
   - Add calendar context to `prompt_builder.py` session_open
   - Assigned to: backend-dev

3. **FU-3: Frontend OAuth Flow**
   - Update `Integrations.tsx`: replace Coming Soon with connect/disconnect
   - Frontend test for Calendar integration card
   - Assigned to: frontend-dev

### Merge Order

FU-1 → FU-2 → FU-3 (FU-2 depends on DB registration; FU-3 is independent of FU-2 but ships after for clean integration)

Note: FU-2 and FU-3 can run in parallel since FU-3 is frontend-only. Just both depend on FU-1 (migration).

## Completeness Checklist

- [x] Every AC has a stable ID (AC-01 through AC-16)
- [x] Every AC maps to at least one functional unit
- [x] Technical decisions reference principles (A1, A3, A6, A10, A14, F1)
- [x] Merge order is explicit and acyclic
- [x] Out-of-scope is explicit
- [x] Edge cases documented with expected behavior
- [x] Testing requirements map to ACs
- [x] Prior work documented (auth bridge, DB constraint, model enum)
- [x] Cross-domain gotchas addressed (dual requirements.txt)
