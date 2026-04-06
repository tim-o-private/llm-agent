# SPEC-028: Morning & Evening Briefings

> **Status:** Draft (Revised)
> **Author:** Tim + Claude (Product)
> **Created:** 2026-02-24
> **Updated:** 2026-03-04

## Goal

Replace scattered notifications (heartbeat findings, email digests, reminders) with a single consolidated daily briefing. Morning: "Here's your day." Evening (optional): "Here's what happened and what's still open." The agent picks 3-5 most important things and explains why — opinionated, not a data dump. This is the flagship feature of Phase 2 and the clearest demonstration of Clarity's judgment.

## Background

Today the agent sends notifications piecemeal: a heartbeat finding here, an email digest there, a reminder somewhere else. A user might receive 4 separate pings across web and Telegram with no coherence. The morning briefing consolidates all of this into one message at a time the user chooses. Non-urgent heartbeat observations get saved for the next briefing instead of interrupting the user's day. Urgent items still surface immediately.

The evening briefing is optional (off by default) and serves a different purpose: "what happened today, what's still open, what's tomorrow." Users who want the closure can opt in via conversation.

### Infrastructure Available

- **Job queue (SPEC-026):** `JobService.create()` with `scheduled_for` for future scheduling. Self-scheduling pattern: handler enqueues the next occurrence on completion. `JobRunnerService` polls every 5s.
- **Notifications (SPEC-025):** `NotificationService.notify_user()` with markdown body, `type="notify"` for web + Telegram delivery, `category` for styling.
- **Bootstrap context (SPEC-021):** `BootstrapContextService.gather()` runs 4 parallel fetchers (tasks, reminders, email, calendar). Returns summary strings — briefings need the same data sources but richer formatting.
- **Scheduled execution (SPEC-021):** `ScheduledExecutionService.execute()` loads agent, invokes with prompt, stores result. Accepts a `schedule` dict with keys: `user_id`, `agent_name`, `prompt`, `config`, `id`. Supports `model_override` and `skip_notification` in `config`.
- **Calendar (SPEC-027):** `CalendarService.list_events()` via Google Calendar API. `CalendarToolProvider.get_all_providers()` for multi-account support.

### What Doesn't Exist Yet

- **User preferences table.** No structured storage for timezone, briefing time, or briefing enabled/disabled. The product-architecture primitives table says "use `UpdateInstructionsTool` or memory tools for user preferences" — but briefing schedules need reliable, queryable storage (not fuzzy memory retrieval). A `user_preferences` table is warranted here.
- **Heartbeat deferral.** Heartbeat findings that aren't urgent have no holding area — they fire immediately or get suppressed via `HEARTBEAT_OK`. Briefings need a place to accumulate deferred observations.
- **Briefing synthesis prompts.** Structured prompt templates that instruct the agent how to compose morning and evening briefings from raw context data.
- **Telegram markdown post-processing.** The synthesis prompt produces rich markdown (h3 headers, nested lists, bold). Telegram's legacy Markdown v1 doesn't support headers or nested lists. A post-processing step is needed.
- **`JobService.fail_by_type()`** — no method exists to fail all pending jobs for a given user+type combo (needed when user disables briefings).
- **First-use discovery signal.** `BootstrapContextService` doesn't check whether the user has configured briefings, so the agent has no signal to proactively offer setup.

### Design Decisions

1. **Briefings render as agent chat messages on web, NOT notification cards.** On web, briefings appear as regular agent messages in the chat stream with full markdown rendering (existing `MarkdownText` component). The notification pathway (`NotificationService.notify_user()`) is still used for Telegram delivery and for the notification record (read tracking, feedback buttons). But the web rendering is via the chat message, not a notification inline component. This eliminates the need for any frontend changes — no new components, no markdown renderer additions.

2. **Post-process markdown for Telegram.** The synthesis prompt produces rich markdown (bold, h3 headers, bullets). A `format_for_telegram()` helper strips/converts unsupported elements for Telegram's legacy Markdown v1 (no headers, no nested lists). The prompt can use the full output format contract without constraining for Telegram compatibility.

3. **Agent proactively offers briefing setup on first session.** `BootstrapContextService.gather()` detects when no `user_preferences` row exists and appends a note to the bootstrap context. The agent's soul/identity already instructs it to be proactive — this context gives it the signal to offer.

4. **All datetimes in UTC.** `user_preferences` stores timezone (IANA string) for scheduling math only. All `scheduled_for` values in the jobs table are UTC. Frontend renders in user's local tz.

## Acceptance Criteria

### Database

- [ ] **AC-01:** A `user_preferences` table exists with columns: `id` (UUID PK), `user_id` (UUID FK → auth.users, UNIQUE), `timezone` (TEXT NOT NULL DEFAULT 'America/New_York'), `morning_briefing_enabled` (BOOLEAN NOT NULL DEFAULT true), `morning_briefing_time` (TIME NOT NULL DEFAULT '07:30:00'), `evening_briefing_enabled` (BOOLEAN NOT NULL DEFAULT false), `evening_briefing_time` (TIME NOT NULL DEFAULT '20:00:00'), `briefing_sections` (JSONB NOT NULL DEFAULT '{"calendar": true, "tasks": true, "email": true, "observations": true}'), `created_at` (TIMESTAMPTZ NOT NULL DEFAULT NOW()), `updated_at` (TIMESTAMPTZ NOT NULL DEFAULT NOW()). RLS enabled with `is_record_owner(user_id)`. [A8, A9]
- [ ] **AC-02:** A `deferred_observations` table exists with columns: `id` (UUID PK), `user_id` (UUID FK → auth.users ON DELETE CASCADE), `content` (TEXT NOT NULL), `source` (TEXT NOT NULL DEFAULT 'heartbeat'), `created_at` (TIMESTAMPTZ NOT NULL DEFAULT NOW()), `consumed_at` (TIMESTAMPTZ). RLS enabled with `is_record_owner(user_id)`. Index on `(user_id, consumed_at)` for efficient retrieval of unconsumed observations. [A8, A9]
- [ ] **AC-03:** Both tables are registered in `USER_SCOPED_TABLES` in `chatServer/database/user_scoped_tables.py`. [A8]
- [ ] **AC-04:** `user_preferences` row is auto-created for new users via an `INSERT ... ON CONFLICT DO NOTHING` pattern when the briefing system first accesses a user's preferences (lazy initialization, no signup hook). [A14]
- [ ] **AC-05:** A `register_briefing_tools` migration registers `manage_briefing_preferences` in the `tools` table with `type='system'`, `approval_tier='auto'`, linked to the default agent via `agent_tools`. [A11]

### Backend: BriefingService

