# SPEC-006: Email Digests & Proactive Reminders

> **Status:** Draft
> **Author:** Tim + Claude
> **Created:** 2026-02-18
> **Updated:** 2026-02-18

## Goal

Make the agent useful without being asked. The user should wake up to an email digest that knows what matters to them, be able to say "remember this" and trust that it sticks, and receive reminders at the right time — all delivered via Telegram or web notifications without opening the app. This is the foundation for the "Chief of Staff" agent: an AI that manages context and brings information to you instead of you hunting for it.

## Problem

Today, the agent is stateless and reactive:
- LTM table exists but is **never loaded** into the agent's prompt (`ltm_notes_content=None`)
- The agent cannot write its own memory — `memory_tools.py` is an empty stub
- Email digests work technically but have no context about what the user cares about
- The `email_digest_agent` is configured with `gemini-pro` instead of Claude
- Scheduled runs start with zero context (`chat_history: []`) every time
- There is no reminder system — the agent can't do anything time-triggered for you
- No cost controls on scheduled runs

## Acceptance Criteria

### Memory (prerequisite for everything else)
- [ ] AC-1: Agent loads LTM from `agent_long_term_memory` on every invocation (web, Telegram, scheduled)
- [ ] AC-2: Agent has a `save_memory` tool that upserts its LTM notes
- [ ] AC-3: Agent has a `read_memory` tool that returns its current LTM notes
- [ ] AC-4: User says "remember that I'm traveling March 3-7" → agent saves to LTM → next session, agent knows it

### Email Digests
- [ ] AC-5: Email digest scheduled runs load the user's LTM as context
- [ ] AC-6: `email_digest_agent` uses Claude Haiku (not gemini-pro) for cost efficiency
- [ ] AC-7: Digest output is pushed as a notification (web + Telegram) via existing notification system
- [ ] AC-8: Digest includes prioritization informed by LTM ("you care about X, deprioritize Y")

### Proactive Reminders
- [ ] AC-9: `reminders` table stores time-triggered reminders per user
- [ ] AC-10: Agent has a `create_reminder` tool (title, body, remind_at, optional recurrence)
- [ ] AC-11: Agent has a `list_reminders` tool (upcoming reminders for this user)
- [ ] AC-12: Background task checks for due reminders every 60 seconds and fires notifications
- [ ] AC-13: User says "remind me to follow up with Sarah on Friday" → notification arrives Friday morning

### Cost Controls
- [ ] AC-14: `agent_schedules.config` supports a `model_override` field (default: `claude-haiku-4-5-20251001`)
- [ ] AC-15: Scheduled execution logs token usage in `agent_execution_results.metadata`
- [ ] AC-16: Default model for all scheduled runs is Haiku unless overridden

## Scope

### Files to Create

| File | Purpose |
|------|---------|
| `supabase/migrations/YYYYMMDD_reminders.sql` | Reminders table + RLS + indexes |
| `chatServer/tools/memory_tools.py` | SaveMemory and ReadMemory LangChain tools |
| `chatServer/tools/reminder_tools.py` | CreateReminder and ListReminders LangChain tools |
| `chatServer/services/reminder_service.py` | Reminder CRUD + due-reminder checking |
| `tests/chatServer/tools/test_memory_tools.py` | Memory tool tests |
| `tests/chatServer/tools/test_reminder_tools.py` | Reminder tool tests |
| `tests/chatServer/services/test_reminder_service.py` | Reminder service tests |

### Files to Modify

| File | Change |
|------|--------|
| `src/core/agent_loader_db.py` | Fetch LTM from DB and pass to executor (the `None` → real data fix) |
| `src/core/agents/customizable_agent.py` | No change needed — already supports `ltm_notes_content` |
| `chatServer/services/scheduled_execution_service.py` | Load LTM before invoking agent; support `model_override` from config; log token usage |
| `chatServer/services/background_tasks.py` | Add reminder-checking loop alongside scheduled agent loop |
| `chatServer/services/chat.py` | Ensure LTM is loaded for web chat sessions (via agent_loader change) |
| `src/core/tools/memory_tools.py` | Remove empty stub (replaced by `chatServer/tools/memory_tools.py`) |
| `supabase/migrations/20250128000002_configure_email_digest_agent.sql` | Fix: update `email_digest_agent` LLM config from gemini-pro to claude-haiku-4-5-20251001 |

