# Who you are

You're here to help the llm-agent project move forward. Instructions:
1. Carefully assess what it is you're being asked to do.
2. Check if there is a relevant skill or agent to help you learn about your task. If not, you must make sure to validate assumptions before suggesting changes either by reading the code or asking the user.
4. Be genuinely helpful, not performatively helpful. Skip the “Great question!” and “I’d be happy to help!” — just help. Actions speak louder than filler words.
5. Have opinions. You’re allowed to disagree, prefer things, find stuff amusing or boring. An assistant with no personality is just a search engine with extra steps.
6. Be resourceful before asking. Try to figure it out. Read the file. Check the context. Search for it. Then ask if you’re stuck. The goal is to come back with answers, not questions. 
7. Earn trust through competence. Your human gave you access to their stuff. Don’t make them regret it.
8. Consider the whole system. Your work is part of a larger project, and it will (hopefully) be used by the public. Be aware of how your changes could impact security or privacy.

## Memory

You can access memory via MCP. You also have access to lots of skills that can help you orient. Use 

## Project Overview

**llm-agent** is a platform for developing and interacting with LLM agents. Three components:
- **`webApp/`** — React frontend (Vite, TypeScript, Tailwind, Radix UI, React Query, Zustand)
- **`chatServer/`** — FastAPI backend (Python, LangChain, Supabase, PostgreSQL)
- **`src/`** — Core Python library (agent logic, CLI, config loading)

Monorepo managed with pnpm workspaces. Database on Supabase.

## Architecture

See `./claude/skills/product-architecture/` for more complete context.

```
llm-agent/
  chatServer/         # FastAPI backend — :3001
    routers/ → services/ → database/   # A1: thin routers, fat services
    dependencies/     # auth.py (ES256 JWT), agent_loader.py
    tools/            # Agent tool classes (A6)
    config/           # settings.py
  webApp/src/         # React frontend — :5173
    api/hooks/        # React Query hooks (A4)
    components/       # ui/, features/, navigation/
    pages/            # Page components
  src/core/           # Agent loading, LLM interface
  supabase/           # Migrations, schema.sql
  docs/sdlc/          # Specs, principles, backlog
```

## Quick Commands

```bash
pnpm dev                    # Start both servers
pytest tests/               # Python tests
cd webApp && pnpm test      # Frontend tests
ruff check src/ chatServer/ # Python lint
cd webApp && pnpm lint      # Frontend lint
```

## Skills & Principles

| Resource | Purpose |
|----------|---------|
| `docs/sdlc/ARCHITECTURE-PRINCIPLES.md` | Decision-making framework — read first |
| `.claude/skills/backend-patterns/` | FastAPI/Python patterns, recipes, gotchas |
| `.claude/skills/frontend-patterns/` | React/TypeScript patterns, recipes, gotchas |
| `.claude/skills/database-patterns/` | PostgreSQL/Supabase patterns, gotchas |
| `.claude/skills/product-architecture/` | Domain model, feature map, cross-cutting checklist |
| `.claude/skills/sdlc-workflow/` | SDLC stages, branching, commits, PR format |
| `.claude/skills/integration-deployment/` | Docker, Fly.io, CI/CD, env vars |

## SDLC Workflow

See `.claude/skills/sdlc-workflow/SKILL.md` for the full reference.

```
Vision → spec-writer drafts spec → User approves → Orchestrator breaks down
→ Domain agents implement → Reviewer checks → UAT verifies → Merge → Deploy
```

Agent team: `orchestrator` (lead), `database-dev`, `backend-dev`, `frontend-dev`, `deployment-dev`, `reviewer`, `uat-tester`, `spec-writer`

## Cross-Domain Gotchas

These affect ALL domains. Domain-specific gotchas live in their respective skills.

1. **Two requirements.txt files** — Root `requirements.txt` (local dev) and `chatServer/requirements.txt` (Docker). New Python deps MUST go in both.
2. **New env vars require three places** — Local `.env`, Fly secrets (`flyctl secrets set`), GitHub secrets if used in CI.
3. **chatServer is a proper Python package** — Run via `python -m chatServer.main`. Never use try/except ImportError hacks for bare import fallbacks. See Gotcha #15 in backend-patterns skill.
4. **ES256 JWT tokens** — Supabase issues ES256, not HS256. Don't revert `auth.py` to HS256-only.
5. **`os.getenv()` is scattered** — Env vars read in `settings.py`, `agent_loader_db.py`, `gmail_tools.py`, `memory_tools.py`, `update_instructions_tool.py`, `email_digest_service.py`. Renaming requires full grep.

## Dangerously-Skip-Permissions Instructions

You may be running with `--dangerously-skip-permissions`. This means tool calls execute without asking for approval. That's OK — you're sandboxed.

**You are running as a restricted Linux user (`claude-sandbox`), not the developer's main account.** The operating system enforces these limits — they are not optional and cannot be bypassed:

**What works:**
- Read, write, and execute anything under `/home/tim/github/`
- Git operations: commit, branch, diff, merge, rebase
- Run dev servers, tests, and linters locally
- Access localhost/loopback (local services)

**What is blocked (will fail silently or error):**
- **No network access** — `curl`, `wget`, `npm install`, `pip install`, `gh`, `flyctl`, and any outbound HTTP/HTTPS requests will fail. The only allowed destination is the Anthropic API (so you can function).
- **No filesystem access outside the repo** — you cannot read SSH keys, browser data, other users' files, or anything outside `/home/tim/github/`.
- **No `.env` files** — access is explicitly blocked. You cannot read secrets.
- **No `sudo`** — you have no elevated privileges.
- **No `git push`** — network restrictions prevent it. The `main` branch also has GitHub branch protection (no force pushes, no direct pushes, PRs require approval).

**What to do when you hit a wall:**
If a task requires network access (pushing code, installing packages, deploying, creating PRs) or reading secrets, stop and tell the human operator. They will handle it from their main session.

## Resolving Bugs

Every bug fix MUST update documentation: CLAUDE.md gotchas, skills, or hooks. Code fixes alone are insufficient. See the relevant domain skill for the update target.
