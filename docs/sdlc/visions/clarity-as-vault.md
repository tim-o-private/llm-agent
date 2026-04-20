# Clarity as Vault

**Status:** Vision doc — product altitude. What we're building, who for, what it solves. Implementation companion: [clarity-as-vault-architecture.md](./clarity-as-vault-architecture.md).

**Authors:** Tim + Claude (2026-04-16 → 2026-04-17)

---

## Thesis

Clarity is an environment where an agent **orchestrates work toward your goals** against a markdown vault shaped by what matters to you. The vault is not a schema we designed — it emerges from your life, through use. Docs, folders, and links take whatever shape reflects your values; the agent navigates that structure, updates it from signals you give it, and identifies the work you need done.

The agent is an orchestrator, not a note-keeper. Its job is to take on cognitive load by **building and running systems that serve you** — workflows on schedule, processes triggered by events, proposed actions awaiting your approval. The vault is where those systems' state and memory live. The **Today page** is the dashboard over what the agent is running for you.

You direct the agent through two always-available surfaces:
- **Conversation** — complex intent, questions, redirection, "why did you do that." The window into what the agent is up to.
- **Direct edits to the vault** — pin what matters, correct the schema, mark what's blocked, drop captures.

Neither surface is special. Both feed the same orchestration kernel. Chat is never the management layer; direct edits are never required. But both are always available, because a system that silently edits things and builds workflows without a visible channel is untrustworthy by construction.

This reframes Clarity from "chat with memory and tools" to "an orchestrator that runs systems against a vault shaped by your life." It absorbs what hq proved works (skills + operating model + markdown-as-config) and exposes that model through a UI a non-technical user can watch, trust, and redirect.

The deeper bet: modern models are agentic when given real tools, real tasks, real consequences, a persistent environment, **and a channel for the user to inspect and redirect**. Prior prompting work (soul.md, bootstrapping phases, heartbeat channels) has been compensating for missing orchestration primitives and missing transparency. Both arrive with this reframe.

---

## Problems this update solves

1. **Apps force users to fit their lives into someone else's schema.** Every productivity tool imposes fields, tabs, and templates. Most of life doesn't fit. The vault inverts this — structure emerges from how the user actually uses it; the agent adapts to the user's shape, not the other way around. Honest qualifier: there are strong defaults (a seed vault structure shipped with Clarity), but they are user-editable markdown — not database columns, not product decisions disguised as UI. "Emergent schema" means the shape evolves through use, not that every user starts from an empty directory.

2. **The agent isn't orchestrating, just responding.** Chat-plus-memory produces an assistant that answers questions. The user needs a partner that **identifies work the user needs done, proposes workflows to do it, runs them, and reports back**. Orchestration — not curation — is the job.

3. **The "inch away for a year" loop.** Incremental fixes to chat + memory + skills kept landing "almost there." A genuinely different shape — vault-as-emergent-schema + orchestrator — means the next iteration isn't another rewrite of the same product.

4. **Silent autonomy is untrustworthy.** An agent that edits docs, proposes workflows, and takes actions without a visible channel is a liability. Conversation as an always-available mode (not the management layer, but a mode alongside direct edits) is how the user inspects, questions, and redirects the system.

5. **Cognitive load has nowhere durable to land.** Chat turns evaporate. The vault is the place where the user's externalized working memory lives, inspectable and co-maintained by user and agent.

6. **Every behavior change requires code or prompt-rewriting.** Workflows, agents, and models as text files = change behavior by editing files. Directly addresses the soul.md / bootstrapping / channels rewrite loop that's been eating sessions for months.

7. **Orphaned scaffolding accumulates.** Bootstrapping, channels, session_open were in flight indefinitely. The reorientation makes them irrelevant rather than finishable — scaffolding moves to hooks/middleware; the agent's self-conception compresses to "I orchestrate work against this vault."

### What this update is explicitly NOT solving

- Specific Stage 1 UX and implementation choices — SPEC territory.
- Non-Tim user acquisition — post-Stage-3 problem.
- Model capability gaps — resolve independently as models improve.
- Continuous autonomous initiative — speculative frontier, deferred past Stage 5.
- Multi-device real-time sync, voice-first interaction, mobile-first UX — deferred.

---

## Wedge

**Stage 1 target: Tim's daily briefing, 100% right.**

Not "personal assistant for Tim." Not "platform for four personas." One loop — the morning brief — executed so well that opening it replaces opening the inbox. Everything else is Stage 2+ or non-goal.

Generalization to other users comes later, and only after the daily-briefing loop is something Tim would defend shipping to someone else. The four-persona collapse (below) is architectural insurance — the substrate can serve all four — not Stage 1 scope.

