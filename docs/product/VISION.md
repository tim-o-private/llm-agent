# Clarity: Product Vision

> **Status:** Draft v1
> **Author:** Tim + Claude (Product)
> **Created:** 2026-02-24

---

## One-Liner

Clarity is the first agent that works for *you* — not for a platform, not for an advertiser, not for a service provider. It manages your entire information life, learns your priorities, and gives you your time back.

## The Problem

A person has hundreds of accounts across hundreds of services. Every one of those services has people working for *it* — optimizing engagement, maximizing revenue, capturing attention. Your bank's app is designed for the bank. Gmail is designed for Google. Your kid's school portal was built to the school district's IT budget. None of them are working for you.

The result is massive, systemic overwhelm. Not because any single service is hard to manage, but because no one is managing the *whole picture* on the individual's behalf. Important things get missed not because people are careless, but because no human can maintain awareness across that many streams simultaneously. Balls get dropped. Time and energy are wasted navigating systems that were never designed with *your* priorities in mind.

And the burden isn't just *information* — it's *executive function*. Every email, notification, and school form represents a decision and often an action. The cognitive load isn't reading the email. It's figuring out what to do about it, when to do it, whether it matters relative to everything else, and then actually following through. For many people — and especially for the millions with ADHD or executive function challenges — this is precisely the thing that's hardest. The information isn't the problem. The thinking-about-the-information is.

Inference changes this equation fundamentally. For the first time, it's possible to build a single product that sits across all of a person's accounts and manages them — not for the platforms, but for the individual. Not just reading and summarizing, but *thinking, deciding, and doing*. The inference providers themselves haven't built this. They're still thinking about maximizing the value of *their* platform. Nobody has built the thing that just works for people.

### Why existing solutions fail

- **Filters** (rules, labels, smart inboxes) — require setup, break on edge cases, can't exercise judgment, and only work within one service
- **Summaries** (AI digests) — reduce volume but not cognitive load; a summary of 50 unimportant emails is still unimportant
- **Task managers** — create another system to maintain; you still need the executive function to use them
- **Agents** (OpenClaw et al.) — take action without guardrails, creating anxiety instead of relieving it
- **Platforms themselves** — each optimizes for its own engagement metrics, not for the user's time

None of them *think about what matters to you* across everything and act accordingly.

## The Product

Clarity is outsourced executive function. It manages your information, breaks down your goals, tells you what needs you and what it can handle, and nudges you toward the things that matter. Not another app demanding your attention — the thing that means you need fewer apps, fewer checks, less time spent on overhead.

**The core metric: a user's time in the product should go *down* over time.** Not because they've churned, but because the agent is handling more. Week one, you're chatting with it, teaching it, correcting it. Month two, it's running things and you're just approving occasionally. Month six, you barely open it because it surfaces only what genuinely needs you.

This is the opposite of every engagement-optimized consumer product. Clarity succeeds when it gives people their time back.

### How it works

1. **Knows who you are** — through conversation, observation, and inference. Not a profile form. A living, evolving mental model of your life, work, family, priorities, relationships, and preferences. Truly custom and unique to the individual.

2. **Manages your signals** — email today, calendar and Slack tomorrow, any information stream eventually. Not by summarizing everything, but by applying *judgment*: what matters, what's urgent, what can wait, what can be ignored. Conducts work on your behalf where trusted to do so.

3. **Does the executive function work** — breaks vague goals into concrete tasks, prioritizes across life domains, identifies what needs the user vs. what the agent can handle, and nudges toward follow-through. The agent doesn't just track your tasks — it thinks about *what you should be doing* and helps you do it. For someone with ADHD, this is the difference between a to-do list (another thing to maintain) and an actual assistant (someone who maintains it for you).

4. **Earns trust through competence** — starts by informing, graduates to recommending, eventually acts autonomously in domains where it's proven reliable. Users can accelerate this at their own discretion, or let it happen naturally. There is nothing stopping this thing from building a team of agents to grow your business — the ceiling is integration and trust, not capability.

5. **Improves silently** — background processes analyze patterns, prune stale context, calibrate judgment, and surface needs for new capabilities. The user doesn't configure this. They just notice the agent getting better.

## Design Principles

