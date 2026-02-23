# SDLC Workflow — Full Reference

## End-to-End Flow

```
User writes spec (or agent generates from requirements)
  -> User invokes orchestrator agent
  -> Orchestrator reads spec, creates team, breaks into tasks with domain assignments
  -> Per functional unit:
     -> Orchestrator creates worktree + branch
     -> Orchestrator writes contract in task description
     -> Domain agent (database/backend/frontend/deployment) implements in worktree
     -> Agent commits, pushes, creates PR
     -> Reviewer checks diff against spec, patterns, scope boundaries, contracts
     -> [BLOCKER] -> Domain agent fixes -> Reviewer re-reviews
     -> [Clean] -> Orchestrator reports PR to user
     -> User UATs + merges
     -> Orchestrator removes worktree, passes contract forward, unblocks next task
  -> All tasks done -> Orchestrator updates spec status, cleans up team
```

## Domain Agent Team

### Orchestrator (Team Lead, Delegate Mode)

- Runs in the main repo directory on the `main` branch
- Cannot write or edit code — coordination only
- Creates worktrees for domain agents
- Determines which domain agent handles each task
- Writes contracts between agents
- Sequences tasks: database-dev → backend-dev → frontend-dev
- Reports PR URLs to the user

### Database Dev (Teammate, Full Capability)

- **Scope:** `supabase/migrations/`, `chatServer/database/`
- Works in an isolated git worktree
- Creates SQL migrations, RLS policies, indexes
- Provides schema contract to backend-dev
- Skills: `database-patterns`, `sdlc-workflow`

### Backend Dev (Teammate, Full Capability)

- **Scope:** `chatServer/` (except database/), `src/`
- Works in an isolated git worktree
- Receives schema contract from database-dev
- Builds services, routers, models
- Provides API contract to frontend-dev
- Skills: `backend-patterns`, `sdlc-workflow`
- Verify: `pytest tests/ -x -q && ruff check src/ chatServer/ tests/`

### Frontend Dev (Teammate, Full Capability)

- **Scope:** `webApp/src/`
- Works in an isolated git worktree
- Receives API contract from backend-dev
- Builds components, hooks, pages, stores
- Skills: `frontend-patterns`, `sdlc-workflow`
- Verify: `cd webApp && pnpm test -- --run && pnpm lint`

### Deployment Dev (Teammate, Full Capability)

- **Scope:** Dockerfiles, fly.toml, CI/CD, env config
- Works in an isolated git worktree
- Receives requirements from other agents (new env vars, packages)
- Manages Docker builds, Fly.io config, CI pipelines
- Skills: `integration-deployment`, `sdlc-workflow`
- Verify: `docker build` succeeds

### Reviewer (Teammate, Read-Only)

- Cannot write or edit code
- Reviews diffs against spec, patterns, and **scope boundaries**
- Verifies contracts were followed
- Runs tests and lint
- Reports BLOCKER/WARNING/NOTE findings
- Scope violations are always BLOCKERs

## Cross-Team Contract Format

When work flows from one domain to another, the orchestrator writes a contract in the downstream task description:

```markdown
## Contract: [source-agent] -> [target-agent]

### Schema / API / Config provided:
- [concrete details: table DDL, endpoint paths, response shapes, env var names]

### What [target] must implement:
- [specific deliverables]

### Assumptions [target] can make:
- [things that are already done and tested by the upstream agent]
```

### Example: database-dev → backend-dev

```markdown
## Contract: database-dev -> backend-dev

### Schema provided:
- Table: `notifications`
  - `id UUID PRIMARY KEY DEFAULT gen_random_uuid()`
  - `user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE`
  - `title TEXT NOT NULL`
  - `body TEXT`
  - `category TEXT NOT NULL CHECK (category IN ('heartbeat', 'approval_needed', 'agent_result', 'error', 'info'))`
  - `read BOOLEAN NOT NULL DEFAULT false`
  - `metadata JSONB DEFAULT '{}'`
  - `created_at TIMESTAMPTZ NOT NULL DEFAULT now()`
- RLS: SELECT for auth.uid(), ALL for service_role
- Index: (user_id, created_at DESC) WHERE read = false

### What you must implement:
- NotificationService with: notify_user, get_notifications, get_unread_count, mark_read, mark_all_read
- Router at /api/notifications with Depends(get_current_user)

### Assumptions you can make:
- Table exists with RLS configured
- is_record_owner() function exists
```

