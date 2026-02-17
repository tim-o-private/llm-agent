# Backlog

Prioritized task queue. Items move to specs when ready for implementation.

## Priority Key

- **P0** — Blocking other work, do immediately
- **P1** — Important, do this milestone
- **P2** — Nice to have, do if time allows
- **P3** — Future consideration

## Active Specs

| Priority | ID | Title | Status | Owner |
|----------|----|-------|--------|-------|
| P1 | SPEC-001 | [Notification System](specs/SPEC-001-notification-system.md) | Impl done, tests missing | — |
| P1 | SPEC-002 | [Telegram Integration](specs/SPEC-002-telegram-integration.md) | Impl done, tests missing | — |
| P1 | SPEC-003 | [Scheduled Agent Execution](specs/SPEC-003-scheduled-execution.md) | Impl done, tests missing | — |

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
