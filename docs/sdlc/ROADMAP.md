# Roadmap

## Vision: Chief of Staff Agent

An AI that manages your context and brings information to you — not a chatbot you babysit. Target users are regular humans with overloaded brains who want AI for common tasks without managing prompts or context.

The core insight: the value of AI is under-realized because using the tools is painful and managing context is manual. The agent should operate autonomously, remember what matters, and bring information to you.

## Milestone 1: Foundation Infrastructure (Feb 2026) — COMPLETE

| ID | Feature | Status | Spec |
|----|---------|--------|------|
| SPEC-001 | Notification System | Done | [SPEC-001](specs/SPEC-001-notification-system.md) |
| SPEC-002 | Telegram Integration | Done | [SPEC-002](specs/SPEC-002-telegram-integration.md) |
| SPEC-003 | Scheduled Agent Execution | Done | [SPEC-003](specs/SPEC-003-scheduled-execution.md) |
| SPEC-004 | Test Coverage for SPEC-001/002/003 | Done | [SPEC-004](specs/SPEC-004-test-coverage-existing-specs.md) |
| SPEC-005 | Unified Sessions | Done | [SPEC-005](specs/SPEC-005-unified-sessions.md) |

Also complete:
- Agent SDLC setup (agents, skills, hooks, documentation)
- Core platform (auth, chat, actions/approval system)
- Gmail integration tools
- Agent loading from DB with TTL cache
- Content block normalization for langchain-anthropic
- Product architecture skill + cruft cleanup

## Milestone 2: Agent Memory & Proactive Value (Feb–Mar 2026) — IN PROGRESS

The agent becomes stateful, context-aware, and proactive. This is the minimum viable "Chief of Staff."

| ID | Feature | Status | Spec |
|----|---------|--------|------|
| SPEC-006 | Email Digests & Proactive Reminders | PRs #30-34 — UAT | [SPEC-006](specs/SPEC-006-email-digests-and-proactive-reminders.md) |
| SPEC-007 | Frontend Cleanup + Approval Toasts | Draft | [SPEC-007](specs/SPEC-007-frontend-cleanup.md) |

Key deliverables:
- **Working memory** — agent remembers things across sessions (LTM wired + memory tools)
- **Email digests** — context-aware, cost-efficient (Haiku), delivered via Telegram/web
- **Proactive reminders** — "remind me about X on Friday" just works
- **Cost controls** — model tiering, token usage tracking
- **Frontend cleanup** — remove cruft pages, add approval toasts

## Milestone 3: Self-Extending Agent (TBD)

The agent can create its own tools and adapt to your needs without you writing code.

- Dynamic tool creation (agent writes DB config rows, validated by API)
- Trust escalation (first-use approval → auto-approve after track record)
- Tool approval dashboard
- Agent-initiated OAuth flows ("I need access to your calendar to do this")

## Milestone 4: Chief of Staff (TBD)

Full orchestration: the agent understands your intent and delegates to specialized sub-agents.

- Agent orchestration (chief creates/manages sub-agents)
- Multi-account email support
- Draft-and-review workflow (agent drafts, you approve via pending actions)
- Morning briefing (consolidated: email + reminders + calendar + priorities)
- Proactive suggestions ("You have a meeting with Sarah tomorrow — here's context from your last conversation")

## Future

- Calendar integration (Google Calendar, Outlook)
- Slack channel integration
- Mobile push notifications
- Notification preferences UI
- Scheduled execution dashboard in webApp
