# SPEC-005: Unified Sessions

> **Status:** Ready
> **Author:** Tim
> **Created:** 2026-02-17
> **Updated:** 2026-02-17

## Goal

Make `chat_sessions` the universal session registry so all agent interactions (web, Telegram, scheduled) are tracked in one place. Fix the Telegram/UI disconnect (Telegram chats invisible to web) and chat history persistence (messages lost on page refresh).

## Acceptance Criteria

- [ ] AC-1: `chat_sessions` has `channel TEXT NOT NULL DEFAULT 'web'` column with CHECK constraint
- [ ] AC-2: `chat_sessions` has `session_id TEXT` column with unique index
- [ ] AC-3: Existing rows backfilled with `channel='web'` and `session_id = chat_id::text`
- [ ] AC-4: `GET /api/chat/sessions` returns user's sessions with optional `channel` filter
- [ ] AC-5: `GET /api/chat/sessions/{session_id}/messages` returns messages with cursor pagination
- [ ] AC-6: Telegram `handle_message()` creates/upserts a `chat_sessions` row with `channel='telegram'`
- [ ] AC-7: `ScheduledExecutionService.execute()` creates a `chat_sessions` row with `channel='scheduled'`
- [ ] AC-8: Frontend loads chat history from server on init (messages survive page refresh)
- [ ] AC-9: Telegram sessions visible in web UI session list

## Scope

### Files to Create

| File | Purpose |
|------|---------|
| `supabase/migrations/YYYYMMDDHHMMSS_add_channel_to_chat_sessions.sql` | Add channel + session_id columns, indexes, backfill |
| `chatServer/services/chat_history_service.py` | Session listing + message fetching service |
| `chatServer/routers/chat_history_router.py` | Chat history API endpoints |
| `tests/chatServer/services/test_chat_history_service.py` | Chat history service tests |
| `tests/chatServer/routers/test_chat_history_router.py` | Chat history API tests |
| `webApp/src/api/hooks/useChatHistoryHooks.ts` | React Query hooks for chat history API |

### Files to Modify

| File | Change |
|------|--------|
| `chatServer/main.py` | Register `chat_history_router` |
| `chatServer/channels/telegram_bot.py` | Create chat_sessions row in `handle_message()` |
| `chatServer/services/scheduled_execution_service.py` | Create chat_sessions row in `execute()` |
| `webApp/src/stores/useChatStore.ts` | Load historical messages from server on init |

### Out of Scope

- Session deletion / archival
- Real-time message sync (WebSocket)
- Session sharing between users
- Modifying the existing chat endpoint behavior

## Technical Approach

### Task 1: Migration (database-dev)

**Branch:** `feat/SPEC-005-migration`

```sql
-- Add channel column
ALTER TABLE chat_sessions
  ADD COLUMN channel TEXT NOT NULL DEFAULT 'web'
  CHECK (channel IN ('web', 'telegram', 'scheduled'));

-- Add session_id column (links to chat_message_history)
ALTER TABLE chat_sessions
  ADD COLUMN session_id TEXT;

-- Unique index on session_id (where not null)
CREATE UNIQUE INDEX idx_chat_sessions_session_id
  ON chat_sessions (session_id) WHERE session_id IS NOT NULL;

-- Composite index for session listing
CREATE INDEX idx_chat_sessions_user_channel_created
  ON chat_sessions (user_id, channel, created_at DESC);

-- Backfill existing rows
UPDATE chat_sessions
  SET session_id = chat_id::text, channel = 'web'
  WHERE session_id IS NULL;
```

### Task 2: Chat History API (backend-dev) — blocked by Task 1

**Branch:** `feat/SPEC-005-chat-history-api`

**Service** (`chatServer/services/chat_history_service.py`):
- `get_sessions(user_id, channel=None, limit=50, offset=0)` — list sessions
- `get_session_messages(session_id, user_id, limit=50, before_id=None)` — cursor pagination

**Router** (`chatServer/routers/chat_history_router.py`):
- `GET /api/chat/sessions` — query params: `channel`, `limit`, `offset`
- `GET /api/chat/sessions/{session_id}/messages` — query params: `limit`, `before_id`
- Both require `Depends(get_current_user)`

**Tests**:
- `tests/chatServer/services/test_chat_history_service.py`
- `tests/chatServer/routers/test_chat_history_router.py`

