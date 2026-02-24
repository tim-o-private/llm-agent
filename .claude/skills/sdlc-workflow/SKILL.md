# SDLC Workflow — Quick Reference

Use this skill when working on specs, managing branches, committing code, or reviewing changes in the llm-agent project.

## Spec Format

Specs live in `docs/sdlc/specs/SPEC-NNN-<name>.md`. See [TEMPLATE](../../docs/sdlc/specs/TEMPLATE.md).

Required sections: Goal, Acceptance Criteria, Scope, Technical Approach, Testing Requirements, Edge Cases, Functional Units.

## Domain Agent Team

| Agent | Scope | Handles |
|-------|-------|---------|
| **database-dev** | `supabase/migrations/`, `chatServer/database/` | Schema, RLS, indexes |
| **backend-dev** | `chatServer/`, `src/` | Services, routers, API |
| **frontend-dev** | `webApp/src/` | Components, hooks, pages |
| **deployment-dev** | Dockerfiles, fly.toml, CI/CD | Docker, deploys, env vars |
| **reviewer** | All (read-only) | Code review (structured VERDICT) |
| **uat-tester** | `tests/uat/` | Flow tests with AC-ID naming |
| **spec-writer** | Specs only | Vision → complete spec draft |

Cross-domain flow: `database-dev → backend-dev → frontend-dev`

## Contract Format

When work flows between domains, the orchestrator writes a contract in the task description:

```markdown
## Contract: [source] -> [target]
### Schema / API / Config provided:
- [concrete details]
### What [target] must implement:
- [deliverables]
### Assumptions [target] can make:
- [what's already done]
```

## Git Coordination

**One writer per branch at a time.** The #1 source of lost work is two agents (or agent + team lead) editing the same branch simultaneously.

- When an agent's task is `in_progress`, they own their branch exclusively
- Team lead must NOT edit files on an active agent's branch — message the agent instead
- After an agent completes, verify their commit before starting the next FU: `git log --oneline -1`
- On shared branches, always `git pull` before starting work
- Commit and push immediately when done — unpushed work blocks everyone else

## Branch Strategy

**Default: Single branch, single PR per spec.**

The orchestrator creates one feature branch (`feat/SPEC-NNN-name`). Domain agents work sequentially on this branch, each committing their FU before the next agent starts. This avoids merge conflicts and worktree coordination overhead.

**Exception: Worktrees for parallel cross-domain work.**

Only use worktrees when:
- The spec has truly independent FUs that don't share files
- Time savings from parallelism outweigh merge coordination cost
- The orchestrator explicitly decides this in the breakdown step

Branch naming: `feat/SPEC-NNN-short-description`

## Commit Format

```
SPEC-NNN: <imperative description>

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
```

Commit frequently — after each logical unit of work.

## Model Tiering

| Role | Model | Rationale |
|------|-------|-----------|
| Orchestrator | opus | Contract authoring, judgment calls, dynamic reasoning |
| Spec-writer | opus | Architecture decisions, codebase analysis |
| Reviewer | opus | Deep semantic review, principle application |
| Domain agents | sonnet | Well-scoped implementation with clear contracts |
| Mechanical tasks | haiku | Config changes, file moves, trivially specific contracts |

## PR Strategy

**Default: Single PR per spec.** All FU commits go on one branch, one PR.

**Exception:** Multi-PR only when the spec has truly parallel, independent FUs on separate branches.

## Testing Requirements

- **Every new function/method** gets at least one test
- **Every new service class** gets tests for all public methods
- **Every new API endpoint** gets integration tests (happy path + auth failure + invalid input)
- **Every new component/hook** gets a test file
- Tests must pass before marking tasks complete

## Review Process

Reviewer checks: **scope boundary**, contract compliance, pattern compliance, test coverage, documentation, security.

- Scope boundary violation = **BLOCKER**
- Missing tests = **BLOCKER**
- Missing documentation = **BLOCKER**
- Out-of-scope changes = **BLOCKER**

## PR Merge Order

PRs follow the cross-domain dependency flow and must be merged in order:

1. **Database PRs** — merged first (no prerequisites)
2. **Backend PRs** — merged second (requires database PR merged)
3. **Frontend PRs** — merged last (requires database + backend PRs merged)

Every PR body must include a "Merge Order" section stating its prerequisites and what it unblocks. The orchestrator reports PRs with numbered merge order — never as "all ready simultaneously" unless truly independent.

## Deviation Logging

When an agent makes a mistake, log it in `docs/sdlc/DEVIATIONS.md` with: what happened, root cause, correction, target (skill/hook/agent/CLAUDE.md).

## Key Files

| File | Purpose |
|------|---------|
| `docs/sdlc/ROADMAP.md` | Milestones and goals |
| `docs/sdlc/BACKLOG.md` | Prioritized task queue |
| `docs/sdlc/specs/` | Spec files |
| `docs/sdlc/DEVIATIONS.md` | Agent error log |
| `.claude/agents/orchestrator.md` | Team lead definition |
| `.claude/agents/database-dev.md` | Database agent |
| `.claude/agents/backend-dev.md` | Backend agent |
| `.claude/agents/frontend-dev.md` | Frontend agent |
| `.claude/agents/deployment-dev.md` | Deployment agent |
| `.claude/agents/reviewer.md` | Reviewer definition |

## Full Reference

See [reference.md](reference.md) for the complete workflow documentation.