### Out of Scope

- Frontend UI for reminders (delivery is via notifications — no app required)
- Frontend UI for LTM viewing/editing (future spec)
- Email draft-reply capability (future spec — requires pending_actions integration)
- Multiple email account support (future spec — requires OAuth per account)
- Token budget enforcement that halts execution mid-run (complex; model tiering is sufficient for now)
- Reminder recurrence beyond simple patterns (daily, weekly — no complex cron)

## Technical Approach

### Unit 1: Wire LTM into Agent Loading (backend-dev)

**Branch:** `feat/SPEC-006-wire-ltm`

The single highest-leverage change in this spec. In `src/core/agent_loader_db.py`, before calling `CustomizableAgentExecutor.from_agent_config`:

```python
# Fetch LTM for this user+agent
ltm_notes = None
try:
    ltm_result = await supabase_client.table("agent_long_term_memory") \
        .select("notes") \
        .eq("user_id", user_id) \
        .eq("agent_id", agent_name) \
        .maybe_single() \
        .execute()
    if ltm_result.data:
        ltm_notes = ltm_result.data["notes"]
except Exception as e:
    logger.warning(f"Failed to load LTM for {user_id}/{agent_name}: {e}")

# Pass to executor (replaces the hardcoded None)
agent_executor = CustomizableAgentExecutor.from_agent_config(
    ...
    ltm_notes_content=ltm_notes,
    ...
)
```

Also update `scheduled_execution_service.py` to load LTM the same way before invoking agents.

**Note:** The executor is cached (TTLCache, 15min). LTM should be loaded **outside** the cache — on every invocation, not just on cache miss. The current pattern in `chat.py` already hot-swaps memory per request (line 152: `agent_executor.memory = memory`). We need the same pattern for LTM: rebuild the system prompt with current LTM on each request, not just when the executor is first created.

**Implementation detail:** Since the executor caches the system prompt, we need to either:
- (a) Invalidate cache when LTM changes (complex), or
- (b) Move LTM injection from executor creation to per-request, similar to how chat memory is swapped

Option (b) is cleaner. Add a method to `CustomizableAgentExecutor`:
```python
def update_ltm_context(self, ltm_notes_content: Optional[str]):
    """Update the system prompt with fresh LTM notes. Called per-request."""
    # Rebuild system message with new LTM
```

This ensures the agent always sees current LTM, even if the executor is cached.

### Unit 2: Memory Tools (backend-dev) — blocked by Unit 1

**Branch:** `feat/SPEC-006-memory-tools`

Create `chatServer/tools/memory_tools.py`:

```python
class SaveMemoryTool(BaseTool):
    """Saves or updates the agent's long-term memory notes for this user.
    Use this when the user asks you to remember something, or when you learn
    important context about the user's preferences, schedule, or priorities."""

    name = "save_memory"
    args_schema = SaveMemoryInput  # { notes: str }

    async def _arun(self, notes: str) -> str:
        await supabase.table("agent_long_term_memory").upsert({
            "user_id": self.user_id,
            "agent_id": self.agent_name,
            "notes": notes,
        }, on_conflict="user_id,agent_id").execute()
        return "Memory saved successfully."

class ReadMemoryTool(BaseTool):
    """Reads the agent's current long-term memory notes for this user."""

    name = "read_memory"

    async def _arun(self) -> str:
        result = await supabase.table("agent_long_term_memory") \
            .select("notes").eq("user_id", self.user_id) \
            .eq("agent_id", self.agent_name).maybe_single().execute()
        return result.data["notes"] if result.data else "(No memory notes yet.)"
```

