# SDLC Workflow — Quick Reference

Use this skill when working on specs, managing branches, committing code, or reviewing changes in the llm-agent project.

## Spec Format

Specs live in `docs/sdlc/specs/SPEC-NNN-<name>.md`. See [TEMPLATE](../../docs/sdlc/specs/TEMPLATE.md).

Required sections: Goal, Acceptance Criteria, Scope, Technical Approach, Testing Requirements, Edge Cases, Functional Units.

## Branch Naming

```
feat/SPEC-NNN-short-description
```

One branch per functional unit. Created via git worktree for parallel work.

## Commit Format

```
SPEC-NNN: <imperative description>

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
```

Commit frequently — after each logical unit of work.

## PR Per Functional Unit

Each self-contained piece gets its own PR:
- Database migration + RLS
- Service layer
- API endpoint + tests
- Frontend component + hook + tests

## Testing Requirements

- **Every new function/method** gets at least one test
- **Every new service class** gets tests for all public methods
- **Every new API endpoint** gets integration tests (happy path + auth failure + invalid input)
- **Every new component/hook** gets a test file
- Tests must pass before marking tasks complete

## Review Process

Reviewer checks: scope compliance, pattern compliance, test coverage, documentation, security.

- Missing tests = **BLOCKER**
- Missing documentation = **BLOCKER**
- Out-of-scope changes = **BLOCKER**

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
| `.claude/agents/implementer.md` | Implementer definition |
| `.claude/agents/reviewer.md` | Reviewer definition |

## Full Reference

See [reference.md](reference.md) for the complete workflow documentation.