### 1. Judgment Over Summarization

The agent's value is not in reducing the volume of information — it's in knowing what matters. An email from your kid's school about a snow day is urgent because you need to arrange childcare. A newsletter from the same school about spring fundraising can wait until the weekend. This distinction requires knowing about the user, not just about the email.

### 2. Show, Don't Interrogate

The agent should never feel like a form or a quiz. It learns by observing, inferring, and occasionally asking *one good question* at the right moment. "You've gotten 3 emails from Riverside Elementary this week — is that your kid's school?" is better than "Please list your children's schools."

### 3. Earn Trust Through Competence

Users grant the agent more capability not by flipping settings, but by experiencing good judgment. The agent proposes its own graduation: "I've been flagging your scheduling emails for two weeks and you've acted on every one. Want me to start handling routine ones automatically?" The answer might be no. That's fine. Ask again in a month.

### 4. Proactive Without Pushy

The agent should feel like a great executive assistant: present when needed, invisible when not. One insight per day is better than five mediocre ones. Silence is a valid response. The agent should never create more work than it saves.

### 5. Accessible by Default

The ideal interaction is a conversation. No dashboards to learn, no settings to configure, no technical knowledge required. "Hey, my mornings are chaos — can you help?" should be enough to get started. Power users get depth through conversation, not through a different UI.

### 6. Do the Thinking, Not Just the Tracking

The difference between a to-do list and an assistant is that the assistant *thinks*. Clarity doesn't just record "renovate kitchen" — it breaks that into "call contractor about timeline," "schedule inspection," "order cabinet hardware," and tells the user which one matters today. When new information arrives (contractor emails about a delay), the agent updates the plan and nudges accordingly. The user's job is to *do things*, not to figure out what to do.

### 7. Safe by Architecture

The agent cannot access secrets, credentials, or systems beyond its explicitly granted scope. Not because we trust the model to behave — because the infrastructure makes it impossible. This is the wedge against competitors who ship fast and insecure: Clarity is safe *by design*, not by prompting.

## The Experience

### Day 0: First Meeting

The user signs in. The agent introduces itself in one sentence, explains what it can do in plain language, and asks one question: *"What's on your plate right now — what's the thing that keeps falling through the cracks?"*

The user says: "Honestly, everything. I have a kitchen renovation going on, my kids' school sends a million emails, work is nuts, and I can never keep up with any of it."

The agent says: "That's a lot of plates spinning. Let's start with the one that's easiest to help with right now — connect your email and I'll start figuring out what actually needs your attention. I won't do anything with it yet, just learn. After a few days I'll show you what I think matters and you tell me if I'm right."

The user connects Gmail. The agent processes the inbox silently. It also records: *two kids, kitchen renovation in progress, feels overwhelmed, work is busy — prioritize reducing cognitive load.*

### Day 1-3: Calibration

End-of-day digest: "Here's what I noticed today. 3 emails I think are important, 2 that can probably wait, and 47 I'd call noise. Am I reading your priorities right?"

The user reacts: "That one from the contractor is actually urgent — we're in the middle of a kitchen reno." The agent records this, adjusts its model, and starts paying more attention to emails from that sender and related threads.

One proactive nudge: "You got a permission slip from Riverside Elementary that's due Friday. Just flagging it."

### Week 2: Graduated Agency

The agent notices the user acts on every scheduling email within an hour. It proposes: "I could draft replies to routine scheduling emails and show them to you for approval before sending. Want to try that?"

If yes: the agent starts drafting. If no: it continues informing. Either way, it's learning.

### Month 2: Chief of Staff Mode

The agent knows:
- The user has two kids at Riverside Elementary
- The contractor emails about the kitchen need fast responses
- Monday mornings are hectic — don't bother with non-urgent stuff before 10am
- The user's work projects and key stakeholders
- Which newsletters are actually read vs. archived

It handles routine email triage automatically, surfaces genuinely important items as notifications, and drafts responses for approval in specific categories.

