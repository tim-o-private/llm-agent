# UAT Plan: Notifications, Telegram, Scheduled Execution

Covers SPEC-001, SPEC-002, SPEC-003.

## Prerequisites

- Local dev running (`pnpm dev`) with `.env` loaded
- `TELEGRAM_BOT_TOKEN` and `TELEGRAM_WEBHOOK_URL` set in `.env`
- Ngrok tunnel active pointing to `:3001`
- All migrations applied (`supabase db push` or applied via dashboard)
- Logged in to web app

---

## D — Developer Smoke Tests

| ID | Area | Test | Pass? |
|----|------|------|-------|
| D1 | Telegram | Generate link token, send `/start <token>` to bot, get "Account linked successfully!" | YES |
| D2 | Telegram | Send free-text message to bot, get agent response back | |
| D3 | Telegram | Disconnect from Settings > Integrations, confirm status changes to unlinked | |
| D4 | Telegram | Send message after unlinking, get "Your account isn't linked yet" response | |
| D5 | Notifications | Insert a notification via SQL/service, see bell icon update with unread count | |
| D6 | Notifications | Click bell, see notification in dropdown with category color | |
| D7 | Notifications | Mark single notification as read, count decreases | |
| D8 | Notifications | Mark all read, badge disappears | |
| D9 | Notifications | 15s polling — insert new notification, wait, see count update without refresh | |
| D10 | Scheduled | Trigger scheduled agent run (modify cron to fire now or call service directly), confirm result row in `agent_execution_results` | |

---

## A — Acceptance Tests (maps to spec ACs)

### SPEC-001: Notification System

| ID | AC | Test | Pass? |
|----|-----|------|-------|
| A1 | AC-1 | `notifications` table exists, RLS blocks cross-user reads (query as different user returns 0) | |
| A2 | AC-2 | `NotificationService.notify_user()` stores a row in notifications table | |
| A3 | AC-2 | `NotificationService.notify_user()` sends Telegram message when user has linked account | |
| A4 | AC-3 | `GET /api/notifications` returns notification list (auth required, 401 without token) | |
| A5 | AC-3 | `GET /api/notifications/unread/count` returns correct count | |
| A6 | AC-3 | `POST /api/notifications/{id}/read` marks notification as read | |
| A7 | AC-3 | `POST /api/notifications/read-all` marks all read, returns count | |
| A8 | AC-4 | NotificationBadge renders bell, shows unread count, opens dropdown | |
| A9 | AC-5 | Polling at 15s interval — new notification appears without manual refresh | |
| A10 | AC-6 | Category colors visually distinct: heartbeat (brand), approval_needed (amber), agent_result (blue), error (red), info (gray) | |
| A11 | AC-7 | Insert notification with >10K char body, confirm stored body is truncated to 10K | |

### SPEC-002: Telegram Integration

| ID | AC | Test | Pass? |
|----|-----|------|-------|
| A12 | AC-1 | `user_channels` table exists with RLS, UNIQUE on (user_id, channel_type) | |
| A13 | AC-2 | `channel_linking_tokens` table exists, token expires after 10 min | |
| A14 | AC-3 | `GET /api/telegram/link-token` returns token + bot_username | |
| A15 | AC-4 | `/start <token>` links account, row appears in `user_channels` | |
| A16 | AC-5 | `POST /api/telegram/unlink` sets `is_active=false`, Settings shows unlinked | |
| A17 | AC-6 | Bot sends markdown-formatted notification text | |
| A18 | AC-7 | Bot sends approval request with inline Approve/Reject keyboard | |
| A19 | AC-8 | Free-text message routed to assistant agent, response sent back | |
| A20 | AC-9 | Agent response >4000 chars is split into multiple messages | |
| A21 | AC-10 | TelegramLink component shows Connected/Disconnected states correctly | |

### SPEC-003: Scheduled Agent Execution

| ID | AC | Test | Pass? |
|----|-----|------|-------|
| A22 | AC-1 | `agent_execution_results` table exists with status CHECK, proper indexes, RLS | |
| A23 | AC-2 | `ScheduledExecutionService.execute()` loads agent, wraps tools, invokes, stores result | |
| A24 | AC-3 | Result row includes: status, result_content, pending_actions_created, execution_duration_ms | |
| A25 | AC-4 | Force an error (bad agent name), confirm error result stored with status='error' | |
| A26 | AC-5 | After execution, notification appears in notifications table | |
| A27 | AC-6 | When execution creates pending actions, an `approval_needed` notification is also created | |
| A28 | AC-7 | `agent_configurations` contains `orchestrator` with Gmail tools linked | |
| A29 | AC-8 | `agent_schedules` contains daily 7AM heartbeat for Telegram-linked users | |
| A30 | AC-9 | `background_tasks.py._execute_scheduled_agent` delegates to `ScheduledExecutionService` | |

---

## E — Edge Case Tests

| ID | Area | Test | Pass? |
|----|------|------|-------|
| E1 | Telegram | Expired token (wait 10 min or update DB) — bot says "Invalid or expired token" | |
| E2 | Telegram | Re-link (already linked user generates new token and links) — chat_id updated via upsert | |
| E3 | Telegram | Bot not configured (unset TELEGRAM_BOT_TOKEN) — `/api/telegram/*` returns 503, no crash | |
| E4 | Notifications | No notifications — dropdown shows "No notifications" or empty state | |
| E5 | Notifications | API list capped at 100 results (insert 110, request all, get 100) | |
| E6 | Scheduled | Agent not found in DB — error result stored, error notification sent | |
| E7 | Scheduled | Very long result (>50K chars) — truncated before storage | |
| E8 | Scheduled | NotificationService fails — execution result still stored (non-fatal) | |

---

## R — Regression Checks

| ID | Area | Test | Pass? |
|----|------|------|-------|
| R1 | Email digest | Existing email digest schedule still works (backward compat in background_tasks.py) | |
| R2 | Chat | Web chat still works normally (no regressions from tool wrapping changes) | |
| R3 | Actions | Pending actions polling still works (10s interval, approval/reject flow) | |
| R4 | Auth | Login/logout cycle — hooks disable/enable correctly, no 401 errors | |
| R5 | CORS | Frontend can reach all new endpoints (notifications, telegram) without CORS errors | |
