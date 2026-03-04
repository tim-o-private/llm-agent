# SPEC-028: Morning & Evening Briefings

> **Status:** Draft
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
- **Scheduled execution (SPEC-021):** `ScheduledExecutionService.execute()` loads agent, invokes with prompt, stores result. Supports `model_override` and `skip_notification`.
- **Calendar (SPEC-027):** `CalendarService.list_events()` via Google Calendar API. `CalendarToolProvider.get_all_providers()` for multi-account support.

### What Doesn't Exist Yet

- **User preferences table.** No structured storage for timezone, briefing time, or briefing enabled/disabled. The product-architecture primitives table says "use `UpdateInstructionsTool` or memory tools for user preferences" — but briefing schedules need reliable, queryable storage (not fuzzy memory retrieval). A `user_preferences` table is warranted here.
- **Heartbeat deferral.** Heartbeat findings that aren't urgent have no holding area — they fire immediately or get suppressed via `HEARTBEAT_OK`. Briefings need a place to accumulate deferred observations.
- **Markdown rendering in NotificationInlineMessage.** The body renders as plain `<p>` text. Briefings are markdown-heavy (headers, bullets, bold). The component needs a lightweight markdown renderer.

## Acceptance Criteria

### Database

- [ ] **AC-01:** A `user_preferences` table exists with columns: `id` (UUID PK), `user_id` (UUID FK → auth.users, UNIQUE), `timezone` (TEXT NOT NULL DEFAULT 'America/New_York'), `morning_briefing_enabled` (BOOLEAN NOT NULL DEFAULT true), `morning_briefing_time` (TIME NOT NULL DEFAULT '07:30'), `evening_briefing_enabled` (BOOLEAN NOT NULL DEFAULT false), `evening_briefing_time` (TIME NOT NULL DEFAULT '20:00'), `briefing_sections` (JSONB NOT NULL DEFAULT '{"calendar": true, "tasks": true, "email": true, "observations": true}'), `created_at` (TIMESTAMPTZ NOT NULL DEFAULT NOW()), `updated_at` (TIMESTAMPTZ NOT NULL DEFAULT NOW()). RLS enabled with `is_record_owner(user_id)`. [A8, A9]
- [ ] **AC-02:** A `deferred_observations` table exists with columns: `id` (UUID PK), `user_id` (UUID FK → auth.users ON DELETE CASCADE), `content` (TEXT NOT NULL), `source` (TEXT NOT NULL DEFAULT 'heartbeat'), `created_at` (TIMESTAMPTZ NOT NULL DEFAULT NOW()), `consumed_at` (TIMESTAMPTZ). RLS enabled with `is_record_owner(user_id)`. Index on `(user_id, consumed_at)` for efficient retrieval of unconsumed observations. [A8, A9]
- [ ] **AC-03:** Both tables are registered in `USER_SCOPED_TABLES` in `chatServer/database/user_scoped_tables.py`. [A8]
- [ ] **AC-04:** `user_preferences` row is auto-created for new users via an `INSERT ... ON CONFLICT DO NOTHING` pattern when the briefing system first accesses a user's preferences (lazy initialization, no signup hook). [A14]
- [ ] **AC-05:** A `register_briefing_tools` migration registers `manage_briefing_preferences` in the `tools` table with `type='system'`, `approval_tier='auto'`, linked to the default agent via `agent_tools`. [A11]

### Backend: BriefingService

