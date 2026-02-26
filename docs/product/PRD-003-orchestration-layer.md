# PRD-003: The Orchestration Layer

> **Status:** Draft v1
> **Author:** Tim + Claude (Product)
> **Created:** 2026-02-24
> **Vision Reference:** `docs/product/VISION.md`
> **Depends On:** PRD-001 (foundation), PRD-002 (signal sources)

---

## Summary

Claude Code is the most capable coding agent in existence. It can read files, edit code, run tests, search the web, spawn sub-agents, and manage complex multi-file changes. What it can't do: remember what happened last time, coordinate multiple sessions, decide what to work on next, know when to stop, or tell you when it's done.

Clarity can do all of those things. It has persistent memory, trust tiers, notification channels, feedback loops, and executive function. What it can't do: write code.

PRD-003 puts them together. Clarity becomes the brain. Claude Code becomes the hands. The user walks away from the computer and comes back to a dev server running the feature they described that morning.

## The Problem

Today, using Claude Code for anything beyond a single-shot task requires constant human orchestration:

1. **You break down the work.** Read the spec, identify the functional units, decide which files to touch, figure out the order.
2. **You write the prompts.** Each Claude Code session needs context about what to do, what patterns to follow, what to avoid.
3. **You manage the sessions.** Spawn agents, watch for idle states, check if they're stuck, kill and respawn when they loop.
4. **You coordinate between agents.** Agent A is editing a file that Agent B needs. Agent A finished but missed a test. Agent B's branch conflicts with Agent C's.
5. **You validate the results.** Run tests, check lint, review the diff, verify it matches the spec.
6. **You handle deviations.** Agent took a wrong turn — fix it manually or restart with better instructions.

This is the "Ralph Wiggum loop" — an agent running in circles without supervision, burning tokens and producing nothing. The current solution is a human in the loop at every step. That works, but it doesn't scale and it defeats the purpose of having an agent.

The real problem isn't that Claude Code is bad at coding. It's excellent. The problem is that **nobody is managing it.** It needs a manager — one that remembers the project context, understands the architecture, knows what worked before, and can make decisions about when to escalate vs. when to retry.

That manager is Clarity.

## The Vision

```
User: "Implement SPEC-025"

Clarity:
  1. Reads the spec (already in its memory/context)
  2. Breaks it into functional units (FU-1 through FU-4)
  3. Identifies which agents are needed (database-dev, backend-dev, frontend-dev)
  4. Generates prompts for each agent, including:
     - Relevant architecture principles
     - Files to read/modify
     - Patterns to follow (from skills)
     - What NOT to do (from memory of past failures)
  5. Spawns Claude Code sessions via Agent SDK
  6. Monitors progress:
     - Did the agent commit?
     - Did tests pass?
     - Is it stuck in a loop?
     - Did it deviate from the spec?
  7. Coordinates between sessions:
     - Agent A finished FU-1, unblocks FU-2
     - Agent B and C can run in parallel on FU-2 and FU-3
  8. Handles failures:
     - Agent stuck → kill, adjust prompt, respawn
     - Tests failing → diagnose, provide fix guidance
     - Spec deviation → pause, notify user
  9. When all FUs pass:
     - Runs full test suite
     - Creates PR with proper description
     - Notifies user: "Dev server is up with SPEC-025. Ready for UAT."
```

The user's involvement: approve the approach at step 2, handle any escalations at step 8, and test the result at step 9.

## What Already Exists

This project has already built — painfully, manually — every piece of this system:

| Component | Current Form | PRD-003 Form |
|-----------|-------------|-------------|
| Spec → FU breakdown | Human reads spec, writes task list | Clarity reads spec, generates tasks |
| Agent prompts | Human writes `.claude/agents/*.md` | Clarity generates per-task prompts from spec + architecture + memory |
| Session management | Human spawns teams, manages worktrees | Clarity spawns via Agent SDK, manages sessions programmatically |
| Progress monitoring | Human checks `git log`, runs tests, reads output | Clarity monitors via hooks + git status + test results |
| Coordination | Human tracks who's working on what, resolves conflicts | Clarity manages task dependencies, branch strategy, merge order |
| Failure handling | Human kills stuck agents, adjusts prompts, respawns | Clarity detects loops, adjusts strategy, respawns with better context |
| Validation | Human runs tests, does UAT | Clarity runs test suite, deploys to dev, notifies user for UAT |
| Memory | MEMORY.md, skills, gotchas files | All of this, plus Clarity's persistent memory of what worked and what didn't |

