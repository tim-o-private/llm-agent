# PRD-003: Competitive Research & Strategic Analysis

> **Status:** Draft v1
> **Author:** Tim + Claude (Product)
> **Created:** 2026-02-25
> **Companion to:** `docs/product/PRD-003-orchestration-layer.md`

---

## Purpose

Research into the Claude Code orchestration tool ecosystem — what exists, what users actually experience, and where the opportunity lies for PRD-003. This is not a feature comparison. It's an honest assessment of what works, what doesn't, and why nobody has solved the problem yet.

---

## Landscape: Tool-by-Tool Assessment

### 1. oh-my-claudecode (OMC) — 7.3K stars

**What it is:** Teams-first multi-agent orchestration plugin for Claude Code. 7 execution modes (Autopilot, Ultrawork, Ralph, Ultrapilot, Ecomode, Swarm, Pipeline), 32 specialized agents, 31 lifecycle hooks. Installs via Claude Code's native hooks system — survived the Jan 2026 OAuth crackdown because it doesn't extract tokens.

**What actually works:**
- Hook-based architecture is sound — builds on official CC primitives
- Pre-defined agent roles (planner, architect, critic) save setup time vs. Agent Teams where the LLM "decides the team composition on the fly each time"
- Ecomode's model routing (Haiku for simple, Opus for complex) genuinely saves 30-50% on tokens