### Example: backend-dev → frontend-dev

```markdown
## Contract: backend-dev -> frontend-dev

### API provided:
- `GET /api/notifications?limit=50&offset=0&unread_only=false` → `Notification[]`
- `GET /api/notifications/unread/count` → `{ count: number }`
- `POST /api/notifications/{id}/read` → `{ success: true }`
- `POST /api/notifications/read-all` → `{ success: true, count: number }`
- All endpoints require `Authorization: Bearer <token>` header

### What you must implement:
- useNotifications, useUnreadCount, useMarkNotificationRead, useMarkAllRead hooks
- NotificationBadge component with bell icon, unread count, dropdown panel

### Assumptions you can make:
- API endpoints work and return the shapes above
- Auth token comes from supabase.auth.getSession()
```

## Scope Boundaries

Each domain agent has strict file scope. The reviewer checks these boundaries.

| Agent | Allowed | Forbidden |
|-------|---------|-----------|
| database-dev | `supabase/migrations/`, `chatServer/database/` | Everything else |
| backend-dev | `chatServer/` (except database/), `src/`, `tests/` | `webApp/`, `supabase/migrations/` |
| frontend-dev | `webApp/src/` | `chatServer/`, `supabase/` |
| deployment-dev | Dockerfiles, fly.toml, `.github/`, `requirements.txt`, `package.json` | Application code |

### How scope enforcement works

`scope-enforcement.sh` fires on every Write/Edit. It identifies the agent type in two ways:

1. **`CLAUDE_AGENT_TYPE` env var** — set explicitly when spawning a domain agent. Takes precedence.
2. **Branch-name fallback** — inferred from branch name keywords (e.g., `*database*` → `database-dev`). **Only active inside git worktrees.** In the main repo, the team lead is unrestricted.

**Key implication:** domain agents must always work in worktrees (not the main repo). The team lead always works in the main repo. An ad-hoc fix branch in the main repo with a domain keyword in its name (e.g., `fix/uat-database-fixes`) will NOT trigger scope enforcement.

## Git Worktree Management

Git worktrees allow multiple branches to be checked out simultaneously in different directories:

```bash
# Create worktree (orchestrator does this)
git worktree add ../llm-agent-SPEC-NNN-<unit> -b feat/SPEC-NNN-<unit>

# List worktrees
git worktree list

# Domain agent works in the worktree directory
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

Commit after each logical unit of work — not just at the end.

## PR Convention

One PR per functional unit. PR title matches commit format:

```
SPEC-NNN: <short description>
```

PR body includes:
- Summary (what changed)
- Spec reference
- Testing status
- Which functional unit this covers
- API or schema contract (if applicable)

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

1. **Scope boundary:** Agent only modified files within its domain
2. **Contract compliance:** Used the correct table names, API shapes, env vars from upstream
3. **Patterns:** Backend/frontend/database skills followed
4. **Tests:** Exist, cover requirements, pass
5. **Documentation:** Updated if behavior changed
6. **Security:** No secrets, RLS on tables, auth on endpoints
7. **Git:** Clean commits, correct branch, no `.env` files

Severity levels:
- **BLOCKER** — Must fix (scope violation, contract violation, missing tests, missing RLS, pattern violation, missing docs, security issue, out of scope)
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

- **Agent stuck:** Messages orchestrator, who may provide guidance or escalate to user
- **Tests fail:** Agent fixes before marking complete. TaskCompleted hook blocks completion without tests.
- **Review has blockers:** Orchestrator messages the original domain agent with specific fixes needed
- **PR merge conflict:** Agent rebases from main in their worktree
- **User rejects in UAT:** Orchestrator creates follow-up tasks for the domain agent
- **Scope violation:** Reviewer blocks. Orchestrator reassigns work to the correct domain agent.

## Git Safety

These operations are blocked by hooks:
- `git push --force` / `git push -f`
- `git reset --hard`
- `git checkout .` / `git restore .`
- `git clean -f`
- `git push` when on `main`
- `git branch -D main`

Always work on feature branches. Never push to main directly.
