# Implementation Plan: Next-Gen Architecture Sprint

> **Goal:** Get to Phase 3 (bwrap sandbox + self-improving agent) as fast as possible.
> **Created:** 2026-04-06

## Strategic Decisions

1. **SPEC-034 (Capability Gateway) — SKIPPED.** Current tool system stays via bridge adapter. Tools become CLI commands in bwrap sandbox.
2. **Drop LangChain format entirely.** Anthropic-native message storage from day one.
3. **SPEC-035 minimized.** Config read path only — just enough for template loading.
4. **Provider-agnostic bwrap.** Linux namespace level. Works on Fly, Hetzner, anywhere.

## Status

| Spec | Status | Branch | Notes |
|------|--------|--------|-------|
| SPEC-033 | **COMPLETE** | `feat/SPEC-033-conversation-handler` | 1090 tests pass |
| SPEC-035 | **COMPLETE** | `feat/SPEC-035-config-service` | 27 tests, merged |
| SPEC-036 | **IN PROGRESS** | — | Agent spawning now |
| SPEC-037 | Pending | — | Blocked on 036 |
| SPEC-038 | Spec written | — | Needs review |
| SPEC-039 | Spec written | — | Needs review |
| SPEC-040 | Spec written | — | Needs review |

## Dependency Graph

```
Wave 1 (COMPLETE):
  ├─ SPEC-033: Conversation Handler          [COMPLETE - 1090 tests]
  ├─ SPEC-035: Config Service (minimal)      [COMPLETE - 27 tests]
  └─ Write SPECs 038-040 (Phase 3)           [COMPLETE - 1413 lines]

Wave 2 (ACTIVE):
  └─ SPEC-036: Workflow Engine               [IN PROGRESS]

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
| 2026-04-06 | SPEC-033 FU-4+5 complete (channel adapters + error handling) |
| 2026-04-06 | SPEC-033 fully complete — 1090 tests pass, 0 failures |
| 2026-04-06 | SPEC-035 merged into 033 branch. Starting Wave 2. |
