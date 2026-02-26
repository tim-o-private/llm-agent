# PRD-002: Expand the World

> **Status:** Draft v1
> **Author:** Tim + Claude (Product)
> **Created:** 2026-02-24
> **Vision Reference:** `docs/product/VISION.md`
> **Depends On:** PRD-001 (Make It Feel Right)

---

## Summary

Phase 1 made the agent feel like a person. Phase 2 gives it more of the user's world to work with.

Today Clarity sees email and whatever the user tells it in conversation. That's enough to demonstrate judgment, but it's not enough to be a chief of staff. A chief of staff knows your calendar, reads the room across channels, and handles things before you realize they need handling. Phase 2 adds the signal sources and capabilities that make this real — without losing the trust model that makes Clarity different from OpenClaw and its "god mode" imitators.

The constraint: every new capability must fit through the trust tier system (Inform → Recommend → Act). Nothing runs unsupervised until it's earned that right.

## Context: What We Learned from OpenClaw

OpenClaw proved the demand. 68K GitHub stars, viral adoption, "JARVIS" comparisons. But it also proved what breaks:

- **Setup is brutal.** Docker, CLI, API keys, port conflicts. Average user bounces.
- **Trust is absent.** Agents delete emails, buy cars, leak API keys. Users say "the thought of it running with my Apple ID was terrifying."
- **Cost is invisible.** Heartbeat loops burn $100+ in API credits with no transparency.
- **Reliability is low.** "It worked last night, now none of my prompts go through."
- **Security is a disaster.** 20% of the ClawHub skill marketplace is malicious. Prompt injection in 36% of skills.

OpenClaw optimized for **capability** — 50+ integrations, shell access, full autonomy. Users want that power but can't trust it. The market is converging on **trust, not features.** Lindy proved people will pay $50/mo for an agent that "just works." Our job is to prove that good judgment beats good hands.

**The need behind the asks:**

| What people say | What they actually need |
|----------------|----------------------|
| "50+ integrations" | Agent that understands their life across a few key channels |
| "Run any shell command" | Safe execution of specific actions with oversight |
| "Local-first, no cloud" | Data privacy and control over what the agent can access |
| "Overnight autonomous work" | Trust that the agent does the right thing unsupervised |
| "Email triage every morning" | Agent that knows what matters and surfaces only that |
| "Calendar + tasks" | Executive function — what to do, when, and why |

## Success Criteria

| Metric | Phase 1 State | Phase 2 Target |
|--------|--------------|----------------|
| Signal sources the agent can draw from | Email + conversation | Email + calendar + web + conversation |
| User receives useful daily briefing | No (scattered notifications) | Yes (single consolidated morning briefing) |
| Agent can propose an action on behalf of the user | Queued in a dead-end panel | Inline approval in chat, result visible |
| User can correct the agent's model of their life | Via conversation only | Conversation + feedback + explicit editing |
| Power users can interact via terminal | No | Claude Code MCP integration |

## What This PRD Covers

Four workstreams:

### 1. Calendar Integration
### 2. Morning & Evening Briefings
### 3. Web Search
### 4. Draft-Reply Workflow

*Note: Claude Code integration was originally scoped here but has been promoted to its own PRD (PRD-003) as the vision expanded from "Claude Code as a client for Clarity" to "Clarity as an orchestration layer over Claude Code." See `docs/product/PRD-003-orchestration-layer.md`.*

---

## Workstream 1: Calendar Integration

### Problem

The agent knows your email but not your schedule. It can't say "you have a call with Mike in 30 minutes — here's context from your recent emails with him." It can't warn you about double-bookings, remind you to prep for meetings, or understand why your afternoon is blocked. Calendar is the single highest-value signal source we can add.

### Design

**Read-only to start.** The agent connects to Google Calendar (same OAuth flow as Gmail, additional scope) and can:

- See today's events and upcoming schedule
- Understand free/busy times
- Cross-reference calendar events with email threads (same people, same topics)
- Include calendar context in daily briefings and session_open summaries

**Not yet:** Creating events, modifying events, or managing RSVPs. Those are Act-tier capabilities that require trust graduation. Read access is Inform-tier — the agent sees your calendar and tells you what it notices.

### What changes

| Change | Scope |
|--------|-------|
| Add Google Calendar read scope to OAuth flow | Backend: external_api_router |
| New `search_calendar_events` tool | Backend: new tool class + service |
| New `get_calendar_event` tool | Backend: new tool class + service |
| Calendar context in session_open bootstrap | Prompt builder: add today's events to pre-computed context |
| Calendar cross-reference in email processing | Email onboarding service: match calendar attendees to email contacts |

### Trust tier

**Inform** — the agent reads your calendar and references it in conversation. No modifications. Graduation to Recommend (suggesting scheduling changes) requires demonstrated judgment over time.

### Open Questions

