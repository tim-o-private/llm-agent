# PRD-001: Make It Feel Right

> **Status:** Draft v1
> **Author:** Tim + Claude (Product)
> **Created:** 2026-02-24
> **Vision Reference:** `docs/product/VISION.md`

---

## Summary

The infrastructure works. The pieces exist. But the experience of using Clarity doesn't yet feel like having a personal chief of staff — it feels like interacting with a chatbot that has some tools bolted on. This PRD defines Phase 1: making the existing system *feel right* before building new capabilities.

Phase 1 is entirely about perception, personality, and feedback. No new integrations. No new signal sources. The scope is: a user connects their email, the agent learns who they are, processes their signals with judgment, and the user can tell it when it's right and when it's wrong. That loop — and the *feel* of it — is the entire product at this stage.

## Success Criteria

| Metric | Current State | Target |
|--------|--------------|--------|
| New user sees a useful first response | 34s, often empty (token bomb) | <3s, always a warm greeting + one question |
| User can tell if the agent "gets them" after 1 week | No structured model visible to agent | Agent references user's life context naturally in conversation |
| User can give feedback on notifications | No mechanism | Thumbs up/down on every proactive surfacing |
| Agent personality feels like a person | Reads like a checklist of instructions | Feels like a capable, opinionated assistant with warmth |
| Returning user session_open feels aware | Burns LLM turns on tool calls | Instant greeting from pre-computed context |

## What This PRD Covers

Four workstreams, roughly in priority order:

### 1. Onboarding Redesign
### 2. Agent Personality & Soul Rewrite
### 3. Notification Feedback Loop
### 4. Structured Mental Model

---

## Workstream 1: Onboarding Redesign

### Problem

The current onboarding does two things wrong:
1. **New users:** Agent tries to call tools (get_tasks, search_gmail, etc.) on a brand new account — finds nothing or burns 120K tokens on raw email bodies. User sees nothing for 34 seconds or gets a data dump.
2. **Philosophical:** "SHOW usefulness, not ASK about it" sounds right but produces the wrong behavior. Usefulness on day 0 isn't "you have 47 unread emails." It's "I'm here, I'm paying attention, and I already have a sense of what to focus on."

### Design

**Decision: Email connection is not mandatory.** The agent must be useful before any integration is connected. Email is the most obvious first integration and the agent should suggest it, but the onboarding conversation needs to stand on its own.

**The "what is this" problem:** Nobody has encountered a system like this before. The agent needs to frame itself without delivering a product tour. The user needs enough context to understand what's possible, but the framing should feel like meeting someone, not reading a brochure.

**New user first interaction:**

The agent's job is to start a relationship — introduce what it is, learn about the user, and suggest a first connection. Four beats:

1. **Frame what this is** — brief, concrete, not a feature list. "I'm here to help you get your time back. I can manage your email, keep track of what you need to do, and handle the stuff you don't have time to think about. The more I learn about you, the more I can take off your plate."

2. **Ask one good question** — open-ended, not interrogative. "What's eating your time right now?" This gives the agent a starting mental model and tells it where to focus.

3. **Have a real conversation** — respond to what they say. If they mention email overwhelm, explore that. If they mention a home project, ask about it. The agent is learning and recording to memory the whole time. This isn't a script — it's a conversation.

4. **Suggest a first connection when natural** — "Want to connect your email? I can start learning what matters to you." Not mandatory. If the user just wants to chat or create some tasks first, that's fine. The agent should be useful regardless.

Under 5 seconds to first response. No tool calls on bootstrap. The agent records everything the user says to memory.

**What happens when email IS connected (whenever that is):**

This is where the magic happens. On email connect, a background job kicks off immediately:

- **Scope:** Last 7 days of email (inbox + sent)
- **Processing time target:** <5 minutes
- **What it extracts:**
  - Key relationships (from both received and sent mail — who does this person communicate with, how often, what about)
  - Communication style profile (from sent messages — how does this user write? Formal/casual, terse/detailed, tone patterns. The agent should sound like the user when drafting on their behalf.)
  - Recurring threads and patterns (newsletters, project threads, automated notifications)
  - Open action items (emails that look like they need replies, deadlines mentioned, commitments made)
  - Inferred interests and life context (school emails → has kids, contractor emails → home project, etc.)
- **Storage:** Structured memory entries with appropriate types (core_identity, project_context, episodic) and entity links

**The chit-chat-while-processing pattern:**

While the background job runs, the agent keeps the conversation going. "Tell me more about what's going on — I'm reading through your email in the background." This serves two purposes: the user teaches the agent context that enriches the email analysis, and the wait doesn't feel like waiting.

**The reveal moment:**

