---
name: evening-briefing
description: Compose personalized daily evening briefing — what got done, what's still open, tomorrow's look-ahead
version: 1
default_gate_policy: none
---

# Evening Briefing

Scheduled workflow that reviews the day's progress and previews tomorrow.

## Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| timezone | yes | User's IANA timezone (e.g., America/New_York) |
| briefing_sections | no | Which sections to include (default: all enabled) |

## Steps

### step-1: Gather Context
- **agent:** context-gatherer
- **depends_on:** []
- **tools:** [search_calendar, get_tasks, search_gmail, search_memories]
- **description:** Fetch tasks completed today, tasks still open with due dates, pending email replies, and tomorrow's calendar events. Output structured context per section.
- **gate:** none

### step-2: Compose Briefing
- **agent:** briefing-composer
- **depends_on:** [gather-context]
- **tools:** []
- **description:** Synthesize gathered context into a 300-word evening briefing. Acknowledge what got done, flag what's still open, preview tomorrow. Use opinionated framing.
- **gate:** none

### step-3: Deliver
- **agent:** briefing-deliverer
- **depends_on:** [compose-briefing]
- **tools:** []
- **node_type:** service
- **description:** Send briefing via NotificationService. Post-process for Telegram. Mark deferred observations as consumed.
- **gate:** none
