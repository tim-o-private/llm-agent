# Product Architecture — Unified Agent Platform

## Vision

llm-agent is a **unified agent platform** where all channels (web, Telegram, scheduled jobs) share the same agent execution, approval, and notification systems. Every agent interaction — regardless of origin — is tracked in `chat_sessions` and routed through the same tool-approval pipeline.

## Feature Map

```
                    chat_sessions (universal registry)
                           |
         +---------+-------+-------+---------+
         |         |               |         |
       Web UI   Telegram     Scheduled    (future)
         |         |               |
         +----+----+-------+------+
              |            |
      chat_message_history  |
              |            |
         Agent Execution --|-- Tool Approval (pending_actions)
              |            |
       NotificationService-+-- routes to web + telegram
```

All channels converge on:
1. **`chat_sessions`** — universal session registry with `channel` tag (`web`, `telegram`, `scheduled`)
2. **`chat_message_history`** — message storage keyed by `session_id`
3. **Agent execution** — `load_agent_executor_db()` + `wrap_tools_with_approval()`
4. **NotificationService** — routes to web (DB) and Telegram (bot)

## Cross-Cutting Checklist

Any feature that invokes an agent MUST:

- [ ] Create/upsert a `chat_sessions` row with the correct `channel` value
- [ ] Use `load_agent_executor_db()` for agent loading
- [ ] Wrap tools with `wrap_tools_with_approval()` using an `ApprovalContext`
- [ ] Normalize content block output (handle list-of-dicts from langchain-anthropic)
- [ ] Route results through `NotificationService` when appropriate
- [ ] Store messages in `chat_message_history` via the session's `session_id`

## Key Tables

| Table | Purpose |
|-------|---------|
| `chat_sessions` | Universal session registry — one row per conversation across all channels |
| `chat_message_history` | LangChain message storage, keyed by `session_id` |
| `notifications` | Web notification inbox (polled by frontend) |
| `user_channels` | Links users to external channels (Telegram `chat_id`) |
| `pending_actions` | Tool calls awaiting user approval |
| `agent_execution_results` | Stored results from scheduled runs |
| `agent_schedules` | Cron/interval schedule definitions |

## Platform Primitives — Reach for These First

Before designing new tables or services, check if an existing primitive handles your need. Adding a `job_type` string is always better than adding a `*_jobs` table.

### Decision Tree

Ask yourself what you're actually building:

1. **"I need to do work in the background"** → Enqueue a `jobs` row. Write a handler. Register it in `job_handlers.py`. Done.
2. **"I need to run something periodically"** → Create an `agent_schedules` row. BackgroundTaskService polls it and enqueues jobs.
3. **"I need to tell the user something"** → Call `NotificationService.notify_user()`. It routes to web + Telegram.
4. **"I need to invoke an agent"** → Use `ChatService.process_chat()` (web), `handle_message()` (Telegram), or `ScheduledExecutionService.execute()` (scheduled). Never build a new agent invocation path.
5. **"I need the user to approve something"** → Use `pending_actions` + the approval tier system. The tool wrapper handles this.
6. **"I need to store user preferences"** → Use `UpdateInstructionsTool` (standing instructions) or memory tools (learned preferences).
7. **"I need to connect to an external API"** → Use `external_api_connections` + the OAuth flow in `OAuthService`.

### Primitives Table

| Need | Primitive | Don't Build |
|------|-----------|-------------|
| Background work | `jobs` table + handler in `job_handlers.py` | A new `*_jobs` or `*_queue` table |
| User approval | `pending_actions` + trust tiers | A new approval/confirmation table |
| Store job results | `jobs.output` JSONB | A new `*_results` table for job output |
| Scheduled trigger | `agent_schedules` → creates jobs | A new cron/timer table |
| Notify user | `NotificationService.notify_user()` | Custom channel-specific delivery |
| Remember something | Memory tools or `update_instructions` | A new preferences/settings table |
| External API creds | `external_api_connections` + OAuth flow | A new credentials table |
| Audit trail | `audit_logs` | Per-feature logging tables |
| Agent execution log | `agent_execution_results` (linked from job) | A new execution tracking table |
| Invoke an agent | ChatService / ScheduledExecutionService | A new agent invocation pipeline |
| Normalize agent output | Content block handler in each channel | A new response formatter |

### How to Add a New Job Type (Most Common Extension Point)

```python
# 1. Write handler in chatServer/services/job_handlers.py
async def handle_my_thing(job: dict) -> dict:
    input_data = job.get("input", {})
    # do work
    return {"success": True}

# 2. Register in BackgroundTaskService startup (main.py)
job_runner.register_handler("my_thing", handle_my_thing)

# 3. Enqueue from anywhere (service layer, not routers)
await job_service.create(
    job_type="my_thing",
    input={"key": "value"},
    user_id=user_id,
)
```

That's it. The runner polls, claims, dispatches, retries on failure. No new tables, no new polling loops.

### Anti-patterns (Real Examples)

**SPEC-023 created `email_processing_jobs`** — a single-purpose table with its own status machine, polling loop, and error handling. SPEC-026 replaced it with `job_type = 'email_processing'` in the universal `jobs` table and a 10-line handler function.

**SPEC-023 inserted jobs from a router** — direct `INSERT INTO` in `external_api_router.py` instead of calling a service method. Violated A1 and created dead code when the actual OAuth flow bypassed that router.

**SPEC-021 used sync agent loader from async context** — called `load_agent_executor_db()` (sync, uses `asyncio.run()` internally) from `ScheduledExecutionService` (async). The async version `load_agent_executor_db_async()` already existed.

**Rule of thumb:** If your new table has a `status` column with lifecycle transitions (pending/processing/complete/failed), it's a job — use the `jobs` table.

See `reference.md` for detailed primitive descriptions and handler registration patterns.

## Recipe: Add a New Channel

Per A7 (cross-channel by default) and A11 (design for N):

1. **Handler:** Create channel-specific handler (like `chatServer/services/telegram_handler.py`)
2. **Session:** Create/lookup `chat_sessions` row with correct `channel` tag
3. **Routing:** Route incoming messages through the shared agent execution pipeline
4. **Notifications:** Register in `NotificationService` for outbound notifications
5. **User linking:** Add channel-specific user identifier to `user_channels` table
6. **Cross-channel:** Ensure messages are visible across all linked channels via shared `chat_id`

Reference: Telegram implementation in `chatServer/services/telegram_handler.py`

## Reference

See `reference.md` in this directory for detailed session lifecycle, message flows, and table relationships.
