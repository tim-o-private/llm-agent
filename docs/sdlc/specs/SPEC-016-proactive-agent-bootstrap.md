# SPEC-016: Proactive Agent — Bootstrap + Session Open

> **Status:** In Progress
> **Author:** spec-writer
> **Created:** 2026-02-23
> **Updated:** 2026-02-23

## Goal

Make Clarity feel like a smart assistant that's already paying attention — one that opens the conversation, not waits for it. Inspired by OpenClaw's heartbeat/wakeup pattern, the agent proactively initiates whenever the user returns to the app. New users get an organic onboarding bootstrap; returning users get a context-aware summary of what's in flight. The agent decides whether to speak or stay silent based on recency and relevance.

## Acceptance Criteria

- [x] **AC-01:** A new `session_open` channel type exists in `prompt_builder.py` with distinct guidance for new-user bootstrap and returning-user context-gather. [A7, A14]
- [x] **AC-02:** `build_agent_prompt()` accepts `last_message_at: datetime | None` and formats a time-context string for returning users. [A14]
- [x] **AC-03:** `POST /api/chat/session_open` endpoint exists, requires auth, accepts `{agent_name, session_id}`, and returns `{session_id, response, is_new_user, silent}`. [A1, A5]
- [x] **AC-04:** `SessionOpenService` loads the agent with `channel="session_open"`, wraps tools with the approval system, invokes the agent, and normalizes content block list output. [A1, A6]
- [x] **AC-05:** The agent returns `WAKEUP_SILENT` (anywhere in output) when the user was recently active and nothing is in flight. The service detects this and sets `silent=True`. [A14]
- [x] **AC-06:** When not silent, the AI response is persisted to LangChain message history so subsequent `/api/chat` calls have context of the opening exchange. [A14]
- [x] **AC-07:** Frontend calls `session_open` on every `initializeSessionAsync` (not just when messages are empty). Agent decides whether to respond. [A4]
- [x] **AC-08:** Frontend fires `triggerWakeup` on `visibilitychange` (tab return) with a 2-minute debounce to prevent spam. [A14]
- [x] **AC-09:** When the agent has something to say (non-silent), the chat panel auto-opens. [A14]
- [x] **AC-10:** Existing onboarding injection (`## Onboarding`) is preserved for `web`/`telegram` channels as a fallback for direct API callers and Telegram (which has no session_open trigger). [A7]
- [x] **AC-11:** All new backend code has unit tests: service (new user, returning user, silent detection, content normalization), router (200/401), prompt builder (session_open channel variants). [S1]

## Scope

### Files to Create

| File | Purpose |
|------|---------|
| `chatServer/models/session_open.py` | Pydantic request/response models |
| `chatServer/routers/session_open_router.py` | Thin router — `POST /api/chat/session_open` |
| `chatServer/services/session_open_service.py` | Fat service — agent invocation, silent detection, message persistence |
| `tests/chatServer/services/test_session_open_service.py` | Service unit tests |
| `tests/chatServer/routers/test_session_open_router.py` | Router unit tests |

### Files to Modify

| File | Change |
|------|--------|
| `chatServer/services/prompt_builder.py` | Add `session_open` channel guidance, `SESSION_OPEN_BOOTSTRAP_GUIDANCE`, `SESSION_OPEN_RETURNING_GUIDANCE`, `_format_time_context()`, `last_message_at` param |
| `src/core/agent_loader_db.py` | Thread `last_message_at` through both sync + async loaders to `build_agent_prompt` |
| `chatServer/main.py` | Register `session_open_router` |
| `webApp/src/stores/useChatStore.ts` | Add `callSessionOpen`, `triggerWakeup`, `lastWakeupAt`, wakeup in `initializeSessionAsync`, auto-open panel |
| `webApp/src/components/ChatPanelV2.tsx` | Wire `visibilitychange` listener to `triggerWakeup` |
| `tests/chatServer/services/test_prompt_builder.py` | Tests for `session_open` channel variants |

