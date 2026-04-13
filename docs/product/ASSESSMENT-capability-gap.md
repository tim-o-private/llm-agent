# Product Assessment: The Capability Gap

> **Status:** Working document
> **Date:** 2026-04-13
> **Author:** Claude (Product) + Tim
> **Purpose:** Honest assessment of where Clarity is vs. where it needs to be. Not a PRD — a diagnosis that leads to action.

---

## The Diagnosis

Clarity has excellent plumbing and an accurate vision. What it doesn't have is behavior. The agent sits behind 25 working tools, a production-grade workflow engine, a multi-layer memory system, a file-based skill/config system, and a sandboxed execution environment — and uses almost none of it proactively. The user opens the app, sees a flat task list, chats with a reasonably pleasant assistant, and closes the app with no reason to come back tomorrow.

The vision documents (VISION.md, PRODUCT-BEHAVIOR-SPEC) describe an agent that builds a structured world model, exercises judgment, proposes its own graduation, creates workflows when it notices patterns, and improves silently over time. The current agent does none of this — not because the infrastructure is missing, but because no one told it to.

**The shortest path to a useful product is not more infrastructure. It's making the agent use what it already has.**

---

## What Actually Works

These are real, functional, production-ready capabilities — not stubs:

| Capability | Implementation | Notes |
|-----------|---------------|-------|
| **25 tools** | Email (read/search/draft/send), calendar, tasks, reminders, schedules, memory (semantic), web search, briefing prefs | All async, error-handled, approval-gated where appropriate |
| **Workflow engine** | LangGraph-based, 4 templates (morning briefing, evening briefing, email triage, draft-reply) | Checkpointed, resumable, human gates, service nodes |
| **Working memory** | AGENTS.md in per-user sandbox, loaded every session via MemoryMiddleware | Agent can read/write; synced to durable storage post-session |
| **Semantic memory** | Qdrant-backed via min-memory MCP server, 10 tools | Types, scopes, entities, tags, linking, semantic search |
| **User skills** | /user/skills/ writable by agent, auto-discovered by SkillsMiddleware | Agent can create skills that persist and load on future sessions |
| **User workflows** | /user/workflows/ writable by agent, discovered by TemplateRegistry | Agent can create workflow templates that shadow system ones |
| **Scheduled execution** | Universal job queue, cron-based, self-rescheduling | Morning/evening briefings, reminders, custom schedules |
| **Heartbeat channel** | Dedicated prompt channel for periodic background checks | Exists in the prompt builder but isn't configured to be useful |
| **Multi-account OAuth** | Gmail + Google Calendar, up to 5 accounts each | Token refresh, multi-account queries |
| **Approval system** | Per-tool trust tiers, pending actions, notification on approval needed | Send-email is REQUIRES_APPROVAL; others configurable |
| **Notification routing** | Web (DB) + Telegram, categories, metadata | Inline in chat + push to Telegram |
| **Subagent delegation** | Defined in agent.yaml, passed to create_deep_agent() | Researcher subagent configured |
| **File-driven config** | agent.yaml + soul.md, mtime-based cache invalidation | Edit config, restart not needed |

This is a substantial platform. The problem is not what's built — it's what the agent does with it.

---

## Reference Models: What Good Looks Like

Three systems demonstrate the pattern Clarity should follow:

### The hq System (Internal)

Tim's own operating system for managing businesses via Claude Code. It works because:

- **CLAUDE.md** provides persistent identity and rules loaded every session
- **Skills** encode reusable procedures the agent discovers automatically
- **Memory** (MEMORY.md + topic files) tracks evolving context — rewritten, not appended
- **Agents** are specialized workers spawned for specific tasks
- **Tasks** track current work with status and coordination
- The agent READS all of this on startup and WRITES to it during sessions

**Key insight:** Every session leaves the system smarter. The agent builds capability as it goes — creating skills, updating memory, improving processes. The interaction is the input; the accumulated capability is the product.

