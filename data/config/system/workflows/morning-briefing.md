---
name: morning-briefing
description: Compose personalized daily morning briefing from calendar, tasks, email, and observations
version: 1
default_gate_policy: none
---

# Morning Briefing

Scheduled workflow that gathers context from multiple sources and composes
an opinionated daily briefing.

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
- **description:** Fetch today's calendar events, active/overdue tasks with due dates, recent unread emails (last 12 hours), and unconsumed deferred observations. Output structured context per section.
- **gate:** none

### step-2: Compose Briefing
- **agent:** briefing-composer
- **depends_on:** [gather-context]
- **tools:** []
- **description:** Synthesize gathered context into a 300-word morning briefing. Pick 3-5 most important items. Order by importance, not category. Use opinionated framing. Include user's standing instructions for tone.
- **gate:** none

### step-3: Deliver
- **agent:** briefing-deliverer
- **depends_on:** [compose-briefing]
- **tools:** []
- **node_type:** service
- **description:** Send briefing via NotificationService. Post-process for Telegram. Mark deferred observations as consumed.
- **gate:** none