When processing completes (ideally while still in the same conversation, or at next session_open if the user left), the agent presents what it found — and validates assumptions:

"Okay, I've been through your recent email. Here's what I'm seeing:
- You're communicating a lot with [contractor name] about what looks like a kitchen renovation
- [School name] sends you a lot — looks like you have kids there?
- You've got about [N] emails that look like they need replies
- And honestly, about [M] subscriptions you might not need anymore

Does that sound right? Am I missing anything important?"

**This is the trust-building moment.** The agent demonstrates judgment (not just data) and invites correction. Every correction is gold — it's the user explicitly calibrating the model. Note: we should assume nobody connects a work email day 1. The initial processing should be calibrated for personal email.

**No-email path:**

For users who don't connect email right away, the agent is still useful:
- Task management with executive function (break down goals, suggest next steps)
- Reminders and scheduling
- General conversation and planning
- The agent continues to suggest email connection at natural moments: "You mentioned you're losing track of contractor emails — want me to connect to your Gmail and keep an eye on those?"

**Returning user session_open:**

SPEC-021 already covers this well: pre-computed context (task counts, reminder counts, unread email counts) injected into the prompt. The agent reads the summary, doesn't call tools. Quick, aware, respectful.

### What changes

| Change | SPEC Coverage |
|--------|--------------|
| Rewrite `SESSION_OPEN_BOOTSTRAP_GUIDANCE` — conversation, not data dump | SPEC-021 AC-08 |
| Rewrite `ONBOARDING_SECTION` to match | SPEC-021 AC-11 |
| Remove tool-call instructions from bootstrap | SPEC-021 AC-08, AC-10 |
| Pre-computed context for returning users | SPEC-021 AC-12, AC-13 |
| Gmail search truncation (data diet) | SPEC-021 AC-01, AC-02, AC-03 |
| **NEW:** Background email processing on Gmail connect | New spec needed |
| **NEW:** Email-to-memory pipeline (categorize, summarize, store) | New spec needed |
| **NEW:** Sent message analysis for writing style profile | Part of email pipeline spec |
| **NEW:** No-email onboarding path (task-first) | Prompt changes in SPEC-021 |
| **DECISION:** Deprecate `/coach` page — Today + chat panel is the UX | Frontend cleanup |
| **DECISION:** New users land on Today with chat auto-opened | Already wired (session init sets `isChatPanelOpen: true`) |

### Open Questions

- **How much email history to process on connect?** 7 days proposed. Should we go deeper for users with low volume? Could adaptively expand if <50 emails found.
- **Model for email processing?** The background job needs to call an LLM to categorize and extract insights. Use a cheaper/faster model (Haiku) for bulk processing, reserve Sonnet/Opus for the synthesis step?
- **How to handle the reveal if the user has left?** If they disconnected before processing finished, deliver via notification + next session_open? Or proactive Telegram message if linked?

---

## Workstream 2: Agent Personality & Soul Rewrite

### Problem

The current soul text is fine as operational instructions:

> *"You manage things so the user doesn't have to hold it all in their head. Be direct and practical. Skip pleasantries when the user is clearly in work mode..."*

But it doesn't create a *person*. It creates a compliant tool. The agent needs character — not personality for its own sake, but because trust is built with *someone*, not *something*. People trust their executive assistant because they know how that person thinks, what they'll prioritize, and when they'll push back.

### Design

The soul rewrite needs to address four dimensions:

**1. Character, not just behavior**

Current: "Be direct and practical."
Better: The agent has a point of view. It thinks some things are more important than others. It'll tell you "honestly, that can wait — this other thing is what I'd focus on today." It's not sycophantic, not robotic. It's the kind of person you'd actually hire.

**2. Executive function as an alignment exercise**

Current: "When the user mentions something they need to do — create a task."
Better: The agent thinks about *what the user should be doing*, not just what they said. It breaks down vague goals, identifies what needs the user vs. what the agent can handle, and nudges toward follow-through without nagging.

But early on, this is fundamentally an *alignment exercise*, not an autonomy exercise. The agent is learning what the user values, how they prioritize, what level of proactivity feels helpful vs. presumptuous. The tone matters enormously here — "Here's what I'd focus on today, but you know your situation better than I do" is very different from "You should do X." Respect the user's comfort level. Build toward autonomy gradually as the agent proves its judgment.

**3. Warmth without performance**

The agent should be warm but never performative. No "Great question!" No "I'd be happy to help!" No emoji storms. But also not cold. It should feel like someone who genuinely gives a shit about your day going well.

**4. Calibrated proactivity**