### Out of Scope

- **Telegram wakeup** — Telegram has no native "app open" event; existing `## Onboarding` fallback preserved
- **Structured onboarding wizard** — Bootstrap is organic conversation, not a multi-step form
- **Per-agent heartbeat checklist for session_open** — All agents share the same logic for now
- **Push notifications** — Heartbeat system handles that separately
- **Frontend unit tests for `callSessionOpen`** — Not implemented in this PR

## Technical Approach

### The Response Contract

Mirrors OpenClaw's `HEARTBEAT_OK` suppression pattern:

| Agent response | Frontend behavior |
|---------------|-------------------|
| Contains `WAKEUP_SILENT` | Suppressed — no message shown, user sees existing history |
| Any other content | Shown as an agent message bubble, chat panel auto-opens |

The agent uses `WAKEUP_SILENT` when the user was here very recently (< 5 minutes) and nothing material has changed. It always responds for new users.

### FU-1: Prompt Builder — `session_open` Channel (Backend)

Two new constants define agent behavior:

- `SESSION_OPEN_BOOTSTRAP_GUIDANCE` — For new users (no memory + no instructions): introduce self, ask about priorities and communication preferences organically, use `save_memory`/`update_instructions` when they respond.
- `SESSION_OPEN_RETURNING_GUIDANCE` — For returning users: includes `{time_context}` placeholder formatted with elapsed time since last message. Agent checks tools (tasks, reminders, emails), greets with brief summary, or returns `WAKEUP_SILENT` if nothing to say.

`build_agent_prompt()` gains a `last_message_at: datetime | None` parameter. `_format_time_context()` helper formats elapsed time into natural language ("less than 2 minutes ago", "45 minutes ago", "3 hours ago").

Section 8 (formerly "Onboarding") becomes conditional: `session_open` channel gets the new guidance; `web`/`telegram` channels retain the existing `ONBOARDING_SECTION` as fallback.

### FU-2: Backend Endpoint + Service (Backend)

**Router** (`session_open_router.py`): Thin router per A1 — `Depends(get_current_user)`, delegates to service. (see `backend-patterns` skill)

**Service** (`session_open_service.py`): Follows `scheduled_execution_service.py` pattern:
1. Detect `is_new_user` by querying `agent_long_term_memory` + `user_agent_prompt_customizations`
2. Query `chat_message_history` for most recent message timestamp → `last_message_at`
3. Load agent with `channel="session_open"` via `load_agent_executor_db_async`
4. Wrap tools with approval system (same `ApprovalContext` pattern as `chat.py`)
5. Invoke agent with internal trigger prompt, empty `chat_history`
6. Normalize output (handle content block lists)
7. Detect silent: `"WAKEUP_SILENT" in output`
8. Persist AI message to LangChain history if not silent
9. Return `{response, is_new_user, silent, session_id}`

**Agent loader** (`agent_loader_db.py`): Both `load_agent_executor_db` and `load_agent_executor_db_async` gain `last_message_at=None` parameter, threaded through to `build_agent_prompt`.

### FU-3: Frontend — Wakeup Trigger (Frontend)

**Store changes** (`useChatStore.ts`):
- `callSessionOpen()` module-level helper — mirrors `loadHistoricalMessages` pattern, uses `supabase.auth.getSession()` for auth token per A5
- `lastWakeupAt: number | null` — tracks last wakeup timestamp for debouncing
- `triggerWakeup()` — debounced (2 min), calls `callSessionOpen`, appends non-silent response, auto-opens panel
- `initializeSessionAsync` — calls `callSessionOpen` after loading historical messages (always, not just when empty); appends non-silent response; auto-opens panel if agent has something to say

**Component changes** (`ChatPanelV2.tsx`):
- `visibilitychange` listener calls `useChatStore.getState().triggerWakeup()` when tab becomes visible

### Dependencies

