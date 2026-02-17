# SPEC-001: Notification System

> **Status:** Implementation Complete — Tests Not Written
> **Author:** Tim
> **Created:** 2026-02-17
> **Updated:** 2026-02-17

## Goal

Deliver a notification system that routes agent results, heartbeats, and approval requests to users via web UI (polling) and Telegram (push). Users see a notification bell in the top bar with unread count, can expand to view recent notifications, and mark them as read.

## Acceptance Criteria

- [x] AC-1: `notifications` table exists with RLS policies restricting access to the owning user
- [x] AC-2: `NotificationService` can store web notifications and route to Telegram when linked
- [x] AC-3: API endpoints exist for listing notifications, getting unread count, marking read, and marking all read — all require auth
- [x] AC-4: `NotificationBadge` component shows unread count, expands to list notifications, supports mark-read and mark-all-read
- [x] AC-5: Notifications auto-refresh every 15 seconds via React Query polling
- [x] AC-6: Category-based styling (heartbeat, approval_needed, agent_result, error, info)
- [x] AC-7: Notification body is truncated at 10,000 chars on storage

## Scope

### Files to Create

| File | Purpose |
|------|---------|
| `supabase/migrations/20260217000001_notifications.sql` | Notifications table + indexes + RLS |
| `chatServer/services/notification_service.py` | NotificationService class with web + Telegram routing |
| `chatServer/routers/notifications_router.py` | API endpoints: list, unread count, mark read, mark all read |
| `webApp/src/api/hooks/useNotificationHooks.ts` | React Query hooks for notification API |
| `webApp/src/components/features/Notifications/NotificationBadge.tsx` | Bell icon + dropdown component |
| `webApp/src/components/features/Notifications/index.ts` | Barrel export |

### Files to Modify

| File | Change |
|------|--------|
| `chatServer/main.py` | Register `notifications_router` |
| `webApp/src/components/navigation/TopBar.tsx` | Add `NotificationBadge` to navigation |

### Out of Scope

- Telegram bot service itself (SPEC-002)
- Scheduled execution that triggers notifications (SPEC-003)
- Notification preferences / per-category channel routing (future spec)
- Push notifications via web push API (future spec)

## Technical Approach

1. **Migration** — Create `notifications` table following `database-patterns` skill: UUID PK, user_id FK with CASCADE, RLS via `auth.uid()` (SELECT + UPDATE for owners, ALL for service role). Partial index on `(user_id, created_at DESC) WHERE read = false` for fast unread queries.

2. **Service layer** — `NotificationService` follows `backend-patterns` service pattern: takes `db_client` in constructor, async methods. `notify_user()` always stores in DB, conditionally routes to Telegram. `notify_pending_actions()` creates a summary notification for pending approvals. `_send_telegram_notification()` does a lazy import of `TelegramBotService` and fails silently if unconfigured.

3. **API endpoints** — Router at `/api/notifications` with `Depends(get_current_user)` and `Depends(get_supabase_client)`. Pydantic response models. Cap list endpoint at 100 results.

4. **Frontend hooks** — Follow `useChatApiHooks.ts` pattern: `supabase.auth.getSession()` for auth headers, React Query with `enabled: !!user`, 15s polling interval. Hooks: `useNotifications`, `useUnreadCount`, `useMarkNotificationRead`, `useMarkAllRead`.

5. **UI component** — `NotificationBadge` with bell icon (lucide), unread count badge, dropdown panel. Uses semantic color tokens per `frontend-patterns` skill. Category-based left border colors. Click-outside to close.

### Dependencies

- `auth.users` table (exists)
- `get_current_user` dependency (exists)
- `get_supabase_client` dependency (exists)
- Telegram integration (SPEC-002) for push — notifications work without it (web-only fallback)

## Testing Requirements

### Unit Tests

- `tests/chatServer/services/test_notification_service.py`:
  - `test_notify_user_stores_web_notification` — verify DB insert called
  - `test_notify_user_routes_to_telegram_when_linked` — verify Telegram send called
  - `test_notify_user_skips_telegram_when_not_linked` — verify no Telegram call
  - `test_get_notifications_returns_user_notifications`
  - `test_get_notifications_filters_unread_only`
  - `test_get_unread_count`
  - `test_mark_read`
  - `test_mark_all_read`
  - `test_body_truncation_at_10000_chars`

### Integration Tests

- `tests/chatServer/routers/test_notifications_router.py`:
  - `test_get_notifications_requires_auth` (401 without token)
  - `test_get_notifications_returns_list`
  - `test_get_unread_count_returns_count`
  - `test_mark_read_returns_success`
  - `test_mark_all_read_returns_count`

### Frontend Tests

- `webApp/src/components/features/Notifications/NotificationBadge.test.tsx`:
  - Renders bell icon
  - Shows unread count badge when count > 0
  - Hides badge when count = 0
  - Opens dropdown on click
  - Closes dropdown on outside click

### Manual Verification (UAT)

- [ ] Bell icon visible in top bar
- [ ] Unread count updates when a notification is created (via API or agent run)
- [ ] Clicking bell shows dropdown with notification list
- [ ] "Mark as read" on individual notification works
- [ ] "Mark all read" clears the unread count
- [ ] Category colors are visually distinct

## Edge Cases

- No notifications: dropdown shows "No notifications" message
- Very long body: truncated at 10,000 chars on storage, line-clamped at 2 lines in UI
- Rapid polling: React Query deduplicates concurrent requests
- Auth expired mid-session: hooks disabled when `user` is null, no 401 errors

## Functional Units

1. **Unit 1:** Migration + RLS (`feat/SPEC-001-migration`) — DONE
2. **Unit 2:** NotificationService (`feat/SPEC-001-notification-service`) — DONE
3. **Unit 3:** API endpoints + tests (`feat/SPEC-001-notification-api`) — DONE (endpoints), NOT STARTED (tests)
4. **Unit 4:** Frontend hooks + NotificationBadge + tests (`feat/SPEC-001-notification-ui`) — DONE (hooks + component), NOT STARTED (tests)

## Outstanding Work

- **All test files listed in Testing Requirements are NOT WRITTEN.** Zero test files exist:
  - `tests/chatServer/services/test_notification_service.py` — missing
  - `tests/chatServer/routers/test_notifications_router.py` — missing
  - `webApp/src/components/features/Notifications/NotificationBadge.test.tsx` — missing
