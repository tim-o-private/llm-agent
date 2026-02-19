# Deviation Log

When an agent makes a mistake or a pattern violation is found during review or UAT, log it here. Each deviation leads to a correction in skills, hooks, agent definitions, or CLAUDE.md.

## Template

```
### DEV-NNN: [date] Short description
- **What happened:** What the agent did wrong
- **Root cause:** Why it happened (missing rule, unclear instruction, etc.)
- **Correction:** What was updated to prevent recurrence
- **Target:** skill | hook | agent definition | CLAUDE.md gotcha
- **Status:** Fixed in [commit hash] | Pending
```

## Log

### DEV-001: 2026-02-18 Agents marked tasks complete with failing tests
- **What happened:** During SPEC-006, agents called TaskUpdate(status=completed) before running tests, or after tests failed. Broken code reached PR review.
- **Root cause:** `task-completed-gate.sh` only checked branch and uncommitted changes — no test verification. Agent instructions said "tests must pass" but nothing enforced it.
- **Correction:** Added pytest collection check (import/syntax errors) and test file existence checks to `task-completed-gate.sh`. Strengthened agent Verify sections to say "Do NOT call TaskUpdate until commands exit 0." Increased hook timeout to 60s.
- **Target:** hook (`task-completed-gate.sh`), agent definitions (backend-dev, frontend-dev), settings.json
- **Status:** Fixed in this commit

### DEV-002: 2026-02-18 Migration timestamp collisions across parallel worktrees
- **What happened:** Two database-dev agents in parallel worktrees both created migrations starting from similar prefixes, causing filename collisions at merge time.
- **Root cause:** No coordination of migration prefixes. Each agent independently derived timestamps.
- **Correction:** Orchestrator now pre-allocates migration prefixes in task contracts. `validate-patterns.sh` detects collisions against main repo. `database-patterns/SKILL.md` documents the rule.
- **Target:** agent (`orchestrator.md`, `database-dev.md`), hook (`validate-patterns.sh`), skill (`database-patterns`)
- **Status:** Fixed in this commit

### DEV-003: 2026-02-18 Inconsistent tool naming conventions
- **What happened:** Tools used mixed naming: `GmailSearch`, `save_memory`, `read_memory`, `EmailDigest` — no standard vocabulary. Domain prefixes placed inconsistently.
- **Root cause:** No documented naming convention existed.
- **Correction:** Added `verb_resource` naming standard to backend-patterns SKILL.md and reference.md. Added tool naming reminder to `validate-patterns.sh` hook for `chatServer/tools/*.py`. Legacy tools documented in BACKLOG.md for future rename.
- **Target:** skill (`backend-patterns`), hook (`validate-patterns.sh`), backlog
- **Status:** Fixed in this commit (convention documented; legacy renames in backlog)

### DEV-004: 2026-02-18 Tables created with agent_name TEXT instead of agent_id UUID FK
- **What happened:** New tables used `agent_name TEXT` to reference agents instead of `agent_id UUID FK → agent_configurations(id)`.
- **Root cause:** CLAUDE.md gotcha #12 documented the rule but it was buried in a long list. Agents missed it.
- **Correction:** Added `agent_name TEXT` detection to `validate-patterns.sh` (CRITICAL WARNING). Added prominent callout in `database-dev.md`. Added explicit BLOCKER check to `reviewer.md`.
- **Target:** hook (`validate-patterns.sh`), agent (`database-dev.md`, `reviewer.md`)
- **Status:** Fixed in this commit

### DEV-005: 2026-02-19 Dual-import singleton bug (Supabase client "not initialized")
- **What happened:** `background_tasks.check_due_reminders` threw "Supabase client not available" every 60s despite successful initialization at startup. The supabase client was initialized in module `database.supabase_client` but background_tasks imported from `chatServer.database.supabase_client` — two different modules with separate `_supabase_manager` globals.
- **Root cause:** Inconsistent `except ImportError` fallback imports. Lifespan used bare paths (`from database.supabase_client`), but other files used fully-qualified paths (`from chatServer.database.supabase_client`). Python loaded the module twice under different names. The `database.connection` module masked the same bug via auto-initialization fallback.
- **Correction:** (1) Standardized ALL `except ImportError` fallbacks in `chatServer/` to bare module paths. (2) Added `ensure_initialized()` auto-init to `supabase_client.py` matching `connection.py`'s pattern. (3) Added gotcha to CLAUDE.md.
- **Target:** CLAUDE.md gotcha, all `chatServer/` import blocks
- **Status:** Fixed in this branch

### DEV-006: 2026-02-19 Telegram bot webhook conflict between dev and prod
- **What happened:** Running the server locally with the production `TELEGRAM_BOT_TOKEN` called `set_webhook()` pointing the production bot at the local ngrok URL, silently breaking prod Telegram. Went unnoticed for days.
- **Root cause:** Single bot token shared between environments. Telegram only allows one webhook URL per bot. No warning when overriding a production webhook from local dev.
- **Correction:** Use separate Telegram bots for dev vs prod (same `TELEGRAM_BOT_TOKEN` env var, different values per environment). Added ngrok tunnel to `pnpm dev` via concurrently. Added gotcha to CLAUDE.md.
- **Target:** CLAUDE.md gotcha, `.env` setup, `package.json`
- **Status:** Fixed in this branch

### DEV-007: 2026-02-19 PostgREST upsert fails on partial unique index
- **What happened:** `telegram_bot.handle_message` used `.upsert(..., on_conflict="session_id")` but `chat_sessions.session_id` only had a partial unique index (`WHERE session_id IS NOT NULL`). PostgREST requires a real UNIQUE constraint for ON CONFLICT.
- **Root cause:** Code assumed a UNIQUE constraint existed when only a partial index did. No integration test covered the Telegram message path against a real database.
- **Correction:** Replaced upsert with select-then-insert pattern. Added gotcha to CLAUDE.md about partial indexes vs PostgREST upsert.
- **Target:** `chatServer/channels/telegram_bot.py`, CLAUDE.md gotcha
- **Status:** Fixed in this branch

### DEV-008: 2026-02-18 PR merge order not communicated
- **What happened:** Multiple PRs from a spec were reported as "ready" simultaneously, but they had implicit ordering (database → backend → frontend). User merged in wrong order.
- **Root cause:** No merge order documentation in PR bodies or orchestrator reporting.
- **Correction:** Added "Merge Order" section to all domain agent PR templates. Orchestrator now reports PRs with numbered merge sequence. Reviewer checks for merge order section. SDLC workflow skill documents the convention.
- **Target:** agent (`orchestrator.md`, `database-dev.md`, `backend-dev.md`, `frontend-dev.md`, `reviewer.md`), skill (`sdlc-workflow`)
- **Status:** Fixed in this commit