### Task 3: Telegram session creation (backend-dev) — blocked by Task 1

**Branch:** `feat/SPEC-005-telegram-sessions`

In `chatServer/channels/telegram_bot.py` `handle_message()`, before invoking the agent:
```python
# Upsert chat_sessions row for this Telegram conversation
await bot_service._db_client.table("chat_sessions").upsert(
    {
        "user_id": user_id,
        "session_id": session_id,
        "channel": "telegram",
        "agent_name": "assistant",
        "is_active": True,
    },
    on_conflict="session_id",
).execute()
```

### Task 4: Scheduled execution session creation (backend-dev) — blocked by Task 1

**Branch:** `feat/SPEC-005-scheduled-sessions`

In `chatServer/services/scheduled_execution_service.py` `execute()`, after generating `session_id`:
```python
# Create chat_sessions row for this scheduled run
supabase_client = await get_supabase_client()
await supabase_client.table("chat_sessions").insert(
    {
        "user_id": user_id,
        "session_id": session_id,
        "channel": "scheduled",
        "agent_name": agent_name,
        "is_active": True,
    }
).execute()
```

Mark inactive after completion:
```python
await supabase_client.table("chat_sessions").update(
    {"is_active": False}
).eq("session_id", session_id).execute()
```

### Task 5: Frontend history loading (frontend-dev) — blocked by Task 2

**Branch:** `feat/SPEC-005-frontend-sessions`

**Hook** (`webApp/src/api/hooks/useChatHistoryHooks.ts`):
- `useChatSessions(channel?)` — list sessions
- `useChatMessages(sessionId)` — load messages for a session

**Store changes** (`webApp/src/stores/useChatStore.ts`):
- On init (when `sessionId` is available), load historical messages from server
- Replace empty `messages: []` with server-loaded history
- Optional: session picker showing web/telegram/scheduled conversations

### Dependencies

```
Task 1 (migration)
 ├── Task 2 (chat history API) ── Task 5 (frontend)
 ├── Task 3 (telegram sessions)
 └── Task 4 (scheduled sessions)
```

Tasks 2, 3, 4 can parallelize after Task 1. Task 5 waits for Task 2.

## Testing Requirements

### Unit Tests

- `tests/chatServer/services/test_chat_history_service.py`:
  - `test_get_sessions_returns_user_sessions`
  - `test_get_sessions_filters_by_channel`
  - `test_get_session_messages_returns_messages`
  - `test_get_session_messages_respects_cursor`
  - `test_get_session_messages_denies_other_user`

- `tests/chatServer/routers/test_chat_history_router.py`:
  - `test_get_sessions_requires_auth`
  - `test_get_sessions_returns_list`
  - `test_get_messages_requires_auth`
  - `test_get_messages_returns_list`

### Integration Tests

- Telegram: send message, verify `chat_sessions` has `channel='telegram'` row
- Scheduled: trigger run, verify `chat_sessions` has `channel='scheduled'` row
- Frontend: send message, refresh page, messages persist

### Manual Verification (UAT)

- [ ] Send message in web UI, refresh page, messages still visible
- [ ] Send message via Telegram, see session in web UI session list
- [ ] Trigger scheduled run, see session in web UI session list
- [ ] Filter sessions by channel works
- [ ] Telegram session shows messages when selected in web UI

## Edge Cases

- Existing sessions without `session_id`: backfill handles this
- Telegram user not linked: no session created (existing behavior)
- Very long session list: pagination prevents memory issues
- Concurrent upserts (Telegram): upsert on `session_id` prevents duplicates
- Session with no messages: shown in list but empty message panel

## Functional Units

1. **Unit 1:** Migration — add channel + session_id (`feat/SPEC-005-migration`) — **database-dev**
2. **Unit 2:** Chat history API + tests (`feat/SPEC-005-chat-history-api`) — **backend-dev** (blocked by 1)
3. **Unit 3:** Telegram session creation (`feat/SPEC-005-telegram-sessions`) — **backend-dev** (blocked by 1)
4. **Unit 4:** Scheduled session creation (`feat/SPEC-005-scheduled-sessions`) — **backend-dev** (blocked by 1)
5. **Unit 5:** Frontend history loading (`feat/SPEC-005-frontend-sessions`) — **frontend-dev** (blocked by 2)