**What breaks ([stress test #301](https://github.com/Yeachan-Heo/oh-my-claudecode/issues/301)):**
- Token counting is broken — 89% undercount (3 tokens recorded vs 27 actual). Users think they're spending less than they are.
- SubagentStop hook expects a `success: boolean` field that doesn't exist in the SDK's actual type — all agents marked "failed" regardless of outcome
- Race condition in ConcurrencyManager — non-atomic queue/count management causes potential deadlocks
- Ralph state corruption from circular imports
- Cancel cleanup misses 20+ state files — daemon processes leak
- 30+ locations silently swallow JSON parsing failures

**Why people leave:** Rapid iteration pace means constant breakage. 15 bugs (4 critical) in a single version. Users who don't track updates closely find their setups break. [Community recommendation](https://jeongil.dev/en/blog/trends/claude-code-agent-teams/): start with Agent Teams because "community tools often stop being maintained."

**Assessment:** Closest competitor to PRD-003's execution layer. Has pipeline stages, agent routing, monitoring. Does **not** have: persistent memory, spec-as-input, trust tiers, or a decision engine that learns.

---

### 2. claude-flow / ruflo — 14.4K stars

**What it claims:** "The leading agent orchestration platform for Claude." 84.8% SWE-Bench solve rate, 352x faster WASM execution, 75% API cost savings, ~500K downloads, 100K MAU across 80+ countries.

**Reality check:** Claims are extraordinary and largely unverifiable. The "Ranked #1 in agent-based frameworks" label appears in the repo's own description. No independent verification of the SWE-Bench claim or MAU figure.

**What actually breaks:**
- [Issue #958](https://github.com/ruvnet/claude-flow/issues/958): "Still can't figure out how to get v3 to actually perform work." User tried CLI, MCP server, shell scripts — all dead ends. Tasks sit in perpetual "pending" status.
- [Issue #984](https://github.com/ruvnet/claude-flow/issues/984): `claude-flow status` shows STOPPED even when daemon is running. The status command calls a `task_summary` tool that doesn't exist.
- [Issue #513](https://github.com/ruvnet/claude-flow/issues/513): "No output or response — tool appeared unresponsive or stuck" after running swarm commands.

**The UX problem:** V2 "made it pretty easy to get up and running" but V3 is a complete rebuild that broke the mental model. The npm package shows only 16 downstream dependents despite the star count.

**Assessment:** High star count relative to real usage evidence. Features byzantine consensus, swarm topologies, neural routing — none of which appear in any user success story. More ambitious prototype than production system.

---

### 3. claude_code_agent_farm — 663 stars

**What it is:** Python script that launches 20+ Claude Code agents in parallel tmux sessions. Three workflows: bug fixing, best practices sweeps, and cooperating agents with lock-based coordination.

**Refreshingly honest about limitations (from the README itself):**
- Coordination protocol depends entirely on Claude following instructions — "no enforcement mechanisms beyond file locking"
- Requires `--dangerously-skip-permissions`
- "34 technology stacks" = config templates and prompt variations, not integrations
- Stale lock detection only handles locks >2 hours old
- Context management is manual

**Assessment:** Does what it says, no more. The simplicity is the feature. Works for embarrassingly parallel tasks (each agent fixes a different bug). Breaks for tasks requiring real collaboration.

---

### 4. Claude Code Agent Teams (Anthropic, built-in)

**What it is:** Official experimental feature (shipped Feb 5, 2026). Lead agent spawns teammates in separate context windows, direct messaging, shared task list.

**Real productivity gains ([from users](https://news.ycombinator.com/item?id=46902368)):**
- QA swarm found 10 actionable issues in 3 minutes across 5 parallel agents
- FastAPI refactor (50K LOC) in 6 minutes with 4 agents vs 18-20 min sequentially
- Rails feature in ~8 hours vs estimated 3-4 days solo

**The hard problems:**
- **File conflict is the killer.** "Two agents editing same file leads to overwrites." Serializes parallel work, "kills the parallelism benefit."
- **Token cost is 2-4x subagents.** Single session ~200K tokens; 3-person team ~800K. 7x in plan mode.
- **No session resumption.** `/resume` doesn't restore in-process teammates.
- **Lead does work instead of coordinating.** Common failure mode.
- **Validation is the real bottleneck.** "Activity doesn't always translate to value" ([Addy Osmani](https://addyosmani.com/blog/claude-code-agent-teams/)).

**Anthropic's own warning:** "We've seen teams invest months building elaborate multi-agent architectures only to discover that improved prompting on a single agent achieved equivalent results."

**Assessment:** Honest about limitations. Best option for collaborative work today. But it's coordination infrastructure — no planning, no memory, no judgment.

---

### 5. Other Tools

**Gas Town (Steve Yegge):** "Kubernetes for AI agents." [DoltHub's experience](https://www.dolthub.com/blog/2026-01-15-a-day-in-gas-town/): $100 in tokens for 60 minutes. All 4 PRs failed. Auto-merged despite failing tests. Required force-push to main. "Genuine anxiety." Yegge himself runs 3 concurrent Claude Max accounts ($600/mo).

**Multiclaude (Dan Lorenc):** "singleplayer" auto-merge + team review modes. Better for long prompts → walk away. More suited for teams than solo.

**[Spec-driven dev](https://alexop.dev/posts/spec-driven-development-claude-code-in-action/) (Alex Opalic blog):** 14 tasks, 14 commits, 45 minutes. Closest to PRD-003's approach. But required human direction at every decision point, no persistent memory, single-session context.

---

## Synthesis: Why Nobody Has Solved This

### 1. Simple beats complex — consistently

Users who get the best results use the simplest approaches. [Boris Tane](https://boristane.com/blog/how-i-use-claude-code/) explicitly dismisses "ralph loops, MCPs, gas towns" and uses a disciplined research-plan-execute pipeline in a single session. Calls multi-agent results "a mess that completely falls apart for anything non-trivial."

Anthropic's own research team "consistently demonstrate they themselves use one agent, and just tune the harness around it." Multiple agents "consume context, which leads to worse performance."

### 2. Coordination overhead is the hidden tax

| Approach | Token cost vs. single session |
|----------|------------------------------|
| Subagents (within session) | ~2x |
| Agent Teams (3 agents) | ~4x |
| Agent Teams (plan mode) | ~7x |
| Gas Town (60 min) | ~10x |
| Multi-agent generally | 3-10x (per Anthropic) |

Sweet spot: 3-5 teammates on genuinely file-disjoint, parallelizable work. Beyond that, diminishing returns.

### 3. Complex orchestration patterns are marketing, not engineering

**What appears in READMEs:** Byzantine fault tolerance, consensus voting, swarm intelligence, neural routing, self-learning optimization.

**What appears in user success stories:** File locks, shared task lists, git worktrees, CLAUDE.md files.

Zero user reports of successfully using consensus mechanisms, swarm behavior, or debate structures for code quality. The one exception: adversarial debugging (agents trying to disprove each other's root cause analysis) — trivially implementable without a framework.

### 4. Everyone is solving the wrong problem

The existing tools are over-engineering the **execution layer** (more agents, fancier coordination) while ignoring the **planning layer** (what should the agent do, in what order, with what context).

This is backwards. The hard part isn't spawning 5 CC sessions. It's:
- Writing prompts that include the right architectural context
- Knowing which files each agent should touch (and which to avoid)
- Remembering what failed last time and adjusting
- Deciding when to retry vs. escalate vs. give up
- Scoping work so agents don't conflict

That's executive function for development. Same as VISION.md, different domain.

### 5. Nobody has the memory layer

Every tool starts every session from zero. OMC doesn't know your codebase. Claude-flow doesn't know your patterns. Agent Teams doesn't remember the last spec. The lessons in our MEMORY.md — "don't let two agents edit the same file," "Haiku needs verbatim code," "always grep after agent reports done" — are invisible to every other tool.

Memory is a compounding advantage. After 10 specs, the prompts are dramatically better than session 1. No competitor can replicate this without rebuilding the learning loop from scratch.

### 6. Spec-as-input is weirdly absent

Everyone starts with "tell the agent what to do." Nobody starts with "feed it a document that defines what done looks like." The spec-driven blog post came closest but still required human decomposition and human-written prompts.

---

## The OAuth Distinction

Anthropic's Feb 2026 ToS update bans extracting OAuth tokens and using them in third-party tools. This killed OpenCode, OpenClaw, and tools that proxied subscription credentials.

**What's banned:** Token extraction, credential proxying, third-party tools making API calls with subscription OAuth tokens.

**What's not banned:** Running the `claude` CLI binary as a subprocess. The daemon model spawns `claude -p "..."` — same as a shell script, CI pipeline, or desktop wrapper (Yume does exactly this). No tokens extracted, no credentials proxied.

The daemon model is clean. User's CC subscription authenticates normally through the official binary. Clarity never touches tokens.

---

## SWOT Analysis

### Strengths

| | |
|-|-|
| **Memory is a real moat** | No existing tool has persistent cross-session memory. Every OMC/claude-flow session starts from zero. Clarity remembers codebase patterns, past failures, what prompts work. This compounds. |
| **The SDLC graph already works** | 22+ specs implemented manually using this process. Codifying it is engineering, not research. |
| **Trust tiers are novel** | Nobody else has graduated autonomy for code orchestration. It's `--dangerously-skip-permissions` or nothing everywhere else. |
| **CLI subprocess model is clean** | No token extraction, no ToS issues. Daemon runs `claude -p`. Legal, simple, works with existing subscriptions. |
| **Spec-as-input is absent from market** | Nobody else starts with a structured document that defines done. |
| **Vision alignment** | PRD-003 isn't a pivot — it's Clarity's executive function vision applied to development. Same architecture (signals → judgment → action), different domain. |

### Weaknesses

| | |
|-|-|
| **Clarity isn't shipped yet** | Orchestration depends on PRD-001/002 infrastructure (memory, notifications, feedback loops). Those are in progress, not done. |
| **Single-founder knowledge bottleneck** | The SDLC graph lives in one person's head + MEMORY.md. Not yet externalized in a generalizable way. |
| **Codebase-specific prompts** | Prompts that work for this repo (architecture principles, hooks, naming conventions) won't transfer to a random Next.js app without adaptation. |
| **N=1 validation** | Every insight about "what works" comes from one codebase, one developer, one workflow. |

### Opportunities

| | |
|-|-|
| **The UX flip** | "Agent prompts you for confirmation" instead of "you prompt the agent." Nobody is selling this. Everyone is selling better ways to prompt. |
| **Engineers don't know they need specs** | Showing that spec → automated implementation is 10x faster than ad-hoc prompting creates a market. Phase 3a is the conversion tool. |
| **Validated demand, failed execution** | 14K stars on claude-flow, 7.3K on OMC — people want this. They bounce off complexity. "It just works" is wide open. |
| **Phase 3a needs no daemon** | Clarity reads spec, generates plan + prompts, user copies into CC manually. Valuable standalone, validates model before building daemon. |
| **Anthropic is a tailwind** | Every CC feature (Agent Teams, hooks, skills, headless CLI) makes the daemon simpler. |
| **Domain generalization** | If this works for code, it works for any structured workflow — legal docs, content pipelines, research synthesis. |

### Threats

| | |
|-|-|
| **Anthropic builds it natively** | Agent Teams is step 1. If they add memory + spec parsing + trust tiers, daemon is redundant. Mitigant: they build for all devs; Clarity builds for individual workflow. |
| **OMC adds memory** | 7.3K stars, active dev. If they bolt on persistent context, they're close. Mitigant: memory is architectural, not a feature flag — hard to retrofit. |
| **Market timing** | "Engineers who write specs + use CC" is small today. If the market takes 2 years to mature, runway matters. |
| **Quality ceiling** | Gas Town lesson: orchestrating bad output faster = more bad output. If CC reliability on complex tasks doesn't improve, human intervention remains required on most specs. |

---

## Customer Segments

### Segment 1: Solo founders / indie devs

- **Pain:** "I spend 60% of my day babysitting Claude Code instead of making product decisions"
- **Need:** Walk away, come back to a PR
- **Willingness to pay:** High (time is the constraint, not money)
- **Size:** Small but growing fast — every dev using CC Max is a candidate
- **PRD-003 fit:** Perfect. Primary design target.

### Segment 2: Small team leads (2-5 devs)

- **Pain:** "I write specs and assign work to junior devs who take 3 days on a 4-hour task"
- **Need:** Spec → PR with quality equivalent to a mid-level dev
- **Willingness to pay:** Very high (replacing contractor hours at $50-150/hr)
- **Size:** Medium — every startup CTO
- **PRD-003 fit:** Strong, but needs multi-user support and shared memory

### Segment 3: Developers who don't write specs (yet)

- **Pain:** "I spend hours prompting Claude Code and it still goes in circles"
- **Need:** They don't know they need specs. They need to discover that structured input → reliable output.
- **Willingness to pay:** Medium (once converted)
- **Size:** Largest segment by far — most CC users
- **PRD-003 fit:** Phase 3a is the conversion tool. "Describe what you want, I'll write the spec, you approve, I'll generate the prompts." The spec becomes invisible infrastructure.

### Segment 4: Agencies / dev shops

- **Pain:** "We have 20 projects and can't hire fast enough"
- **Need:** Multiply developer output across client projects
- **Willingness to pay:** Very high (billable hours math)
- **Size:** Large market, needs reliability guarantees
- **PRD-003 fit:** Phase 3c+ — needs proven track record first

---

## Key Pain Points Across All Segments

| Pain Point | Who feels it | Current "solution" | PRD-003 answer |
|-----------|-------------|-------------------|---------------|
| Writing the same prompt patterns over and over | Every CC user | Copy-paste from notes, CLAUDE.md | Prompt generator with memory — learns what works |
| Agent goes in circles, kill and restart | Every CC user | Manual monitoring, tmux | Progress monitor + decision engine: detect loops, adjust, retry |
| Multi-agent file conflicts | Team/parallel users | Manual coordination, file locks | Task planner prevents conflicts by design — file-disjoint assignment |
| Can't walk away — needs me every 10 minutes | Power users | Stay at keyboard | Trust tiers: escalate only on genuine blockers |
| Setup is brutal, gave up after 30 minutes | OMC/claude-flow users | Don't use orchestration | Daemon install, point at repo, done |
| No visibility into cost or progress | All agent users | Stare at terminal, check billing later | Progress notifications via Telegram, token tracking per task |
| Output quality is inconsistent | All agent users | Manual review of everything | Validation node: tests, lint, AC matching. Bad output caught before you see it. |

---

## The Opportunity in One Sentence

Everyone is building better ways to run Claude Code. Nobody is building the thing that knows *what to tell it to do.*

That's executive function for development. Same as the vision, different domain.

---

## Sources

- [OMC stress test: 15 bugs in v3.9.5](https://github.com/Yeachan-Heo/oh-my-claudecode/issues/301)
- [claude-flow "can't perform work" issue](https://github.com/ruvnet/claude-flow/issues/958)
- [claude-flow status bug](https://github.com/ruvnet/claude-flow/issues/984)
- [DoltHub's Gas Town experience](https://www.dolthub.com/blog/2026-01-15-a-day-in-gas-town/)
- [Spec-driven development with Claude Code](https://alexop.dev/posts/spec-driven-development-claude-code-in-action/)
- [Jeongil: AI coding agent ecosystem comparison](https://jeongil.dev/en/blog/trends/claude-code-agent-teams/)
- [Boris Tane: How I use Claude Code](https://boristane.com/blog/how-i-use-claude-code/)
- [Addy Osmani: Agent Teams guide](https://addyosmani.com/blog/claude-code-agent-teams/)
- [Anthropic: Building multi-agent systems](https://claude.com/blog/building-multi-agent-systems-when-and-how-to-use-them)
- [Anthropic: Legal and compliance](https://code.claude.com/docs/en/legal-and-compliance)
- [The Register: Anthropic clarifies third-party ban](https://www.theregister.com/2026/02/20/anthropic_clarifies_ban_third_party_claude_access)
- [Autonomee: Claude Code ToS explained](https://autonomee.ai/blog/claude-code-terms-of-service-explained/)
- [HN: Agent Teams discussion](https://news.ycombinator.com/item?id=46902368)
- [HN: Subscription auth ban discussion](https://news.ycombinator.com/item?id=47069299)