The SDLC workflow (`.claude/skills/sdlc-workflow/`) already documents the process. The agent definitions (`.claude/agents/`) already define the roles. The hooks (`validate-patterns.sh`, `scope-enforcement.sh`, `task-completed-gate.sh`) already enforce quality gates. Clarity just needs to drive the process instead of a human.

## Architecture: The Daemon Model

### Why a Daemon

The naive approach: Clarity runs Claude Code sessions server-side, pays for tokens, manages everything in the cloud. This is the OpenClaw model — and it's why their users burn $100+ in API credits without realizing it.

We flip it. **The user brings their own Claude Code subscription.** Clarity's job is orchestration — planning, prompts, coordination, monitoring. Execution happens locally on the user's machine (or their own cloud VM). Code never leaves their environment. Clarity never sees their source code.

**Critical distinction: the daemon runs Claude Code, not a third-party API client.** Anthropic's Feb 2026 ToS update bans extracting OAuth tokens and using them in third-party tools. But the daemon doesn't touch tokens — it spawns the `claude` CLI as a subprocess, the same way a user would invoke it from the terminal. This is no different from Yume (a desktop UI that spawns CC as a subprocess), or a shell script that runs `claude -p "..."`. The user's CC subscription authenticates normally through the official binary. The daemon is an orchestration layer over the product, not a replacement for it.

This is the model:

```
┌──────────────────────────────────────────────┐
│               USER'S MACHINE                  │
│                                               │
│  ┌─────────────────────────────────────────┐  │
│  │           Clarity Daemon                 │  │
│  │  - Receives orchestration instructions   │  │
│  │  - Spawns Claude Code sessions locally   │  │
│  │  - Reports progress back to Clarity      │  │
│  │  - Uses user's Claude Code subscription  │  │
│  └──────────┬──────────────┬───────────────┘  │
│             │              │                   │
│     ┌───────▼──────┐  ┌───▼───────────┐      │
│     │ Claude Code  │  │ Claude Code   │      │
│     │ Session A    │  │ Session B     │      │
│     │ (DB work)    │  │ (Backend)     │      │
│     └──────────────┘  └───────────────┘      │
│             │              │                   │
│     ┌───────▼──────────────▼───────────┐      │
│     │         Local Git Repo           │      │
│     └──────────────────────────────────┘      │
│                                               │
└──────────────────┬───────────────────────────┘
                   │ Progress reports,
                   │ escalations, results
                   │ (structured data only —
                   │ no source code)
                   ▼
┌──────────────────────────────────────────────┐
│             CLARITY CLOUD                     │
│                                               │
│  Orchestration engine:                        │
│  - Spec reader, task planner, prompt gen      │
│  - Decision engine                            │
│  - Memory (what worked, what didn't)          │
│  - User notifications (chat, Telegram)        │
│                                               │
└──────────────────────────────────────────────┘
```

### Why This Works

**For users:**
- Use their existing Claude Max / API subscription — no double-billing
- Code stays on their machine — no trust issues
- Install a daemon, point it at a repo, done

**For us:**
- Zero execution cost per user — we only run the orchestration LLM calls (planning, decisions, prompt generation)
- No infrastructure for running user code
- No liability for what agents do to user codebases

**For Anthropic:**
- More Claude Code usage — we're driving subscriptions to their product
- No ToS issue — daemon spawns the CC binary as a subprocess, doesn't extract OAuth tokens or proxy credentials. Same as any shell script, CI pipeline, or desktop wrapper that runs `claude -p`

### The Daemon

A lightweight local process (Python or Node) that:

