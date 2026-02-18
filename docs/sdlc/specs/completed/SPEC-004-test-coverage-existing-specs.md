# SPEC-004: Test Coverage for Existing Specs

> **Status:** Ready
> **Author:** Tim
> **Created:** 2026-02-17
> **Updated:** 2026-02-17

## Goal

Write the missing tests for SPEC-001 (Notifications), SPEC-002 (Telegram), and SPEC-003 (Scheduled Execution) before changing session architecture in SPEC-005. These tests establish a safety net for the refactoring work ahead.

## Acceptance Criteria

- [ ] AC-1: `tests/chatServer/services/test_notification_service.py` exists with all cases from SPEC-001
- [ ] AC-2: `tests/chatServer/routers/test_notifications_router.py` exists with auth and CRUD cases
- [ ] AC-3: `tests/chatServer/services/test_telegram_linking_service.py` exists with token lifecycle cases
- [ ] AC-4: `tests/chatServer/channels/test_telegram_bot.py` exists with send/receive cases
- [ ] AC-5: `tests/chatServer/routers/test_telegram_router.py` exists with webhook + auth cases
- [ ] AC-6: `tests/chatServer/services/test_scheduled_execution_service.py` exists with execute lifecycle cases
- [ ] AC-7: `webApp/src/components/features/Notifications/NotificationBadge.test.tsx` exists with render + interaction cases
- [ ] AC-8: `webApp/src/components/features/TelegramLink/TelegramLink.test.tsx` exists with link/unlink flow cases
- [ ] AC-9: `pytest tests/` passes (excluding pre-existing failures)
- [ ] AC-10: `cd webApp && pnpm test -- --run` passes

## Scope

### Files to Create

| File | Purpose |
|------|---------|
| `tests/chatServer/services/test_notification_service.py` | NotificationService unit tests |
| `tests/chatServer/routers/test_notifications_router.py` | Notifications API tests |
| `tests/chatServer/services/test_telegram_linking_service.py` | TelegramLinkingService unit tests |
| `tests/chatServer/channels/test_telegram_bot.py` | TelegramBotService unit tests |
| `tests/chatServer/routers/test_telegram_router.py` | Telegram API tests |
| `tests/chatServer/services/test_scheduled_execution_service.py` | ScheduledExecutionService unit tests |
| `webApp/src/components/features/Notifications/NotificationBadge.test.tsx` | NotificationBadge component tests |
| `webApp/src/components/features/TelegramLink/TelegramLink.test.tsx` | TelegramLink component tests |

### Files to Modify

None — this spec only adds tests.

### Out of Scope

- Changing any implementation code
- Integration tests requiring a live database
- End-to-end tests

## Technical Approach

All tasks are independent and can run in parallel.

### Task 1: Notification Service Tests (backend-dev)

**Branch:** `feat/SPEC-004-notification-tests`

Create `tests/chatServer/services/test_notification_service.py`:
- Mock `db_client` (Supabase client) with `AsyncMock`
- Test `notify_user` stores web notification (verify DB insert args)
- Test `notify_user` routes to Telegram when user has linked account
- Test `notify_user` skips Telegram when no linked account
- Test `get_notifications` returns results from DB
- Test `get_unread_count` returns count
- Test `mark_read` calls update with correct filters
- Test `mark_all_read` calls update with correct filters
- Test body truncation at 10,000 chars

Create `tests/chatServer/routers/test_notifications_router.py`:
- Use `httpx.AsyncClient` with FastAPI `TestClient`
- Mock `get_current_user` dependency
- Test GET `/api/notifications` returns list
- Test GET `/api/notifications/unread-count` returns count
- Test PATCH `/api/notifications/{id}/read` returns success
- Test POST `/api/notifications/mark-all-read` returns count
- Test all endpoints require auth (401 without token)

**Pattern reference:** `tests/chatServer/services/test_chat.py`, `tests/chatServer/security/test_tool_wrapper.py`

**Verify:** `pytest tests/chatServer/services/test_notification_service.py tests/chatServer/routers/test_notifications_router.py -v`

### Task 2: Telegram Tests (backend-dev)

**Branch:** `feat/SPEC-004-telegram-tests`