- SPEC-015 (Prompt Overhaul) — must be merged (provides `build_agent_prompt` with `tools` param and tool `prompt_section()`)
- `chatServer/security/tool_wrapper.py` — `ApprovalContext` + `wrap_tools_with_approval` must exist
- `chatServer/config/constants.py` — `CHAT_MESSAGE_HISTORY_TABLE_NAME` must exist

## Testing Requirements

### Unit Tests (required)

- `test_session_open_service.py`: new user detection, returning user, `WAKEUP_SILENT` detection, content block normalization, channel passed to loader, message persistence gating
- `test_session_open_router.py`: 200 with valid auth, 401 without
- `test_prompt_builder.py`: `session_open` + new user (bootstrap guidance, no `## Onboarding`), `session_open` + returning user with time context, `web` + new user still gets `## Onboarding`

### What to Test

- Happy path: new user bootstrap, returning user greeting, returning user silent
- Auth failure (401)
- Content block list normalization
- Time context formatting edge cases

### AC-to-Test Mapping

| AC | Test Type | Test Function |
|----|-----------|--------------|
| AC-01 | Unit | `test_prompt_builder::test_channel_session_open_new_user`, `test_channel_session_open_returning_user` |
| AC-02 | Unit | `test_prompt_builder::test_session_open_returning_time_context` |
| AC-03 | Unit | `test_session_open_router::test_session_open_success`, `test_session_open_requires_auth` |
| AC-04 | Unit | `test_session_open_service::test_agent_loaded_with_session_open_channel` |
| AC-05 | Unit | `test_session_open_service::test_wakeup_silent_detection` |
| AC-06 | Unit | `test_session_open_service::test_persist_when_not_silent`, `test_no_persist_when_silent` |
| AC-10 | Unit | `test_prompt_builder::test_web_channel_still_has_onboarding` |

### Manual Verification (UAT)

- [ ] New user: Log in fresh → chat panel opens → agent greeting appears unprompted
- [ ] Refresh: greeting persists (loaded from LangChain history)
- [ ] Reply: agent has context of the opening exchange
- [ ] Returning user, 10+ min later: switch away and return → agent greets with in-flight items
- [ ] Returning user, 30 seconds later: switch away and return → `WAKEUP_SILENT`, no new bubble
- [ ] Tab focus: minimize and restore → `triggerWakeup` fires via `visibilitychange`

## Edge Cases

- **Agent invocation failure**: Service catches exceptions, logs warning. Frontend treats `null` return as no-op (non-fatal).
- **Empty agent response**: Normalized to empty string. Frontend shows no message (treated as silent).
- **Concurrent tab race**: Each tab calls `session_open` independently. Both get greetings. Acceptable — each has its own session instance.
- **Page refresh before user types**: If the non-silent AI message was persisted (AC-06), `loadHistoricalMessages` returns it and the new `session_open` call may return `WAKEUP_SILENT` (recent interaction).
- **`chat_message_history` table missing for session**: `_get_last_message_at` returns `None`, treated as "first time opening this session."

## Functional Units (for PR Breakdown)

Single PR encompasses all three FUs since they are tightly coupled:

1. **FU-1:** Prompt builder changes (`chatServer/services/prompt_builder.py`) + agent loader threading (`src/core/agent_loader_db.py`)
2. **FU-2:** Models + service + router + main.py registration + backend tests
3. **FU-3:** Frontend store changes + ChatPanelV2 `visibilitychange` wiring

**Merge order:** Single PR, merge after `main` — `feat/spec-016-session-open`

## Completeness Checklist

- [x] Every AC has a stable ID (AC-01 through AC-11)
- [x] Every AC maps to at least one functional unit
- [x] Every cross-domain boundary has a contract (API request/response models defined)
- [x] Technical decisions reference principles from architecture-principles skill
- [x] Merge order is explicit (single PR)
- [x] Out-of-scope is explicit
- [x] Edge cases documented with expected behavior
- [x] Testing requirements map to ACs
