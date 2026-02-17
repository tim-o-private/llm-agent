# Backlog

Prioritized task queue. Items move to specs when ready for implementation.

## Priority Key

- **P0** — Blocking other work, do immediately
- **P1** — Important, do this milestone
- **P2** — Nice to have, do if time allows
- **P3** — Future consideration

## Active Specs

| Priority | ID | Title | Status | Outstanding Work |
|----------|----|-------|--------|------------------|
| P0 | SPEC-004 | [Test Coverage](specs/SPEC-004-test-coverage-existing-specs.md) | Ready | 5 parallel tasks: notification tests, telegram tests, scheduled exec tests, NotificationBadge UI tests, TelegramLink UI tests |
| P1 | SPEC-005 | [Unified Sessions](specs/SPEC-005-unified-sessions.md) | Ready (blocked by SPEC-004) | Migration, chat history API, telegram sessions, scheduled sessions, frontend history loading |
| P1 | SPEC-001 | [Notification System](specs/SPEC-001-notification-system.md) | Implementation Complete — Tests Outstanding | Covered by SPEC-004 |
| P1 | SPEC-002 | [Telegram Integration](specs/SPEC-002-telegram-integration.md) | Implementation Complete — Tests Outstanding | Covered by SPEC-004 |
| P1 | SPEC-003 | [Scheduled Agent Execution](specs/SPEC-003-scheduled-execution.md) | Implementation Complete — Tests Outstanding | Covered by SPEC-004 |

## Backlog Items (Not Yet Specced)

| Priority | Title | Notes |
|----------|-------|-------|
| P1 | Notification preferences UI | Settings page for per-category channel routing |
| P1 | Set Telegram env vars on Fly.io | Set `TELEGRAM_BOT_TOKEN` and `TELEGRAM_WEBHOOK_URL` as Fly secrets on `clarity-chatserver` before deploy |
| P2 | Execution results dashboard | View past scheduled runs in webApp |
| P2 | Agent schedule management UI | CRUD for agent_schedules in webApp |
| P3 | Slack channel integration | Similar to Telegram pattern via user_channels |
| P3 | Mobile push via web push API | Service worker + VAPID keys |

## Done

| ID | Title | Merged |
|----|-------|--------|
| — | — | — |