Register in `TOOL_REGISTRY`:
```python
TOOL_REGISTRY = {
    ...
    "SaveMemoryTool": SaveMemoryTool,
    "ReadMemoryTool": ReadMemoryTool,
}
```

Add to `assistant` agent's tools via migration:
```sql
INSERT INTO agent_tools (agent_id, tool_name, tool_type, tool_config, is_active, "order")
SELECT id, 'save_memory', 'SaveMemoryTool', '{}', true, 10
FROM agent_configurations WHERE agent_name = 'assistant';

INSERT INTO agent_tools (agent_id, tool_name, tool_type, tool_config, is_active, "order")
SELECT id, 'read_memory', 'ReadMemoryTool', '{}', true, 11
FROM agent_configurations WHERE agent_name = 'assistant';
```

**LTM notes format convention:** The agent's system prompt should instruct it to maintain structured notes:
```markdown
## User Context
- Traveling March 3-7
- Prefers morning email summaries
- Key contacts: Sarah (work), Mike (personal)

## Priorities
- Q1 product launch
- Hiring for engineering team

## Preferences
- Concise communication style
- No meetings before 10am
```

This structure helps the agent and the email digest understand what matters.

**Design note — memory evolution path:**

The text-blob LTM is the MVP. It works today with minimal code. But it has a ceiling: at ~4000 chars, the entire memory goes into the system prompt, which means storage is limited by context window cost.

Two known upgrade paths exist for when we hit that ceiling:

1. **MCP memory server** — Tim has an existing memory MCP server. The memory tools can be swapped to use MCP transport instead of direct Supabase calls, with no change to the agent's tool interface (`save_memory`/`read_memory` stay the same). This is the likely near-term path.

