# Roadmap

## Current Milestone: Foundation Infrastructure (Feb 2026)

### In-Flight Work

| ID | Feature | Status | Spec |
|----|---------|--------|------|
| SPEC-005 | Unified Sessions | Ready | [SPEC-005](specs/SPEC-005-unified-sessions.md) |

### Completed

- Agent SDLC setup (agents, skills, hooks, documentation)
- Core platform (auth, chat, actions/approval system)
- Gmail integration tools
- Agent loading from DB with TTL cache
- Content block normalization for langchain-anthropic
- Product architecture skill + cruft cleanup
- SPEC-001: Notification system (implementation + tests)
- SPEC-002: Telegram integration (implementation + tests)
- SPEC-003: Scheduled agent execution (implementation + tests)
- SPEC-004: Test coverage for SPEC-001/002/003 (PRs #14-19 merged)
- Pre-existing test failures fixed (36+20 → 0, PR #21)
- Telegram env vars deployed to Fly.io

## Next Milestone: Agent Autonomy (TBD)

- Agent-to-agent communication
- Multi-step workflow orchestration
- Scheduled execution dashboard in webApp
- Notification preferences UI

## Future

- Mobile push notifications
- Slack channel integration
- Agent marketplace / sharing
- Execution cost tracking and budgets
