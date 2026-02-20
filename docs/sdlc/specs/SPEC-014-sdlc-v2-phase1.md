# SPEC-014: SDLC v2 Phase 1 — Codify Principles, Fix Process, Strengthen Enforcement

> **Status:** Done
> **Author:** Tim (with Claude)
> **Created:** 2026-02-20
> **Updated:** 2026-02-20

## Goal

Close the critical gaps in the SDLC that force the human operator into a verification role. Agents spend hours building features, then the operator spends days getting them merged — primarily because: no automated end-to-end verification, principles are advisory not enforced, and human gates exist where automation should.

Phase 1 codifies principles with rationale, fixes SDLC process gaps, and adds automated enforcement. Phases 2-3 (testing infrastructure, automation) build on this foundation.

## Acceptance Criteria

- [x] **AC-01:** All 23 principles (S1-S7, F1-F2, A1-A14) documented with statement, rationale, enforcement mechanism, and correct/incorrect examples [S4, F1]
- [x] **AC-02:** Principles doc follows progressive disclosure — compact SKILL.md for quick reference, full reference.md for deep context [S4]
- [x] **AC-03:** spec-writer agent exists that takes a vision statement and produces a complete spec draft [S5, F1]
- [x] **AC-04:** All domain agents (database, backend, frontend, deployment) restructured as principle-based with decision framework, post-review fix process, and recovery process [P2, P3, P7]
- [x] **AC-05:** Orchestrator includes breakdown validation, UAT-per-PR process, re-review loop (max 3 rounds), and agent recovery routing [P4, P6]
- [x] **AC-06:** Reviewer outputs structured VERDICT with principle ID references on blockers [I5]
- [x] **AC-07:** UAT tester uses AC-ID test naming convention (test_ac_NN_description) [I5]
- [x] **AC-08:** validate-patterns.sh hook enforces: RLS on new tables (A8), no DB ops in routers (A1), no useAuthStore in API hooks (A5), tool naming (A10) [I2]
- [x] **AC-09:** TEMPLATE.md includes AC stable IDs, AC-to-test mapping, and completeness checklist [I5]
- [x] **AC-10:** End-to-end recipes added to backend-patterns (new tool, new endpoint, data planes), frontend-patterns (new page), product-architecture (new channel) [F1]
- [x] **AC-11:** CLAUDE.md slimmed to ~60 lines; domain-specific gotchas moved to respective skills [S7]
- [x] **AC-12:** Agent definitions target ~80 lines each with principle references replacing verbose checklists [P7]

## Scope

### Files Created

| File | Purpose |
|------|---------|
| `.claude/skills/architecture-principles/SKILL.md` | Compact principle table (54 lines) |
| `.claude/skills/architecture-principles/reference.md` | Full rationale and examples (752 lines) |
| `.claude/agents/spec-writer.md` | Vision-to-spec pipeline agent |
| `docs/sdlc/ARCHITECTURE-PRINCIPLES.md` | Pointer to the skill |

### Files Modified

| File | Change |
|------|--------|
| `.claude/agents/orchestrator.md` | +breakdown validation, +UAT-per-PR, +re-review loop, +recovery |
| `.claude/agents/reviewer.md` | +structured VERDICT format with principle IDs |
| `.claude/agents/uat-tester.md` | +AC-ID test naming, +per-PR UAT scope |
| `.claude/agents/database-dev.md` | Principle-based restructure, +fix/recovery process |
| `.claude/agents/backend-dev.md` | Same restructure |
| `.claude/agents/frontend-dev.md` | Same restructure |
| `.claude/agents/deployment-dev.md` | Same restructure |
| `.claude/hooks/validate-patterns.sh` | +4 new checks (A1, A5, A8, A10) |
| `.claude/skills/backend-patterns/SKILL.md` | +3 recipes, +4 gotchas |
| `.claude/skills/frontend-patterns/SKILL.md` | +1 recipe, +4 gotchas |
| `.claude/skills/product-architecture/SKILL.md` | +1 recipe |
| `.claude/skills/database-patterns/SKILL.md` | +1 gotcha |
| `.claude/skills/integration-deployment/SKILL.md` | +3 gotchas |
| `.claude/skills/sdlc-workflow/SKILL.md` | +spec-writer, uat-tester in team table |
| `CLAUDE.md` | Slimmed from 267 to ~60 lines |
| `docs/sdlc/specs/TEMPLATE.md` | +AC IDs, +test mapping, +completeness checklist |

### Out of Scope

- Phase 2: Playwright setup, API integration tests, migration validation in CI
- Phase 3: Auto-merge pipeline, post-deploy smoke test, deploy notifications, trust escalation

## Gaps Closed

| Gap | Description | Items |
|-----|-------------|-------|
| I2 | Principles enforced by docs, not hooks | 4 new hook checks |
| I4 | Principles not documented with rationale | architecture-principles skill |
| I5 | No structured reviewer verdict / AC traceability | VERDICT format, AC-ID naming |
| P1 | No vision-to-spec pipeline | spec-writer agent |
| P2 | Post-review fix process undefined | Fix process in all agents |
| P3 | No retry/recovery for stuck agents | Recovery process in all agents |
| P4 | Orchestrator breakdown quality has no validation | Breakdown validation step |
| P6 | UAT runs on integration branch only | Per-PR verification step |
| P7 | Agent instructions checklist-based, not principle-based | All agents restructured |
| F1 | Architecture gaps (no recipes) | End-to-end recipes in 3 skills |
| S7 | Knowledge not compounding into skills | Gotchas distributed to skills |