But more than that, it's doing the *thinking*:
- The contractor emailed about a 2-week delay on countertops. The agent updated the kitchen renovation task timeline, flagged that the plumber was scheduled for next week (which now conflicts), and drafted a message to the plumber asking to reschedule.
- The user mentioned wanting to grow their consulting business. The agent broke that into concrete workstreams, identified three things the user needs to do personally and two it can research on its own, and has started a background brief on competitor pricing.
- It noticed the user always forgets to reply to their accountant. Now it nudges at 9am on Tuesdays: "Your accountant sent Q4 docs last week. Want me to draft a reply?"

The user barely opens their inbox anymore. They open Clarity — and even that is getting less frequent, because the agent handles more each week.

## Trust Tiers

The agent operates at three levels, per domain (email, calendar, tasks, etc.):

| Tier | Agent Behavior | User Experience |
|------|---------------|----------------|
| **Inform** | "Here's what I noticed" | Digest, flags, summaries |
| **Recommend** | "Here's what I think you should do" | Suggested actions, draft responses |
| **Act** | Agent takes action, reports after | Auto-triage, auto-reply, auto-schedule |

**Default:** Everything starts at Inform.

**Graduation:** The agent proposes moving to Recommend for specific domains after demonstrating accurate judgment. Act is only reached when explicitly approved, per domain.

**Acceleration:** Power users can skip the crawl via a trust settings panel. Their risk, clearly communicated. This is not hidden — the agent itself can mention it: "If you want, you can give me more autonomy in Settings. I'll still learn the same way, just faster."

**Demotion:** Users can always dial back. "Stop auto-replying to scheduling emails" immediately drops that domain back to Inform.

## The Mental Model

The agent maintains a structured internal model of each user:

### Life Domains (discovered, not configured)
- Work — projects, stakeholders, recurring meetings
- Family — kids' schools, partner's schedule, family events
- Home — maintenance, contractors, utilities
- Health — appointments, habits
- Finances — bills, subscriptions, budgeting
- Interests — hobbies, communities

### Key Entities
- People (who matters, what their relationship is, how urgent their communications tend to be)
- Organizations (employer, schools, service providers)
- Projects (ongoing work with deadlines, dependencies, collaborators)
- Recurring events (weekly meetings, monthly bills, school terms)

### Priority Signals
- What the user has reacted to quickly vs. let sit
- What they've marked as important vs. dismissed
- What generates follow-up action vs. gets archived
- Explicit corrections: "this is actually important" / "stop bothering me about this"

### Behavioral Patterns
- Active hours and time zones
- Response latency by sender/category
- Communication style preferences (terse vs. detailed, formal vs. casual)
- Task completion patterns (procrastinates on X, immediately handles Y)

This model is not a static profile. It's a living document the agent continuously refines through observation, inference, and explicit feedback. Background processes prune stale entries, resolve contradictions, and surface gaps.

## Signal Processing Architecture

Email is the first signal source, but the architecture treats it as one of many:

```
Signal Sources              Signal Processor              Output
─────────────              ─────────────────              ──────
Gmail  ──────┐
Calendar ────┤             ┌──────────────┐
Slack ───────┼──────────── │  Judgment    │ ──── Notifications
Discord ─────┤             │  Engine     │ ──── Suggested Actions
RSS feeds ───┤             │  (LLM +     │ ──── Auto-actions (Act tier)
Bank alerts ─┘             │  Mental     │ ──── Memory updates
                           │  Model)     │ ──── Task creation
                           └──────────────┘
```

Each signal source implements a common interface:
- **Ingest:** Pull new signals on a schedule or via webhook
- **Normalize:** Convert to a common format (who, what, when, thread context)
- **Enrich:** Attach user-model context (sender relationship, domain, historical priority)
- **Judge:** LLM applies user's mental model to determine importance and action

The judgment engine doesn't process each signal in isolation. It maintains a running awareness of "what's happening in this person's life right now" and interprets new signals through that lens.

## Feedback Loops

### Explicit Feedback (User → Agent)
- Reacting to notifications: "this was useful" / "don't bother me with this"
- Correcting triage: "that email was actually important"
- Adjusting instructions: "always flag emails from [person]"
- Trust tier changes: "start drafting replies" / "stop auto-scheduling"

### Implicit Feedback (Observed Behavior)
- User opens notification immediately → signal was correctly prioritized
- User dismisses without reading → signal was probably noise
- User takes action the agent suggested → recommendation was good
- User ignores suggestion → recommendation was off-base
- User manually does something the agent could have done → opportunity to offer help