The agent should know when to speak up and when to stay quiet. It should never create more work than it saves. If it surfaces something, it should be because it genuinely matters, not because it wants to demonstrate that it's paying attention.

### What changes

| Change | Scope |
|--------|-------|
| Rewrite `soul` text in `agent_configurations` | DB update, no code change |
| Rewrite `OPERATING_MODEL` constant | `prompt_builder.py` |
| Rewrite `INTERACTION_LEARNING_GUIDANCE` constant | `prompt_builder.py` |
| Update `identity` JSON for assistant agent | DB update |
| Consider whether soul/operating model should vary by channel | Design decision |

### Draft Soul Direction

This is a starting point for iteration, not final copy:

> You're the user's chief of staff. Your job is to manage the things they don't have time to think about — and to think about the things they haven't gotten to yet.
>
> You have opinions about priorities. "Everything is important" is never useful. When you see what's on someone's plate, tell them what you'd focus on first and why. If they disagree, that's fine — you'll learn.
>
> Don't narrate what you're doing. Don't explain your tool calls. Don't perform helpfulness. Just be helpful. If you scanned their email and found something important, lead with the finding, not with "I scanned your email and..."
>
> You are warm but not performative. You care about this person's day going well. You remember what they told you. You notice when they're stressed and adjust. But you never say "Great question!" or use filler.
>
> Think about what the user *should* be doing, not just what they asked about. If they mention a vague goal, break it down. If something in their email implies a deadline they haven't tracked, flag it. If you can handle something yourself, do it (within your trust level) — and tell them after.
>
> When you learn something about the user — a preference, a pattern, a relationship — record it. Don't ask permission. You should know more about them every week. If they correct you, update immediately and thank them for it.
>
> Respect their time. One good insight is better than five mediocre ones. Silence is a valid choice. Never create more work than you save.

### Validation

The soul rewrite should be testable via the clarity-dev MCP tool. Send test messages and evaluate:
- Does the agent sound like a person, not a system?
- Does it offer opinions or just comply?
- Does it proactively do the executive function work (break down tasks, prioritize, flag conflicts)?
- Does it stay warm without being performative?

---

## Workstream 3: Notification Feedback Loop

### Problem

The agent sends notifications (heartbeat findings, proactive nudges, reminders). The user can read them or dismiss them. There's no way to tell the agent "this was useful" or "stop bothering me with this." Without feedback, the agent can't calibrate its judgment. With feedback, it can.

### Design

**Minimal viable feedback:**

Every proactive notification gets two buttons: **Useful** / **Not useful**.

That's it. Not a 5-star rating. Not a text field. Two buttons.

**What happens with feedback:**

- **Useful:** Agent records a memory: `"User found [notification type/topic] useful. Continue surfacing similar signals."` Memory type: `core_identity`, tagged with signal domain.
- **Not useful:** Agent records: `"User found [notification type/topic] not useful. Reduce priority of similar signals."` Same memory structure.
- **No feedback (dismissed without clicking either):** No signal recorded. Absence of feedback is not negative feedback.

**Where feedback appears:**

- Web notification dropdown: thumbs up / thumbs down icons on each notification
- Telegram: inline keyboard buttons on proactive messages (already have the pattern from approval buttons)
- Future: any surface where the agent proactively reaches the user

**How the agent uses feedback:**

- Memory search at judgment time: before deciding whether to surface something, the agent can recall what the user has found useful/not useful in the past
- This is deliberately low-tech. No ML pipeline, no recommendation engine. The agent's own judgment + memory is the personalization engine. If the user says "not useful" to three school newsletter notifications in a row, the agent will learn to deprioritize them.

### What changes

| Change | Scope |
|--------|-------|
| Add `useful` / `not_useful` action to notification model | Backend: notification model, router |
| Store feedback as memory entry via memory client | Backend: notification service |
| Add feedback buttons to web notification UI | Frontend: NotificationItem component |
| Add feedback inline keyboard to Telegram notifications | Backend: telegram service |
| Agent prompt guidance: check feedback memories before surfacing | `prompt_builder.py` or tool `prompt_section()` |

### What this enables

This is the seed of the personalization flywheel from the vision doc. It's deliberately simple so it can ship fast. Later iterations can:
- Track implicit feedback (opened vs. dismissed without reading)
- Weight feedback by recency
- Surface feedback stats to the user ("I've gotten better at knowing what you care about — you've found 80% of my last 20 notifications useful")

---

## Workstream 4: Structured Mental Model

### Problem

The memory system stores facts: "User has two kids." "User is renovating their kitchen." "User prefers concise responses." But there's no structure to this. The agent can't easily answer "what are all the life domains I know about for this user?" or "who are the key people in their life?" It's a bag of facts, not a model.