- [ ] **AC-06:** `BriefingService` class exists in `chatServer/services/briefing_service.py` with constructor accepting `db_client`. [A1, A10]
- [ ] **AC-07:** `BriefingService.generate_morning_briefing(user_id)` gathers context from 4 sources in parallel — calendar events (today), active/overdue tasks, recent emails (since last session or last 12 hours), and unconsumed deferred observations — then invokes the agent with a briefing synthesis prompt using `ScheduledExecutionService.execute()` with `model_override="claude-haiku-4-5-20251001"` and `skip_notification=True`. Returns the synthesized briefing text. [A1, A3]
- [ ] **AC-08:** `BriefingService.generate_evening_briefing(user_id)` gathers context from: tasks completed today, tasks still open, pending replies, and tomorrow's calendar — then invokes the agent with an evening synthesis prompt using `ScheduledExecutionService.execute()` with the same model override. Returns the synthesized briefing text. [A1]
- [ ] **AC-09:** After generating a briefing, `BriefingService` delivers it via `NotificationService.notify_user()` with `type="notify"`, `category="briefing"`, and the synthesized markdown as `body`. [A7]
- [ ] **AC-10:** After generating a briefing, `BriefingService` marks all unconsumed `deferred_observations` for that user as consumed (`consumed_at = NOW()`). [A1]
- [ ] **AC-11:** `BriefingService.get_user_preferences(user_id)` returns the user's preferences row, lazily creating one with defaults if none exists. [A1]
- [ ] **AC-12:** `BriefingService.update_user_preferences(user_id, updates)` updates specific preference fields (timezone, morning_briefing_time, evening_briefing_enabled, etc.) and returns the updated row. [A1]

### Backend: Job Handlers

- [ ] **AC-13:** `handle_morning_briefing` async handler exists in `chatServer/services/job_handlers.py`, accepts a job dict with `input: {user_id}`, calls `BriefingService.generate_morning_briefing()`, and on completion self-schedules the next morning briefing job via `JobService.create()` with `scheduled_for` computed from the user's timezone + morning_briefing_time for the next day. [A1, A11]
- [ ] **AC-14:** `handle_evening_briefing` async handler exists in `chatServer/services/job_handlers.py`, follows the same pattern as AC-13 but for evening briefings. [A1, A11]
- [ ] **AC-15:** Both handlers are registered in `BackgroundTaskService.start_background_tasks()` via `job_runner.register_handler()`. [A11]
- [ ] **AC-16:** If a briefing handler fails, the job retries via the standard `JobService.fail()` backoff. After `max_retries` exhausted, the next occurrence is still scheduled (failure of today's briefing must not break tomorrow's). [A14]

### Backend: Briefing Schedule Bootstrapping

- [ ] **AC-17:** On server startup, `BackgroundTaskService` runs a one-time bootstrap that queries all users with `morning_briefing_enabled=true` (or `evening_briefing_enabled=true`) and ensures each has a pending `morning_briefing` (or `evening_briefing`) job in the `jobs` table. If no pending/claimed/running job exists for that user+type, one is created with `scheduled_for` set to the next occurrence. [A14]
- [ ] **AC-18:** When a user enables briefings via the tool (AC-20), the tool immediately creates the first briefing job with `scheduled_for` computed from their timezone and preferred time. If the preferred time has already passed today, schedules for tomorrow. [A1]
- [ ] **AC-19:** When a user disables briefings via the tool, any pending briefing jobs for that user and type are marked as `failed` with error `'Briefing disabled by user'` and `should_retry=False`. [A1]

### Backend: Briefing Preferences Tool

- [ ] **AC-20:** `ManageBriefingPreferencesTool` exists in `chatServer/tools/briefing_tools.py` as a `BaseTool` subclass. Accepts JSON input with `action` ("get", "update") and optional `preferences` dict. For "update", validates timezone against `zoneinfo.available_timezones()`, validates time format (HH:MM), and calls `BriefingService.update_user_preferences()`. Creates/cancels briefing jobs as side effects per AC-18/AC-19. [A6, A1]
- [ ] **AC-21:** The tool is registered in the `tools` table via migration with `type='system'`, `approval_tier='auto'` (no user approval needed to change their own briefing preferences). [A11]

### Backend: Heartbeat Deferral

- [ ] **AC-22:** `ScheduledExecutionService._notify_user()` is updated: when `schedule_type == "heartbeat"` and the output is NOT `HEARTBEAT_OK`, instead of sending a notification immediately, the output is inserted into `deferred_observations` with `source='heartbeat'`. The notification is suppressed. [A1]
- [ ] **AC-23:** If the user has `morning_briefing_enabled=false`, heartbeat findings are delivered immediately as before (no deferral). Deferral only applies when briefings will consume the observations. [A14]

### Frontend: Markdown in Notifications