---

## Users and jobs

One user shape with overlapping contexts, collapsed into one substrate:

| Context | What it needs from the system |
|---|---|
| Technical user / AI researcher | Direct vault access. Custom skills. Scheduled jobs. Transparency and control. |
| Small business owner | Inbox triage, draft replies, meeting prep, CRM-lite via entity docs. |
| Parent with complex family life + ADHD | Externalized working memory. Universal capture. Agent surfacing what's due without notifications. |
| Person tired of tech managing them | Agent as co-worker, not a feed. Approval lanes over interruptions. Agent owns state; user provides direction. |

These collapse to one requirement: **an orchestrator that builds and runs systems against a vault whose schema reflects the user's life, with user direction arriving through conversation and direct edits.**

---

## Transactions (the interaction model)

A transaction is **a signal that feeds the orchestrator** — from user, agent, or external event. The agent translates signals into vault edits, workflow runs, proposed actions, or schema changes. Seven shapes cover nearly everything:

1. **Capture.** User drops a thought (text, voice). Agent routes into the graph, confirms placement, and may propose a workflow if it recognizes a recurring pattern.
2. **Conversation.** User talks to the agent about intent, plans, or "why did you do that." The agent answers, surfaces relevant vault state, and — when direction is given — translates it into edits, workflows, or proposed actions. Chat is a *mode*: not the management layer, but always available.
3. **Direct edit.** User edits a vault doc. Agent notices, incorporates into its understanding, and adapts what it's running. Edits also communicate schema intent — "I want a folder for this" becomes a structural signal.
4. **Ambient update.** Agent, on schedule or trigger, edits docs without user initiation. Morning brief populates. Threads get new entries. Entity docs refresh.
5. **Orchestration proposal.** Agent notices recurring work (repeated captures of the same shape, a standing question, a pattern of requests) and proposes a new workflow, agent, or skill. User approves, edits, or rejects. Approved proposals land as text files the system runs.
6. **Review + approval.** Agent surfaces a prepared action (draft, proposed event, outreach). User approves inline. Approved action executes; result logged.
7. **Delegation.** User marks an intent ("plan the Santa Fe trip"). Agent opens a thread-doc, possibly spins up a workflow, drives the work forward, surfaces in Today when something needs input.

### Why both conversation and direct edits are always available

They serve different modes of direction:
- **Conversation** is for intent that doesn't fit in an edit — "stop suggesting outreach on weekends," "figure out what's blocking the Q3 plan," "why is this in the approval queue."
- **Direct edits** are for schema and state control — "this matters now," "archive this," "the shape of my work is different this month."

Without conversation, a user can't redirect the system when edits don't express what they mean. Without direct edits, the user has to negotiate every structural change through a chat turn.

What we refuse: making chat *the* surface. That collapses back to conversational AI with extra steps and turns the vault into scratch space behind a chat window.

---

## The single pane: Today

Today is the **dashboard over what the agent is running for you**, regenerated on schedule, treated as the front door. Structure:

- **Header.** Date. One-line framing of what kind of day this is.
- **Your day.** Calendar, decisions needed, meeting prep. Linked.
- **To do.**
- **Notes.** Input for new thoughts. Becomes input for To Do, agent, and approval queues.
- **Agent.** What workflows are running, what it's watching, what it did since you last looked, what it's blocked on. Each item links deeper into the vault.
- **Approvals.** Pending actions — drafts, proposed events, suggested outreach, proposed new workflows — persistent until drained.
- **Recent.** Recently touched docs for fast return.

Today isn't a document the agent maintains for its own sake — it's the control surface for everything the agent is doing on the user's behalf. The graph underneath is the state those workflows operate over. The conversation surface (Cmd-K or similar) is always one keystroke away for "why is that in approvals" or "stop doing that."

---

## Architectural primitives

Everything in the system is built from four text-file primitives. Code is written only where a security boundary, a tool, the runtime kernel, or the UI demands it.

```
Workflow    →    Node   →   Agent                  →   Model
(text file)     (references    (markdown +              (field in
                 an agent)      frontmatter)             frontmatter)
```

- **Workflow** — a text file defining a directed graph. Each node references an agent by name. Triggered by cron, user action, or other workflows. **Zero code to add or modify.**
- **Agent** — a markdown file with frontmatter (Claude Code / hq convention): `name`, `description`, `model`, `tools`. Per-agent model = per-task cost routing, declared not programmed.
- **Skill** — a markdown file declaring a reusable procedure (hq convention). Loaded on demand. **Zero code.**
- **MCP tool** — external capability. Code at the boundary; the *use* of it is declared in agent frontmatter.

### Why this matters