### OpenClaw (Open Source Personal Agent)

The most successful open-source personal agent (~247K GitHub stars). Key patterns:

- **MEMORY.md as curated dashboard** — not a log, a living summary of what matters. Recommended under 100 lines. Rewritten to stay current. Loaded every session. This is the source of "the agent knows me."
- **Heartbeat vs. cron split** — heartbeats are periodic checks (default 30 min) where the agent reviews what's happening and stays silent if nothing needs attention. Cron jobs are scheduled one-shot tasks. The heartbeat is what makes the agent feel alive without being annoying.
- **3-5 proactive messages/day** — explicitly designed sweet spot. More causes alert fatigue. Fewer loses the feeling of having an assistant.
- **"Dreaming" (background consolidation)** — after sessions, a background process reviews what happened and distills it into structured persistent knowledge. Three phases: ingest, reflect, promote to MEMORY.md. This is how raw conversation becomes durable understanding.
- **"If it's not written to a file, it doesn't exist"** — conversational context is ephemeral (lost during context compaction). Only file-based memory persists. Pre-compaction flush saves important facts before they're lost.
- **Retrieval-before-action protocol** — the agent searches memory before acting, so continuity comes from actually looking things up rather than relying on context.

### Hermes Agent (Open Source, Nous Research)

Key differentiators beyond the OpenClaw pattern:

- **Self-improving skill system** — a closed loop: execute task, evaluate outcome, extract reusable skill, refine over time. Skills are stored as files, browsable, compatible with the agentskills.io standard.
- **USER.md separate from MEMORY.md** — explicit user profile (preferences, communication style, decision patterns) distinct from working notes.
- **Honcho dialectic user modeling** — a background process that runs after each conversation, analyzing the exchange to derive conclusions about the user: reasoning patterns, communication style, decision-making tendencies. Goes beyond storing what you said to modeling how you think.
- **"Agent stops asking questions it already knows"** — behavioral adaptation from accumulated user knowledge. Tracks task preferences, decision history, explicit corrections and implicit acceptance/rejection signals.

---

## The Gap: Specific, Mapped to Current Code

### Gap 1: The Agent Doesn't Operate on a World Model

**Vision says:** "A living, evolving mental model — domains, entities, priorities, patterns."

**Reality:** AGENTS.md seed is three empty sections:
```
## User Profile
*(Not yet known)*
## Preferences
*(None observed yet.)*
## Key Context
*(Nothing recorded yet.)*
```

The seed shapes the behavior. An empty notebook produces an agent that doesn't know what to write down. The interaction-learning skill mentions life domains and entities but doesn't provide structure for the agent to fill in. The semantic memory has 10 tools but the agent has no protocol for when/what to store vs. retrieve.

**What's needed:** A structured AGENTS.md seed that invites the agent to build a world model — goals, active plans, life domains, key people, observations, open questions. And explicit instructions in soul.md for how to maintain it.

### Gap 2: No Planning Abstraction

**Vision says:** "Breaks vague goals into concrete tasks... the agent doesn't just track tasks — it thinks about what you should be doing."

**Reality:** The agent has flat task CRUD. No goals, no plans, no milestones, no hierarchy, no timelines, no dependencies. A user who says "I want to grow my consulting business" gets... a task called "grow consulting business." The Today page shows a flat list because that's all the data model supports.

**What's needed:** The ability for the agent to decompose goals into structured plans (milestones, tasks, follow-ups, timelines) and track progress across sessions. This can start as a section in AGENTS.md (document-first, per Tim's direction) with tools for structured data following.

### Gap 3: The Agent Doesn't Build on Itself

**PRODUCT-BEHAVIOR-SPEC says:** "The agent periodically introspects on its own performance and can: create new workflows, improve prompts, or propose new capabilities."

**Reality:** The agent has write access to /user/skills/ and /user/workflows/. SkillsMiddleware and TemplateRegistry auto-discover new files. Post-session sync persists them. **The mechanism works.** But soul.md never mentions skills, workflows, or self-improvement. The agent doesn't know it can do this.

