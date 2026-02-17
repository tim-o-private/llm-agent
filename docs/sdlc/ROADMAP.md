# Roadmap

## Current Milestone: Foundation Infrastructure (Feb 2026)

### In-Flight Work

| ID | Feature | Status | Spec |
|----|---------|--------|------|
| SPEC-001 | Notification System | Implementation Complete — Tests Outstanding | [SPEC-001](specs/SPEC-001-notification-system.md) |
| SPEC-002 | Telegram Integration | Implementation Complete — Tests Outstanding | [SPEC-002](specs/SPEC-002-telegram-integration.md) |
| SPEC-003 | Scheduled Agent Execution | Implementation Complete — Tests Outstanding | [SPEC-003](specs/SPEC-003-scheduled-execution.md) |
| SPEC-004 | Test Coverage for SPEC-001/002/003 | Ready | [SPEC-004](specs/SPEC-004-test-coverage-existing-specs.md) |
| SPEC-005 | Unified Sessions | Ready (blocked by SPEC-004) | [SPEC-005](specs/SPEC-005-unified-sessions.md) |

### Completed

- Agent SDLC setup (agents, skills, hooks, documentation)
- Core platform (auth, chat, actions/approval system)
- Gmail integration tools
- Agent loading from DB with TTL cache
- Content block normalization for langchain-anthropic
- Product architecture skill + cruft cleanup

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