- **Orchestration is text authoring.** Building a new system for a user need — a recurring workflow, a new triage process, a custom brief — is writing a workflow file and a handful of agent markdown files. No deploy, no code review, no engineering ticket.
- Adding a new Today variant, a capture handler, a morning-brief tone: edit text.
- Changing which model handles a task: edit one line of frontmatter.
- Graph + agent markdown + ledger = complete, inspectable definition of system behavior.
- **Structured autonomy:** the agent can author these files itself (proposing new workflows when it identifies recurring work), but every change flows through the same proposal → approval → execution path any other action does.

### Self-improvement is free

Because behavior is declared in markdown in the vault, and the agent already writes to the vault, **self-improvement is not a separate capability — it's the agent editing config files through the same approval-lane mechanism as drafting an email.** hq proves this: agents update MEMORY.md, write skills, tweak agent definitions, all via markdown + human review.

**Caveat:** "self-improvement is free" is free *for technical users*. hq's self-editing works because Tim reads markdown and fixes an agent that writes a broken skill. For non-technical users the same mechanism needs more UX — rollback, dry-run preview, conservative defaults on what the agent proposes to change. That's a Stage 5 concern, not a Stage 1 claim.

What's deferred past Stage 5: unbounded autonomous initiative (agent continuously watching its own performance and editing without explicit trigger). Human-in-the-loop, approval-gated self-improvement is not speculative — it's what hq already does, promoted to a first-class primitive.

### Transparency and safety

Structured autonomy, by design:
- Behavior lives in text — inspectable, diffable, revertable via git.
- Every agent action leaves a ledger entry.
- Every world-facing action requires approval with an unforgeable record.
- Security enforcement (auth, sandbox, RLS) is code, not configuration.

### Where code lives

Code is written, carefully, only at these boundaries:
- **Security** — auth, sandbox, permission enforcement.
- **Tools** — MCP server implementations.
- **Runtime kernel** — workflow engine, dispatch layer, model-call integration.
- **UI** — the web app.

Everything else is text. Implementation details: see architecture companion.

---

## Substrate: Obsidian-compatible markdown

The vault is **Obsidian-compatible markdown** — plain markdown + YAML frontmatter + `[[wikilinks]]`. No invented format.

This gives us properties we want anyway:
- **Portable.** A user's vault is a directory of `.md` files they own. No lock-in.
- **Openable in Obsidian.** Power users get graph view, dataview, templater, mobile apps, plugin ecosystem — for free.
- **Privacy story.** Local-first, user-owned files is the easiest privacy pitch available.
- **Trust signal.** Users trust a tool when they can also open their data in software we don't control.

**Architectural stance:** we build our own web app as primary UI. Obsidian is a supported peer viewer, not a dependency. Everything works without it.

---

## Step-wise build plan

Each stage delivers standalone value and tests the metaphor. Exit criterion per stage determines proceed or pivot.

### Stage 1 — Vault + Today workflow + conversation mode, read-only (~3–4 weeks)

*Context on timeline: workflow engine and base web UI already exist. Stage 1's new work is the vault directory render, Today-specific layout, and the conversation surface that edits markdown agent config. Estimate accounts for the conversation surface being non-trivial (see sanity check).*

- Per-user markdown vault.
- `workflows/today.md` — a workflow text file with nodes for gmail fetch, calendar fetch, summarize, and write-today.
- Minimal agent set: one markdown file per node.
- Workflow engine schedules Today on cron; runs on dev runtime.
- Web app renders Today as the landing page (full vault browser ships with S2 in a later spec).
- **Conversation surface available from Today** — user can ask "why this?", "change that," "explain." Chat can issue redirection that modifies Today's agent config (markdown edits) but cannot take outbound actions.
- Read-only with respect to the outside world — no emails sent, no calendar events created.
- **Primary exit:** does opening Today replace opening my inbox for 2 weeks?
- **Secondary exit (architecture test):** can I change Today's tone or structure by editing only text files (directly or via chat direction), with no code change?

### Stage 2 — Capture → vault (~1 week)
- Text input routes thoughts into the graph.
- Agent confirms placement; user can redirect.
- **Exit:** does working memory feel externalized?

### Stage 3 — Approval lane (~2 weeks)
- Agent proposes actions: drafts, tentative blocks, suggested outreach.
- UI renders approval lane; user drains it.
- Approved actions execute; results logged.
- **Exit:** do I trust its judgment enough to drain the lane daily?

### Stage 4 — Auto-maintained entity docs (~1 week)
- Person / project / company pages kept current with backlinks.
- **Exit:** does the graph feel alive?