### Design

This is about how the agent *organizes what it learns*, not about new data sources. The structured mental model is a set of memory conventions the agent follows when recording observations.

**Life Domains:**

The agent organizes observations into domains, discovered through interaction:

- `work` — projects, stakeholders, meetings, deadlines
- `family` — kids, partner, family events, school
- `home` — maintenance, contractors, house projects
- `health` — appointments, habits, medical
- `finances` — bills, subscriptions, budgeting
- `interests` — hobbies, communities, personal projects

These aren't configured by the user. The agent creates domain entities in memory as it discovers them. A user who never mentions health doesn't get a health domain.

**Key Entities:**

For each domain, the agent tracks key entities as min-memory entities:

- **People:** name, relationship to user, communication frequency, typical urgency
- **Organizations:** name, domain, user's relationship (employer, school, service provider)
- **Projects:** name, domain, status, key deadlines, collaborators
- **Recurring events:** name, frequency, domain, next occurrence

**Priority Model:**

The agent tracks what the user cares about — not through explicit ranking, but through observed behavior and explicit feedback:

- Notification feedback (from Workstream 3)
- Response latency patterns (reacted quickly → high priority)
- Explicit statements ("this is really important" / "I don't care about this")
- Behavioral inference ("user always handles contractor emails within an hour")

### What changes

| Change | Scope |
|--------|-------|
| Define memory conventions for domain/entity/priority recording | Prompt engineering: soul, operating model, tool guidance |
| Update `create_memories` prompt_section to guide structured recording | `memory_tools.py` |
| Create seed entities on onboarding (from email processing) | Background email pipeline (Workstream 1) |
| Agent can query by domain: "what do I know about this user's work?" | Already possible via memory search + entity system |

### What this is NOT

- Not a new database schema. The min-memory system already supports entities, relationships, scoping, and tagging. This is about giving the agent conventions for *using* what already exists.
- Not user-visible (yet). The mental model is internal to the agent. Future work could expose a "what does my agent know about me?" view for transparency.
- Not a rigid ontology. The agent can create new domains and entity types as needed. The conventions are guidelines, not constraints.

---

## Dependencies & Sequencing

```
Workstream 1 (Onboarding)     Workstream 2 (Personality)
         │                              │
         │    SPEC-021 (in draft)        │   Mostly prompt/DB changes
         │    + new email pipeline spec  │   Can ship independently
         ▼                              ▼
         ├──────────────────────────────┤
         │   These two should ship      │
         │   together — personality     │
         │   informs onboarding tone    │
         └──────────┬───────────────────┘
                    │
                    ▼
         Workstream 3 (Feedback)
         │   Needs notifications working well first
         │   + personality to inform what gets surfaced
         ▼
         Workstream 4 (Mental Model)
         │   Needs onboarding pipeline (to seed initial model)
         │   + personality (to guide how agent records)
         ▼
         Phase 1 Complete
```

**Recommended approach:**
1. Ship Workstreams 1+2 together as SPEC-021 (expanded) + a personality spec
2. Ship Workstream 3 as its own spec
3. Ship Workstream 4 as prompt engineering + conventions (may not need a full spec)

## SPECs Needed

| SPEC | Covers | Status |
|------|--------|--------|
| SPEC-021 (expand) | Onboarding redesign, bootstrap rewrite, Gmail hardening, error resilience | Draft exists, needs onboarding conversation design added |
| SPEC-022 (new) | Agent personality & soul rewrite | Needs drafting |
| SPEC-023 (new) | Background email processing pipeline (on Gmail connect) | Needs drafting |
| SPEC-024 (new) | Notification feedback loop | Needs drafting |
| SPEC-025 (new) | Mental model conventions & prompt guidance | May be prompt-only, no code spec needed |

## Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Soul rewrite changes agent behavior in unexpected ways | Users accustomed to current behavior may notice | Test extensively via clarity-dev MCP before deploying; ship as DB update (instant rollback) |
| Background email pipeline is expensive (LLM processing 7 days of email) | High inference cost per new user | Process emails in batches; use cheaper model for categorization; set token budget per user |
| Notification feedback creates noisy memories | Agent's memory fills with "user liked X / didn't like Y" | Structured tagging + periodic background pruning (Phase 3 scope) |
| Onboarding conversation feels too slow for power users | Users who know what they want may be impatient | Agent should read the room — if user immediately says "just connect my email," skip the warmth and do it |
| Structured mental model is too rigid | Real lives don't fit in neat categories | Domains are suggestions, not constraints; agent can create new ones freely |

---

*This PRD defines the work. Individual SPECs will define implementation details, acceptance criteria, and test plans.*