- [ ] **AC-24:** `NotificationInlineMessage` renders the notification body as markdown instead of plain text. Uses a lightweight renderer (e.g., `react-markdown` or the existing markdown renderer used in chat messages). Supports: bold, italic, bullet lists, numbered lists, headers (h3/h4 only — no h1/h2 to avoid visual hierarchy conflict with the notification title). [F1]
- [ ] **AC-25:** Markdown rendering is applied to ALL notification bodies, not just briefings. Existing notifications that contain no markdown render identically to before (plain text is valid markdown). [F1]

### Testing

- [ ] **AC-26:** Unit tests exist for `BriefingService`: `generate_morning_briefing` (mocked agent invocation + context gathering), `get_user_preferences` (lazy creation), `update_user_preferences` (validation). [S1]
- [ ] **AC-27:** Unit tests exist for `handle_morning_briefing` and `handle_evening_briefing`: successful generation + self-scheduling, failure + self-scheduling of next occurrence. [S1]
- [ ] **AC-28:** Unit test for `ManageBriefingPreferencesTool`: get preferences, update valid preferences, reject invalid timezone, reject invalid time format. [S1]
- [ ] **AC-29:** Unit test for heartbeat deferral: heartbeat output deferred to `deferred_observations` when briefings enabled, delivered immediately when briefings disabled. [S1]
- [ ] **AC-30:** Frontend test for `NotificationInlineMessage`: renders markdown bold/list correctly, renders plain text unchanged. [S1]
- [ ] **AC-31:** Integration test: full briefing lifecycle — create user preferences, create morning briefing job, handler runs, notification created, next job self-scheduled. [S1]

## Scope

### Files to Create

| File | Purpose |
|------|---------|
| `supabase/migrations/2026MMDD000001_create_user_preferences.sql` | Create `user_preferences` table with indexes and RLS |
| `supabase/migrations/2026MMDD000002_create_deferred_observations.sql` | Create `deferred_observations` table with indexes and RLS |
| `supabase/migrations/2026MMDD000003_register_briefing_tools.sql` | Register `manage_briefing_preferences` tool in `tools` + `agent_tools` |
| `chatServer/services/briefing_service.py` | BriefingService — context gathering, agent invocation, preference CRUD |
| `chatServer/tools/briefing_tools.py` | ManageBriefingPreferencesTool — conversational preference management |
| `tests/chatServer/services/test_briefing_service.py` | BriefingService unit tests |
| `tests/chatServer/services/test_briefing_handlers.py` | Briefing job handler tests (self-scheduling, failure recovery) |
| `tests/chatServer/tools/test_briefing_tools.py` | ManageBriefingPreferencesTool tests |

### Files to Modify

| File | Change |
|------|--------|
| `chatServer/services/job_handlers.py` | Add `handle_morning_briefing` and `handle_evening_briefing` handler functions |
| `chatServer/services/background_tasks.py` | Register briefing handlers; add startup bootstrap for briefing jobs |
| `chatServer/services/scheduled_execution_service.py` | Update `_notify_user()` to defer heartbeat findings to `deferred_observations` when briefings are enabled |
| `chatServer/database/user_scoped_tables.py` | Add `"user_preferences"` and `"deferred_observations"` to `USER_SCOPED_TABLES` |
| `webApp/src/components/ui/chat/NotificationInlineMessage.tsx` | Replace plain `<p>` body with markdown renderer |
| `webApp/src/components/ui/chat/NotificationInlineMessage.test.tsx` | Add markdown rendering tests |

### Out of Scope

- **Briefing customization via conversation** ("skip email in my morning briefing") — the `briefing_sections` JSONB in `user_preferences` supports this, but the conversational UX for toggling sections is deferred. Users can only enable/disable entire morning/evening briefings and set times in this spec.
- **Settings UI for briefings** — all preference management is via conversation (the tool). No settings page.
- **Briefing history / archive** — briefings are delivered as notifications. Users can scroll back in their notification stream. No separate briefing archive.
- **Multiple briefing times per day** — one morning, one evening. No arbitrary schedule.
- **Briefing for users without any connected services** — if a user has no email, no calendar, no tasks, the briefing has nothing to say. The agent should handle this gracefully ("nothing to report today") but we don't special-case it.
- **Non-Google calendar providers** — SPEC-027 is Google-only. Briefings consume whatever calendar data is available.
- **Timezone auto-detection** — user must tell the agent their timezone. Auto-detection from browser or IP is future scope.

