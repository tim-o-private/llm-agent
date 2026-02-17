# SPEC-003: Scheduled Agent Execution

> **Status:** Implementation Complete — Tests Not Written
> **Author:** Tim
> **Created:** 2026-02-17
> **Updated:** 2026-02-17

## Goal

Enable any agent to run on a schedule (cron-based), with results stored in a dedicated table, tools wrapped with the approval system, and notifications sent via SPEC-001's NotificationService. Replaces the special-cased execution in BackgroundTaskService with a generalized service.

## Acceptance Criteria

- [x] AC-1: `agent_execution_results` table exists with RLS (SELECT for owner, ALL for service role)
- [x] AC-2: `ScheduledExecutionService.execute()` loads an agent from DB, wraps tools with approval, invokes the agent, normalizes output, and stores the result
- [x] AC-3: Execution results include: status (success/error/partial), output content, pending actions count, duration in ms
- [x] AC-4: Error results are stored (not lost) — both the error message and duration
- [x] AC-5: After execution, NotificationService is called with the result summary
- [x] AC-6: Pending actions trigger a separate `approval_needed` notification
- [x] AC-7: Orchestrator agent configuration exists in DB with Gmail read tools linked
- [x] AC-8: Default daily 7AM heartbeat schedule created for users with Telegram linked
- [x] AC-9: `BackgroundTaskService` calls `ScheduledExecutionService` instead of inline agent logic

## Scope

### Files to Create

| File | Purpose |
|------|---------|
| `supabase/migrations/20260217000000_agent_execution_results.sql` | Execution results table + indexes + RLS |
| `supabase/migrations/20260217000003_configure_orchestrator_agent.sql` | Orchestrator agent config + schedule |
| `chatServer/services/scheduled_execution_service.py` | Generalized agent execution service |

### Files to Modify

| File | Change |
|------|--------|
| `chatServer/services/background_tasks.py` | Replace inline execution with `ScheduledExecutionService` call |

### Out of Scope

- Web UI for viewing execution results (future spec)
- Web UI for managing schedules (future spec)
- Agent schedule CRUD API (future spec)
- Non-cron scheduling patterns (future spec)

## Technical Approach

1. **Migration — execution results** — Table with: UUID PK, user_id FK, schedule_id FK (nullable, SET NULL on delete), agent_name, prompt, result_content (TEXT, truncated at 50K), status CHECK (success/error/partial), pending_actions_created, execution_duration_ms, metadata JSONB. RLS: SELECT for `auth.uid()`, ALL for `postgres` role. Indexes on (user_id, created_at DESC) and (schedule_id).

2. **Migration — orchestrator config** — Insert `orchestrator` agent configuration with Claude Sonnet model, read-only system prompt. Link Gmail read tools (gmail_search, gmail_get_message). Create default heartbeat schedule for users with active Telegram channels.

3. **ScheduledExecutionService** — Mirrors `chatServer/services/chat.py` patterns:
   - Load agent from DB via `load_agent_executor_db()` (always fresh, no cache)
   - Wrap tools with `ApprovalContext` + `wrap_tools_with_approval()`
   - Invoke with `ainvoke()`, normalize content blocks
   - Store result in `agent_execution_results`
   - Call `NotificationService.notify_user()` with result summary
   - Call `NotificationService.notify_pending_actions()` if pending > 0
   - On error: store error result, log, return error dict

4. **BackgroundTaskService integration** — Replace inline agent execution in `_execute_scheduled_agent` with a call to `ScheduledExecutionService.execute(schedule)`.

### Dependencies

- SPEC-001 (NotificationService) — for result notifications
- `agent_configurations` table (exists)
- `agent_tools` table (exists)
- `agent_schedules` table (exists)
- `tools` table with Gmail tools (exists)
- `load_agent_executor_db` function (exists)
- `ApprovalContext` + `wrap_tools_with_approval` (exists)

## Testing Requirements

### Unit Tests

- `tests/chatServer/services/test_scheduled_execution_service.py`:
  - `test_execute_success` — verify agent invoked, result stored, notification sent
  - `test_execute_error` — verify error result stored, error returned
  - `test_execute_wraps_tools_with_approval`
  - `test_execute_normalizes_content_blocks` — list of blocks -> string
  - `test_execute_stores_duration_ms`
  - `test_execute_truncates_result_at_50000_chars`
  - `test_execute_notifies_pending_actions_when_count_gt_0`
  - `test_execute_skips_pending_notification_when_count_0`

### Integration Tests

- `tests/chatServer/services/test_scheduled_execution_integration.py`:
  - `test_full_execution_cycle` — end-to-end with mocked agent

### Manual Verification (UAT)

- [ ] Trigger a scheduled agent run manually (via BackgroundTaskService)
- [ ] Verify result appears in `agent_execution_results` table
- [ ] Verify notification appears in the notification bell (SPEC-001)
- [ ] Verify error execution stores error result (not lost)
- [ ] Verify pending actions trigger approval_needed notification

## Edge Cases

- Agent not found in DB: error result stored, notification with error category
- Agent tool wrapping fails: non-fatal warning, execution continues without approval
- Very long result: truncated at 50,000 chars before storage
- NotificationService fails: non-fatal warning logged, execution result still stored
- Schedule has no prompt: uses empty string, agent handles it
- Concurrent executions of same schedule: each gets unique session_id

## Functional Units

1. **Unit 1:** Migration — agent_execution_results table (`feat/SPEC-003-migration`) — DONE
2. **Unit 2:** ScheduledExecutionService + tests (`feat/SPEC-003-execution-service`) — DONE (service), NOT STARTED (tests)
3. **Unit 3:** Orchestrator agent config migration (`feat/SPEC-003-orchestrator-config`) — DONE
4. **Unit 4:** BackgroundTaskService integration (`feat/SPEC-003-background-integration`) — DONE

## Outstanding Work

- **All test files listed in Testing Requirements are NOT WRITTEN.** Zero test files exist:
  - `tests/chatServer/services/test_scheduled_execution_service.py` — missing
  - `tests/chatServer/services/test_scheduled_execution_integration.py` — missing