**What's needed:** Explicit instructions in soul.md and/or a system skill that teaches the agent: "When you notice a recurring pattern, create a skill. When you notice a multi-step process you've done before, create a workflow template. Your capabilities should grow over time."

### Gap 4: Heartbeat Is Wasted

**Vision says:** "Proactive without pushy. Present when needed, invisible when not."

**Reality:** The heartbeat channel prompt says: "Check each area, respond HEARTBEAT_OK if fine, otherwise report what needs action." But "each area" is undefined. The agent has no protocol for what to check, no world model to check against, and no guidance on what warrants interrupting the user vs. staying silent.

**What's needed:** A heartbeat protocol that references the world model: "Review AGENTS.md for active plans and pending follow-ups. Check calendar for upcoming conflicts. Check email for anything urgent from key contacts. Check overdue tasks. If anything needs the user's attention, message them with context. If not, HEARTBEAT_OK. Target 3-5 proactive messages per day maximum."

### Gap 5: No Session Continuity Protocol

**OpenClaw proves:** The agent should start every session by loading its world model and orienting — not waiting for the user to speak.

**Reality:** The session_open channel exists and computes bootstrap context (time since last interaction, first-time vs. returning), but this context is not fully injected into the prompt. The agent says something like "Hi, how can I help?" instead of "Your contractor emailed about the permit — needs a reply by Thursday. You have 3 meetings today, and the 2pm conflicts with the plumber."

**What's needed:** Session open should load AGENTS.md, check signals (calendar, email, overdue tasks), and lead with what matters. The current bootstrap context computation needs to be wired into the prompt.

### Gap 6: No Post-Session Consolidation

**Hermes proves:** Background processing after conversations is how raw chat becomes durable understanding.

**Reality:** After invocation, the system syncs modified files to durable storage. But there's no reflection step — no process that reviews what was discussed and updates the world model, extracts patterns, or creates skills. If the agent didn't explicitly write to AGENTS.md during the conversation, nothing persists except the raw chat history.

**What's needed:** A lightweight post-session workflow (or even just prompt guidance): "Before ending, review this conversation. Update AGENTS.md with anything you learned. If you noticed a pattern worth encoding, create a skill."

### Gap 7: The Today Page Doesn't Reflect the World Model

**Tim says:** "A flat task list belies the capability here. If it's going to help with executive function, it's not just enough to chat — it's to help come up with a longer term plan."

**Reality:** Today page = flat task list + chat panel. No goals, no plans, no progress tracking, no briefing, no "here's what matters today."

**What's needed:** Eventually, a plan-aware UI. But this is Tier 3 — the agent needs the world model and planning capability before the UI can reflect it. For now, the daily check-in workflow delivering via chat/Telegram is sufficient.

---

## What to Do: Priority Order

### Tier 1: Tell the Agent to Behave Differently (Days)

Pure prompt/config changes. No code. Highest leverage.

| Change | What | Why |
|--------|------|-----|
| **Rewrite AGENTS.md seed** | Structured world model template: Goals & Plans, Life Domains, Key People, Active Threads, Observations, Open Questions, Capability Log | The seed shapes what the agent writes. A structured template produces structured behavior. |
| **Rewrite soul.md** | Add explicit capability-building instructions: maintain world model, create skills for patterns, create workflows for processes, reference memory before acting, consolidate learning at session end | The agent does what it's told. Tell it to build on itself. |
| **Create agent-ops skill** | /system/skills/agent-ops/ — teaches the agent it can write to /user/skills/ and /user/workflows/, with format examples and decision criteria for when to create them | The mechanism exists. The agent just doesn't know about it. |
| **Rewrite heartbeat prompt** | Reference world model, check signals against active plans, 3-5 messages/day target, silence is valid | Make the heartbeat actually useful instead of a generic "check things." |
| **Wire bootstrap context** | Ensure session_open prompt includes pre-fetched calendar/email/task signals and leads with what matters | The context is computed. It just needs to land in the prompt. |

