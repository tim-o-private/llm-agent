# Implementation Plan: Next-Gen Architecture Sprint

> **Goal:** Get to Phase 3 (bwrap sandbox + self-improving agent) as fast as possible.
> **Created:** 2026-04-06

## Strategic Decisions

1. **SPEC-034 (Capability Gateway) — SKIPPED.** Current tool system stays via bridge adapter.
2. **Drop LangChain format entirely.** Anthropic-native message storage from day one.
3. **SPEC-035 minimized.** Config read path only — just enough for template loading.
4. **Provider-agnostic bwrap.** Linux namespace level, not infrastructure level.

## Status

| Spec | Status | Branch | Notes |
|------|--------|--------|-------|
| SPEC-033 | FU-1,2,3 complete, FU-4 partial, FU-5 pending | `feat/SPEC-033-conversation-handler` | Agent finishing FU-4/5 |
| SPEC-035 | Complete | `feat/SPEC-035-config-service` | 27 tests, 1032 regression pass |
| SPEC-036 | Pending | — | Blocked on 033+035 merge |
| SPEC-037 | Pending | — | Blocked on 036 |
| SPEC-038 | Spec written | — | Needs backend-dev review |
| SPEC-039 | Spec written | — | Needs backend-dev review |
| SPEC-040 | Spec written | — | Needs backend-dev review |

## Dependency Graph

```
Wave 1 (parallel):
  ├─ SPEC-033: Conversation Handler          [IN PROGRESS - finishing FU-4/5]
  ├─ SPEC-035: Config Service (minimal)      [COMPLETE]
  └─ Write SPECs 038-040 (Phase 3)           [COMPLETE]

Wave 2 (needs 033 + 035):
  └─ SPEC-036: Workflow Engine               [NEXT]

Wave 3 (needs 036):
  └─ SPEC-037: Initial Workflows             [BLOCKED]

Wave 4 (needs 037 + specs approved):
  ├─ SPEC-038: bwrap Provisioning            [BLOCKED]
  ├─ SPEC-039: Security Boundary             [BLOCKED]
  └─ SPEC-040: Introspection Loop            [BLOCKED]
```

## Progress Log

| Date | Event |
|------|-------|
| 2026-04-06 | Plan created. Wave 1 agents spawned. |
| 2026-04-06 | SPEC-035 complete (config service + 27 tests + agent loader integration) |
| 2026-04-06 | SPEC-033 FU-1 complete (conversation handler + bridge + adapter, 55 tests) |
| 2026-04-06 | Phase 3 specs written (038, 039, 040 — 1413 lines total) |
| 2026-04-06 | SPEC-033 FU-2+3 complete (SSE streaming + feature flag routing, 8 tests) |
| 2026-04-06 | SPEC-033 FU-4 partial (Telegram adapter + push utility extracted) |
| 2026-04-06 | Agent spawned to finish SPEC-033 FU-4/5 |
