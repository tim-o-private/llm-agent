---
name: architecture-principles
description: Project decision-making framework. All 23 principles (S1-S7, F1-F2, A1-A14) with one-liners and enforcement. Read this before starting any task. See reference.md for full rationale, examples, and edge cases.
---

# Architecture Principles — Quick Reference

When you face a design decision, find the applicable principle below. If the one-liner is enough, follow it. If you need rationale or examples for a novel situation, see [reference.md](reference.md).

## SDLC Principles (How Work Gets Done)

| ID | Principle | One-liner | Enforced By |
|----|-----------|-----------|-------------|
| S1 | Done = verified | Unit tests + lint + end-to-end — not just "it compiles" | `task-completed-gate.sh` |
| S2 | Humans decide, machines verify | Operator = CPO/CTO; agents + hooks catch bugs | Review gates, hooks |
| S3 | Executable, not advisory | If there's no hook/gate enforcing it, it's a suggestion | `validate-patterns.sh`, gates |
| S4 | Understand WHY | Rationale enables generalization to novel situations | This document |
| S5 | Spec = contract | Post-approval, system delivers without further human intervention | Orchestrator workflow |
| S6 | Fail fast, fail early | Progressive gates catch issues at the earliest possible stage | Hooks → review → UAT |
| S7 | Knowledge compounds | Every deviation gets encoded as a hook, skill, or gotcha | `DEVIATIONS.md` → updates |

## Foundation Principles (Architecture ↔ Process)

| ID | Principle | One-liner | Enforced By |
|----|-----------|-----------|-------------|
| F1 | Prescriptive architecture | If an agent invents structure, that's an architecture gap — file it | Reviewer, orchestrator |
| F2 | Self-evident standards | Knowing layer relationships predicts naming, flow, shape, tests | Domain skills, A10 |

## Architectural Principles (How Code Is Structured)

| ID | Principle | One-liner | Enforced By |
|----|-----------|-----------|-------------|
| A1 | Thin routers, fat services | Routers wire deps + delegate. No `.select()` in routers. | `validate-patterns.sh` BLOCKS |
| A2 | DB config, code behavior | No-deploy changes = DB rows; test-requiring changes = code | Reviewer |
| A3 | Two data planes | Supabase REST+RLS for user CRUD; psycopg for high-volume/framework | Reviewer |
| A4 | React Query ≠ Zustand | Server state in React Query; client-only state in Zustand. Never duplicate. | Reviewer |
| A5 | Auth from getSession() | Never use Zustand auth store for API tokens | `validate-patterns.sh` BLOCKS in hooks |
| A6 | Tools = capability units | New capability = BaseTool subclass + service + DB row + registry | backend-patterns recipe |
| A7 | Cross-channel default | Every message feature works web + Telegram via shared chat_id | product-architecture checklist |
| A8 | RLS = security boundary | Every user-owned table has RLS. No app-layer filtering instead. | `validate-patterns.sh` BLOCKS |
| A9 | UUID FKs, not names | All inter-table refs use UUID FK with ON DELETE. Never agent_name TEXT. | `validate-patterns.sh` BLOCKS |
| A10 | Predictable naming | Entity "foo" → `foos` table, `foo_service.py`, `foo_router.py`, `useFooHooks.ts` | `validate-patterns.sh` (tools) |
| A11 | Design for N | Pluggable patterns; config over new infrastructure | Reviewer |
| A12 | Autonomy + safety rails | Approval tiers, RLS, audit logs — enable autonomy, don't restrict it | Reviewer |
| A13 | User config is first-class | Users can inspect and modify their settings and data | Reviewer |
| A14 | Pragmatic progressivism | Build abstractions when proven; don't over-engineer | Reviewer |

## Using Principles in Your Work

- **In code comments/commits:** cite by ID — `# Per A1, delegate to service`
- **In reviewer verdicts:** every BLOCKER cites a principle — `A8: Table missing RLS`
- **In specs:** ACs reference relevant principles — `AC-03: Cross-channel delivery [A7]`
- **Novel situation?** Read the full rationale in [reference.md](reference.md) for the closest principle
- **Nothing covers it?** That's an F1 gap — flag to orchestrator
