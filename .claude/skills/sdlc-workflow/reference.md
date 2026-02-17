# SDLC Workflow — Full Reference

## End-to-End Flow

```
User writes spec (or agent generates from requirements)
  -> User invokes orchestrator agent
  -> Orchestrator reads spec, creates team, breaks into tasks
  -> Per functional unit:
     -> Orchestrator creates worktree + branch
     -> Implementer writes code + tests in worktree
     -> Implementer commits, pushes, creates PR
     -> Reviewer checks diff against spec, patterns, tests, docs
     -> [BLOCKER] -> Implementer fixes -> Reviewer re-reviews
     -> [Clean] -> Orchestrator reports PR to user
     -> User UATs + merges
     -> Orchestrator removes worktree, unblocks next task
  -> All tasks done -> Orchestrator updates spec status, cleans up team
```

## Agent Team Structure

### Orchestrator (Team Lead, Delegate Mode)

- Runs in the main repo directory on the `main` branch
- Cannot write or edit code — coordination only
- Creates worktrees for implementers
- Sequences tasks respecting dependencies
- Spawns implementer and reviewer teammates
- Reports PR URLs to the user

### Implementer (Teammate, Full Capability)

- Works in an isolated git worktree
- Has full read/write access
- Writes code, tests, commits, creates PRs
- Follows project skills and patterns
- Reports completion to orchestrator

### Reviewer (Teammate, Read-Only)

- Cannot write or edit code
- Reviews diffs against spec and patterns
- Runs tests and lint
- Reports BLOCKER/WARNING/NOTE findings
- Missing tests or docs are always BLOCKERs

## Git Worktree Management

Git worktrees allow multiple branches to be checked out simultaneously in different directories:

```bash
# Create worktree (orchestrator does this)
git worktree add ../llm-agent-SPEC-NNN-<unit> -b feat/SPEC-NNN-<unit>

# List worktrees
git worktree list

# Implementer works in the worktree directory
cd ../llm-agent-SPEC-NNN-<unit>

# After PR merged, clean up (orchestrator does this)
git worktree remove ../llm-agent-SPEC-NNN-<unit>
```

Directory layout:
```
/home/tim/github/
  llm-agent/                          <- main repo (main branch)
  llm-agent-SPEC-001-migration/       <- worktree (feat/SPEC-001-migration)
  llm-agent-SPEC-001-service/         <- worktree (feat/SPEC-001-service)
```

## Branch Naming Convention

```
feat/SPEC-NNN-short-description
```

Examples:
- `feat/SPEC-001-migration`
- `feat/SPEC-001-notification-service`
- `feat/SPEC-001-notification-api`
- `feat/SPEC-001-notification-ui`

## Commit Convention

```
SPEC-NNN: <imperative description>

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
```

Examples:
- `SPEC-001: Add notifications table with RLS policies`
- `SPEC-001: Implement NotificationService with web and Telegram routing`
- `SPEC-001: Add notification API endpoints with auth`

Commit after each logical unit of work — not just at the end.

## PR Convention

One PR per functional unit. PR title matches commit format:

```
SPEC-NNN: <short description>
```

PR body includes:
- Summary (what changed)
- Spec reference
- Testing status (pytest, pnpm test, ruff, eslint)
- Which functional unit this covers

## Testing Requirements

### Unit Tests

| Source Location | Test Location |
|----------------|---------------|
| `chatServer/services/foo.py` | `tests/chatServer/services/test_foo.py` |
| `chatServer/routers/foo.py` | `tests/chatServer/routers/test_foo.py` |
| `src/core/foo.py` | `tests/core/test_foo.py` |
| `webApp/src/components/Foo.tsx` | `webApp/src/components/Foo.test.tsx` |
| `webApp/src/api/hooks/useFoo.ts` | `webApp/src/api/hooks/useFoo.test.ts` |

### What to Test

- Happy path for each public method
- Auth failure (401/403) for API endpoints
- Invalid input handling
- Edge cases from the spec
- Error paths (database failures, network errors)

### Integration Tests

- **API endpoints:** Use `httpx.AsyncClient` with the FastAPI `app`
- **RLS policies:** Query as different users, verify row filtering
- **Frontend hooks:** Use `@testing-library/react` + `msw` for API mocking

### Running Tests

```bash
# All Python tests
pytest tests/ -x -q

# Specific test file
pytest tests/chatServer/services/test_notification_service.py -v

# Python lint
ruff check src/ chatServer/ tests/

# Frontend tests
cd webApp && pnpm test -- --run

# Frontend lint
cd webApp && pnpm lint
```

## Review Checklist

1. **Scope:** Changes within spec scope, no scope creep
2. **Patterns:** Backend/frontend/database skills followed
3. **Tests:** Exist, cover requirements, pass
4. **Documentation:** Updated if behavior changed
5. **Security:** No secrets, RLS on tables, auth on endpoints
6. **Git:** Clean commits, correct branch, no `.env` files

Severity levels:
- **BLOCKER** — Must fix (missing tests, missing RLS, pattern violation, missing docs, security issue, out of scope)
- **WARNING** — Should fix (minor style, missing edge case test)
- **NOTE** — Informational (future improvement suggestion)

## Feedback Loop

When a deviation is detected (by reviewer, CI, or user during UAT):

1. Log in `docs/sdlc/DEVIATIONS.md` (what, root cause, correction)
2. Determine correction target:
   - Skill needs update? -> Update the skill
   - Hook could catch it? -> Add/tighten hook
   - CLAUDE.md gotcha? -> Add to Known Gotchas
   - Agent prompt unclear? -> Update agent definition
3. Apply correction
4. Verify correction prevents recurrence

## Failure Handling

- **Implementer stuck:** Messages orchestrator, who may provide guidance or escalate to user
- **Tests fail:** Implementer fixes before marking complete. TaskCompleted hook blocks completion without tests.
- **Review has blockers:** Orchestrator messages implementer with specific fixes needed
- **PR merge conflict:** Implementer rebases from main in their worktree
- **User rejects in UAT:** Orchestrator creates follow-up tasks for the implementer

## Git Safety

These operations are blocked by hooks:
- `git push --force` / `git push -f`
- `git reset --hard`
- `git checkout .` / `git restore .`
- `git clean -f`
- `git push` when on `main`
- `git branch -D main`

Always work on feature branches. Never push to main directly.