## Technical Approach

### 1. Database: `user_preferences` Table (FU-1)

A dedicated table is warranted here despite the architecture primitives recommending memory/instructions for preferences. Briefing schedules must be reliably queryable at server startup across all users — memory tool retrieval is per-user and probabilistic. The table is intentionally narrow (briefing prefs only) and will grow to hold other structured preferences in future specs.

```sql
CREATE TABLE user_preferences (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL UNIQUE REFERENCES auth.users(id) ON DELETE CASCADE,
    timezone TEXT NOT NULL DEFAULT 'America/New_York',
    morning_briefing_enabled BOOLEAN NOT NULL DEFAULT true,
    morning_briefing_time TIME NOT NULL DEFAULT '07:30',
    evening_briefing_enabled BOOLEAN NOT NULL DEFAULT false,
    evening_briefing_time TIME NOT NULL DEFAULT '20:00',
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

        # 1. Gather signals in parallel (reuse bootstrap patterns)
        context = await self._gather_morning_context(user_id, sections)

        # 2. Build synthesis prompt
        prompt = self._build_morning_prompt(context)

        # 3. Invoke agent via ScheduledExecutionService
        result = await self._invoke_briefing_agent(
            user_id=user_id,
            prompt=prompt,
            briefing_type="morning",
        )

        # 4. Deliver via NotificationService
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
        """Parallel fetch: calendar, tasks, email, observations."""
        ...

    def _build_morning_prompt(self, context: dict) -> str:
        """Build the synthesis prompt with gathered context."""
        ...

    async def _invoke_briefing_agent(self, user_id, prompt, briefing_type) -> dict:
        """Invoke via ScheduledExecutionService with Haiku model override."""
        ...

    async def _deliver_briefing(self, user_id, title, body) -> str:
        """Deliver via NotificationService.notify_user()."""
        ...

    async def _consume_deferred_observations(self, user_id: str) -> None:
        """Mark unconsumed observations as consumed."""
        ...
```

**Context gathering** reuses the same data sources as `BootstrapContextService` but returns richer data (not just summary strings). For example:

- **Calendar:** Full event list with times, attendees, conflicts (not just "3 events today")
- **Tasks:** Overdue items with due dates, today's due items, top priority suggestions
- **Email:** Recent unread emails with sender, subject, age (requires Gmail API call)
- **Observations:** Raw text from `deferred_observations` table

**Synthesis prompt** is the key to quality. The agent receives all context as structured text and is instructed to:

1. Pick the 3-5 most important things
2. Explain why each matters
3. Be concise and scannable (bullet points, not paragraphs)
4. Use markdown formatting (bold for emphasis, headers for sections)
5. If a section has nothing noteworthy, skip it entirely

### 4. Job Handlers: Self-Scheduling Pattern (FU-2)

The self-scheduling pattern mirrors how `ReminderService.handle_recurrence()` works — after completing, schedule the next one.

```python
# In chatServer/services/job_handlers.py

async def handle_morning_briefing(job: dict) -> dict:
    """Generate morning briefing and self-schedule next occurrence."""
    user_id = str(job["input"]["user_id"])
    db_client = await create_system_client()
    briefing_service = BriefingService(db_client)

    # 1. Generate the briefing
    result = await briefing_service.generate_morning_briefing(user_id)

    # 2. Self-schedule next morning briefing
    prefs = await briefing_service.get_user_preferences(user_id)
    if prefs["morning_briefing_enabled"]:
        next_scheduled = _compute_next_briefing_time(
            prefs["timezone"], prefs["morning_briefing_time"], "morning"
        )
        job_service = _get_job_service()
        await job_service.create(
            job_type="morning_briefing",
            input={"user_id": user_id},
            user_id=user_id,
            scheduled_for=next_scheduled,
            max_retries=2,
        )

    return result


def _compute_next_briefing_time(
    tz_name: str, briefing_time: str, briefing_type: str
) -> datetime:
    """Compute the next occurrence of a briefing in UTC.

    Args:
        tz_name: IANA timezone (e.g., 'America/New_York')
        briefing_time: HH:MM string (e.g., '07:30')
        briefing_type: 'morning' or 'evening'

    Returns:
        datetime in UTC for the next occurrence (always tomorrow or later).
    """
    from zoneinfo import ZoneInfo
    tz = ZoneInfo(tz_name)
    now_local = datetime.now(tz)
    hour, minute = map(int, briefing_time.split(":"))
    tomorrow_local = (now_local + timedelta(days=1)).replace(
        hour=hour, minute=minute, second=0, microsecond=0
    )
    return tomorrow_local.astimezone(timezone.utc)
```