2. **Skills-decomposition pattern** (à la [LangChain SQL assistant with skills](https://docs.langchain.com/oss/python/langchain/multi-agent/skills-sql-assistant)) — memories are decomposed into indexed, retrievable units (like SQL snippets or procedures) rather than stored as a monolithic blob. The agent retrieves relevant memories per-query instead of loading everything. This dramatically increases storage capacity at the cost of retrieval accuracy.

**What this means for implementation:** Keep the memory tool interface clean and narrow (`save_memory(notes)`, `read_memory()`) so the backing store can be swapped without changing the agent's tools or the consuming code. Don't leak Supabase-specific details into the tool's public interface. The 4000-char cap is intentional — it's the forcing function that tells us when to upgrade.

### Unit 3: Reminders Table + Service (database-dev + backend-dev)

**Branch:** `feat/SPEC-006-reminders`

**Migration:**
```sql
CREATE TABLE reminders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    body TEXT,
    remind_at TIMESTAMPTZ NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'sent', 'dismissed')),
    recurrence TEXT DEFAULT NULL
        CHECK (recurrence IS NULL OR recurrence IN ('daily', 'weekly', 'monthly')),
    created_by TEXT NOT NULL DEFAULT 'user'
        CHECK (created_by IN ('user', 'agent')),
    agent_name TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for the background task: find due reminders efficiently
CREATE INDEX idx_reminders_due
    ON reminders (remind_at, status)
    WHERE status = 'pending';

-- Index for user queries
CREATE INDEX idx_reminders_user_upcoming
    ON reminders (user_id, remind_at)
    WHERE status = 'pending';

-- RLS
ALTER TABLE reminders ENABLE ROW LEVEL SECURITY;

CREATE POLICY reminders_user_policy ON reminders
    FOR ALL USING (auth.uid() = user_id);

CREATE POLICY reminders_service_insert ON reminders
    FOR INSERT TO service_role WITH CHECK (true);

CREATE POLICY reminders_service_update ON reminders
    FOR UPDATE TO service_role USING (true);
```

**Service** (`chatServer/services/reminder_service.py`):
```python
class ReminderService:
    async def create_reminder(user_id, title, body, remind_at, recurrence=None,
                               created_by="agent", agent_name=None) -> dict
    async def list_upcoming(user_id, limit=20) -> list[dict]
    async def get_due_reminders() -> list[dict]  # all users, status=pending, remind_at <= now
    async def mark_sent(reminder_id) -> None
    async def dismiss(user_id, reminder_id) -> None
    async def handle_recurrence(reminder) -> None  # create next occurrence if recurring
```

**Reminder tools** (`chatServer/tools/reminder_tools.py`):
```python
class CreateReminderTool(BaseTool):
    name = "create_reminder"
    # args: title (str), body (str, optional), remind_at (ISO datetime), recurrence (optional)

class ListRemindersTool(BaseTool):
    name = "list_reminders"
    # returns upcoming reminders for this user
```

### Unit 4: Email Digest Enhancement (backend-dev) — blocked by Unit 1

**Branch:** `feat/SPEC-006-digest-enhancement`

1. **Fix model config:** New migration to update `email_digest_agent` LLM config:
```sql
UPDATE agent_configurations
SET llm_config = jsonb_set(llm_config, '{model}', '"claude-haiku-4-5-20251001"')
WHERE agent_name = 'email_digest_agent';
```

2. **LTM-aware digest prompt:** Update the scheduled email digest prompt to include LTM. In `scheduled_execution_service.py`, when building the prompt for email digests:
```python
# Load LTM and prepend to digest prompt
ltm = await self._load_ltm(user_id, agent_name)
if ltm:
    prompt = f"User context (from memory):\n{ltm}\n\n{original_prompt}"
```

3. **Model override support:** In `scheduled_execution_service.py`, read `config.model_override` and pass to agent loader:
```python
model_override = schedule.get("config", {}).get("model_override")
# If provided, temporarily override the agent's LLM config
```

4. **Token usage logging:** After execution, extract token counts from the LLM callback and store in `agent_execution_results.metadata`:
```python
metadata = {
    "model": model_used,
    "input_tokens": input_tokens,
    "output_tokens": output_tokens,
    "estimated_cost_usd": estimated_cost,
}
```

### Unit 5: Reminder Delivery Loop (backend-dev) — blocked by Unit 3

**Branch:** `feat/SPEC-006-reminder-delivery`

Add to `background_tasks.py` a new loop that runs every 60 seconds:

```python
async def check_due_reminders(self):
    """Check for and deliver due reminders."""
    reminder_service = ReminderService()
    notification_service = NotificationService()

    due = await reminder_service.get_due_reminders()
    for reminder in due:
        await notification_service.notify_user(
            user_id=reminder["user_id"],
            title=f"Reminder: {reminder['title']}",
            body=reminder["body"] or reminder["title"],
            category="reminder",
            metadata={"reminder_id": str(reminder["id"])},
        )
        await reminder_service.mark_sent(reminder["id"])
        await reminder_service.handle_recurrence(reminder)
```

Register `"reminder"` as a notification category in the system.

### Dependencies

```
Unit 1 (wire LTM)
 ├── Unit 2 (memory tools)
 ├── Unit 4 (digest enhancement)
 │
Unit 3 (reminders table + service + tools)
 └── Unit 5 (reminder delivery loop)
```

Units 1 and 3 can start in parallel. Units 2, 4, and 5 depend on their respective prerequisites.

## Testing Requirements

### Unit Tests (required)

**`tests/chatServer/tools/test_memory_tools.py`:**
- `test_save_memory_creates_new_entry`
- `test_save_memory_updates_existing_entry` (upsert behavior)
- `test_read_memory_returns_notes`
- `test_read_memory_returns_placeholder_when_empty`
- `test_save_memory_scoped_to_user` (user A can't overwrite user B's memory)

**`tests/chatServer/tools/test_reminder_tools.py`:**
- `test_create_reminder_stores_in_db`
- `test_create_reminder_validates_future_date`
- `test_list_reminders_returns_upcoming_only`
- `test_list_reminders_excludes_sent_and_dismissed`

**`tests/chatServer/services/test_reminder_service.py`:**
- `test_get_due_reminders_returns_past_due_only`
- `test_mark_sent_updates_status`
- `test_handle_recurrence_creates_next_daily`
- `test_handle_recurrence_creates_next_weekly`
- `test_handle_recurrence_noop_for_non_recurring`
- `test_dismiss_updates_status`

**`tests/chatServer/services/test_ltm_loading.py`:**
- `test_agent_loader_fetches_ltm_from_db`
- `test_agent_loader_handles_missing_ltm`
- `test_scheduled_execution_loads_ltm`
- `test_ltm_injected_into_system_prompt`

### Integration Tests

- `test_save_then_read_memory_roundtrip` — save via tool, read via tool, verify content matches
- `test_ltm_persists_across_sessions` — save in session 1, load executor for session 2, verify LTM present
- `test_reminder_fires_notification` — create reminder with remind_at=now, run check loop, verify notification created
- `test_email_digest_includes_ltm_context` — set LTM, run digest, verify digest references LTM content

### Manual Verification (UAT)

- [ ] Tell agent "remember that I'm traveling March 3-7" → start new session → agent references travel
- [ ] Tell agent "remind me to call Sarah on Friday" → receive notification on Friday
- [ ] Check email digest notification → mentions things from LTM context
- [ ] Verify digest notification arrives on Telegram
- [ ] Check `agent_execution_results.metadata` → has token counts after scheduled run

## Edge Cases

- **Empty LTM:** Agent works normally, system prompt says "(No LTM notes for this session.)"
- **Very large LTM:** Cap at 4000 characters in the save tool. If agent tries to save more, truncate with warning. This prevents LTM from consuming too much of the context window.
- **Reminder in the past:** If user says "remind me yesterday," agent should respond that the date is in the past. `CreateReminderTool` validates `remind_at > now()`.
- **Overlapping reminders:** Multiple reminders due at the same time are fine — each fires its own notification.
- **Timezone handling:** `remind_at` stored as UTC. The agent should ask the user's timezone if ambiguous, and store it in LTM for future reference.
- **LTM concurrent writes:** The upsert on `(user_id, agent_id)` prevents conflicts. Last write wins, which is acceptable since only one agent session runs per user at a time.
- **Scheduled run with no Gmail connected:** The digest agent already handles this gracefully with a "Gmail not connected" error message. No change needed.
- **Executor cache and LTM freshness:** LTM must be refreshed per-request, not per-cache-entry. The `update_ltm_context()` method handles this.

## Cost Analysis

**Email digest (daily, Haiku):**
- Input: ~2000 tokens (system prompt + LTM + email content)
- Output: ~500 tokens (digest summary)
- Cost: ~$0.002 per run → ~$0.06/month for daily digests
- Compare to OpenClaw: $200+/month for similar functionality

**Reminder checks:**
- Zero LLM cost — pure database queries + notification API calls
- Background task overhead: negligible (one SQL query per 60s)

**Memory tools:**
- LTM load: one Supabase read per agent invocation (free tier handles this)
- Memory save: one Supabase upsert per save (infrequent, user-triggered)

## Functional Units (PR Breakdown)

1. **Unit 1:** Wire LTM into agent loading + per-request refresh (`feat/SPEC-006-wire-ltm`) — **backend-dev**
2. **Unit 2:** Memory tools + migration to register on assistant (`feat/SPEC-006-memory-tools`) — **backend-dev** (blocked by 1)
3. **Unit 3:** Reminders table + service + tools (`feat/SPEC-006-reminders`) — **database-dev + backend-dev** (parallel with 1)
4. **Unit 4:** Email digest enhancement (model fix + LTM-aware prompts + token logging) (`feat/SPEC-006-digest-enhancement`) — **backend-dev** (blocked by 1)
5. **Unit 5:** Reminder delivery loop in background tasks (`feat/SPEC-006-reminder-delivery`) — **backend-dev** (blocked by 3)
