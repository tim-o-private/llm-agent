# SPEC-002: Telegram Integration

> **Status:** Implementation Complete — Tests Not Written
> **Author:** Tim
> **Created:** 2026-02-17
> **Updated:** 2026-02-17

## Goal

Enable users to link their Telegram account and receive notifications, approve/reject agent actions, and chat with agents directly via Telegram. Uses a token-based linking flow and aiogram 3.x in webhook mode.

## Acceptance Criteria

- [x] AC-1: `user_channels` table exists with RLS, storing linked Telegram chat IDs
- [x] AC-2: `channel_linking_tokens` table exists for the secure token-based linking flow
- [x] AC-3: Users can generate a linking token from the web UI
- [x] AC-4: Sending `/start <token>` to the Telegram bot links the account
- [x] AC-5: Users can unlink their Telegram account from the web UI
- [x] AC-6: TelegramBotService sends notifications (text + markdown)
- [x] AC-7: TelegramBotService sends approval requests with inline approve/reject buttons
- [x] AC-8: Free-text messages to the bot are routed to the assistant agent
- [x] AC-9: Agent responses in Telegram handle content block lists and the 4096-char limit
- [x] AC-10: TelegramLink component on Settings/Integrations page shows status + link/unlink flow

## Scope

### Files to Create

| File | Purpose |
|------|---------|
| `supabase/migrations/20260217000002_user_channels.sql` | user_channels + channel_linking_tokens tables + RLS |
| `chatServer/channels/telegram_bot.py` | TelegramBotService class + message handlers |
| `chatServer/services/telegram_linking_service.py` | Token generation, linking, unlinking, status |
| `chatServer/routers/telegram_router.py` | Webhook + linking API endpoints |
| `webApp/src/api/hooks/useTelegramHooks.ts` | React Query hooks for Telegram API |
| `webApp/src/components/features/TelegramLink/TelegramLink.tsx` | Link/unlink UI component |
| `webApp/src/components/features/TelegramLink/index.ts` | Barrel export |

### Files to Modify

| File | Change |
|------|--------|
| `chatServer/main.py` | Register `telegram_router`, initialize bot in lifespan |
| `chatServer/config/settings.py` | Add `telegram_bot_token` and `telegram_webhook_url` settings |
| `webApp/src/pages/Settings/Integrations.tsx` | Add TelegramLink component |
| `requirements.txt` | Add `aiogram>=3.0` |

### Out of Scope

- Notification routing logic (SPEC-001 — NotificationService calls TelegramBotService)
- Scheduled execution (SPEC-003)
- Group chat support (only 1:1 bot chats)
- Voice/media message handling (text only)

## Technical Approach

1. **Migration** — Two tables: `user_channels` (user_id, channel_type, channel_id, is_active, UNIQUE on user_id+channel_type) and `channel_linking_tokens` (token, user_id, expires_at default 10min, used flag). RLS on both.

2. **Telegram bot** — `TelegramBotService` using aiogram 3.x in webhook mode. No long-polling thread — Telegram POSTs to `/api/telegram/webhook`. Handlers: `/start <token>` for linking, callback queries for approve/reject, free-text routed to assistant agent. Bot initialized in FastAPI lifespan if `TELEGRAM_BOT_TOKEN` is set.

3. **Linking service** — `create_linking_token()` generates a `secrets.token_urlsafe(32)`, stores in DB with 10-min expiry. `link_telegram_account()` validates token + expiry, upserts into user_channels, marks token used. `unlink_telegram_account()` sets `is_active=False`. `get_telegram_status()` returns linked/unlinked status.

4. **API endpoints** — Router at `/api/telegram`. Webhook endpoint (no auth — Telegram calls it). Linking endpoints (auth required): `GET /link-token`, `GET /status`, `POST /unlink`.