- [ ] **AC-06:** `BriefingService` class exists in `chatServer/services/briefing_service.py` with constructor accepting `db_client`. [A1, A10]
- [ ] **AC-07:** `BriefingService.generate_morning_briefing(user_id)` gathers context from 4 sources in parallel — calendar events (today), active/overdue tasks with due dates, recent emails with sender+subject (since last session or last 12 hours), and unconsumed deferred observations — then invokes the agent with a morning synthesis prompt using `ScheduledExecutionService().execute()` with the schedule dict interface (see Technical Approach §3). Returns the synthesized briefing text. [A1, A3]
- [ ] **AC-08:** `BriefingService.generate_evening_briefing(user_id)` gathers context from: tasks completed today, tasks still open with due dates, pending replies, and tomorrow's calendar — then invokes the agent with an evening synthesis prompt using `ScheduledExecutionService().execute()` with the same schedule dict interface. Returns the synthesized briefing text. [A1]
- [ ] **AC-09:** After generating a briefing, `BriefingService` delivers it via `NotificationService.notify_user()` with `type="notify"`, `category="briefing"`, and the synthesized markdown as `body`. For Telegram delivery, the body is post-processed via `format_for_telegram()` before passing to the notification service. [A7]
- [ ] **AC-10:** After generating a briefing, `BriefingService` marks all unconsumed `deferred_observations` for that user as consumed (`consumed_at = NOW()`). [A1]
- [ ] **AC-11:** `BriefingService.get_user_preferences(user_id)` returns the user's preferences row, lazily creating one with defaults if none exists. [A1]
- [ ] **AC-12:** `BriefingService.update_user_preferences(user_id, updates)` updates specific preference fields (timezone, morning_briefing_time, evening_briefing_enabled, etc.) and returns the updated row. [A1]

### Backend: Briefing Prompts

- [ ] **AC-32:** `chatServer/services/briefing_prompts.py` exists containing: `MORNING_BRIEFING_PROMPT` (300-word limit, 3-5 items, ordered by importance not category), `EVENING_BRIEFING_PROMPT` (250-word limit, reflective framing), `BRIEFING_SECTIONS_DEFAULT` dict, `BRIEFING_SECTION_KEYS` frozenset, `get_enabled_sections()` validation helper, and `_format_context_block()` helper that omits empty sections. [A1]
- [ ] **AC-33:** Context injection format uses tagged markdown sections (not JSON). Example: `## Calendar\n- 9:00 AM: Team standup\n- 2:00 PM: 1:1 with Sarah`. `_format_context_block(label, items)` returns empty string when `items` is empty, omitting the section entirely. [A1]
- [ ] **AC-34:** `BRIEFING_SECTIONS_DEFAULT` and `BRIEFING_SECTION_KEYS` define the JSONB schema for `briefing_sections`:
  ```python
  BRIEFING_SECTIONS_DEFAULT = {
      "calendar": True,
      "tasks": True,
      "email": True,
      "observations": True,
  }
  BRIEFING_SECTION_KEYS = frozenset(BRIEFING_SECTIONS_DEFAULT.keys())
  ```
  Validation rules: all keys must be in `BRIEFING_SECTION_KEYS` (reject unknowns), all values must be boolean (reject non-boolean truthy values like `"yes"`), `None`/null uses defaults, forward-compatible (future dict values like `{"enabled": true, "max_items": 3}` are truthy). [A1]

### Backend: Job Handlers

- [ ] **AC-13:** `handle_morning_briefing` async handler exists in `chatServer/services/job_handlers.py`, accepts a job dict with `input: {user_id}`, calls `BriefingService.generate_morning_briefing()`, and on completion self-schedules the next morning briefing job via `JobService.create()` with `scheduled_for` computed from the user's timezone + morning_briefing_time for the next day. Sets `expires_at = scheduled_for + timedelta(hours=4)` on the new job to prevent stale accumulation. [A1, A11]
- [ ] **AC-14:** `handle_evening_briefing` async handler exists in `chatServer/services/job_handlers.py`, follows the same pattern as AC-13 but for evening briefings. [A1, A11]
- [ ] **AC-15:** Both handlers are registered in `BackgroundTaskService.start_background_tasks()` via `job_runner.register_handler()`. Bootstrap must be awaited before the job runner starts. [A11]
- [ ] **AC-16:** If a briefing handler fails, the job retries via the standard `JobService.fail()` backoff. After `max_retries` exhausted, the next occurrence is still scheduled (failure of today's briefing must not break tomorrow's). [A14]

### Backend: Briefing Schedule Bootstrapping

- [ ] **AC-17:** On server startup, `BackgroundTaskService` runs a one-time bootstrap that queries all users with `morning_briefing_enabled=true` (or `evening_briefing_enabled=true`) and ensures each has a pending `morning_briefing` (or `evening_briefing`) job in the `jobs` table. If no pending/claimed/running job exists for that user+type, one is created with `scheduled_for` set to the next occurrence and `expires_at = scheduled_for + timedelta(hours=4)`. [A14]
- [ ] **AC-18:** When a user enables briefings via the tool (AC-20), the tool immediately creates the first briefing job with `scheduled_for` computed from their timezone and preferred time, and `expires_at = scheduled_for + timedelta(hours=4)`. If the preferred time has already passed today, schedules for tomorrow. [A1]
- [ ] **AC-19:** When a user disables briefings via the tool, any pending briefing jobs for that user and type are cancelled via `JobService.fail_by_type(user_id, job_type, 'Briefing disabled by user')`. [A1]

### Backend: `JobService.fail_by_type()`

- [ ] **AC-35:** `JobService.fail_by_type(user_id, job_type, error)` method exists in `chatServer/services/job_service.py`. Marks all pending jobs matching `user_id` + `job_type` as `failed` with `should_retry=False`, sets `error` and `completed_at = NOW()`. Returns count of affected rows. [A1]

### Backend: Briefing Preferences Tool

- [ ] **AC-20:** `ManageBriefingPreferencesTool` exists in `chatServer/tools/briefing_tools.py` as a `BaseTool` subclass. Accepts JSON input with `action` ("get", "update") and optional `preferences` dict. For "update", validates timezone against `zoneinfo.available_timezones()`, validates time format (HH:MM, normalized to HH:MM:SS for the TIME column), validates `briefing_sections` against `BRIEFING_SECTION_KEYS`, and calls `BriefingService.update_user_preferences()`. Creates/cancels briefing jobs as side effects per AC-18/AC-19. Uses `_get_briefing_service()` lazy import helper to avoid circular imports. [A6, A1]
- [ ] **AC-21:** The tool is registered in the `tools` table via migration with `type='system'`, `approval_tier='auto'` (no user approval needed to change their own briefing preferences). [A11]

### Backend: Heartbeat Deferral

- [ ] **AC-22:** `ScheduledExecutionService.execute()` is updated: after the agent invocation completes and `is_heartbeat_ok` is evaluated (step 7 in the current code), when `schedule_type == "heartbeat"` and the output is NOT `HEARTBEAT_OK`, instead of proceeding to the notification branch, the output is inserted into `deferred_observations` with `source='heartbeat'` and the notification is suppressed. This check goes BEFORE the `skip_notification` / `_notify_user()` branch — inline in `execute()`, NOT in `_notify_user()`. [A1]
- [ ] **AC-23:** If the user has `morning_briefing_enabled=false`, heartbeat findings are delivered immediately as before (no deferral). Deferral only applies when briefings will consume the observations. [A14]

### Backend: Telegram Post-Processing

- [ ] **AC-36:** `format_for_telegram(markdown: str) -> str` helper exists (in `briefing_service.py` or a shared utility). Strips `###` headers and converts to `**Header**\n` (bold text on its own line). Flattens nested lists to single-level. Preserves bold, italic, and flat bullet points. Ensures output stays under 4000 chars (Telegram hard limit is 4096, bot truncates at 4000). [A1]

### Backend: First-Use Discovery