1. **Authenticates** with Clarity cloud (user's Clarity account)
2. **Registers** its capabilities (which repo, available tools, Claude Code version)
3. **Receives orchestration instructions** via WebSocket or polling:
   - "Spawn a Claude Code session with this prompt in this worktree"
   - "Kill session X, it's looping"
   - "Resume session Y with this additional context"
4. **Executes locally** using Claude Agent SDK or headless `claude -p`
5. **Reports back** structured progress:
   - Files modified, commits made, test results
   - Token consumption per session
   - Agent errors, stuck states, completion
6. **Never sends source code** — only metadata and structured results

Distribution: `pip install clarity-daemon` or `brew install clarity-daemon`. First-run wizard links to Clarity account and validates Claude Code access.

### The Execution Layer

The daemon spawns the Claude Code CLI as a subprocess — using the user's own installation, their own authentication, their own subscription. No token extraction. No credential proxying. Just running a binary.

```bash
# This is all the daemon does at the execution layer.
# The user's own `claude` binary, authenticated normally.
claude -p "$CLARITY_GENERATED_PROMPT" \
  --output-format stream-json \
  --allowedTools Read,Edit,Write,Bash,Glob,Grep \
  --cwd /path/to/worktree
```

The daemon reads the JSON stream for progress monitoring (file edits, test runs, errors, completion). Hooks (CLAUDE.md-configured, or `settings.json`) report structured events back to Clarity cloud.

**Why CLI-first, not Agent SDK:**
- Works today with any Claude Code version — no additional dependencies
- Uses the user's existing auth — no token management, no ToS ambiguity
- Agent SDK is an upgrade path for finer control (resume sessions, subagents), but it currently requires API key auth which means pay-per-token instead of subscription. When/if Anthropic enables SDK with subscription auth, we switch. Until then, headless CLI is strictly better for users.

```python
# Future: Agent SDK path (when subscription auth is supported)
from claude_agent_sdk import query, ClaudeAgentOptions

async for message in query(
    prompt=clarity_generated_prompt,
    options=ClaudeAgentOptions(
        allowed_tools=["Read", "Edit", "Write", "Bash", "Glob", "Grep"],
        cwd="/path/to/worktree",
        hooks={
            "PostToolUse": [progress_reporter],
            "Stop": [completion_reporter],
        },
    ),
):
    daemon.report_progress(message)
```

### The SDLC Graph

The orchestration layer models software development as a directed graph. Each node is a well-defined stage with clear inputs, outputs, and transition rules. This is the same process we've been running manually — codified into something that "just works OOTB."

```
                    ┌──────────┐
                    │  SPEC    │  Input: approved spec document
                    │  INGEST  │  Output: structured spec data
                    └────┬─────┘
                         │
                    ┌────▼─────┐
                    │ DECOMPOSE│  Input: structured spec
                    │          │  Output: ordered task list with
                    └────┬─────┘  dependencies, agent assignments
                         │
              ┌──────────┼──────────┐
              │          │          │  (parallel where deps allow)
         ┌────▼───┐ ┌───▼────┐ ┌──▼─────┐
         │GENERATE│ │GENERATE│ │GENERATE │  Input: task + skills + memory
         │PROMPT A│ │PROMPT B│ │PROMPT C │  Output: complete agent prompt
         └────┬───┘ └───┬────┘ └──┬─────┘
              │         │         │
         ┌────▼───┐ ┌───▼────┐ ┌──▼─────┐
         │EXECUTE │ │EXECUTE │ │EXECUTE  │  Daemon spawns CC sessions
         │        │ │        │ │         │  Hooks report progress
         └────┬───┘ └───┬────┘ └──┬─────┘
              │         │         │
         ┌────▼───┐ ┌───▼────┐ ┌──▼─────┐
         │VALIDATE│ │VALIDATE│ │VALIDATE │  Tests pass? Lint clean?
         │        │ │        │ │         │  Matches ACs?
         └────┬───┘ └───┬────┘ └──┬─────┘
              │         │         │
              │    ┌────▼─────┐   │
              │    │ RETRY?   │   │  Failure → adjust prompt → re-execute
              │    │          │   │  Stuck → kill → escalate
              │    └────┬─────┘   │  Deviation → pause → notify user
              │         │         │
              └────┬────┘─────────┘
                   │
              ┌────▼─────┐
              │INTEGRATE │  Merge branches, run full suite,
              │          │  resolve conflicts
              └────┬─────┘
                   │
              ┌────▼─────┐
              │ DELIVER  │  Create PR, deploy to dev,
              │          │  notify user: "ready for UAT"
              └──────────┘
```

**Each node is simple.** The complexity is in the transitions and the memory that informs them — not in the individual stages. A simplified version of this repo's prompts powers each node. Users don't need to understand SDLC methodology or prompt engineering. They write a spec (or tell Clarity what they want and it writes the spec), approve the plan, and walk away.

**The graph is the product.** Everything else — the daemon, the Agent SDK, the prompt generator — is plumbing. The graph is what makes it predictable and reliable instead of the "Ralph Wiggum loop" of letting an agent free-run.

#### Node Definitions

| Node | Input | Output | Failure Mode | Recovery |
|------|-------|--------|-------------|----------|
| Spec Ingest | Markdown spec file | Structured data: ACs, FUs, files, deps | Parse failure | Ask user to clarify spec format |
| Decompose | Structured spec | Task list with deps + agent assignments | Ambiguous scope | Ask user to clarify; use memory of similar specs |
| Generate Prompt | Task + architecture + memory | Complete CC session prompt | N/A (deterministic) | N/A |
| Execute | Prompt + worktree | Code changes + commits | Agent loops, errors, goes off-spec | Retry (below) |
| Validate | Code changes | Pass/fail + details | Test failure, lint error | Feed errors to retry |
| Retry | Failed task + error context | Adjusted prompt → re-execute | Retry budget exceeded (default: 2) | Escalate to user |
| Integrate | All task branches | Merged branch, full test suite green | Merge conflict | Sequential merge with conflict resolution prompt |
| Deliver | Green branch | PR + dev deployment + user notification | Deploy failure | Notify user, provide PR for manual deploy |

#### What Makes This Different from "Just Run Claude Code"

People have duct-taped this together with hooks and scripts. Power users make it work. But it's fragile because:

1. **No memory between sessions.** Every session starts from zero. Clarity remembers what worked.
2. **No coordination.** Two sessions editing the same file = conflict. Clarity prevents this.
3. **No judgment on failures.** Agent fails → human decides what to do. Clarity has a decision engine.
4. **No progress visibility.** You stare at terminal output. Clarity sends you a Telegram message.
5. **No trust model.** It's all-or-nothing (`--dangerously-skip-permissions`). Clarity graduates trust.

The graph makes it a product instead of a hack.

### Clarity's New Components

**1. Spec Reader**

Parses a SPEC markdown file into structured data: acceptance criteria, functional units, files to create/modify, dependencies, testing requirements. This is mechanical — the SPECs already follow a consistent format.

**2. Task Planner**

Takes structured spec data and produces an execution plan:
- Which FUs can run in parallel vs. must be sequential
- What agent type each FU needs (database-dev, backend-dev, frontend-dev)
- Pre-allocated branch names and worktree paths
- Migration prefix allocation (avoid collisions)

The planner uses Clarity's memory of past executions: "Last time we ran backend and frontend in parallel, they both edited `main.py` and conflicted. Run them sequentially this time."

**3. Prompt Generator**

The most critical component. For each task, generates a complete Claude Code prompt that includes:
- The specific FU's acceptance criteria
- Relevant architecture principles (from skills)
- Files to read first (from spec scope tables)
- Patterns to follow (from skills + memory)
- Anti-patterns to avoid (from memory of past failures)
- Git coordination rules (branch name, commit format, what NOT to touch)
- Test requirements (which tests to write, which to run)

This is where memory is the superpower. After 10 spec implementations, Clarity knows:
- "Haiku agents need exact code in prompts, not descriptions"
- "Always grep for the old pattern after agent reports done"
- "Don't let two agents edit the same file"
- "Run pytest collection check before declaring done"
- "validate-patterns.sh catches test fixtures — use approved naming"

These lessons, currently in MEMORY.md, become executable knowledge.

**4. Session Manager**

Manages the lifecycle of Claude Code sessions:
- Spawns sessions via Agent SDK with generated prompts
- Tracks session state: running, completed, failed, stuck
- Manages worktrees (create, cleanup)
- Handles sequential and parallel execution
- Implements retry logic with adjusted prompts

**5. Progress Monitor**

Watches agent sessions via hooks and git:
- `PostToolUse` hooks report file edits, bash commands, test runs
- Periodic git status checks: has the agent committed? What files changed?
- Token consumption tracking (detect runaway loops)
- Test result parsing (did the tests pass? which failed? why?)
- Stuck detection: agent making the same edit repeatedly, or no file changes for N minutes

**6. Decision Engine**

When something goes wrong, decides what to do:

| Situation | Decision |
|-----------|----------|
| Tests pass, agent completed | Mark task done, unblock next |
| Tests fail, failure is obvious | Provide fix guidance, resume session |
| Agent stuck in loop | Kill, adjust prompt, respawn |
| Agent deviated from spec | Pause, notify user with diff |
| Agent made unexpected changes | Revert, notify user |
| Conflict between agents | Queue the blocked agent, retry after merge |
| All FUs complete | Run full test suite, create PR |
| User attention needed | Send `notify` notification with context |

### What the User Sees

**On their phone (Telegram):**
```
Clarity: Starting implementation of SPEC-025.
4 functional units:
  FU-1: Migration + notification types (database-dev)
  FU-2: Approval flow unification (backend-dev)
  FU-3: Inline notifications (frontend-dev)
  FU-4: Cleanup (frontend-dev)

Running FU-1 now. I'll notify you when there's something to look at.

[2 hours later]

Clarity: SPEC-025 is implemented. All 20 tests pass.
PR: github.com/user/repo/pull/92
Dev server is running at localhost:3001 — ready for UAT.

FU-1: ✅ Migration + types (12 min)
FU-2: ✅ Approval flow (28 min)
FU-3: ✅ Inline notifications (45 min)
FU-4: ✅ Cleanup (8 min)

One thing to note: FU-3 required a retry — the first attempt put
notification components in the wrong directory. I fixed the prompt
and it got it right on the second pass.

[Approve PR] [View Diff] [Open Dev Server]
```

**On a deviation:**
```
Clarity: FU-2 hit a problem. The backend-dev agent wants to
modify tool_wrapper.py but the change doesn't match AC-07.

The spec says: "softer message — agent continues"
The agent wrote: "STOP: Action requires approval" (same as before)

Options:
[Let me fix the prompt and retry]
[Show me the diff]
[I'll handle this manually]
```

## Trust Model

This is where Clarity's existing trust architecture becomes critical. The orchestration layer has its own trust tiers:

**Inform (default):**
- Clarity shows you the execution plan before starting
- You approve the approach
- Clarity notifies you at completion
- You review the PR

**Recommend (earned):**
- Clarity proposes the plan and starts immediately (you can interrupt)
- Clarity handles retries without asking
- Clarity creates the PR
- You just do UAT

**Act (fully earned):**
- Clarity takes a spec and ships it
- Handles all retries, coordination, PR creation
- Deploys to staging
- Only notifies you when UAT is ready or there's a genuine blocker

Trust graduation for the orchestration layer follows the same pattern as personal use: demonstrated track record, explicit user approval, per-domain. A user might trust Clarity to auto-ship backend specs but want to review all frontend PRs.

## What This Is NOT

- **Not a CI/CD system.** This doesn't replace GitHub Actions. It runs before CI — Clarity orchestrates the development, CI validates the result.
- **Not a project management tool.** Clarity doesn't manage sprints or track velocity. It takes a spec and ships it.
- **Not a replacement for human judgment.** The user writes the specs, makes design decisions, and does UAT. Clarity handles the execution gap between "approved spec" and "PR ready for review."
- **Not magic.** Claude Code agents will still fail, hallucinate, and need retries. The value is that Clarity handles the retries intelligently instead of a human watching terminal output.
- **Not general-purpose.** This is scoped to the Clarity project's own development initially. Generalizing to arbitrary codebases is a future consideration.

## Technical Approach

### Cloud Components (Clarity)

| Component | Implementation | Location |
|-----------|---------------|----------|
| Spec Reader | Python parser for SPEC markdown format | `chatServer/services/orchestration/spec_reader.py` |
| Task Planner | LLM-assisted planning with memory context | `chatServer/services/orchestration/task_planner.py` |
| Prompt Generator | Template + LLM synthesis from skills/memory | `chatServer/services/orchestration/prompt_generator.py` |
| Decision Engine | Rule-based + LLM-assisted decision making | `chatServer/services/orchestration/decision_engine.py` |
| Daemon Protocol | WebSocket API for daemon ↔ cloud communication | `chatServer/services/orchestration/daemon_protocol.py` |

### Local Components (Daemon)

| Component | Implementation | Distribution |
|-----------|---------------|-------------|
| Daemon process | Long-running service, receives instructions | `pip install clarity-daemon` / `brew install clarity-daemon` |
| Session runner | Spawns CC via Agent SDK or headless CLI | Bundled with daemon |
| Progress reporter | Hooks into CC, sends structured updates | Bundled with daemon |
| Worktree manager | Creates/cleans git worktrees for parallel agents | Bundled with daemon |
| Token tracker | Monitors per-session spend, enforces budgets | Bundled with daemon |

### Dependencies

- **Claude Code** (user's own installation + subscription) — the execution engine. Daemon spawns `claude` as subprocess.
- **PRD-001** — personality and memory (Clarity needs to remember what works)
- **PRD-002** — notification infrastructure (Clarity notifies the user via chat/Telegram)
- **SPEC-025** — unified notifications (inline progress updates in chat)
- **Existing SDLC infrastructure** — skills, agents, hooks, validation scripts (shipped as simplified templates with the daemon)
- **Claude Agent SDK** (future, optional) — upgrade path for finer session control when subscription auth is supported

### Daemon ↔ Cloud Protocol

The protocol is deliberately simple. Clarity cloud sends **instructions**; the daemon sends **reports**. No source code crosses the wire.

**Cloud → Daemon (instructions):**
```json
{"type": "spawn_session", "task_id": "fu-1", "prompt": "...", "worktree": "spec-025/fu-1", "allowed_tools": ["Read","Edit","Write","Bash"], "token_budget": 50000}
{"type": "kill_session", "task_id": "fu-1", "reason": "stuck_loop"}
{"type": "resume_session", "task_id": "fu-1", "additional_context": "..."}
```

**Daemon → Cloud (reports):**
```json
{"type": "progress", "task_id": "fu-1", "files_modified": ["src/foo.py"], "tokens_used": 12400}
{"type": "session_complete", "task_id": "fu-1", "commit": "abc123", "tests_passed": true, "test_summary": "14 passed"}
{"type": "session_failed", "task_id": "fu-1", "error": "test_failure", "details": "test_notification_type_validation FAILED: AssertionError"}
{"type": "session_stuck", "task_id": "fu-1", "reason": "no_file_changes_5min", "tokens_used": 28000}
```

## Open Questions

1. **Daemon distribution.** `pip install` vs. native binary vs. Docker container? Pip is easiest for Python devs but adds a dependency. A standalone binary (PyInstaller or similar) reaches more users. Docker is heaviest but most isolated. Start with pip, revisit.

2. **First-run experience.** The daemon needs: Clarity account linked, Claude Code available on PATH, repo pointed at. How smooth can we make this? `clarity-daemon init` should handle it in under 2 minutes.

3. **Subscription headroom.** Claude Code's own Agent Teams already spawns 5+ parallel sessions as a first-party feature. Max plans have significant weekly limits — heavy multi-session use barely scratches them. The daemon's usage pattern is indistinguishable from a user running Agent Teams. Not a real concern today, but worth monitoring if Anthropic changes pricing tiers.

4. **Concurrency limits.** How many CC sessions can run in parallel? API rate limits, filesystem contention, and git merge complexity all increase with parallelism. Start with 2-3 concurrent sessions and tune.

5. **Offline tolerance.** What happens if the daemon loses connection to Clarity cloud mid-execution? Sessions should continue (they're local). Daemon queues reports and syncs when reconnected. Clarity shows "daemon offline" status.

6. **Dogfooding.** Should the first version of the orchestration layer be built using the orchestration layer? (Bootstrapping problem.) Probably not — build it manually first, then use it to build the next thing.

7. **Security.** CC sessions with `bypassPermissions` have full filesystem access. The `claude-sandbox` user pattern already exists for isolation. Daemon should default to sandbox mode.

8. **Failure budget.** How many retries before escalating to user? 2? 3? Should depend on failure type (test failure = retry with error context, spec deviation = escalate immediately).

9. **Simplified prompt templates.** The current repo's agent prompts are complex and project-specific. The daemon ships with simplified, generalized templates. How much project-specific context can Clarity infer vs. what does the user need to configure? Memory helps here — after a few runs, Clarity knows the project's patterns.

10. **Multi-repo support.** One daemon per repo, or one daemon managing multiple repos? Start with single repo, but the protocol should support it.

## Phased Rollout

### Phase 3a: Spec Reader + Task Planner (Cloud Only, No Daemon)

Clarity reads a spec and produces an execution plan with generated prompts — as copyable text. The user still spawns Claude Code sessions manually, but Clarity writes the prompts and tracks progress via conversation. This is "Clarity as the project manager, human as the executor."

No daemon needed. Ships as a Clarity feature. Tests the spec reader and prompt generator with real users before building the daemon.

**Value:** Better prompts (from memory), consistent task breakdown, progress tracking. Validates the SDLC graph model.

### Phase 3b: The Daemon (Local Execution)

Ship `clarity-daemon`. User installs it, links their account, points it at a repo. Clarity sends orchestration instructions, daemon executes locally with user's Claude Code subscription. Progress reports flow back to Clarity cloud.

Simple version: daemon runs one session at a time, sequentially through the task list. No parallelism yet. User watches progress in Clarity chat or Telegram.

**Value:** Walk-away execution. User approves the plan, daemon runs it, Clarity pings when done.

### Phase 3c: Intelligent Orchestration

Parallel session management. Full decision engine: spec deviation detection, adaptive prompt refinement from memory, automatic PR creation. Daemon manages worktrees for concurrent agents.

**Value:** Spec → PR with minimal human involvement. 2-4 agents working in parallel.

### Phase 3d: Self-Improvement

Clarity uses the orchestration layer to improve itself — implementing its own specs, building its own features, testing its own changes. The daemon runs against the Clarity repo.

**Value:** Recursive improvement. The "bootstrapping moment."

## Success Criteria

| Metric | Phase 3a | Phase 3b | Phase 3c |
|--------|----------|----------|----------|
| Time from spec to PR | Hours (human driving) | Hours (Clarity driving) | Under 2 hours for a 3-FU spec |
| Human involvement per spec | Break down + prompt + monitor + validate | Approve plan + UAT | UAT only |
| Retry success rate | N/A (human retries) | 50% auto-resolved | 80% auto-resolved |
| Specs shipped per day | 1-2 (human bottleneck) | 2-4 | 4+ |
| Agent prompt quality | Manual + memory | Clarity-generated, memory-informed | Self-improving from feedback |

## Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Claude Code CLI/SDK changes break daemon | Daemon stops working until updated | Use `--output-format stream-json` (stable interface); test against CC releases; version-pin daemon ↔ CC compatibility matrix |
| Anthropic restricts programmatic CLI usage | Daemon model breaks entirely | Current ToS allows running the CLI binary programmatically (hooks, CI, scripts are all blessed). But Anthropic reserves the right to change. Monitor policy. Open-source daemon reduces lock-in risk. |
| Anthropic tightens subscription limits | Throttled execution | Current Max plans have significant headroom — multi-session Agent Teams usage barely dents weekly limits. Monitor; API-key fallback exists if needed. |
| Users can't install daemon (corp firewalls, IT policies) | Limits addressable market | Phase 3a works without daemon; web-based prompt copy is always available |
| Daemon security (runs with file access) | Malicious prompt injection from cloud | Daemon validates instructions against allowlist; sandbox mode by default; open-source daemon so users can audit |
| Overselling autonomy before it's reliable | Users lose trust when things fail | Phase 3a is explicitly human-in-loop; earn daemon trust gradually like personal trust tiers |
| Competition (OMC, claude-flow, Anthropic's Agent Teams) | Someone ships the brain before we do | Our moat is memory + judgment, not plumbing. OMC has 7.3K stars but no persistent memory, no spec reader, no trust model. Agent Teams is coordination without intelligence. Ship 3a fast to validate. |

---

*This PRD describes the long-term product direction. Implementation will be phased and informed by learnings from each phase. The first step is Phase 3a — giving Clarity the ability to read specs and generate execution plans, while the human still drives. No daemon needed for Phase 3a. The daemon ships in Phase 3b once the orchestration model is validated.*