- **Multiple calendars?** Users often have personal + work calendars in one Google account. Process all by default, let user exclude?
- **Recurring events?** How much context to give the agent about patterns (weekly team standup, biweekly 1:1)?
- **Calendar from non-Google?** Outlook/iCal support is future scope, but the service layer should be provider-agnostic.

---

## Workstream 2: Morning & Evening Briefings

### Problem

The agent sends scattered notifications: a heartbeat finding here, an email digest there, a reminder somewhere else. The user gets 4 pings across 2 channels with no coherence. What they want is one message in the morning: "Here's your day." And optionally one in the evening: "Here's what happened today and what's still open."

This is the #1 use case in every OpenClaw list. It's also the use case that best demonstrates Clarity's judgment — the agent has to decide what's worth mentioning and what to leave out.

### Design

**Morning briefing (daily, configurable time):**

A single `notify` notification that consolidates:

1. **Calendar:** Today's events, any conflicts or tight transitions
2. **Tasks:** What's due today, what's overdue, what the agent suggests focusing on
3. **Email:** Anything that arrived since last session that looks time-sensitive or important
4. **Proactive observations:** Patterns the agent has noticed ("you haven't replied to [person] in 3 days — they usually hear back faster")

Format: concise, scannable, opinionated. Not a data dump. The agent picks the 3-5 most important things and says why. Everything else is available if the user asks.

**Evening briefing (optional, off by default):**

1. **Today's progress:** Tasks completed, emails handled
2. **Loose ends:** Things that didn't get done, replies still pending
3. **Tomorrow preview:** What's on deck

**Delivery:** Via chat stream (web) and Telegram (if linked). Uses the notification type system from SPEC-025 — morning briefing is `notify` type.

### What changes

| Change | Scope |
|--------|-------|
| New `BriefingService` that composes signals | Backend: new service |
| Briefing generation scheduled in background tasks | Backend: background_tasks.py |
| User preference for briefing time + channels | DB: user preferences table or memory |
| Briefing template prompt for the LLM | Prompt engineering |
| Calendar integration feeds into briefing | Depends on Workstream 1 |

### What this replaces

The heartbeat notification pattern (SPEC-006) gets absorbed into the morning briefing. Instead of scattered findings throughout the day, the agent saves non-urgent observations for the next briefing. Urgent items still surface immediately via `notify`.

### Open Questions

- **Briefing customization:** Should the user be able to say "I don't care about email in the morning, just calendar and tasks"? Probably yes, but via conversation ("Hey, skip the email stuff in my morning briefing"), not a settings UI.
- **Cost per briefing:** Each briefing requires an LLM call to synthesize. Estimate ~5K tokens input (context), ~500 tokens output. At Haiku rates, ~$0.003/briefing. Negligible.
- **Timezone handling:** Briefing time must respect user timezone. Store as UTC offset or IANA timezone string.

---

## Workstream 3: Web Search

### Problem

The agent can't look things up. If a user asks "what's the weather this weekend" or "find me a plumber near [city]" or "what happened with [news event]," the agent has to say "I can't do that." This is table stakes for a general-purpose assistant and a frequent frustration in the OpenClaw community when models hallucinate instead of searching.

### Design

SPEC-016 (Web Search Tool) is already drafted. The tool:

- Takes a search query + optional constraints
- Returns summarized results via a search API (Tavily, SerpAPI, or similar)
- Agent decides when to search vs. when it already knows
- Results are ephemeral (not stored in memory unless the user asks to remember something)

**Trust tier:** Auto-approve. Searching the web is read-only and low-risk. No approval needed.

### What changes

| Change | Scope |
|--------|-------|
| Implement SPEC-016 | Backend: new tool class + service |
| Search API integration (Tavily recommended) | Backend: new external service |
| API key management | Config: new env var |
| Cost monitoring | Tavily: ~$0.005/search, budget ~$1/user/month |

### Risks

- **Cost at scale:** If the agent decides to search on every turn, costs add up. Rate limit to N searches per session (configurable).
- **Result quality:** Search APIs return varied quality. Agent must evaluate results, not just parrot them.
- **Privacy:** Search queries could reveal sensitive information. Don't log query content, only metadata.

---

## Workstream 4: Draft-Reply Workflow

### Problem

The agent can read email but can't help you respond. "Draft a reply to Mike about the renovation timeline" should produce a draft the user reviews and sends. This is the first **Act-tier** capability — the agent does something on the user's behalf, with approval.