**Critical: failure recovery.** If the handler raises an exception, the job runner retries via `JobService.fail()`. But the self-scheduling of the next day's briefing happens at the END of the handler (after success). If all retries are exhausted, the next day's briefing is NOT scheduled. The bootstrap loop (AC-17) catches this on next server restart, but there could be a gap. To mitigate: the handler schedules the next occurrence FIRST (before generating), then generates. If generation fails, the next day is already scheduled. If the handler crashes before scheduling, the retry will re-attempt.

```python
# Revised handler pattern: schedule next FIRST, then generate
async def handle_morning_briefing(job: dict) -> dict:
    user_id = str(job["input"]["user_id"])
    db_client = await create_system_client()
    briefing_service = BriefingService(db_client)

    prefs = await briefing_service.get_user_preferences(user_id)

    # 1. Self-schedule next occurrence FIRST (idempotent — checked in bootstrap)
    if prefs["morning_briefing_enabled"]:
        next_scheduled = _compute_next_briefing_time(
            prefs["timezone"], prefs["morning_briefing_time"], "morning"
        )
        job_service = _get_job_service()
        await job_service.create(
            job_type="morning_briefing",
            input={"user_id": user_id},
            user_id=user_id,
            scheduled_for=next_scheduled,
            max_retries=2,
        )

    # 2. Generate today's briefing
    result = await briefing_service.generate_morning_briefing(user_id)
    return result
```

### 5. Briefing Schedule Bootstrap (FU-2)

On server startup, ensures every eligible user has a pending briefing job. This catches: first-time deployments, users who enabled briefings while the server was down, and failed self-scheduling chains.

```python
# In BackgroundTaskService
async def _bootstrap_briefing_jobs(self) -> None:
    """Ensure all users with briefings enabled have pending jobs."""
    db_client = await create_system_client()
    briefing_service = BriefingService(db_client)

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
                max_retries=2,
            )
```

### 6. ManageBriefingPreferencesTool (FU-3)

Conversational interface for preference management. The agent calls this tool when the user says things like "set my morning briefing to 7:30am Eastern" or "turn off evening briefings."

```python
# chatServer/tools/briefing_tools.py
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
- `morning_briefing_time` / `evening_briefing_time` as `HH:MM` format, 00:00-23:59
- Boolean fields for enabled/disabled

Side effects on update:
- If `morning_briefing_enabled` changes to `true`: create first briefing job (AC-18)
- If `morning_briefing_enabled` changes to `false`: cancel pending jobs (AC-19)
- If `morning_briefing_time` or `timezone` changes while enabled: cancel existing pending job, create new one with updated time

### 7. Heartbeat Deferral (FU-2)

Modify `ScheduledExecutionService._notify_user()` to check whether the user has briefings enabled before sending heartbeat notifications.

```python
# In ScheduledExecutionService._notify_user()
if schedule_type == "heartbeat" and not is_heartbeat_ok:
    # Check if user has briefings enabled
    briefing_service = BriefingService(supabase_client)
    prefs = await briefing_service.get_user_preferences(user_id)

    if prefs.get("morning_briefing_enabled"):
        # Defer to next briefing instead of notifying immediately
        await supabase_client.table("deferred_observations").insert({
            "user_id": user_id,
            "content": result_content,
            "source": "heartbeat",
        }).execute()
        logger.info(f"Deferred heartbeat finding for {user_id} to next briefing")
        return  # Skip notification

    # Fall through to normal notification if briefings disabled
```

### 8. Frontend: Markdown in NotificationInlineMessage (FU-4)

Replace the plain `<p>` body text with a markdown renderer. The chat messages already render markdown — reuse the same renderer or dependency.

```tsx
// In NotificationInlineMessage.tsx
import ReactMarkdown from 'react-markdown';

