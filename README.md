# llm-agent

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A multi-channel AI agent platform where agents are context-aware, act autonomously on your behalf, and do so safely. Agents connect to your real tools (email, task lists, calendars) and take action — but every operation is classified by risk level and gated by an approval system that the LLM cannot override.

The same agent serves you across web, Telegram, and scheduled background jobs. It remembers context across sessions, learns your preferences over time, and stays quiet when there's nothing to report.

## Why this exists

Most agent frameworks give the LLM direct access to tools and hope for the best. That's fine for demos, but not for an agent that reads your email, manages your tasks, and sends messages on your behalf. The core problem is: **how do you let an agent act autonomously without giving it unchecked access to destructive operations?**

This platform solves it with a tiered approval system enforced at the application layer — not by prompt engineering, not by trusting the model to self-police, and not by asking the user to approve every single action.

## Approval tiers

Every tool an agent can use is classified into one of three tiers:

| Tier | Behavior | Examples |
|------|----------|---------|
| `AUTO_APPROVE` | Executes immediately, no user involvement | Search email, read memory, list tasks |
| `REQUIRES_APPROVAL` | Always queued for user approval before execution | Send email, delete tasks, write files |
| `USER_CONFIGURABLE` | Safe defaults, user can promote to auto-approve | Create tasks, set reminders |

This is enforced in the tool-wrapping layer (`wrap_tools_with_approval`), not in the prompt. The LLM sees the tool, calls it, and the application decides whether to execute or queue. There is no prompt injection or jailbreak that bypasses this — the approval check happens after the LLM's output, before execution.

Queued actions are surfaced to the user (web UI or Telegram) for approve/reject. The agent can continue working on other things while waiting.

## Unified multi-channel architecture

The agent doesn't live in one interface. Every interaction — web chat, Telegram message, scheduled background run — goes through the same pipeline:

```
Channel input  -->  Resolve user + session  -->  Load agent (cached, TTL 15min)
    --> Wrap tools with approval context  -->  Execute  -->  Route response back to channel
```

All sessions register in a single `chat_sessions` table tagged by channel (`web`, `telegram`, `scheduled`, `heartbeat`). This means:

- **Web and Telegram share the same agent state.** Start a conversation on web, continue it on Telegram.
- **Scheduled jobs use the same agent and tools.** A background run can check your email, create a task, and queue an approval — all using the same pipeline as an interactive chat.
- **The agent's memory and preferences are channel-agnostic.** What it learns in one channel applies everywhere.

## Heartbeat: ambient monitoring that stays quiet

Scheduled agent runs that check a configurable list of things (new emails, pending approvals, upcoming deadlines) and only notify you when something actually needs attention.

If the agent's output starts with `HEARTBEAT_OK`, the notification is suppressed. The check still runs, the result is still logged, but you aren't bothered. This turns the agent from something you interact with into something that watches your back — and only taps your shoulder when it matters.

## Context-aware from the first interaction

On a user's first interactive session, if no memory or preferences exist, the agent's prompt automatically includes an onboarding section — it knows to introduce itself and learn about you. Once it saves its first memory or you set preferences, subsequent loads skip onboarding. No manual configuration, no "setup wizard."

Over time, the agent builds long-term memory: notes about your preferences, communication style, recurring tasks, and context from past conversations. This memory is loaded into every session, making the agent progressively more useful.

## Architecture

```
llm-agent/
  chatServer/             # FastAPI backend (Python) — :3001
    routers/              #   API endpoints (chat, actions, email, Telegram webhook)
    services/             #   Business logic (chat, approvals, scheduling, audit)
    dependencies/         #   Auth (ES256 JWT), agent loading
    tools/                #   Agent tool implementations (Gmail, tasks, memory, reminders)
    security/             #   Approval tier definitions and enforcement
    database/             #   Supabase client, connection pooling
  webApp/                 # React frontend (TypeScript) — :5173
    src/
      api/hooks/          #   React Query hooks (chat, actions, tasks)
      components/         #   UI components (Radix Themes + Tailwind)
      features/auth/      #   Auth (Supabase, ES256 JWT)
      pages/              #   TodayView, CoachPage, Login
  src/core/               # Agent loading, executor caching, LLM interface
  supabase/migrations/    # 44 PostgreSQL migrations (RLS-first)
  tests/                  # pytest (backend) + vitest (frontend)
```

### Key design decisions

- **RLS-first database.** Every table has Row Level Security. The Python code never manually filters by `user_id` — Supabase RLS handles it. This means a bug in application code can't leak another user's data.
- **Agent executor caching.** Loaded agents are cached in memory with a 15-minute TTL, keyed by `(user_id, agent_name)`. Repeat interactions within the window are near-instant.
- **Content block normalization.** LangChain's Anthropic integration returns responses as structured content blocks (`[{"type": "text", "text": "..."}]`), not plain strings. The chat service normalizes this transparently so channels don't need to care.
- **Database-driven agent config.** Agent definitions, tool registrations, and schedules live in PostgreSQL — not YAML files. This means config changes don't require redeployment.

## Tech stack

- **Backend:** Python, FastAPI, LangChain, langchain-anthropic (Claude)
- **Frontend:** React, TypeScript, Vite, Tailwind CSS, Radix Themes, React Query, Zustand
- **Database:** PostgreSQL on Supabase (RLS-first, 44 migrations)
- **Auth:** Supabase Auth with ES256 JWT verification
- **Channels:** Web UI, Telegram (aiogram), scheduled jobs (APScheduler)
- **Deployment:** Fly.io (Docker), GitHub Actions CI

## Running locally

```bash
# Prerequisites: Python 3.10+, Node.js with pnpm

git clone https://github.com/tim-o-private/llm-agent.git
cd llm-agent

# Python setup
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -r chatServer/requirements.txt

# Frontend setup
pnpm install

# Configure environment
cp .env.example .env        # Edit with your Supabase URL, API keys
# Create webApp/.env with VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY

# Run both services
pnpm dev                    # webApp on :5173, chatServer on :3001
```

## Testing

```bash
pytest tests/                          # Backend tests
cd webApp && pnpm test                 # Frontend tests
ruff check src/ chatServer/ tests/     # Python linting
cd webApp && pnpm lint                 # TypeScript linting
```

## How it's built

The codebase is developed using an agent-based SDLC workflow. Written specs are executed by a team of specialized Claude Code agents (orchestrator, database-dev, backend-dev, frontend-dev, reviewer, UAT tester), coordinated through cross-domain contracts and enforced by automated quality gates. Agent definitions, hooks, and domain knowledge skills live in [`.claude/`](.claude/). See [`docs/sdlc/`](docs/sdlc/) for specs and the deviation log.

## License

MIT — see [LICENSE](LICENSE).