This is also where the writing style profile (from SPEC-023's sent message analysis) pays off. The agent doesn't draft in its own voice — it drafts in the user's voice.

### Design

**Flow:**

1. User says "reply to Mike's last email about the timeline"
2. Agent finds the email, drafts a reply using the user's writing style profile
3. Draft is presented as a `notify` notification with `requires_approval = true`
4. User reviews inline in chat, can edit or approve
5. On approval, agent sends via Gmail compose API

**Trust tier:** This starts at **Recommend** — the agent proposes the draft, user approves every time. Graduation to Act (agent sends without asking) requires N successful send-and-no-correction cycles. The agent proposes graduation: "I've drafted 10 replies for you and you've approved all of them without changes. Want me to start sending these automatically?"

**Writing style application:**

The SPEC-023 email onboarding pipeline extracts a writing style profile (tone, length, greeting/signoff patterns, formality level). The draft tool uses this profile in its system prompt:

```
Draft a reply in the user's voice. Their style:
- Casual tone, uses contractions
- Typical length: 2-4 sentences
- Signs off with first name only
- No formal greetings
```

### What changes

| Change | Scope |
|--------|-------|
| New Gmail compose OAuth scope | Backend: OAuth flow update |
| New `draft_email_reply` tool | Backend: new tool class + service |
| New `send_email_draft` tool (approval-gated) | Backend: new tool, requires_approval=true |
| Writing style profile integration | Backend: memory lookup in draft tool |
| Inline draft review UX | Frontend: new component in chat stream (Markdown preview + edit + approve) |

### Prerequisites

- SPEC-023 (email onboarding) — for writing style profile
- SPEC-025 (unified notifications) — for inline approval flow
- Gmail compose scope — new OAuth consent

### Open Questions

- **Edit before send:** Can the user edit the draft inline, or do they need to open a modal/editor? Inline editing of a Markdown preview is ideal but complex. MVP could be: user says "change the second sentence to X" and agent revises.
- **Thread vs. new message:** Drafting a reply vs. composing a new email are different flows. Start with replies only?
- **Attachments:** Out of scope for MVP. Text-only replies.

---

## Dependencies & Sequencing

```
SPEC-025 (Unified Notifications)     SPEC-023 (Email Pipeline)
         │                                    │
         ▼                                    ▼
Workstream 2 (Briefings)            Workstream 4 (Draft-Reply)
    needs inline notifications         needs writing style profile
    needs calendar (WS1)               needs compose OAuth scope
         │                                    │
         ▼                                    │
Workstream 1 (Calendar)                       │
    new OAuth scope                           │
    new tools                                 │
    feeds into briefings                      │
         │                                    │
         ▼                                    ▼
Workstream 3 (Web Search)           Phase 2 Complete
    independent, can ship anytime        │
                                         ▼
                                    PRD-003 (Orchestration Layer)
                                        Phase 3
```

**Recommended implementation order:**

1. **Calendar Integration** — unblocks briefings, high user value
2. **Web Search** — independent, quick win, SPEC already drafted
3. **Morning Briefings** — the flagship feature of Phase 2, needs calendar
4. **Draft-Reply** — most complex, highest trust requirement, ship last

## SPECs Needed

| SPEC | Covers | Status | Phase |
|------|--------|--------|-------|
| SPEC-025 | Unified notification experience (prerequisite) | Draft complete | 2a |
| SPEC-016 | Web search tool (DDG + Tavily provider abstraction) | Draft complete | 2a |
| SPEC-026 | Universal job queue & scheduler — reusable background job primitives | Draft | 2a |
| SPEC-027 | Google Calendar integration — OAuth, read tools, session context | Draft complete | 2a |
| SPEC-028 | Morning & evening briefings — consolidation service, scheduling | Placeholder (depends on 025 + 026 + 027) | 2b |
| SPEC-029 | Draft-reply workflow — compose OAuth, draft tool, conversational editing | Placeholder (depends on 023 + 025) | 2c |

## Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Calendar scope increases OAuth complexity | Users may hesitate to grant more permissions | Clear explanation of read-only access; separate consent step |
| Briefing quality varies (LLM judgment) | Bad briefings erode trust faster than no briefings | Feedback buttons on briefings; iterate on prompt; cost is low so iterate fast |
| Web search costs at scale | Per-query pricing adds up | Rate limit per session; monitor per-user spend; Tavily is cheap (~$0.005/query) |
| Claude Code orchestration (PRD-003) pulls focus from user-facing features | Phase 2 and 3 compete for bandwidth | Phase 2 ships first; PRD-003 can develop in parallel as research |
| Draft-reply introduces write access to email | Security-critical; wrong email sent is catastrophic | Strict approval tier; user sees exact text before send; no auto-send until proven |
| Feature creep from OpenClaw comparisons | Pressure to add integrations for their own sake | Every integration must pass: "Does this help the agent exercise better judgment?" If not, defer. |

## What This Phase Is NOT

- **Not 50 integrations.** Three new signal sources (calendar, web, email write). Quality over quantity.
- **Not autonomous.** Every new capability starts at Inform or Recommend tier. The agent earns Act.
- **Not a developer tool.** Claude Code orchestration is Phase 3 (PRD-003), not Phase 2.
- **Not a platform.** No skill marketplace, no third-party plugins. OpenClaw proved that's a security disaster. Every capability is built by us, reviewed by us.

---

*This PRD defines the Phase 2 arc. Individual SPECs will define implementation details, acceptance criteria, and test plans.*