// Replace:
//   <p className="text-xs text-text-secondary mt-0.5">{message.text}</p>
// With:
<div className="text-xs text-text-secondary mt-0.5 prose prose-xs prose-notification">
  <ReactMarkdown
    allowedElements={['p', 'strong', 'em', 'ul', 'ol', 'li', 'h3', 'h4', 'a', 'br']}
  >
    {message.text}
  </ReactMarkdown>
</div>
```

The `allowedElements` whitelist prevents h1/h2 (visual hierarchy conflict), images (security), and scripts. Tailwind `prose-xs` keeps the rendered markdown compact within the notification card. Add minimal CSS for notification-specific prose sizing.

### Dependencies

- **SPEC-025** (Unified Notification Experience) — `NotificationService.notify_user()` for delivery
- **SPEC-026** (Universal Job Queue) — `JobService` for scheduling, `JobRunnerService` for dispatch
- **SPEC-027** (Google Calendar Integration) — `CalendarService` for calendar context in briefings
- **react-markdown** npm package — for frontend markdown rendering (check if already installed; chat messages may use a different renderer)

## Testing Requirements

### Unit Tests (required)

- `test_briefing_service.py`: Mock agent invocation and context sources. Test morning briefing generation, evening briefing generation, preference CRUD with lazy creation, deferred observation consumption.
- `test_briefing_handlers.py`: Mock `BriefingService` and `JobService`. Test self-scheduling after success, self-scheduling after failure (next day still scheduled), disabled briefing skips scheduling.
- `test_briefing_tools.py`: Test get/update actions, timezone validation, time format validation, job creation/cancellation side effects.

### Integration Tests (required for DB changes)

- Full briefing lifecycle: create preferences → enqueue job → handler runs → notification created → next job scheduled
- RLS: user can only access own preferences and observations

### Frontend Tests

- `NotificationInlineMessage.test.tsx`: Markdown bold/italic renders correctly, bullet lists render, plain text is unchanged, disallowed elements (h1, img) are stripped.

### What to Test

- Happy path for morning and evening briefings
- User with no connected services (calendar/email) — briefing still generates with available data
- User with briefings disabled — heartbeat delivered immediately, no deferral
- Timezone edge cases: user in UTC+12, user in UTC-12, DST transitions
- Self-scheduling chain: today's briefing schedules tomorrow's
- Bootstrap: server restart recovers missing briefing jobs
- Tool validation: invalid timezone rejected, invalid time format rejected

### AC-to-Test Mapping

| AC | Test Type | Test Function |
|----|-----------|---------------|
| AC-01 | Integration | `test_ac_01_user_preferences_table_schema` |
| AC-02 | Integration | `test_ac_02_deferred_observations_table_schema` |
| AC-04 | Unit | `test_ac_04_lazy_preference_creation` |
| AC-07 | Unit | `test_ac_07_morning_briefing_generation` |
| AC-08 | Unit | `test_ac_08_evening_briefing_generation` |
| AC-09 | Unit | `test_ac_09_briefing_delivers_notification` |
| AC-10 | Unit | `test_ac_10_observations_consumed_after_briefing` |
| AC-13 | Unit | `test_ac_13_morning_handler_self_schedules` |
| AC-16 | Unit | `test_ac_16_failed_briefing_schedules_next_day` |
| AC-17 | Unit | `test_ac_17_bootstrap_creates_missing_jobs` |
| AC-18 | Unit | `test_ac_18_enable_creates_first_job` |
| AC-19 | Unit | `test_ac_19_disable_cancels_pending_jobs` |
| AC-20 | Unit | `test_ac_20_tool_validates_timezone_and_time` |
| AC-22 | Unit | `test_ac_22_heartbeat_deferred_when_briefings_enabled` |
| AC-23 | Unit | `test_ac_23_heartbeat_immediate_when_briefings_disabled` |
| AC-24 | Frontend | `test_ac_24_markdown_renders_in_notification` |
| AC-25 | Frontend | `test_ac_25_plain_text_unchanged` |
| AC-31 | Integration | `test_ac_31_full_briefing_lifecycle` |

### Manual Verification (UAT)

- [ ] Start `pnpm dev`. Via chat, say "Set my morning briefing for 7:30am Eastern." Verify the tool runs, preferences are saved, and a pending `morning_briefing` job appears in the `jobs` table with correct `scheduled_for`.
- [ ] Manually set `scheduled_for` to `NOW()` on the pending job. Wait for the job runner to pick it up (~5s). Verify: briefing notification appears in web UI with markdown formatting (bold, bullets), notification delivered to Telegram (if linked), next day's job is self-scheduled.
- [ ] Via chat, say "Turn off my morning briefing." Verify the pending job is cancelled (status='failed', error='Briefing disabled by user').
- [ ] Trigger a heartbeat run. Verify the finding is deferred to `deferred_observations` (not delivered as a notification). Re-enable morning briefing, trigger it, and verify the deferred observation appears in the briefing content.
- [ ] Via chat, say "Set my evening briefing for 8pm." Verify evening briefing is enabled, preferences updated, and a pending `evening_briefing` job is created.
- [ ] Verify the NotificationInlineMessage renders markdown: bold text appears bold, bullet lists render as HTML lists, h1/h2 are stripped.

## Edge Cases

- **User changes timezone after job is scheduled:** The pending job has a UTC `scheduled_for`. If the user changes timezone, the existing job fires at the old UTC time. The self-scheduling after that job uses the new timezone. Acceptable — worst case is one briefing arrives at a slightly wrong time.
- **User changes briefing time after job is scheduled:** The tool cancels the old pending job and creates a new one with the updated time (AC-19 + AC-18).
- **DST transition:** `zoneinfo` handles DST correctly. A 7:30am briefing stays at 7:30am local time even across DST boundaries because `_compute_next_briefing_time` uses `ZoneInfo` for the conversion.
- **Server restart with no `user_preferences` rows:** Bootstrap queries the table — if empty, no jobs are created. Users must enable briefings via conversation first (or accept the default, which creates a row on first access by a tool call or heartbeat deferral check).
- **Multiple pending jobs for the same user+type:** The bootstrap checks for existing pending/claimed/running jobs before creating. The self-scheduling creates unconditionally (because the previous job just completed). Duplicate jobs are harmless — two briefings would generate at the same time, but `claim_next` with `SKIP LOCKED` ensures only one runs. The other would be stale-expired. Still, the bootstrap should be the safeguard, not the norm.
- **Briefing generation takes >30 minutes:** The job would be expired as stale. Unlikely at Haiku rates (~2s generation time), but if it happens, the job retries. To prevent: set `max_retries=2` so it gets 3 attempts.
- **User has no data in any source:** The agent receives empty context for all sections and should respond with something like "Nothing notable today — your calendar is clear and no emails need attention." The synthesis prompt instructs the agent to handle this gracefully.
- **Evening briefing references "tomorrow's calendar" but user has no calendar:** The agent simply omits that section. The `briefing_sections` JSONB allows future per-section toggles.
- **Deferred observations accumulate without briefing:** If a user disables briefings but heartbeat keeps running, AC-23 ensures heartbeats are delivered immediately (no deferral). If a user enables briefings but the briefing job fails for days, observations accumulate. The bootstrap + retry should prevent this, but old observations are still consumed on the next successful briefing.

## Functional Units (for PR Breakdown)

1. **FU-1: Database Migrations** (`feat/SPEC-028-migration`)
   - Domain: `database-dev`
   - Complexity: Simple
   - Create `user_preferences` table, indexes, RLS
   - Create `deferred_observations` table, indexes, RLS
   - Register `manage_briefing_preferences` tool in `tools` + `agent_tools`
   - Add both tables to `USER_SCOPED_TABLES`
   - Covers: AC-01, AC-02, AC-03, AC-05

2. **FU-2: BriefingService + Handlers + Heartbeat Deferral** (`feat/SPEC-028-service`)
   - Domain: `backend-dev`
   - Complexity: Complex
   - Depends on: FU-1 merged
   - Create `BriefingService` with context gathering, agent invocation, preference CRUD
   - Create `handle_morning_briefing` and `handle_evening_briefing` in `job_handlers.py`
   - Register handlers in `BackgroundTaskService.start_background_tasks()`
   - Add briefing job bootstrap to `BackgroundTaskService`
   - Update `ScheduledExecutionService._notify_user()` for heartbeat deferral
   - Unit tests for service and handlers
   - Covers: AC-04, AC-06, AC-07, AC-08, AC-09, AC-10, AC-11, AC-12, AC-13, AC-14, AC-15, AC-16, AC-17, AC-22, AC-23, AC-26, AC-27, AC-29, AC-31

3. **FU-3: Briefing Preferences Tool** (`feat/SPEC-028-tool`)
   - Domain: `backend-dev`
   - Complexity: Moderate
   - Depends on: FU-2 merged (needs `BriefingService`)
   - Create `ManageBriefingPreferencesTool` in `chatServer/tools/briefing_tools.py`
   - Job creation/cancellation side effects
   - Unit tests for tool
   - Covers: AC-18, AC-19, AC-20, AC-21, AC-28

4. **FU-4: Frontend Markdown Rendering** (`feat/SPEC-028-markdown`)
   - Domain: `frontend-dev`
   - Complexity: Simple
   - No backend dependency (can run in parallel with FU-2/FU-3)
   - Update `NotificationInlineMessage.tsx` with markdown renderer
   - Add/update tests
   - Covers: AC-24, AC-25, AC-30

### Merge Order

```
FU-1 (migration) → FU-2 (service + handlers) → FU-3 (tool)
                  ↗
