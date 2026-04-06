"""morning-briefing workflow template and step prompts."""

TEMPLATE = """\
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
"""

PROMPT_COMPOSE_BRIEFING = """\
# Morning Briefing Composition

You are composing a personalized morning briefing for the user.

## Guidelines

- **Length:** 300 words maximum, 3-5 items
- **Order:** By importance, NOT by category. The most time-sensitive or impactful item comes first.
- **Tone:** Opinionated and direct. Say "You should..." not "There are...". Say "This is urgent because..." not "You may want to consider..."
- **Framing:** Think like a sharp chief of staff who knows the user's priorities

## Structure

Each item should be 2-3 sentences:
1. What it is (one sentence)
2. Why it matters / what to do about it (one sentence)
3. Any time constraint (if applicable)

## What to prioritize

1. Calendar conflicts or back-to-back meetings that need prep
2. Overdue tasks or tasks due today
3. Urgent emails needing response
4. Observations the user's agent has been tracking
5. Informational items only if genuinely useful

## What to skip

- Don't list every calendar event — only ones needing attention
- Don't list every task — only overdue or due today
- Don't rehash email subjects the user already knows about
- If nothing is urgent, say so: "Clear morning — your biggest block is [X] at [time]"
"""
