---
name: regenerate-today
description: Rebuild today.md from calendar, inbox signals, approvals, and recent vault activity. Produces a seven-section body (Header, Your day, To do, Notes, Agent, Approvals, Recent) and writes it to the vault at today.md.
version: 1
default_gate_policy: none
---

# Regenerate Today

Scheduled or on-demand workflow that refreshes the user's `today.md` landing
page. The gather step pulls ambient context (calendar events, recent mail,
recent vault activity). The composer step rewrites `today.md` in place via
the agent's sandboxed `write_file` tool. Stage 1: prompt is intentionally
minimal — iterate the composer prose in a follow-up PR against the kill
criterion ("does Today replace the inbox").

## Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| date | no | Target date in user-local tz (default: today) |

## Steps

### step-1: Gather context
- **agent:** today-gather
- **depends_on:** []
- **tools:** [search_gmail, list_calendar_events]
- **description:** Collect today's calendar events, last-24h important mail, and recent vault activity. Output structured data for the composer: a list of meetings (title, start, end, attendees, link), a short digest of signal-worthy mail (sender, subject, one-line summary), and up to 5 recently-touched vault paths with mtime.
- **gate:** none

### step-2: Compose Today
- **agent:** today-composer
- **depends_on:** [step-1]
- **tools:** [write_file]
- **description:** Produce a `today.md` body with exactly these seven H2 sections in order — Header, Your day, To do, Notes, Agent, Approvals, Recent. One-line framing sentence under Header. Meetings as bullets under Your day with wikilinks to entity docs when known. Carry forward any existing To do and Notes items that were captured since the last regeneration. Leave Agent and Approvals empty if there is nothing to surface (empty-state prose is fine). Write the result to `today.md` via write_file. Do not add sections beyond the seven listed.
- **gate:** none