FU-4 (frontend markdown) — independent, can merge anytime
```

FU-4 has no backend dependency and can be developed/merged in parallel with FU-1 through FU-3. FU-2 depends on FU-1 (tables must exist). FU-3 depends on FU-2 (tool calls service methods).

## Cross-Domain Contracts

### FU-1 → FU-2: Database Schema

| Table | Key Columns | Notes |
|-------|-------------|-------|
| `user_preferences` | `user_id` (UNIQUE), `timezone`, `morning_briefing_enabled`, `morning_briefing_time`, `evening_briefing_enabled`, `evening_briefing_time`, `briefing_sections` | Lazy-init pattern — row created on first access |
| `deferred_observations` | `user_id`, `content`, `source`, `consumed_at` | `consumed_at IS NULL` = unconsumed |

### FU-2 → FU-3: Service Interface

| Method | Input | Output | Notes |
|--------|-------|--------|-------|
| `BriefingService.get_user_preferences(user_id)` | `str` | `dict` (row) | Lazy-creates if missing |
| `BriefingService.update_user_preferences(user_id, updates)` | `str`, `dict` | `dict` (updated row) | Validates timezone + time format |

### FU-2 → Job Queue: Handler Contracts

| `job_type` | `input` Shape | Handler | Returns |
|------------|---------------|---------|---------|
| `morning_briefing` | `{"user_id": "uuid"}` | `handle_morning_briefing` | `{"success": True, "briefing": "...", "notification_id": "..."}` |
| `evening_briefing` | `{"user_id": "uuid"}` | `handle_evening_briefing` | Same shape as morning |

## Effort Estimation

| FU | Domain Agent | Complexity | Estimated Effort |
|----|-------------|------------|-----------------|
| FU-1 | database-dev | Simple | 3 migration files, straightforward schema |
| FU-2 | backend-dev | Complex | New service + 2 handlers + heartbeat deferral + bootstrap + tests |
| FU-3 | backend-dev | Moderate | 1 tool class + job side effects + tests |
| FU-4 | frontend-dev | Simple | Markdown renderer swap + tests |

**Total agents needed:** database-dev, backend-dev, frontend-dev
**Dependencies on other specs:** SPEC-025 (merged), SPEC-026 (merged), SPEC-027 (must be merged for calendar context)
**Dependencies on external packages:** `react-markdown` (frontend, check if already installed)

## Completeness Checklist

- [x] Every AC has a stable ID (AC-01 through AC-31)
- [x] Every AC maps to at least one functional unit
- [x] Every cross-domain boundary has a contract (schema → service → tool → frontend)
- [x] Technical decisions reference principles (A1, A3, A6, A7, A8, A9, A10, A11, A14, F1, S1)
- [x] Merge order is explicit and acyclic (FU-1 → FU-2 → FU-3; FU-4 independent)
- [x] Out-of-scope is explicit
- [x] Edge cases documented with expected behavior
- [x] Testing requirements map to ACs