- [ ] **AC-37:** `BootstrapContextService.gather()` checks for `user_preferences` row existence via a lightweight DB query. If no row exists, appends `"User hasn't configured morning briefings yet — you can offer to set this up."` to the bootstrap context string (added as a new field or appended to the render output). The agent's existing proactive behavior handles the rest. [A1, A14]

### Backend: Briefing-as-Chat-Message

- [ ] **AC-38:** When `BriefingService` invokes `ScheduledExecutionService.execute()`, it passes `skip_notification=True` in the config. The agent's response is stored as a chat message in `chat_sessions` (the standard `ScheduledExecutionService` behavior). The briefing also creates a notification record via `NotificationService.notify_user()` for Telegram delivery and read tracking/feedback. On web, the user sees the briefing as a regular chat message — no special rendering needed. [A1, A7]

### Testing

- [ ] **AC-26:** Unit tests exist for `BriefingService`: `generate_morning_briefing` (mocked agent invocation + context gathering), `get_user_preferences` (lazy creation), `update_user_preferences` (validation). [S1]
- [ ] **AC-27:** Unit tests exist for `handle_morning_briefing` and `handle_evening_briefing`: successful generation + self-scheduling, failure + self-scheduling of next occurrence, `expires_at` set correctly on self-scheduled jobs. [S1]
- [ ] **AC-28:** Unit test for `ManageBriefingPreferencesTool`: get preferences, update valid preferences, reject invalid timezone, reject invalid time format, reject invalid briefing_sections keys/values. [S1]
- [ ] **AC-29:** Unit test for heartbeat deferral: heartbeat output deferred to `deferred_observations` when briefings enabled, delivered immediately when briefings disabled. [S1]
- [ ] **AC-39:** Unit tests for `format_for_telegram()`: strips h3 headers to bold, flattens nested lists, preserves bold/italic/flat bullets, truncates output exceeding 4000 chars. [S1]
- [ ] **AC-40:** Unit tests for prompt assembly: `_format_context_block()` omits empty sections, `get_enabled_sections()` rejects unknown keys and non-boolean values, morning prompt stays within 300-word limit, evening prompt stays within 250-word limit. [S1]
- [ ] **AC-41:** Prompt scenario tests covering 5 cases: typical weekday morning (all sources populated), empty day (no events/tasks/email), crisis day (many overdue tasks + urgent emails), evening productive day (many tasks completed), no connected services (all sections unavailable). Each scenario verifies the assembled prompt contains the expected context blocks and the correct prompt template. [S1]
- [ ] **AC-31:** Integration test: full briefing lifecycle — create user preferences, create morning briefing job, handler runs, notification created, next job self-scheduled with correct `expires_at`. [S1]

## Scope

### Files to Create

| File | Purpose |
|------|---------|
| `supabase/migrations/2026MMDD000001_create_user_preferences.sql` | Create `user_preferences` table with indexes and RLS |
| `supabase/migrations/2026MMDD000002_create_deferred_observations.sql` | Create `deferred_observations` table with indexes and RLS |
| `supabase/migrations/2026MMDD000003_register_briefing_tools.sql` | Register `manage_briefing_preferences` tool in `tools` + `agent_tools` |
| `chatServer/services/briefing_service.py` | BriefingService — context gathering, agent invocation, preference CRUD, Telegram post-processing |
| `chatServer/services/briefing_prompts.py` | Prompt constants, JSONB schema definitions, context formatting helpers |
| `chatServer/tools/briefing_tools.py` | ManageBriefingPreferencesTool — conversational preference management |
| `tests/chatServer/services/test_briefing_service.py` | BriefingService unit tests |
| `tests/chatServer/services/test_briefing_handlers.py` | Briefing job handler tests (self-scheduling, failure recovery) |
| `tests/chatServer/services/test_briefing_prompts.py` | Prompt assembly tests, format_for_telegram tests, scenario tests |
| `tests/chatServer/tools/test_briefing_tools.py` | ManageBriefingPreferencesTool tests |

### Files to Modify

| File | Change |
|------|--------|
| `chatServer/services/job_handlers.py` | Add `handle_morning_briefing` and `handle_evening_briefing` handler functions |
| `chatServer/services/job_service.py` | Add `fail_by_type(user_id, job_type, error)` method |
| `chatServer/services/background_tasks.py` | Register briefing handlers; add startup bootstrap for briefing jobs; await bootstrap before starting job runner |
| `chatServer/services/scheduled_execution_service.py` | Add heartbeat deferral logic in `execute()` before the notification branch |
| `chatServer/services/bootstrap_context_service.py` | Add `user_preferences` existence check, append first-use discovery note |
| `chatServer/database/user_scoped_tables.py` | Add `"user_preferences"` and `"deferred_observations"` to `USER_SCOPED_TABLES` |

### Out of Scope

- **Briefing customization via conversation** ("skip email in my morning briefing") — the `briefing_sections` JSONB in `user_preferences` supports this, but the conversational UX for toggling sections is deferred. Users can only enable/disable entire morning/evening briefings and set times in this spec.
- **Settings UI for briefings** — all preference management is via conversation (the tool). No settings page.
- **Briefing history / archive** — briefings are delivered as notifications and chat messages. Users can scroll back. No separate briefing archive.
- **Multiple briefing times per day** — one morning, one evening. No arbitrary schedule.
- **Briefing for users without any connected services** — if a user has no email, no calendar, no tasks, the briefing has nothing to say. The agent should handle this gracefully ("nothing to report today") but we don't special-case it.
- **Non-Google calendar providers** — SPEC-027 is Google-only. Briefings consume whatever calendar data is available.
- **Timezone auto-detection** — user must tell the agent their timezone. Auto-detection from browser or IP is future scope.
- **Frontend changes** — briefings render as chat messages using the existing `MarkdownText` component. No new UI components or frontend work needed.

## Technical Approach

### 1. Database: `user_preferences` Table (FU-1)

A dedicated table is warranted here despite the architecture primitives recommending memory/instructions for preferences. Briefing schedules must be reliably queryable at server startup across all users — memory tool retrieval is per-user and probabilistic. The table is intentionally narrow (briefing prefs only) and will grow to hold other structured preferences in future specs.

```sql
CREATE TABLE user_preferences (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL UNIQUE REFERENCES auth.users(id) ON DELETE CASCADE,
    timezone TEXT NOT NULL DEFAULT 'America/New_York',
    morning_briefing_enabled BOOLEAN NOT NULL DEFAULT true,
    morning_briefing_time TIME NOT NULL DEFAULT '07:30:00',
    evening_briefing_enabled BOOLEAN NOT NULL DEFAULT false,
    evening_briefing_time TIME NOT NULL DEFAULT '20:00:00',
    briefing_sections JSONB NOT NULL DEFAULT '{"calendar": true, "tasks": true, "email": true, "observations": true}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE user_preferences ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Enable full access for record owners on user_preferences"
ON user_preferences FOR ALL
USING (public.is_record_owner(user_id))
WITH CHECK (public.is_record_owner(user_id));

CREATE POLICY "Service role can access all user_preferences"
ON user_preferences TO service_role USING (true) WITH CHECK (true);

CREATE INDEX idx_user_preferences_user ON user_preferences (user_id);

CREATE TRIGGER update_user_preferences_updated_at
BEFORE UPDATE ON user_preferences
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
```