### Stage 5 — Agent-initiated threads + orchestration proposals (~1–2 weeks)
- Agent notices on scheduled check, opens thread-docs, surfaces in Today.
- **Orchestration proposals ship as first-class:** agent recognizes recurring work and proposes new workflows, agents, or skills via the approval lane. Approved proposals land as text files the system runs.
- **Exit:** does it feel like a co-worker? Are proposed workflows actually taking load off, or noise?

**Decision point after Stage 3:** by then we know if the metaphor holds. If yes, continue to 4–5 and plan commercialization. If no, we've learned cheaply and can pivot without having torn down Clarity.

### Kill criterion

If at the end of Stage 1's window Tim is still **manually patching Today's output to make it useful** — adding missing context, rewriting sections, correcting what the agent assembled — stop and reassess architecture rather than push through to Stage 2. "Am I opening Today every morning" is too easy to pass through willpower and investment bias; "am I still compensating for what the agent got wrong" is the honest test. The "inch away for a year" pattern breaks through discipline, not more design.

---

## What Clarity's existing architecture becomes

### Load-bearing, keep
- **Workflow engine (SPEC-036/037)** — dispatch spine. Everything zero-code-configurable hangs off it.
- **Deep Agents integration** — prod runtime. SPEC-044 bwrap backend on the critical path.
- **hq is the vault convention.** Tim's `hq/` repo *is* his vault. For other users, their vault is hq-shaped: `system/` holds Clarity-shipped content; everything else is user content. Clarity-the-code provides the kernel; hq-the-content provides the graph.
- **Memory protocol / Qdrant** — durable cross-surface memory layer.
- **bwrap sandbox (SPEC-044)** — multi-user isolation.
- **chatServer + Postgres** — auth, sessions, encrypted secrets, approval records, billing, RLS enforcement. The vault complements Postgres; it does not replace it.

### Demoted / simplified
- **soul.md / bootstrapping / channels / session_open** — replaced by runtime scaffolding. Agent's self-conception compresses to "I maintain this vault."
- **Per-request agent orchestration in chatServer** — superseded by workflow engine.
- **Legacy LangChain agent loops** — superseded by Deep Agents as the single agent abstraction.

### Reframed
- **Skills** — per-user markdown in the vault.
- **Task management in DB** — superseded by approval lane + ledger (keep only if a specific capability depends on it).
- **Prompt template system** — simplified; behavior lives in agent markdown.

---

## Non-goals (Stage 1)

Explicit about what Stage 1 does not try to do:
- Serve users other than Tim.
- Support mobile beyond read-only (Obsidian iOS covers this).
- Take any outbound action in the world.
- Ship agent-initiated orchestration proposals (Stage 5 concern). Stage 1 chat can direct existing workflow edits; agent can't propose new workflows unprompted.
- Support multi-device real-time sync beyond git-backed vault semantics.

---

## Resolved (prior open questions)

- **Next user** — relative, friend, or sourced from ADHD / Obsidian communities. Personal network first, community second. Stage 2+ assumes *fresh vault start*, not import from existing Obsidian vaults (matches what's being tested now).
- **Name** — working title **Clarity**. SEO/positioning work deferred; "Clarity" is taken by several productivity products, which will matter later but isn't blocking.
- **Pricing** — subscription + BYOK via OpenRouter per-user key. Subscription pays for the software, web UI, skills library, hosting, updates. OpenRouter isolation removes central-API-key commercial risk and keeps per-agent model routing viable. Central Anthropic key becomes optional fallback for users who don't want to provision their own.
- **Mobile** — punted. Obsidian iOS covers read + capture for technical users; everyone else waits until fundamentals are working.
- **Graph visualization in the UI** — not a concern. Power users get this from Obsidian if they want it.

## Still open (product altitude)

1. **Subscription scope.** What does the subscription include precisely — updates, skills library, hosted workflows, support? Naming this gives pricing a shape. Not blocking Stage 1.
2. **ZDR disclosure UX.** Once OpenRouter BYOK is in, users pick their own routes; we need a simple "is this route privacy-safe" indicator. Stage 3+ concern.
3. **Onboarding for ADHD / Obsidian community user #2.** Fresh-vault start means Stage 2 onboarding needs to assemble a coherent seed structure without dumping the user into empty directories. Concrete UX question, not blocking alignment.

Implementation-level questions (hook/middleware shim, multi-user storage, conflict resolution, voice tech, MCP hosting, vault versioning cadence, trigger mechanics, workflow format) live in the architecture companion.

---

## Next steps

1. Get alignment on this vision doc.
2. Break Stage 1 into a SPEC under normal SDLC.
3. Cancel or consolidate remaining orphaned bootstrapping work from prior sessions — most become irrelevant under this architecture.
4. Decide name / branding question before external-facing work begins.
