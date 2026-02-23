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
| P0 | SPEC-009 | [Conversation History & Agent Scheduling](specs/SPEC-009-conversation-history-and-agent-scheduling.md) | Planning |
| P0 | SPEC-017 | [User-Scoped Database Access](specs/SPEC-017-user-scoped-db-access.md) | Draft — 4 functional units |
| P1 | SPEC-007 | [Frontend Cleanup + Approval Toasts](specs/SPEC-007-frontend-cleanup.md) | Draft |
| P1 | SPEC-008 | [Context Management & Compaction](specs/SPEC-008-context-management-and-compaction.md) | Draft |
| P1 | SPEC-010 | [Agent Prompt Architecture](specs/SPEC-010-agent-prompt-architecture.md) | Draft — 3 functional units |
| P1 | SPEC-012 | [Unified Agent Invocation Service](specs/SPEC-012-agent-invocation-service.md) | Draft — 4 functional units |
| P1 | SPEC-013 | [Agent Task Tools](specs/SPEC-013-agent-task-tools.md) | Draft — 5 functional units |

## Backlog Items (Not Yet Specced)

### Legacy Tool Renaming (P2)

These tools predate the `verb_resource` naming convention. Each rename requires: Python class, DB `tools.name`, `agent_tool_type` enum value, and a migration.

| Current Name | New Name | Current Class | New Class |
|-------------|----------|---------------|-----------|
| `gmail_search` | `search_gmail_messages` | `GmailSearchTool` | `SearchGmailMessagesTool` |
| `gmail_get_message` | `get_gmail_message` | `GmailGetMessageTool` | `GetGmailMessageTool` |
| `gmail_digest` | `create_gmail_digest` | `GmailDigestTool` | `CreateGmailDigestTool` |
| `email_digest` | `send_email_digest` | `EmailDigestTool` | `SendEmailDigestTool` |

### Other Items

| Priority | Title | Notes |
|----------|-------|-------|
| P1 | MCP UAT expansion — browser-free UI testing | Extend `scripts/mcp/clarity_dev_server.py` with tools covering key UI flows: list sessions, list agents, list notifications, list pending actions, approve/reject action. Enables agents to do full UAT without browser access. Current MCP only covers `chat_with_clarity`. |
| P1 | Dynamic tool creation | Agent writes tool config rows to DB; validated by API; no code execution. Enables self-extending agent. |
| P1 | Trust escalation model | First-use manual approval → auto-approve after N consistent approvals. Rejection resets. Dashboard. |
| P2 | Email draft-reply workflow | Agent drafts replies via pending_actions; user approves/edits/sends. Requires compose OAuth scope. |
| P2 | Morning briefing (consolidated) | Single notification: email digest + due reminders + calendar + priorities from LTM |
| P2 | Multi-account email | OAuth per email account; agent triages across all accounts |
| P2 | Calendar integration | Google Calendar read access for scheduling context |
| P2 | Notification preferences UI | Settings page for per-category channel routing |
| P2 | Consolidate dual-access tables to single path | `tasks`, `chat_sessions`, `external_api_connections` are accessed both directly from frontend (anon key + RLS) and via backend (service_role + UserScopedClient). Both paths enforce user isolation, but dual access creates race conditions (concurrent agent + user edits). Consolidate to API-only access. Depends on SPEC-017. |
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
| SPEC-006 | Email Digests & Proactive Reminders | Feb 2026 |