> **Gotcha: TIME column returns `HH:MM:SS`.** User input will be `HH:MM`. Normalize to `HH:MM:SS` before writing (append `:00`), or handle both formats on read by stripping trailing `:00` when displaying to the user.

### 2. Database: `deferred_observations` Table (FU-1)

Heartbeat findings that aren't urgent accumulate here until the next briefing consumes them. Lightweight — just text + source + timestamp. Consumed observations are marked with `consumed_at` rather than deleted, providing an audit trail.

```sql
CREATE TABLE deferred_observations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT 'heartbeat',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    consumed_at TIMESTAMPTZ
);

ALTER TABLE deferred_observations ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Enable full access for record owners on deferred_observations"
ON deferred_observations FOR ALL
USING (public.is_record_owner(user_id))
WITH CHECK (public.is_record_owner(user_id));

CREATE POLICY "Service role can access all deferred_observations"
ON deferred_observations TO service_role USING (true) WITH CHECK (true);

CREATE INDEX idx_deferred_observations_unconsumed
ON deferred_observations (user_id, consumed_at)
WHERE consumed_at IS NULL;
```

### 3. BriefingService (FU-2)

The service is the core composition layer. It gathers signals, builds a synthesis prompt, invokes the agent, and delivers the result.

```python
# chatServer/services/briefing_service.py
class BriefingService:
    """Composes signals and generates daily briefings via LLM synthesis."""

    def __init__(self, db_client):
        self.db = db_client

    async def generate_morning_briefing(self, user_id: str) -> dict:
        """Gather context, invoke agent for synthesis, deliver notification.

        Returns: {"success": True, "briefing": str, "notification_id": str}
        """
        prefs = await self.get_user_preferences(user_id)
        sections = prefs.get("briefing_sections", {})

        # 1. Gather signals in parallel (richer than bootstrap — see below)
        context = await self._gather_morning_context(user_id, sections)

        # 2. Build synthesis prompt from briefing_prompts.py constants
        from chatServer.services.briefing_prompts import (
            MORNING_BRIEFING_PROMPT,
            _format_context_block,
        )
        prompt = MORNING_BRIEFING_PROMPT + "\n\n" + _format_context_block(context)

        # 3. Invoke agent via ScheduledExecutionService
        result = await self._invoke_briefing_agent(
            user_id=user_id,
            prompt=prompt,
            briefing_type="morning",
        )

        # 4. Deliver via NotificationService (for Telegram + read tracking)
        notification_id = await self._deliver_briefing(
            user_id=user_id,
            title="Good morning — here's your day",
            body=result["output"],
        )

        # 5. Mark deferred observations as consumed
        await self._consume_deferred_observations(user_id)

        return {
            "success": True,
            "briefing": result["output"],
            "notification_id": notification_id,
        }

    async def generate_evening_briefing(self, user_id: str) -> dict:
        """Same pattern as morning but different context and prompt."""
        ...

    async def get_user_preferences(self, user_id: str) -> dict:
        """Get or lazily create user preferences."""
        ...

    async def update_user_preferences(self, user_id: str, updates: dict) -> dict:
        """Update specific preference fields. Validates timezone and time format."""
        ...

    async def _gather_morning_context(self, user_id: str, sections: dict) -> dict:
        """Parallel fetch: calendar, tasks, email, observations.

        Returns richer data than BootstrapContextService — full event lists,
        actual email subjects, task details with due dates.
        """
        ...

    async def _invoke_briefing_agent(self, user_id, prompt, briefing_type) -> dict:
        """Invoke via ScheduledExecutionService with the schedule dict interface."""
        from chatServer.services.scheduled_execution_service import ScheduledExecutionService

        return await ScheduledExecutionService().execute({
            "user_id": user_id,
            "agent_name": "assistant",
            "prompt": prompt,
            "config": {
                "model_override": "claude-haiku-4-5-20251001",
                "skip_notification": True,
                "schedule_type": "briefing",
            },
            "id": None,  # no agent_schedule row
        })

    async def _deliver_briefing(self, user_id, title, body) -> str:
        """Deliver via NotificationService.notify_user() for Telegram + tracking.

        Post-processes markdown for Telegram before delivery.
        """
        from chatServer.services.notification_service import NotificationService

        telegram_body = format_for_telegram(body)
        notification_service = NotificationService(self.db)
        return await notification_service.notify_user(
            user_id=user_id,
            title=title,
            body=telegram_body,  # Telegram-safe version
            category="briefing",
            metadata={"briefing_type": "morning", "full_markdown": body},
            type="notify",
        )

    async def _consume_deferred_observations(self, user_id: str) -> None:
        """Mark unconsumed observations as consumed."""
        ...
```

**Context gathering** does NOT reuse `BootstrapContextService` — it needs richer data than summary strings. Dedicated fetcher methods return:

- **Calendar:** Full event list with times, attendees, conflicts (not just "3 events today")
- **Tasks:** Overdue items with due dates, today's due items, top priority suggestions, task details
- **Email:** Recent unread emails with sender, subject, age (requires Gmail API call, actual subjects not just counts)
- **Observations:** Raw text from `deferred_observations` table

