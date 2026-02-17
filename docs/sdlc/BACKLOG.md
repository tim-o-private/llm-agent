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
| P0 | SPEC-005 | [Unified Sessions](specs/SPEC-005-unified-sessions.md) | Ready | Migration, chat history API, telegram sessions, scheduled sessions, frontend history loading |

## Backlog Items (Not Yet Specced)

| Priority | Title | Notes |
|----------|-------|-------|
| P1 | Notification preferences UI | Settings page for per-category channel routing |
| ~~P1~~ | ~~Set Telegram env vars on Fly.io~~ | Done — secrets set on `clarity-chatserver` |
| P2 | Execution results dashboard | View past scheduled runs in webApp |
| P2 | Agent schedule management UI | CRUD for agent_schedules in webApp |
| P3 | Slack channel integration | Similar to Telegram pattern via user_channels |
| P3 | Mobile push via web push API | Service worker + VAPID keys |

## Done

| ID | Title | Merged |
|----|-------|--------|
| SPEC-001 | Notification System | Pre-SDLC |
| SPEC-002 | Telegram Integration | Pre-SDLC |
| SPEC-003 | Scheduled Agent Execution | Pre-SDLC |
| SPEC-004 | Test Coverage for SPEC-001/002/003 | PRs #14-19 |