### Tier 2: Structured Execution (1-2 Weeks)

New workflow templates + minor code to support planning abstraction.

| Change | What | Why |
|--------|------|-----|
| **Daily check-in workflow** | Structured graph: load world model, gather signals, synthesize priorities, present briefing, capture user direction, update plan. Replaces current morning briefing. | A workflow enforces that each step happens and produces output. Freeform chat loses state. |
| **Planning workflow** | Triggered when user describes a goal: clarify, decompose into milestones/tasks, identify dependencies, write plan to AGENTS.md, schedule follow-ups | Without structured planning, "grow my business" stays a single task forever. |
| **Session reflection** | Post-session: review conversation, update AGENTS.md, extract patterns, create skills if warranted | Raw conversation should become durable knowledge automatically. |
| **Goal/plan tools** | Either extend task tools with hierarchy (parent_id, type=goal/milestone/task) or create dedicated goal tools that the agent uses alongside AGENTS.md | The agent thinks in documents (AGENTS.md) but needs structured data for the UI to render plans. |

### Tier 3: UI Catches Up (Weeks)

The frontend reflects the world model.

| Change | What | Why |
|--------|------|-----|
| **Plan-aware Today page** | Replace flat task list with: active goals, their plans, current status, what needs attention today | The data exists in AGENTS.md + structured tools. The UI should surface it. |
| **Briefing view** | Morning check-in rendered as a structured card (not just chat text) with actionable items | Check-in workflow output should be a first-class UI element. |
| **Capability browser** | Show what skills and workflows the agent has created, let user review/edit | Transparency about self-improvement per PRODUCT-BEHAVIOR-SPEC section 4.3 |
| **Trust tier UI** | Per-domain trust display, graduation proposals, quick approve/reject | The autonomy flywheel needs a user-facing surface |

---

## Starting Point

**Tier 1 is the move.** It requires no code changes, no migrations, no UI work. It's rewriting text files that reshape how the agent behaves. If the soul.md rewrite and AGENTS.md seed restructure work, the agent should feel meaningfully different in the next session — maintaining a world model, referencing it proactively, and starting to build its own skills.

The test: after Tier 1 changes, open the app. Does the agent demonstrate that it knows your world? Does it lead with what matters? Does it create a skill or workflow without being asked? If yes, proceed to Tier 2. If not, iterate on prompts until it does.

Tier 2 workflows add the structural enforcement Tim identified as critical: "inference within a specific structure enforced in graphs." Without workflows, the agent might gesture at planning but never complete it. The daily check-in and planning workflows ensure that plans get created, progress gets tracked, and sessions don't have amnesia.

Tier 3 is important but not urgent. The agent can deliver value through chat and Telegram before the UI catches up. A good morning check-in via Telegram is more useful than a beautiful empty dashboard.

---

## Open Questions

1. **Model choice for autonomous behavior.** agent.yaml specifies claude-haiku-4-5. Is that sufficient for the judgment and self-improvement we're asking for, or does autonomous planning/skill-creation need a more capable model? Haiku for chat, Sonnet for workflows?

2. **How aggressive should skill creation be?** Should the agent create skills liberally (and prune later) or conservatively (only when very confident)? OpenClaw leans toward liberal capture; Hermes toward evaluated extraction.

3. **Heartbeat frequency.** OpenClaw defaults to 30 min. What's right for Clarity? Should it vary by time of day (more frequent in morning, less at night)?

4. **Session reflection trigger.** Should this be a full workflow (graph-enforced steps) or just prompt guidance ("before ending, update AGENTS.md")? Workflow is more reliable but heavier.

5. **Plan data model.** Start with AGENTS.md only (agent-as-document) or immediately add structured goal/milestone/task hierarchy in the DB? The former is faster; the latter enables UI earlier.