Create `tests/chatServer/services/test_telegram_linking_service.py`:
- Mock DB client
- Test `create_linking_token` stores token with expiry
- Test `link_telegram_account` with valid token — upserts user_channels
- Test `link_telegram_account` with expired token — returns False
- Test `link_telegram_account` with used token — returns False
- Test `unlink_telegram_account` sets is_active=False
- Test `get_telegram_status` when linked vs not linked

Create `tests/chatServer/channels/test_telegram_bot.py`:
- Mock aiogram Bot
- Test `send_notification` truncates at 4000 chars
- Test `send_approval_request` creates inline keyboard with approve/reject
- Test `process_update` handles invalid data without crashing

Create `tests/chatServer/routers/test_telegram_router.py`:
- Test POST `/api/telegram/webhook` returns 200
- Test GET `/api/telegram/link-token` requires auth
- Test GET `/api/telegram/status` requires auth
- Test POST `/api/telegram/unlink` requires auth

**Verify:** `pytest tests/chatServer/services/test_telegram_linking_service.py tests/chatServer/channels/test_telegram_bot.py tests/chatServer/routers/test_telegram_router.py -v`

### Task 3: Scheduled Execution Tests (backend-dev)

**Branch:** `feat/SPEC-004-scheduled-execution-tests`

Create `tests/chatServer/services/test_scheduled_execution_service.py`:
- Mock `load_agent_executor_db`, `get_supabase_client`, `NotificationService`
- Test `execute` success: agent invoked, result stored, notification sent
- Test `execute` error: error result stored, error returned
- Test tool wrapping: verify `wrap_tools_with_approval` called
- Test content block normalization: list of dicts → string
- Test duration tracking: verify `execution_duration_ms` stored
- Test result truncation at 50,000 chars
- Test pending actions notification: called when count > 0, skipped when count = 0

**Verify:** `pytest tests/chatServer/services/test_scheduled_execution_service.py -v`

### Task 4: NotificationBadge UI Tests (frontend-dev)

**Branch:** `feat/SPEC-004-notification-ui-tests`

Create `webApp/src/components/features/Notifications/NotificationBadge.test.tsx`:
- Mock `useNotificationHooks` hooks
- Test renders bell icon
- Test shows unread count badge when count > 0
- Test hides unread badge when count = 0
- Test opens dropdown on click
- Test closes dropdown on outside click

**Verify:** `cd webApp && pnpm test -- --run`

### Task 5: TelegramLink UI Tests (frontend-dev)

**Branch:** `feat/SPEC-004-telegram-ui-tests`

Create `webApp/src/components/features/TelegramLink/TelegramLink.test.tsx`:
- Mock `useTelegramHooks` hooks
- Test shows "Connect Telegram" button when not linked
- Test shows "Connected" badge when linked
- Test token generation flow
- Test unlink confirmation dialog

**Verify:** `cd webApp && pnpm test -- --run`

### Dependencies

None — all 5 tasks are independent.

## Testing Requirements

This spec IS the tests. All acceptance criteria are test files passing.

### Manual Verification (UAT)

- [ ] `pytest tests/chatServer/services/test_notification_service.py tests/chatServer/routers/test_notifications_router.py -v` — all pass
- [ ] `pytest tests/chatServer/services/test_telegram_linking_service.py tests/chatServer/channels/test_telegram_bot.py tests/chatServer/routers/test_telegram_router.py -v` — all pass
- [ ] `pytest tests/chatServer/services/test_scheduled_execution_service.py -v` — all pass
- [ ] `cd webApp && pnpm test -- --run` — all pass
- [ ] `ruff check tests/` — clean

## Functional Units

1. **Unit 1:** Notification service + router tests (`feat/SPEC-004-notification-tests`) — **backend-dev**
2. **Unit 2:** Telegram service + bot + router tests (`feat/SPEC-004-telegram-tests`) — **backend-dev**
3. **Unit 3:** Scheduled execution tests (`feat/SPEC-004-scheduled-execution-tests`) — **backend-dev**
4. **Unit 4:** NotificationBadge UI tests (`feat/SPEC-004-notification-ui-tests`) — **frontend-dev**
5. **Unit 5:** TelegramLink UI tests (`feat/SPEC-004-telegram-ui-tests`) — **frontend-dev**
