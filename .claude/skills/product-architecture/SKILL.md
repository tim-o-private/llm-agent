# Product Architecture — Unified Agent Platform

## Vision

llm-agent is a **unified agent platform** where all channels (web, Telegram, scheduled jobs) share the same agent execution, approval, and notification systems. Every agent interaction — regardless of origin — is tracked in `chat_sessions` and routed through the same tool-approval pipeline.

## Feature Map

```
                    chat_sessions (universal registry)
                           |
         +---------+-------+-------+-----------+
         |         |               |           |
       Web UI   Telegram     Scheduled    Heartbeat
         |         |               |           |
         +----+----+-------+------+-----------+
              |            |
      chat_message_history  |
              |            |
         Agent Execution --|-- Tool Approval (pending_actions)
              |            |
       NotificationService-+-- routes to web + telegram
                           |
                    (heartbeat: suppressed when HEARTBEAT_OK)
```

All channels converge on:
1. **`chat_sessions`** — universal session registry with `channel` tag (`web`, `telegram`, `scheduled`)
2. **`chat_message_history`** — message storage keyed by `session_id`
3. **Agent execution** — `load_agent_executor_db()` + `wrap_tools_with_approval()`
4. **NotificationService** — routes to web (DB) and Telegram (bot); heartbeat suppresses when nothing to report

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

## Reference

See `reference.md` in this directory for detailed session lifecycle, message flows, and table relationships.
