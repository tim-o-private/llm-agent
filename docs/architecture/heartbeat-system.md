# Heartbeat System

## Problem

Agents are reactive — they only respond when a user sends a message. There's no mechanism for an agent to proactively check on things (new emails, pending approvals, stale tasks) and only bother the user when something actually needs attention.

Scheduled runs exist, but they always notify the user with the result, even when everything is fine. This trains users to ignore notifications.

## Solution

A heartbeat is a special type of scheduled run where the agent:

1. Wakes on a cron schedule
2. Checks a list of items using its tools
3. Responds with `HEARTBEAT_OK` if nothing needs attention (notification suppressed)
4. Reports only actionable findings (notification sent)

## How It Works

### Data Model

No new tables. Heartbeats use the existing `agent_schedules` table with specific keys in the `config` JSONB column:

```json
{
  "schedule_type": "heartbeat",
  "heartbeat_checklist": [
    "Check for new emails in the last 12 hours and summarize any needing attention",
    "Check if any pending approval actions are still waiting"
  ]
}
```

- `schedule_type: "heartbeat"` — triggers heartbeat behavior instead of regular scheduled run
- `heartbeat_checklist` — list of plain-English items the agent should check. Optional — if omitted, the agent gets the raw prompt only.

### Execution Flow

```
BackgroundTaskService (every 60s)
  → finds due agent_schedules row
  → calls ScheduledExecutionService.execute(schedule)

ScheduledExecutionService.execute():
  1. Reads schedule_type from config
  2. Sets channel = "heartbeat" (not "scheduled")
  3. Loads agent with channel="heartbeat"
     → prompt_builder injects heartbeat channel guidance:
        "This is an automated heartbeat check. No one is waiting for a response.
         Check each item on your checklist using tools. If nothing needs attention,
         respond with exactly: HEARTBEAT_OK. Otherwise, report only what needs action."
  4. Builds effective prompt:
     - If heartbeat_checklist exists → appends formatted checklist to prompt
     - If no checklist → uses original prompt as-is
  5. Invokes agent
  6. Reads output:
     - Starts with "HEARTBEAT_OK" → store result with status="heartbeat_ok", skip notification
     - Anything else → store with status="success", send notification normally
```

### What the Agent Sees

When a heartbeat fires with a checklist, the agent receives a prompt like:

```
Check on my daily items

## Heartbeat Checklist
Check each item below using your tools:
- Check for new emails in the last 12 hours and summarize any needing attention
- Check if any pending approval actions are still waiting

If nothing needs attention, respond with exactly: HEARTBEAT_OK
Otherwise, report only what needs action.
```

The system prompt's channel section also tells the agent it's a heartbeat (no one is waiting, use tools to check, be silent if nothing to report).

### What Gets Stored

Every heartbeat execution creates a row in `agent_execution_results`, regardless of outcome:

| Scenario | `status` | `result_content` | Notification |
|----------|----------|-------------------|--------------|
| Nothing to report | `heartbeat_ok` | `"HEARTBEAT_OK"` | Suppressed |
| Something found | `success` | Agent's report | Sent |
| Agent error | `error` | Error message | None (error path) |

This means you can audit heartbeat history — how often it fires, how often it finds something, what it found.

## Heartbeat vs Scheduled

| Aspect | Scheduled | Heartbeat |
|--------|-----------|-----------|
| `config.schedule_type` | `"scheduled"` (or absent) | `"heartbeat"` |
| Channel passed to agent | `"scheduled"` | `"heartbeat"` |
| Prompt modification | None | Checklist appended if provided |
| System prompt guidance | "Be thorough, don't ask follow-up questions" | "Check items, respond HEARTBEAT_OK if nothing" |
| Notification | Always | Only when actionable |
| Result status | `"success"` or `"error"` | `"heartbeat_ok"`, `"success"`, or `"error"` |

## Creating a Heartbeat Schedule

Insert directly into `agent_schedules` (no migration needed):

```sql
INSERT INTO agent_schedules (user_id, agent_name, prompt, cron_expression, config, is_active)
VALUES (
  'user-uuid',
  'assistant',
  'Morning check-in',
  '0 8 * * *',  -- 8 AM daily
  '{
    "schedule_type": "heartbeat",
    "heartbeat_checklist": [
      "Check for new emails in the last 12 hours and summarize any needing attention",
      "Check if any pending approval actions are still waiting",
      "Check if any reminders are due today"
    ]
  }'::jsonb,
  true
);
```

## Key Files

| File | What it does |
|------|-------------|
| `chatServer/services/scheduled_execution_service.py` | `_build_heartbeat_prompt()`, HEARTBEAT_OK detection, notification suppression |
| `chatServer/services/prompt_builder.py` | `"heartbeat"` channel guidance in `CHANNEL_GUIDANCE` |
| `agent_schedules` table | `config` JSONB holds `schedule_type` and `heartbeat_checklist` |
