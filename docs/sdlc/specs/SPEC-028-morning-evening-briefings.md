# SPEC-028: Morning & Evening Briefings

> **Status:** Placeholder
> **Author:** Tim + Claude (Product)
> **Created:** 2026-02-24
> **PRD:** PRD-002 (Expand the World), Workstream 2

## Goal

Replace scattered notifications (heartbeat findings, email digests, reminders) with a single consolidated daily briefing. Morning: "Here's your day." Evening (optional): "Here's what happened and what's still open." The flagship feature of Phase 2 — demonstrates Clarity's judgment by choosing what's worth mentioning.

## Dependencies

- **SPEC-025** (Unified Notification Experience) — briefings deliver as `notify` type inline notifications
- **SPEC-026** (Universal Job Queue) — briefing generation runs as a job type
- **SPEC-027** (Google Calendar Integration) — calendar events are a primary briefing input

## Key Design Points (from PRD-002)

- **Morning briefing:** Consolidates calendar (today's events, conflicts), tasks (due/overdue, focus suggestions), email (time-sensitive items since last session), proactive observations (patterns). Concise, scannable, opinionated — agent picks 3-5 most important things.
- **Evening briefing:** Optional, off by default. Today's progress, loose ends, tomorrow preview.
- **Replaces heartbeat pattern:** Non-urgent heartbeat findings saved for next briefing instead of scattered throughout the day. Urgent items still surface immediately.
- **Delivery:** Via chat stream (web) and Telegram (if linked). Uses SPEC-025 notification types.
- **Scheduling:** User preference for briefing time. Store as IANA timezone string. Configurable via conversation, not settings UI.
- **Cost estimate:** ~5K tokens input, ~500 output. ~$0.003/briefing at Haiku rates.

## What Needs Drafting

- `BriefingService` design — how it composes signals from calendar, tasks, email, and memory
- Background task scheduling — how briefing generation is triggered at the right time per user
- User preference storage — memory vs. dedicated DB column for briefing time/channels
- Briefing template prompt — the system prompt that guides LLM synthesis
- How heartbeat findings get deferred to briefing vs. surfaced immediately

## Rough Scope

| Area | Estimated Changes |
|------|-------------------|
| Backend | New `BriefingService`, background task scheduling, briefing prompt |
| Database | User briefing preferences (time, channels, enabled/disabled) |
| Prompt | Briefing generation prompt template |
| Frontend | None (briefings render as inline notifications via SPEC-025) |

## Open Questions

- Should the user be able to customize briefing sections via conversation? ("Skip email in my morning briefing")
- How to handle timezone changes (user travels)?
- How does the agent decide what's "urgent enough" to surface immediately vs. defer to briefing?

---

*This is a placeholder. Full spec will be drafted when SPEC-025 and SPEC-027 are closer to completion.*