5. **Frontend** — `TelegramLink` component on Integrations page. Shows "Connected" badge when linked, "Connect Telegram" button when not. Token flow: generate token -> display `/start <token>` with copy button -> 10-min expiry notice.

### Dependencies

- SPEC-001 (NotificationService) — for Telegram notification routing
- `TELEGRAM_BOT_TOKEN` environment variable
- `TELEGRAM_WEBHOOK_URL` environment variable (e.g., `https://api.example.com/api/telegram/webhook`)
- aiogram 3.x package

## Testing Requirements

### Unit Tests

- `tests/chatServer/services/test_telegram_linking_service.py`:
  - `test_create_linking_token_stores_in_db`
  - `test_link_telegram_account_valid_token` — verify upsert into user_channels
  - `test_link_telegram_account_expired_token` — verify rejection
  - `test_link_telegram_account_used_token` — verify rejection
  - `test_unlink_telegram_account` — verify sets is_active=False
  - `test_get_telegram_status_linked` — returns linked=True
  - `test_get_telegram_status_not_linked` — returns linked=False

- `tests/chatServer/channels/test_telegram_bot.py`:
  - `test_send_notification_truncates_at_4000_chars`
  - `test_send_approval_request_has_inline_keyboard`
  - `test_process_update_handles_invalid_data`

### Integration Tests

- `tests/chatServer/routers/test_telegram_router.py`:
  - `test_webhook_returns_ok`
  - `test_get_link_token_requires_auth`
  - `test_get_status_requires_auth`
  - `test_unlink_requires_auth`

### Frontend Tests

- `webApp/src/components/features/TelegramLink/TelegramLink.test.tsx`:
  - Shows "Connect Telegram" button when not linked
  - Shows "Connected" badge when linked
  - Shows token + copy button after generating
  - Shows confirmation dialog before unlinking

### Manual Verification (UAT)

- [ ] Generate link token from Settings > Integrations
- [ ] Send `/start <token>` to bot in Telegram
- [ ] Bot responds with "Account linked successfully!"
- [ ] Settings page shows "Connected" status
- [ ] Send a text message to bot — get agent response
- [ ] Disconnect from Settings works
- [ ] Expired token is rejected by bot

## Edge Cases

- Bot not configured (`TELEGRAM_BOT_TOKEN` not set): endpoints return 503, no crash
- Token expired: bot responds with "Invalid or expired token"
- User already linked: upsert updates the chat_id (re-linking)
- Very long agent response: split into 4000-char chunks
- Bot initializing: responds with "Bot is still initializing"

## Functional Units

1. **Unit 1:** Migration — user_channels + channel_linking_tokens (`feat/SPEC-002-migration`) — DONE
2. **Unit 2:** Telegram bot service + linking service (`feat/SPEC-002-telegram-service`) — DONE
3. **Unit 3:** API endpoints + tests (`feat/SPEC-002-telegram-api`) — DONE (endpoints), NOT STARTED (tests)
4. **Unit 4:** Frontend TelegramLink component + hooks + tests (`feat/SPEC-002-telegram-ui`) — DONE (component + hooks), NOT STARTED (tests)

## Outstanding Work

- **All test files listed in Testing Requirements are NOT WRITTEN.** Zero test files exist:
  - `tests/chatServer/services/test_telegram_linking_service.py` — missing
  - `tests/chatServer/channels/test_telegram_bot.py` — missing
  - `tests/chatServer/routers/test_telegram_router.py` — missing
  - `webApp/src/components/features/TelegramLink/TelegramLink.test.tsx` — missing

## Implementation Deviations

- **`channels/` package**: Spec listed `chatServer/channels/__init__.py` as a file to create, but it was not listed in "Files to Create" table. The `__init__.py` does exist.
- **`chatServer/models/telegram.py`**: Spec listed this in the plan-file but NOT in the spec's "Files to Create" table. Response models are defined inline in `telegram_router.py` instead of a separate models file. This is fine — simpler approach.
