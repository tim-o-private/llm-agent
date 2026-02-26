# SPEC-020: SDLC Autonomy Upgrade — CTO Mode

> **Status:** Done
> **Author:** Claude (Opus 4.6) + Tim
> **Created:** 2026-02-24
> **Updated:** 2026-02-24

## Goal

Restructure the SDLC agent system so the user operates as CTO/head of product rather than engineering team lead. Today the user writes specs, spawns agents, babysits stuck workers, and manually coordinates. After this spec, the user describes intent, approves a spec, and receives a reviewed PR — everything between is autonomous.

Three root problems this solves:
1. **Spec overhead** — Too much manual work before code starts
2. **Mandate creep** — Orchestrators do implementation work instead of delegating; agents stray outside their scope
3. **Attention drift** — After creating a team, the orchestrator loses focus on managing members and starts doing work itself

## Acceptance Criteria

- [ ] **AC-01:** The orchestrator agent definition explicitly forbids implementation work and includes model-tiering directives (spawn domain agents on sonnet/haiku, not opus) [S2, S5]
- [ ] **AC-02:** A shared `agent-protocols` skill exists containing blocker handling, git coordination, escalation, and stuck-agent procedures — extracted from the 4 redundant copies in domain agent definitions [F2, S7]
- [ ] **AC-03:** Domain agent definitions reference `agent-protocols` skill instead of duplicating shared sections; each is ≤60 lines [F2]
- [ ] **AC-04:** The spec-writer agent can be invoked with a one-sentence vision statement and autonomously produces a complete spec draft — including codebase research, auto-numbering, principle citations, and cross-domain contracts [S5]
- [ ] **AC-05:** The orchestrator includes an "attention loop" protocol: after spawning agents, it enters a monitoring cycle (check TaskList → check for messages → handle blockers → repeat) rather than doing ad-hoc work [S2]
- [ ] **AC-06:** The `prompt-reminder.sh` UserPromptSubmit hook is removed or replaced with a targeted hook that only fires for team-member agents (not the user's main session) [S3]
- [ ] **AC-07:** The sdlc-workflow skill documents single-branch/single-PR as the default strategy, with worktrees as the exception for explicitly parallel cross-domain specs [S7]
- [ ] **AC-08:** The orchestrator definition includes explicit model directives: `model: "sonnet"` for domain agents, `model: "haiku"` for simple/mechanical tasks, `model: "opus"` for orchestrator, reviewer, and spec-writer [S2]
- [ ] **AC-09:** Scope enforcement hook (`scope-enforcement.sh`) handles the case where an orchestrator/team-lead agent attempts to Write/Edit application code — blocks with a message directing it to delegate instead [S3, S6]
- [ ] **AC-10:** The orchestrator's "Rules" section includes: "If you find yourself about to use Write, Edit, or create a file — STOP. Delegate to a domain agent instead. Your job is to coordinate, not implement." [S2]
- [ ] **AC-11:** Each domain skill (backend-patterns, frontend-patterns, database-patterns, integration-deployment) includes a "Principles That Apply" section with the 4-5 relevant principles excerpted as a table — domain agents no longer need `architecture-principles` in Required Reading [F2, S4]
- [ ] **AC-12:** Agent-protocols skill includes a "Before Declaring Done" protocol requiring agents to re-read their task via `TaskGet` and verify all deliverables before marking complete [S1, S5]
- [ ] **AC-13:** The orchestrator's attention loop includes polling for GitHub PR review feedback (`gh pr view <number> --json reviews`) and routing blockers back to the domain agent [S2, S6]
- [ ] **AC-14:** The `claude-code-review.yml` workflow prompt instructs the reviewer to check only the incremental diff on `synchronize` events (follow-up pushes), not re-review the entire PR [S2, A14]

## Scope

### Files to Create

| File | Purpose |
|------|---------|
| `.claude/skills/agent-protocols/SKILL.md` | Shared protocols: blocker handling, git coordination, escalation, stuck procedures |

### Files to Modify

| File | Change |
|------|--------|
| `.claude/agents/orchestrator.md` | Add attention loop, model directives, stronger anti-implementation rules, remove boilerplate |
| `.claude/agents/spec-writer.md` | Add autonomous research workflow, auto-numbering, codebase analysis step |
| `.claude/agents/backend-dev.md` | Replace duplicated sections with `agent-protocols` skill reference, trim to ≤60 lines |
| `.claude/agents/frontend-dev.md` | Replace duplicated sections with `agent-protocols` skill reference, trim to ≤60 lines |
| `.claude/agents/database-dev.md` | Replace duplicated sections with `agent-protocols` skill reference, trim to ≤60 lines |
| `.claude/agents/deployment-dev.md` | Replace duplicated sections with `agent-protocols` skill reference, trim to ≤60 lines |
| `.claude/agents/reviewer.md` | Add model directive note (should run as opus) |
| `.claude/agents/uat-tester.md` | Replace duplicated sections with `agent-protocols` skill reference |
| `.claude/skills/sdlc-workflow/SKILL.md` | Update default branch strategy to single-branch/single-PR |
| `.claude/skills/sdlc-workflow/reference.md` | Update workflow to reflect single-PR default, model tiering |
| `.claude/hooks/scope-enforcement.sh` | Add orchestrator/team-lead Write/Edit blocking |
| `.claude/hooks/prompt-reminder.sh` | Remove or replace with team-member-only targeting |
| `.github/workflows/claude-code-review.yml` | Add incremental review logic for `synchronize` events |
| `.claude/skills/backend-patterns/SKILL.md` | Add "Principles That Apply" section (A1, A3, A5, A6, A8, A10) |
| `.claude/skills/frontend-patterns/SKILL.md` | Add "Principles That Apply" section (A4, A5, A7, A10) |
| `.claude/skills/database-patterns/SKILL.md` | Add "Principles That Apply" section (A3, A8, A9, A10) |
| `.claude/skills/integration-deployment/SKILL.md` | Add "Principles That Apply" section (A3, A11) |

### Out of Scope

- Automated PR merging (user wants PR-level approval control)
- Post-deploy smoke testing / monitoring integration
- Changes to CI/CD pipelines
- Changes to `validate-patterns.sh`, `task-completed-gate.sh`, or other existing hooks (except scope-enforcement and prompt-reminder)
- New agent types beyond what exists today
- Changes to architecture principles (S1-S7, A1-A14)

## Technical Approach

### 1. Extract Shared Agent Protocols (AC-02, AC-03)

The following sections are duplicated verbatim across 4+ agent files:
- "When Reviewer Finds a Blocker" (5 steps)
- "When You're Stuck" (4 steps)
- "Git Coordination" (6 rules)
- Common "Rules" items (never push to main, never force-push)

Create `.claude/skills/agent-protocols/SKILL.md` containing these. Each domain agent replaces its duplicated sections with:

```markdown
## Required Reading
1. `.claude/skills/agent-protocols/SKILL.md` — blocker handling, git coordination, escalation
```

This reduces each agent file from ~90 lines to ~60 lines, saving ~120 tokens per agent invocation.

### 2. Strengthen Orchestrator Focus (AC-01, AC-05, AC-08, AC-10)

The orchestrator's core failure mode is "attention drift" — it creates a team, spawns the first agent, then starts doing implementation work itself or loses track of agent progress.

**Attention Loop Protocol:**

After spawning agents, the orchestrator enters a structured monitoring loop:

```
WHILE tasks remain incomplete:
  1. TaskList — check status of all tasks
  2. For each in_progress task:
     - Has the agent sent a message? → Handle it (review request, blocker, question)
     - Has the agent gone idle with no message? → Check task status, send a nudge if needed
  3. For each completed task:
     - Verify commit exists on branch
     - If reviewer needed: spawn reviewer
     - If next task unblocked: spawn next agent
  4. For each blocked task:
     - Is the blocker resolved? → Unblock and spawn agent
  5. Report status to user at milestones (not every loop iteration)
```

**Model Directives:**

Add explicit guidance to the orchestrator:

```markdown
## Model Selection for Agents

When spawning agents via the Task tool, use the `model` parameter:
- **`model: "opus"`** — orchestrator (you), reviewer, spec-writer. These roles require
  dynamic reasoning, architectural judgment, and deep codebase understanding.
- **`model: "sonnet"`** — domain agents (database-dev, backend-dev, frontend-dev, deployment-dev).
  These roles execute well-scoped contracts with clear inputs and outputs.
- **`model: "haiku"`** — simple/mechanical tasks (file moves, config changes, boilerplate).
  Use when the contract is trivially specific and success is obvious.

The orchestrator runs on opus because it makes judgment calls — contract authoring,
parallelism decisions, blocker diagnosis, escalation timing. Sonnet can follow a
well-defined contract; opus writes the contract.
```

**Anti-Implementation Guard:**

Add to orchestrator's Rules section:
```markdown
- If you find yourself about to use Write, Edit, or create a file — STOP.
  Delegate to a domain agent instead. Your job is to coordinate, not implement.
- The only files you may create are task descriptions (via TaskCreate).
- If a task seems too small to spawn an agent for, it's either (a) part of a larger task
  that should go to an agent, or (b) not worth doing. Never "just quickly do it yourself."
```

### 3. Upgrade Spec-Writer for Autonomous Operation (AC-04)

Current spec-writer requires the user to provide structured input. Upgrade to accept a one-sentence vision:

```
User: "I want email digests to include task summaries"
→ spec-writer researches codebase (email_digest_service.py, task tools, schema)
→ spec-writer identifies affected files, dependencies, patterns
→ spec-writer produces complete SPEC-NNN draft
→ User approves or requests changes
```

New workflow additions:
1. **Auto-numbering** — Read `docs/sdlc/specs/`, find highest SPEC number, use next
2. **Codebase research** — Grep for related code, read schema, read existing services
3. **Effort estimation** — Count FUs, estimate domain agents needed
4. **Dependency detection** — Check if any other specs (draft or in-progress) overlap

### 4. Fix Scope Enforcement for Orchestrators (AC-09)

Current `scope-enforcement.sh` only enforces scope for agents detected in worktrees. The orchestrator runs in the main repo and is unrestricted — it should be blocked from Write/Edit on application code.

Add detection: if `CLAUDE_AGENT_TYPE` is "orchestrator" or branch name contains "orchestrator", block Write/Edit on all files except `docs/` and task management.

### 5. Update Default Branch Strategy (AC-07)

The sdlc-workflow skill currently defaults to multi-branch worktrees. Formalize the lesson from SPEC-017:

```markdown
## Branch Strategy

**Default: Single branch, single PR per spec.**

The orchestrator creates one feature branch (`feat/SPEC-NNN-name`).
Domain agents work sequentially on this branch, each committing their FU
before the next agent starts.

**Exception: Worktrees for parallel cross-domain work.**

Only use worktrees when:
- The spec has truly independent FUs that don't share files
- Time savings from parallelism outweigh merge coordination cost
- The orchestrator explicitly decides this in the breakdown step
```

### 6. Distribute Principles to Domain Skills (AC-11)

Currently every domain agent's Required Reading includes `architecture-principles/SKILL.md` (54 lines, all 23 principles). Most agents only need 4-5 of those principles.

Add a "Principles That Apply" table to each domain skill:

```markdown
## Principles That Apply

| ID | Rule | Enforcement |
|----|------|-------------|
| A1 | Routers delegate to services, no .select() | validate-patterns.sh BLOCKS |
| A8 | Use get_user_scoped_client, never raw client | validate-patterns.sh BLOCKS |

For full rationale: `.claude/skills/architecture-principles/reference.md`
```

**Principle distribution:**

| Domain Skill | Relevant Principles |
|-------------|-------------------|
| backend-patterns | A1, A3, A5, A6, A8, A10 |
| frontend-patterns | A4, A5, A7, A10 |
| database-patterns | A3, A8, A9, A10 |
| integration-deployment | A3, A11 |

Domain agent definitions then replace:
```markdown
## Required Reading
1. `.claude/skills/architecture-principles/SKILL.md`  ← REMOVE
2. `.claude/skills/backend-patterns/SKILL.md`          ← now includes relevant principles
```

The orchestrator, reviewer, and spec-writer KEEP `architecture-principles/SKILL.md` in their Required Reading since they need the full picture. The centralized `reference.md` stays untouched as the source of truth.

### 7. "Before Declaring Done" Protocol (AC-12)

Domain agents lose their task contract during context compaction. The agent definition survives (system-level), but the specific task description (deliverables, ACs, file list) gets compressed.

Add to `agent-protocols/SKILL.md`:

```markdown
## Before Declaring Done

Your task contract may have been compressed during this session. Before marking complete:

1. **Re-read your task:** `TaskGet` with your task ID — the description field is durable storage
2. **Check every deliverable** listed in the task description against what you've committed
3. **If you can't remember your full scope, re-read it** — don't guess from what's in front of you
4. Run verification (tests + lint) one final time
5. Only then: `TaskUpdate` status to completed + message the orchestrator
```

This costs one tool call (`TaskGet`) but prevents the "fixed the tests, looks good, all done!" failure mode where the agent forgets half its deliverables.

### 8. GitHub Review Feedback Loop (AC-13)

Today the `claude-code-review.yml` workflow posts review comments on PRs, but nobody reads them — the orchestrator doesn't poll GitHub. Blockers sit unactioned until the user notices.

Add to the orchestrator's attention loop:

```
WHILE tasks remain incomplete:
  ...existing steps...
  6. For each PR with pending reviews:
     - `gh pr view <number> --json reviews --jq '.reviews[-1]'`
     - If latest review has BLOCKERS: parse findings, message domain agent with fix instructions
     - If APPROVED: note in task status, proceed to next step
```

The orchestrator already has Bash access for read-only git commands. `gh pr view` is read-only and fits within existing permissions.

### 9. Incremental Review on Follow-Up Pushes (AC-14)

The `claude-code-review.yml` workflow runs the same full-PR review on every push (`synchronize` event). After a blocker fix, the reviewer re-checks all 21 ACs instead of just verifying the fix.

Update the workflow prompt to detect the trigger event and scope the review:

```yaml
prompt: |
  {{#if github.event.action == 'synchronize'}}
  This is a follow-up push. A previous review found issues.
  1. Read the PREVIOUS review comment on this PR (use `gh api`)
  2. Review ONLY the new commits since the last review
  3. Verify the previously reported blockers are resolved
  4. Check that the fix didn't introduce new violations
  5. Do NOT re-check all ACs — only verify blocker resolution + new code
  {{else}}
  [existing full review prompt]
  {{/if}}
```

The actual implementation will use GitHub Actions context (`${{ github.event.action }}`) to branch the prompt, since the claude-code-action doesn't support Handlebars. Two separate prompt strings conditionally selected.

### 10. Remove/Replace Prompt Reminder Hook (AC-06)

The `prompt-reminder.sh` hook fires on every user prompt with generic advice already present in CLAUDE.md. Two options:

**Option A (recommended): Remove it entirely.** The information is already in CLAUDE.md and agent definitions. Per S3, advisory-only reminders without enforcement are noise.

**Option B: Target it to team members only.** If the hook detects `CLAUDE_AGENT_TYPE` is set (indicating a spawned agent, not the user's main session), provide a focused reminder. Otherwise, skip.

## Testing Requirements

### Validation (all manual — these are prompt/config changes, not code)

| AC | Validation Method |
|----|-------------------|
| AC-01 | Read orchestrator.md, verify anti-implementation rules and model directives present |
| AC-02 | Read agent-protocols/SKILL.md, verify all 3 shared sections extracted |
| AC-03 | Read each domain agent, verify ≤60 lines, verify references agent-protocols skill |
| AC-04 | Invoke spec-writer with "I want users to see their memory timeline" — verify it researches codebase and produces complete spec |
| AC-05 | Read orchestrator.md, verify attention loop protocol documented |
| AC-06 | Read prompt-reminder.sh, verify it's removed or team-member targeted |
| AC-07 | Read sdlc-workflow SKILL.md, verify single-branch default documented |
| AC-08 | Read orchestrator.md, verify model directives with explicit model names |
| AC-09 | Set CLAUDE_AGENT_TYPE=orchestrator, attempt Write on chatServer/ file, verify blocked |
| AC-10 | Read orchestrator.md, verify "STOP and delegate" rule present |
| AC-11 | Read each domain skill, verify "Principles That Apply" table present with correct principle IDs; read domain agent definitions, verify architecture-principles removed from Required Reading |
| AC-12 | Read agent-protocols/SKILL.md, verify "Before Declaring Done" section exists with TaskGet re-read step |
| AC-13 | Read orchestrator.md, verify attention loop includes `gh pr view` polling step for review feedback |
| AC-14 | Read claude-code-review.yml, verify `synchronize` events use incremental review prompt (not full re-review) |

### Smoke Test

After all changes:
1. Start a new Claude Code session
2. Say: "Execute SPEC-019" (or any pending spec)
3. Verify: Claude picks up orchestrator.md, creates team, spawns domain agents on sonnet, enters attention loop
4. Verify: Orchestrator does NOT write any code itself
5. Verify: Domain agents receive properly scoped contracts

## Edge Cases

- **Spec-writer can't determine scope** — If codebase research is inconclusive, spec-writer should flag ambiguity to user rather than guessing
- **Orchestrator has no agents to spawn** — If all tasks are blocked, orchestrator should report the situation to user rather than trying to unblock itself by doing the work
- **Agent goes idle permanently** — Attention loop should detect "idle > 5 minutes with incomplete task" and escalate to user
- **Hook false positives on orchestrator detection** — If a non-orchestrator agent has "orchestrator" in its branch name, scope enforcement could incorrectly block. Use `CLAUDE_AGENT_TYPE` env var as primary detection, branch name as fallback only.

## Functional Units

All changes are to agent definitions, skills, and hooks — single domain (SDLC infrastructure). Single branch, single PR.

1. **FU-1: Extract shared agent protocols** — Create `agent-protocols/SKILL.md` with shared protocols + "Before Declaring Done" protocol, update all domain agent definitions to reference it
2. **FU-2: Distribute principles to domain skills** — Add "Principles That Apply" tables to backend-patterns, frontend-patterns, database-patterns, integration-deployment; remove architecture-principles from domain agent Required Reading
3. **FU-3: Upgrade orchestrator** — Attention loop (including GitHub review polling), model directives, anti-implementation rules, stronger delegation language
4. **FU-4: Upgrade spec-writer** — Autonomous research workflow, auto-numbering, effort estimation
5. **FU-5: Update sdlc-workflow skill** — Single-branch default, model tiering documentation
6. **FU-6: Fix hooks and CI** — scope-enforcement.sh for orchestrator blocking, prompt-reminder.sh removal, claude-code-review.yml incremental review

**Merge order:** Single PR. FU-1 → FU-2 → FU-3 → FU-4 → FU-5 → FU-6 (sequential commits on one branch).

## Completeness Checklist

- [x] Every AC has a stable ID (AC-01 through AC-14)
- [x] Every AC maps to at least one FU
- [x] Technical decisions reference principles (S2, S3, S5, S6, S7, F2)
- [x] Merge order is explicit (single PR)
- [x] Out of scope is explicit
- [x] Edge cases documented with expected behavior
- [x] Validation methods map to ACs

## Decisions (Resolved)

1. **Prompt reminder hook (AC-06):** Remove entirely. Per S3, advisory without enforcement is noise.
2. **Model defaults:** Sonnet for all domain agents. Haiku at orchestrator's discretion for mechanical tasks.
3. **Spec-writer model:** Opus. Spec quality determines implementation quality.
4. **Orchestrator model:** Opus. Dynamic reasoning, contract authoring, and judgment calls require it.
