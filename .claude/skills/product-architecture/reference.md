# Product Architecture Reference

## Session Lifecycle by Channel

### Web (`channel = 'web'`)

```
User opens chat in web UI
  -> Frontend creates/resumes chat_sessions row (channel='web')
  -> POST /api/chat with session_id
  -> chatServer/services/chat.py:
       1. Load agent via load_agent_executor_db(session_id=session_id)
       2. Wrap tools with approval
       3. Load chat_message_history from PostgresChatMessageHistory(session_id)
       4. Invoke agent
       5. Response stored in chat_message_history automatically
       6. Return response to frontend
  -> Frontend displays response
```

### Telegram (`channel = 'telegram'`)

```
User sends message in Telegram
  -> Telegram webhook -> chatServer/routers/telegram_router.py
  -> chatServer/channels/telegram_bot.py handle_message():
       1. Look up user_id from chat_id via user_channels table
       2. Create/upsert chat_sessions row (channel='telegram', session_id='telegram_{chat_id}')
       3. Load agent via load_agent_executor_db(session_id=session_id)
       4. Wrap tools with approval
       5. Invoke agent
       6. Send response back via bot.send_message()
```

### Scheduled (`channel = 'scheduled'`)

```
APScheduler triggers a job
  -> chatServer/services/scheduled_execution_service.py execute():
       1. Create chat_sessions row (channel='scheduled', session_id='scheduled_{agent}_{timestamp}')
       2. Load agent via load_agent_executor_db(session_id=session_id)
       3. Wrap tools with approval
       4. Invoke agent
       5. Store result in agent_execution_results
       6. Notify user via NotificationService
       7. Mark chat_sessions as inactive on completion
```

## Message Flow

```
[Any Channel] -> Agent Invocation
                    |
                    v
             Tool Execution
                    |
            +-------+-------+
            |               |
     Auto-approved    Needs Approval
            |               |
            v               v
       Execute tool   pending_actions row
            |               |
            v               v
       Return result  NotificationService
                            |
                    +-------+-------+
                    |               |
                  Web DB        Telegram
                (notifications)  (bot.send)
                    |               |
                    v               v
              Frontend poll    Chat message
              (10s interval)
```

## Table Relationships

```
auth.users
  |-- 1:N --> chat_sessions (user_id)
  |             |-- session_id TEXT (unique, used as chat_message_history key)
  |             |-- channel TEXT ('web' | 'telegram' | 'scheduled')
  |             |-- is_active BOOLEAN
  |             |-- agent_name TEXT
  |
  |-- 1:N --> chat_message_history (session_id FK via chat_sessions.session_id)
  |             |-- content TEXT (message body)
  |             |-- type TEXT ('human' | 'ai' | 'system')
  |
  |-- 1:N --> notifications (user_id)
  |             |-- title, body, category, read, metadata
  |
  |-- 1:N --> user_channels (user_id)
  |             |-- channel_type TEXT ('telegram')
  |             |-- channel_id TEXT (telegram chat_id)
  |
  |-- 1:N --> pending_actions (user_id)
  |             |-- tool_name, tool_args, status, session_id
  |
  |-- 1:N --> agent_schedules (user_id)
  |             |-- agent_name, prompt, cron_expression, config
  |
  |-- 1:N --> agent_execution_results (user_id)
                |-- schedule_id, agent_name, result_content, status
```

## Shared Patterns

### Agent Loading
All channels use the same loader:
```python
from src.core.agent_loader_db import load_agent_executor_db

agent_executor = load_agent_executor_db(
    agent_name=agent_name,
    user_id=user_id,
    session_id=session_id,  # Must match chat_sessions.session_id
)
```

### Approval Wrapping
All channels wrap tools identically:
```python
from chatServer.security.tool_wrapper import ApprovalContext, wrap_tools_with_approval

approval_context = ApprovalContext(
    user_id=user_id,
    session_id=session_id,
    agent_name=agent_name,
    db_client=supabase_client,
    pending_actions_service=pending_service,
    audit_service=audit_service,
)
if hasattr(agent_executor, "tools") and agent_executor.tools:
    wrap_tools_with_approval(agent_executor.tools, approval_context)
```

## Platform Primitives (Detailed)

These are the reusable infrastructure components. New features should compose these, not reinvent them.

### Jobs Queue (`jobs` table, SPEC-026)

Universal background job queue. Any trigger (cron, event, user action) inserts a row; `JobRunnerService` dispatches to a registered handler by `job_type`.

**Adding a new job type:**
1. Write an async handler function in `chatServer/services/job_handlers.py`
2. Register it: `job_runner.register_handler('my_job_type', handle_my_job)`
3. Create jobs from wherever: `await job_service.create(job_type='my_job_type', input={...}, user_id=...)`

**Job lifecycle:** `pending` → `claimed` (atomic via SKIP LOCKED) → `running` → `complete`/`failed`
**Retry:** Automatic with exponential backoff (30s × 2^retry_count, capped at 15min)
**Key files:** `chatServer/services/job_service.py`, `chatServer/services/job_runner_service.py`, `chatServer/services/job_handlers.py`

### Pending Actions (`pending_actions` table)

Human-in-the-loop approval queue. The agent proposes an action; the user approves or rejects.

**When to use:** Any Act-tier capability where the agent does something on the user's behalf.
**When NOT to use:** Background work that doesn't need approval — use the jobs queue instead.
**Key files:** `chatServer/services/pending_actions.py`

### Notifications (`notifications` table + `NotificationService`)

Routes messages to users across channels (web DB, Telegram bot).

**When to use:** Any proactive communication to the user.
**Key files:** `chatServer/services/notification_service.py`

### Agent Schedules (`agent_schedules` table)

Cron-based trigger configuration. Evaluates cron expressions and creates jobs.

**When to use:** Recurring background work. The schedule creates jobs; the jobs queue executes them.
**Not for:** One-off deferred work — use `jobs.scheduled_for` instead.

### External API Connections (`external_api_connections` table)

OAuth credential storage with provider abstraction.

**When to use:** Any new external service integration (Google, Slack, etc.).
**Key files:** `chatServer/services/langchain_auth_bridge.py`, `chatServer/routers/external_api_router.py`

### Content Block Normalization
All channels must handle the list-of-dicts response format:
```python
output = response.get("output", "")
if isinstance(output, list):
    output = "".join(
        block.get("text", "") for block in output
        if isinstance(block, dict) and block.get("type") == "text"
    ) or "No response."
```