> **Gotcha: Circular import risk.** `briefing_tools.py` → `briefing_service.py` → `scheduled_execution_service.py` → `agent_loader_db.py` → tool imports. Use `_get_briefing_service()` lazy import helper in `briefing_tools.py` (same pattern as `calendar_tools.py`'s `_get_calendar_service()`).

### 4. Briefing Prompts (FU-2)

All prompt constants and context formatting live in `chatServer/services/briefing_prompts.py`.

```python
# chatServer/services/briefing_prompts.py

BRIEFING_SECTIONS_DEFAULT = {
    "calendar": True,
    "tasks": True,
    "email": True,
    "observations": True,
}
BRIEFING_SECTION_KEYS = frozenset(BRIEFING_SECTIONS_DEFAULT.keys())

MORNING_BRIEFING_PROMPT = """You are composing a morning briefing for the user.

Pick the 3-5 most important items from the context below. Order by importance,
not by category. Explain WHY each item matters in one sentence.

Rules:
- Maximum 300 words
- Use markdown: **bold** for emphasis, ### for section headers, bullet points
- If a section has nothing noteworthy, skip it entirely
- Be opinionated — "You have a 1:1 with Sarah at 2pm and 3 overdue tasks"
  is better than "You have 5 calendar events and 8 tasks"
- End with one actionable suggestion for the day
"""

EVENING_BRIEFING_PROMPT = """You are composing an evening briefing for the user.

Reflect on the day: what got done, what's still open, what's tomorrow.

Rules:
- Maximum 250 words
- Use markdown: **bold** for emphasis, ### for section headers, bullet points
- Reflective framing — "You knocked out 4 tasks today" not "4 tasks were completed"
- If nothing happened, say so briefly
- End with what to expect tomorrow (preview from calendar)
"""


def get_enabled_sections(sections_input: dict | None) -> dict:
    """Validate and return enabled sections dict.

    - None/null → use BRIEFING_SECTIONS_DEFAULT
    - All keys must be in BRIEFING_SECTION_KEYS — reject unknowns
    - All values must be boolean — reject non-boolean truthy values like "yes"
    - Forward-compatible: future dict values like {"enabled": true, "max_items": 3} are truthy
    """
    if sections_input is None:
        return dict(BRIEFING_SECTIONS_DEFAULT)

    validated = {}
    for key, value in sections_input.items():
        if key not in BRIEFING_SECTION_KEYS:
            raise ValueError(f"Unknown briefing section: {key}")
        if not isinstance(value, bool):
            # Forward-compat: dicts are truthy (future {"enabled": true, ...})
            if isinstance(value, dict):
                validated[key] = bool(value)
            else:
                raise ValueError(
                    f"briefing_sections[{key}] must be boolean, got {type(value).__name__}"
                )
        else:
            validated[key] = value
    return validated


def _format_context_block(context: dict) -> str:
    """Format gathered context as tagged markdown sections.

    Omits sections with empty/None data entirely.

    Example output:
        ## Calendar
        - 9:00 AM: Team standup (30 min)
        - 2:00 PM: 1:1 with Sarah (1 hr)

        ## Tasks
        - [overdue] Submit Q1 report (due Mar 1)
        - [today] Review PR #42
    """
    blocks = []
    for label, items in context.items():
        if not items:
            continue
        if isinstance(items, list):
            formatted = "\n".join(f"- {item}" for item in items)
        else:
            formatted = str(items)
        blocks.append(f"## {label.title()}\n{formatted}")
    return "\n\n".join(blocks)
```

### 5. Telegram Post-Processing (FU-2)

```python
# In chatServer/services/briefing_service.py (or a shared utility)

TELEGRAM_CHAR_LIMIT = 4000  # Hard limit is 4096, bot truncates at 4000

def format_for_telegram(markdown: str) -> str:
    """Post-process rich markdown for Telegram's legacy Markdown v1.

    - Strips ### headers → **Header** (bold on its own line)
    - Flattens nested lists to single-level
    - Preserves bold, italic, and flat bullet points
    - Truncates to TELEGRAM_CHAR_LIMIT chars
    """
    import re

    # Convert ### headers to bold
    result = re.sub(r'^###\s+(.+)$', r'**\1**', markdown, flags=re.MULTILINE)

    # Flatten nested lists (  - item → - item)
    result = re.sub(r'^(\s{2,})-\s+', r'- ', result, flags=re.MULTILINE)

    # Truncate if needed
    if len(result) > TELEGRAM_CHAR_LIMIT:
        result = result[:TELEGRAM_CHAR_LIMIT - 3] + "..."

    return result
```

### 6. Job Handlers: Self-Scheduling Pattern (FU-2)

The self-scheduling pattern mirrors how `ReminderService.handle_recurrence()` works — after completing, schedule the next one. Critically, the next occurrence is scheduled FIRST (before generating) so that a generation failure doesn't break the chain.

```python
# In chatServer/services/job_handlers.py

async def handle_morning_briefing(job: dict) -> dict:
    """Generate morning briefing and self-schedule next occurrence.

    Schedule next FIRST, then generate — so generation failure
    doesn't break the scheduling chain.
    """
    user_id = str(job["input"]["user_id"])
    db_client = await create_system_client()
    briefing_service = BriefingService(db_client)

    prefs = await briefing_service.get_user_preferences(user_id)

    # 1. Self-schedule next occurrence FIRST
    if prefs["morning_briefing_enabled"]:
        next_scheduled = _compute_next_briefing_time(
            prefs["timezone"], prefs["morning_briefing_time"], "morning"
        )
        # Use get_database_manager().pool — don't create new pools
        from chatServer.database.connection import get_database_manager
        db_manager = get_database_manager()
        job_service = JobService(db_manager.pool)
        await job_service.create(
            job_type="morning_briefing",
            input={"user_id": user_id},
            user_id=user_id,
            scheduled_for=next_scheduled,
            expires_at=next_scheduled + timedelta(hours=4),
            max_retries=2,
        )

    # 2. Generate today's briefing
    result = await briefing_service.generate_morning_briefing(user_id)
    return result


def _compute_next_briefing_time(
    tz_name: str, briefing_time: str, briefing_type: str
) -> datetime:
    """Compute the next occurrence of a briefing in UTC.

    Args:
        tz_name: IANA timezone (e.g., 'America/New_York')
        briefing_time: HH:MM or HH:MM:SS string (e.g., '07:30' or '07:30:00')
        briefing_type: 'morning' or 'evening'

    Returns:
        datetime in UTC for the next occurrence (always tomorrow or later).
    """
    from zoneinfo import ZoneInfo
    tz = ZoneInfo(tz_name)
    now_local = datetime.now(tz)
    # Handle both HH:MM and HH:MM:SS from TIME column
    parts = briefing_time.split(":")
    hour, minute = int(parts[0]), int(parts[1])
    tomorrow_local = (now_local + timedelta(days=1)).replace(
        hour=hour, minute=minute, second=0, microsecond=0
    )
    return tomorrow_local.astimezone(timezone.utc)
```

> **Gotcha: Use `get_database_manager().pool`** to get `JobService` in handlers. Do not create new connection pools.

> **Gotcha: `expires_at` is mandatory on briefing jobs.** Set to `scheduled_for + timedelta(hours=4)` to prevent stale job accumulation if the runner is down for an extended period.

### 7. `JobService.fail_by_type()` (FU-2)

New method needed for AC-19 (cancel pending jobs when user disables briefings).

```python
# In chatServer/services/job_service.py

async def fail_by_type(self, user_id: str, job_type: str, error: str) -> int:
    """Fail all pending jobs for a user+type. Returns count of affected rows."""
    async with self.pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                UPDATE jobs
                SET status = 'failed',
                    error = %s,
                    completed_at = NOW(),
                    updated_at = NOW()
                WHERE user_id = %s
                  AND job_type = %s
                  AND status = 'pending'
                RETURNING id
                """,
                (error, user_id, job_type),
            )
            rows = await cur.fetchall()
            return len(rows)
```

### 8. Briefing Schedule Bootstrap (FU-2)

On server startup, ensures every eligible user has a pending briefing job. This catches: first-time deployments, users who enabled briefings while the server was down, and failed self-scheduling chains.

```python
# In BackgroundTaskService
async def _bootstrap_briefing_jobs(self) -> None:
    """Ensure all users with briefings enabled have pending jobs."""
    db_client = await create_system_client()

    # Query all users with morning or evening briefings enabled
    result = await db_client.table("user_preferences").select(
        "user_id, timezone, morning_briefing_enabled, morning_briefing_time, "
        "evening_briefing_enabled, evening_briefing_time"
    ).or_(
        "morning_briefing_enabled.eq.true,evening_briefing_enabled.eq.true"
    ).execute()

    for pref in (result.data or []):
        user_id = pref["user_id"]
        for briefing_type in ["morning", "evening"]:
            enabled_key = f"{briefing_type}_briefing_enabled"
            time_key = f"{briefing_type}_briefing_time"
            if not pref.get(enabled_key):
                continue

            # Check if a pending job already exists
            job_type = f"{briefing_type}_briefing"
            existing = await self._check_pending_briefing_job(user_id, job_type)
            if existing:
                continue

            next_time = _compute_next_briefing_time(
                pref["timezone"], pref[time_key], briefing_type
            )
            await self._job_service.create(
                job_type=job_type,
                input={"user_id": user_id},
                user_id=user_id,
                scheduled_for=next_time,
                expires_at=next_time + timedelta(hours=4),
                max_retries=2,
            )
```

> **Gotcha: Bootstrap must be awaited before the job runner starts** in `start_background_tasks()`. The bootstrap creates jobs that the runner should immediately be able to pick up. If the runner starts first, it might poll and find nothing, then sleep for 5s before checking again.

### 9. ManageBriefingPreferencesTool (FU-3)

Conversational interface for preference management. The agent calls this tool when the user says things like "set my morning briefing to 7:30am Eastern" or "turn off evening briefings."

```python
# chatServer/tools/briefing_tools.py

def _get_briefing_service():
    """Lazy import to avoid circular dependency."""
    from chatServer.services.briefing_service import BriefingService
    return BriefingService

class ManageBriefingPreferencesTool(BaseTool):
    name = "manage_briefing_preferences"
    description = (
        "View or update briefing preferences (morning/evening briefing time, "
        "timezone, enabled/disabled). Use 'get' to view current settings, "
        "'update' to change them."
    )

    async def _arun(self, action: str, preferences: dict = None) -> str:
        # action: "get" | "update"
        # preferences: {timezone?, morning_briefing_time?, morning_briefing_enabled?, ...}
        ...
```

The tool validates:
- `timezone` against `zoneinfo.available_timezones()` — rejects invalid IANA strings
- `morning_briefing_time` / `evening_briefing_time` as `HH:MM` format, 00:00-23:59 — normalized to `HH:MM:00` for the TIME column
- Boolean fields for enabled/disabled
- `briefing_sections` validated via `get_enabled_sections()` from `briefing_prompts.py`

Side effects on update:
- If `morning_briefing_enabled` changes to `true`: create first briefing job (AC-18)
- If `morning_briefing_enabled` changes to `false`: cancel pending jobs via `fail_by_type()` (AC-19)
- If `morning_briefing_time` or `timezone` changes while enabled: cancel existing pending job, create new one with updated time

### 10. Heartbeat Deferral (FU-2)

Modify `ScheduledExecutionService.execute()` to defer heartbeat findings when briefings are enabled. The deferral check goes inline in `execute()` — AFTER `is_heartbeat_ok` is evaluated (step 7), BEFORE the `skip_notification` / `_notify_user()` branch (step 11).

```python
# In ScheduledExecutionService.execute(), after step 7 (is_heartbeat_ok),
# BEFORE step 11 (notification branch):

# 7b. Defer non-OK heartbeat findings when briefings are enabled
if schedule_type == "heartbeat" and not is_heartbeat_ok:
    try:
        from chatServer.services.briefing_service import BriefingService
        briefing_svc = BriefingService(supabase_client)
        prefs = await briefing_svc.get_user_preferences(user_id)

        if prefs.get("morning_briefing_enabled"):
            # Defer to next briefing instead of notifying immediately
            await supabase_client.table("deferred_observations").insert({
                "user_id": user_id,
                "content": output,
                "source": "heartbeat",
            }).execute()
            logger.info(f"Deferred heartbeat finding for {user_id} to next briefing")
            # Skip notification — mark session inactive and return
            await supabase_client.table("chat_sessions").update(
                {"is_active": False}
            ).eq("session_id", session_id).execute()
            return {
                "success": True,
                "output": output,
                "deferred": True,
                "pending_actions_created": pending_count,
                "duration_ms": duration_ms,
            }
    except Exception as e:
        logger.warning(f"Failed to check briefing deferral, delivering immediately: {e}")
    # Fall through to normal notification if briefings disabled or check failed
```

> **Gotcha: Deferral insertion point matters.** This goes in `execute()`, NOT in `_notify_user()`. The `_notify_user()` method is only about notification formatting/delivery. The decision to defer vs. deliver is a control flow decision that belongs in the main execution path, before we even reach the notification branch.

### 11. First-Use Discovery (FU-2)

```python
# In BootstrapContextService, add to gather():

async def gather(self, user_id: str) -> BootstrapContext:
    """Gather context from all sources. Never raises."""
    tasks_result, reminders_result, email_result, calendar_result, briefing_check = (
        await asyncio.gather(
            self._get_tasks_summary(user_id),
            self._get_reminders_summary(user_id),
            self._get_email_summary(user_id),
            self._get_calendar_summary(user_id),
            self._check_briefing_setup(user_id),
            return_exceptions=True,
        )
    )

    ctx = BootstrapContext(
        tasks_summary=tasks_result if isinstance(tasks_result, str) else "(unavailable)",
        reminders_summary=reminders_result if isinstance(reminders_result, str) else "(unavailable)",
        email_summary=email_result if isinstance(email_result, str) else "(unavailable)",
        calendar_summary=calendar_result if isinstance(calendar_result, str) else "(unavailable)",
    )

    # Append first-use discovery note
    if isinstance(briefing_check, str) and briefing_check:
        ctx.briefing_note = briefing_check  # New field on BootstrapContext

    return ctx

async def _check_briefing_setup(self, user_id: str) -> str:
    """Check if user has configured briefings. Returns note if not."""
    try:
        resp = await self.db.table("user_preferences").select("id").eq(
            "user_id", user_id
        ).limit(1).execute()
        if not (resp.data or []):
            return "User hasn't configured morning briefings yet — you can offer to set this up."
        return ""
    except Exception:
        return ""
```

### Dependencies

- **SPEC-025** (Unified Notification Experience) — `NotificationService.notify_user()` for delivery
- **SPEC-026** (Universal Job Queue) — `JobService` for scheduling, `JobRunnerService` for dispatch
- **SPEC-027** (Google Calendar Integration) — `CalendarService` for calendar context in briefings

### Notification Delivery Shape

When `BriefingService` delivers a briefing notification:

```python
await notification_service.notify_user(
    user_id=user_id,
    title="Good morning — here's your day",  # or "Here's your evening wrap-up"
    body=telegram_formatted_body,
    category="briefing",
    metadata={
        "briefing_type": "morning",  # or "evening"
        "full_markdown": original_body,  # full-fidelity version
    },
    type="notify",
)
```

## Testing Requirements

### Unit Tests (required)

- `test_briefing_service.py`: Mock agent invocation and context sources. Test morning briefing generation, evening briefing generation, preference CRUD with lazy creation, deferred observation consumption, Telegram post-processing in delivery.
- `test_briefing_handlers.py`: Mock `BriefingService` and `JobService`. Test self-scheduling after success, self-scheduling after failure (next day still scheduled), disabled briefing skips scheduling, `expires_at` set correctly.
- `test_briefing_tools.py`: Test get/update actions, timezone validation, time format validation (HH:MM normalized to HH:MM:SS), briefing_sections validation, job creation/cancellation side effects.
- `test_briefing_prompts.py`: Test `_format_context_block()` omits empty sections, `get_enabled_sections()` rejects unknown keys and non-boolean values, `format_for_telegram()` strips headers/flattens lists/truncates.

### Integration Tests (required for DB changes)

- Full briefing lifecycle: create preferences → enqueue job → handler runs → notification created → next job scheduled with correct `expires_at`
- RLS: user can only access own preferences and observations

### Prompt Scenario Tests (required)

Five scenarios that verify prompt assembly produces the correct context blocks:

1. **Typical weekday morning:** Calendar has 4 events, 2 overdue tasks, 5 unread emails, 1 deferred observation. Verify all 4 sections present in assembled prompt.
2. **Empty day:** No events, no tasks due, no emails, no observations. Verify prompt has no context sections (all omitted by `_format_context_block`).
3. **Crisis day:** 6 overdue tasks, 12 urgent emails, conflicting calendar events. Verify all sections present with high item counts.
4. **Evening productive day:** 5 tasks completed, 2 still open, tomorrow has 3 events. Verify evening prompt sections.
5. **No connected services:** Calendar unavailable, email unavailable, tasks empty, no observations. Verify prompt assembles with only the base prompt (no context sections).

### What to Test

- Happy path for morning and evening briefings
- User with no connected services (calendar/email) — briefing still generates with available data
- User with briefings disabled — heartbeat delivered immediately, no deferral
- Timezone edge cases: user in UTC+12, user in UTC-12, DST transitions
- Self-scheduling chain: today's briefing schedules tomorrow's
- Bootstrap: server restart recovers missing briefing jobs
- Tool validation: invalid timezone rejected, invalid time format rejected, invalid briefing_sections keys rejected
- `format_for_telegram()`: h3 → bold, nested lists flattened, long output truncated at 4000 chars
- `_format_context_block()`: empty sections omitted, non-empty rendered as tagged markdown
- `get_enabled_sections()`: None → defaults, unknown keys → error, `"yes"` → error, `dict` → truthy

### AC-to-Test Mapping

| AC | Test Type | Test Function |
|----|-----------|---------------|
| AC-01 | Integration | `test_ac_01_user_preferences_table_schema` |
| AC-02 | Integration | `test_ac_02_deferred_observations_table_schema` |
| AC-04 | Unit | `test_ac_04_lazy_preference_creation` |
| AC-07 | Unit | `test_ac_07_morning_briefing_generation` |
| AC-08 | Unit | `test_ac_08_evening_briefing_generation` |
| AC-09 | Unit | `test_ac_09_briefing_delivers_notification_with_telegram_format` |
| AC-10 | Unit | `test_ac_10_observations_consumed_after_briefing` |
| AC-13 | Unit | `test_ac_13_morning_handler_self_schedules_with_expires` |
| AC-16 | Unit | `test_ac_16_failed_briefing_schedules_next_day` |
| AC-17 | Unit | `test_ac_17_bootstrap_creates_missing_jobs` |
| AC-18 | Unit | `test_ac_18_enable_creates_first_job` |
| AC-19 | Unit | `test_ac_19_disable_cancels_pending_jobs_via_fail_by_type` |
| AC-20 | Unit | `test_ac_20_tool_validates_timezone_time_and_sections` |
| AC-22 | Unit | `test_ac_22_heartbeat_deferred_in_execute_when_briefings_enabled` |
| AC-23 | Unit | `test_ac_23_heartbeat_immediate_when_briefings_disabled` |
| AC-31 | Integration | `test_ac_31_full_briefing_lifecycle` |
| AC-32 | Unit | `test_ac_32_prompt_constants_exist` |
| AC-33 | Unit | `test_ac_33_format_context_block_omits_empty` |
| AC-34 | Unit | `test_ac_34_get_enabled_sections_validation` |
| AC-35 | Unit | `test_ac_35_fail_by_type_cancels_pending_jobs` |
| AC-36 | Unit | `test_ac_36_format_for_telegram_strips_headers` |
| AC-37 | Unit | `test_ac_37_bootstrap_context_briefing_discovery` |
| AC-38 | Unit | `test_ac_38_briefing_uses_skip_notification_and_chat_message` |
| AC-39 | Unit | `test_ac_39_telegram_format_nested_lists_and_truncation` |
| AC-40 | Unit | `test_ac_40_prompt_assembly_within_word_limits` |
| AC-41 | Unit | `test_ac_41_prompt_scenario_*` (5 scenarios) |

### Manual Verification (UAT)

- [ ] Start `pnpm dev`. Via chat, say "Set my morning briefing for 7:30am Eastern." Verify the tool runs, preferences are saved, and a pending `morning_briefing` job appears in the `jobs` table with correct `scheduled_for` (UTC) and `expires_at`.
- [ ] Manually set `scheduled_for` to `NOW()` on the pending job. Wait for the job runner to pick it up (~5s). Verify: briefing appears as a chat message in the web UI with full markdown formatting (bold, bullets, headers), notification delivered to Telegram (if linked) with headers converted to bold, next day's job is self-scheduled with `expires_at`.
- [ ] Via chat, say "Turn off my morning briefing." Verify the pending job is cancelled via `fail_by_type` (status='failed', error='Briefing disabled by user').
- [ ] Trigger a heartbeat run. Verify the finding is deferred to `deferred_observations` (not delivered as a notification). Re-enable morning briefing, trigger it, and verify the deferred observation appears in the briefing content.
- [ ] Via chat, say "Set my evening briefing for 8pm." Verify evening briefing is enabled, preferences updated, and a pending `evening_briefing` job is created.
- [ ] Open a new chat session as a user with no `user_preferences` row. Verify the agent proactively mentions briefing setup in its greeting.
- [ ] Verify briefing in Telegram: no `###` headers (converted to bold), no nested lists, output under 4000 chars.

## Edge Cases

- **User changes timezone after job is scheduled:** The pending job has a UTC `scheduled_for`. If the user changes timezone, the existing job fires at the old UTC time. The self-scheduling after that job uses the new timezone. Acceptable — worst case is one briefing arrives at a slightly wrong time.
- **User changes briefing time after job is scheduled:** The tool cancels the old pending job via `fail_by_type()` and creates a new one with the updated time (AC-19 + AC-18).
- **DST transition:** `zoneinfo` handles DST correctly. A 7:30am briefing stays at 7:30am local time even across DST boundaries because `_compute_next_briefing_time` uses `ZoneInfo` for the conversion.
- **Server restart with no `user_preferences` rows:** Bootstrap queries the table — if empty, no jobs are created. Users must enable briefings via conversation first (or accept the default, which creates a row on first access by a tool call or heartbeat deferral check).
- **Multiple pending jobs for the same user+type:** The bootstrap checks for existing pending/claimed/running jobs before creating. The self-scheduling creates unconditionally (because the previous job just completed). Duplicate jobs are harmless — two briefings would generate at the same time, but `claim_next` with `SKIP LOCKED` ensures only one runs. The other would be stale-expired. Still, the bootstrap should be the safeguard, not the norm.
- **Briefing generation takes >30 minutes:** The job would be expired as stale. Unlikely at Haiku rates (~2s generation time), but if it happens, the job retries. To prevent: set `max_retries=2` so it gets 3 attempts.
- **User has no data in any source:** The agent receives empty context for all sections and should respond with something like "Nothing notable today — your calendar is clear and no emails need attention." The synthesis prompt instructs the agent to handle this gracefully.
- **Evening briefing references "tomorrow's calendar" but user has no calendar:** The agent simply omits that section. The `briefing_sections` JSONB allows future per-section toggles.
- **Deferred observations accumulate without briefing:** If a user disables briefings but heartbeat keeps running, AC-23 ensures heartbeats are delivered immediately (no deferral). If a user enables briefings but the briefing job fails for days, observations accumulate. The bootstrap + retry should prevent this, but old observations are still consumed on the next successful briefing.
- **TIME column format mismatch:** `morning_briefing_time` column is TIME, which returns `HH:MM:SS`. User input is `HH:MM`. Tool normalizes on write (appends `:00`). `_compute_next_briefing_time` handles both formats by splitting on `:` and taking first two parts.

## Functional Units (for PR Breakdown)

1. **FU-1: Database Migrations** (`feat/SPEC-028-migration`)
   - Domain: `database-dev`
   - Complexity: Simple
   - Create `user_preferences` table, indexes, RLS
   - Create `deferred_observations` table, indexes, RLS
   - Register `manage_briefing_preferences` tool in `tools` + `agent_tools`
   - Add both tables to `USER_SCOPED_TABLES`
   - Covers: AC-01, AC-02, AC-03, AC-05

2. **FU-2: BriefingService + Prompts + Handlers + Heartbeat Deferral + Telegram Formatting + Bootstrap Discovery** (`feat/SPEC-028-service`)
   - Domain: `backend-dev`
   - Complexity: Complex
   - Depends on: FU-1 merged
   - Create `chatServer/services/briefing_prompts.py` with prompt constants, JSONB schema, context formatting helpers
   - Create `chatServer/services/briefing_service.py` with context gathering, agent invocation, preference CRUD, `format_for_telegram()`
   - Create `handle_morning_briefing` and `handle_evening_briefing` in `job_handlers.py`
   - Add `fail_by_type()` to `JobService`
   - Register handlers in `BackgroundTaskService.start_background_tasks()`; await bootstrap before runner starts
   - Add briefing job bootstrap to `BackgroundTaskService`
   - Update `ScheduledExecutionService.execute()` for heartbeat deferral (inline, before notification branch)
   - Update `BootstrapContextService.gather()` for first-use discovery signal
   - Unit tests for service, handlers, prompts, telegram formatting, prompt scenarios
   - Covers: AC-04, AC-06, AC-07, AC-08, AC-09, AC-10, AC-11, AC-12, AC-13, AC-14, AC-15, AC-16, AC-17, AC-22, AC-23, AC-26, AC-27, AC-29, AC-31, AC-32, AC-33, AC-34, AC-35, AC-36, AC-37, AC-38, AC-39, AC-40, AC-41

3. **FU-3: Briefing Preferences Tool** (`feat/SPEC-028-tool`)
   - Domain: `backend-dev`
   - Complexity: Moderate
   - Depends on: FU-2 merged (needs `BriefingService` and `briefing_prompts.py`)
   - Create `ManageBriefingPreferencesTool` in `chatServer/tools/briefing_tools.py` with `_get_briefing_service()` lazy import
   - Job creation/cancellation side effects via `fail_by_type()`
   - Unit tests for tool including sections validation
   - Covers: AC-18, AC-19, AC-20, AC-21, AC-28

### Merge Order

```
FU-1 (migration) → FU-2 (service + prompts + handlers) → FU-3 (tool)
```

Linear chain. No parallel tracks — FU-2 depends on FU-1, FU-3 depends on FU-2.

## Cross-Domain Contracts

### FU-1 → FU-2: Database Schema

| Table | Key Columns | Notes |
|-------|-------------|-------|
| `user_preferences` | `user_id` (UNIQUE), `timezone`, `morning_briefing_enabled`, `morning_briefing_time` (TIME, returns HH:MM:SS), `evening_briefing_enabled`, `evening_briefing_time` (TIME), `briefing_sections` (JSONB) | Lazy-init pattern — row created on first access |
| `deferred_observations` | `user_id`, `content`, `source`, `consumed_at` | `consumed_at IS NULL` = unconsumed |

### FU-2 → FU-3: Service Interface

| Method | Input | Output | Notes |
|--------|-------|--------|-------|
| `BriefingService.get_user_preferences(user_id)` | `str` | `dict` (row) | Lazy-creates if missing |
| `BriefingService.update_user_preferences(user_id, updates)` | `str`, `dict` | `dict` (updated row) | Validates timezone + time format |
| `JobService.fail_by_type(user_id, job_type, error)` | `str`, `str`, `str` | `int` (affected count) | Used by tool to cancel pending jobs |
| `get_enabled_sections(sections_input)` | `dict \| None` | `dict` | From `briefing_prompts.py` |

### FU-2 → Job Queue: Handler Contracts

| `job_type` | `input` Shape | Handler | Returns |
|------------|---------------|---------|---------|
| `morning_briefing` | `{"user_id": "uuid"}` | `handle_morning_briefing` | `{"success": True, "briefing": "...", "notification_id": "..."}` |
| `evening_briefing` | `{"user_id": "uuid"}` | `handle_evening_briefing` | Same shape as morning |

### FU-2 → Notification: Delivery Shape

| Field | Value | Notes |
|-------|-------|-------|
| `type` | `"notify"` | Web + Telegram |
| `category` | `"briefing"` | For styling/filtering |
| `body` | Telegram-formatted markdown | Post-processed via `format_for_telegram()` |
| `metadata.briefing_type` | `"morning"` or `"evening"` | |
| `metadata.full_markdown` | Original rich markdown | Full-fidelity version for future use |

## Effort Estimation

| FU | Domain Agent | Complexity | Estimated Effort |
|----|-------------|------------|-----------------|
| FU-1 | database-dev | Simple | 3 migration files, straightforward schema |
| FU-2 | backend-dev | Complex | 2 new service files + 2 handlers + heartbeat deferral + bootstrap + Telegram formatting + bootstrap discovery + prompts + tests (5 test scenarios) |
| FU-3 | backend-dev | Moderate | 1 tool class + job side effects + sections validation + tests |

**Total agents needed:** database-dev, backend-dev
**Dependencies on other specs:** SPEC-025 (merged), SPEC-026 (merged), SPEC-027 (must be merged for calendar context)
**No frontend dependencies or external packages needed.**

## Completeness Checklist

- [x] Every AC has a stable ID (AC-01 through AC-05, AC-06 through AC-12, AC-13 through AC-23, AC-26 through AC-29, AC-31 through AC-41)
- [x] Every AC maps to at least one functional unit
- [x] Every cross-domain boundary has a contract (schema → service → tool; service → notification; service → job queue)
- [x] Technical decisions reference principles (A1, A3, A6, A7, A8, A9, A10, A11, A14, S1)
- [x] Merge order is explicit and acyclic (FU-1 → FU-2 → FU-3)
- [x] Out-of-scope is explicit (includes "Frontend changes" as explicitly out)
- [x] Edge cases documented with expected behavior (including TIME format mismatch)
- [x] Testing requirements map to ACs (including 5 prompt scenarios)
- [x] Design decisions documented (briefing-as-chat-message, Telegram post-processing, first-use discovery, UTC datetimes)
- [x] ScheduledExecutionService interface uses correct schedule dict format
- [x] Heartbeat deferral insertion point is in `execute()`, not `_notify_user()`
- [x] `briefing_prompts.py` module defined with JSONB schema, validation, and context formatting
- [x] `format_for_telegram()` specified with conversion rules and char limit
- [x] `JobService.fail_by_type()` specified for cancellation
- [x] All backend implementation gotchas captured (lazy imports, pool access, TIME format, bootstrap ordering, circular imports, expires_at)
- [x] FU-4 (frontend) eliminated — no frontend work needed