### Silent Improvement (Background Processes)
- **Memory pruning:** Remove stale or contradicted observations
- **Prompt calibration:** Adjust tool guidance weights based on what's working
- **Pattern detection:** Surface emerging routines the agent can assist with
- **Tool discovery:** Identify needs the current tool set can't address and flag them
- **Judgment auditing:** Periodically review the agent's triage accuracy against user actions

## Competitive Position

### The landscape is agents working for platforms

Every major AI company is building agents that serve *their* ecosystem. Google's agent optimizes for Google products. Apple Intelligence optimizes for Apple's ecosystem. OpenAI and Anthropic sell inference to developers. OpenClaw ships raw agency without guardrails.

**Nobody is building the agent that works for the individual across everything.** That's the gap.

### Why Not ChatGPT / Claude / Gemini?
They're conversation tools. You go to them with a question. Clarity goes to you with awareness. They're smart search bars you invoke. Clarity is a staff member who's always working.

### Why Not OpenClaw?
OpenClaw ships agency without guardrails. It can read your email and call APIs, but there's no trust architecture, no graduated autonomy, and no architectural security boundary. Clarity demonstrates that safety and capability aren't tradeoffs — they're complementary. You shouldn't need to worry about whether your agent is going to leak your API keys.

### Moat
**Primary: the personalization flywheel.** Every interaction calibrates the mental model. After a month, Clarity knows what matters to you in a way no competitor can replicate without a month of learning. After six months, switching costs are astronomical — not because of lock-in, but because the value is in the understanding. This is the first product where "it knows me" is literally true.

**Secondary: the trust architecture.** Being able to say "your agent literally cannot access your credentials" is a differentiator that takes real engineering, not just prompting. Shipping fast and insecure is easy. Shipping fast and safe is hard — and it's a moat once you've done it.

**Tertiary: decreasing engagement as a feature.** Competitors optimizing for DAU will always push users toward more interaction. Clarity's incentive alignment is different — it succeeds when users need it less. This attracts the exact users who are exhausted by attention-hungry apps.

## What Exists Today

| Capability | Status | Gap |
|-----------|--------|-----|
| Agent infrastructure | Solid | Prompt personality needs work |
| Memory system | Working | Captures facts, not judgment calibration |
| Email processing | Working | No signal abstraction; no judgment layer |
| Notifications | Working | No feedback mechanism on notifications |
| Bootstrap/onboarding | Implemented | Dumps data instead of building relationship |
| Trust tiers | Not built | Everything is flat — no graduated autonomy |
| Feedback loops | Not built | No mechanism for user reactions to shape behavior |
| Signal abstraction | Not built | Email is hardwired |
| Background optimization | Not built | No silent improvement processes |
| Mental model schema | Partial | Memories exist but not structured as user model |

## Roadmap (Suggested Priority)

### Phase 1: Make What Exists Feel Right
- Redesign onboarding as a conversation, not a data dump (SPEC-021 is a step)
- Rewrite agent personality: soul text, operating model, interaction patterns
- Add notification feedback mechanism (useful / not useful)
- Structure the mental model schema (domains, entities, priorities)

### Phase 2: Judgment Layer
- Build the signal processing abstraction
- Implement email triage with judgment (not just summarization)
- Trust tier system: Inform → Recommend → Act per domain
- Agent-proposed graduation ("Want me to handle this?")

### Phase 3: Feedback Flywheel
- Implicit feedback tracking (what users act on vs. ignore)
- Background memory pruning and model refinement
- Prompt self-calibration based on interaction outcomes
- Tool gap detection and surfacing

### Phase 4: Signal Expansion
- Calendar integration
- Slack/Discord integration
- RSS/news monitoring
- Financial alerts

### Phase 5: Full Autonomy
- Act-tier capabilities: auto-reply, auto-schedule, auto-triage
- Approval workflows for high-stakes actions
- Cross-signal reasoning ("you have a meeting at 3 but your contractor just emailed about coming at 2:30")

---

*This document is the north star. PRDs will detail specific phases. SPECs will detail specific implementations within those PRDs.*
