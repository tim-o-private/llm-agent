# Backlog

Prioritized task queue. Items move to specs when ready for implementation.

## Priority Key

- **P0** — Blocking other work, do immediately
- **P1** — Important, do this milestone
- **P2** — Nice to have, do if time allows
- **P3** — Future consideration

## Active Specs

| Priority | ID | Title | Status |
|----------|----|-------|--------|
| P0 | SPEC-006 | [Email Digests & Proactive Reminders](specs/SPEC-006-email-digests-and-proactive-reminders.md) | Draft — 5 functional units |

## Backlog Items (Not Yet Specced)

| Priority | Title | Notes |
|----------|-------|-------|
| P1 | Dynamic tool creation | Agent writes tool config rows to DB; validated by API; no code execution. Enables self-extending agent. |
| P1 | Trust escalation model | First-use manual approval → auto-approve after N consistent approvals. Rejection resets. Dashboard. |
| P1 | Set Telegram env vars on Fly.io | Set `TELEGRAM_BOT_TOKEN` and `TELEGRAM_WEBHOOK_URL` as Fly secrets on `clarity-chatserver` before deploy |
| P2 | Email draft-reply workflow | Agent drafts replies via pending_actions; user approves/edits/sends. Requires compose OAuth scope. |
| P2 | Morning briefing (consolidated) | Single notification: email digest + due reminders + calendar + priorities from LTM |
| P2 | Multi-account email | OAuth per email account; agent triages across all accounts |
| P2 | Calendar integration | Google Calendar read access for scheduling context |
| P2 | Notification preferences UI | Settings page for per-category channel routing |
| P2 | Execution results dashboard | View past scheduled runs in webApp |
| P3 | Agent orchestration | Chief agent creates/manages sub-agents for complex tasks |
| P3 | Slack channel integration | Similar to Telegram pattern via user_channels |
| P3 | Mobile push via web push API | Service worker + VAPID keys |
| P3 | LTM viewing/editing UI | Frontend for seeing and editing what the agent remembers |

## Done

| ID | Title | Merged |
|----|-------|--------|
| SPEC-001 | Notification System | Feb 2026 |
| SPEC-002 | Telegram Integration | Feb 2026 |
| SPEC-003 | Scheduled Agent Execution | Feb 2026 |
| SPEC-004 | Test Coverage | Feb 2026 |
| SPEC-005 | Unified Sessions | Feb 2026 |
