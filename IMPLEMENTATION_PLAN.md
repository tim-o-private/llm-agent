# Implementation Plan: Next-Gen Architecture Sprint

> **Goal:** Get to Phase 3 (bwrap sandbox + self-improving agent) as fast as possible.
> **Branch:** `feat/next-architecture-sprint`
> **Created:** 2026-04-06

## Strategic Decisions

1. **SPEC-034 (Capability Gateway) — SKIPPED.** Current tool system stays. Bridge adapter in SPEC-033 is sufficient. Tools become CLI commands in the sandbox (Phase 3) — gateway pattern emerges from filesystem naturally.
2. **Drop LangChain format entirely.** Store messages in Anthropic-native format. Use assistant-stream SSE from day one. No backward compat with unused system.
3. **SPEC-035 minimized.** Config read path only — no REST API, no elaborate caching. Just enough for template loading. Real config system is bwrap (files on disk, git-tracked).
4. **Provider-agnostic bwrap.** Linux namespace level, not infrastructure level. Persistent disk + unprivileged user namespaces. Works on Fly, Hetzner, anywhere.

## Dependency Graph

```
Wave 1 (parallel — no cross-deps):
  ├─ SPEC-033: Conversation Handler          [PENDING]
  ├─ SPEC-035: Config Service (minimal)      [PENDING]
  └─ Write SPECs 038-040 (Phase 3)           [PENDING]
       └─ Backend-dev review of specs         [BLOCKED on spec writing]

Wave 2 (needs 033 + 035):
  └─ SPEC-036: Workflow Engine               [BLOCKED on 033, 035]

Wave 3 (needs 036):
  └─ SPEC-037: Initial Workflows             [BLOCKED on 036]

Wave 4 (needs 037 + specs 038-040 approved):
  ├─ SPEC-038: bwrap Provisioning            [BLOCKED on spec approval + 037]
  ├─ SPEC-039: Security Boundary             [BLOCKED on 038]
  └─ SPEC-040: Introspection Loop            [BLOCKED on 039]
```

## Spec Modifications (vs. original drafts)

### SPEC-033 Changes
- Drop LangChain message format entirely — store in Anthropic-native format
- Use assistant-stream SSE format from day one (not custom JSON-per-line)
- Message history adapter becomes one-time migration, not ongoing translator
- No backward compat with LangChain-based channels

### SPEC-034 Status
- **SKIPPED** — current tool system retained through SPEC-033's LangChainToolBridge
- Tools migrate to CLI commands in bwrap sandbox (Phase 3), not to a Python gateway

### SPEC-035 Changes
- Minimal read path only: ConfigService.read() with overlay resolution
- No REST API endpoints (AC-11 through AC-14 deferred)
- No elaborate caching layers (simple dict + cache-bust-on-write)
- No migration scripts (lazy fallback sufficient)
- Just enough for SPEC-036 to load workflow templates

### SPEC-036 Changes
- Template format kept (hot-loading is the point)
- LangGraph checkpointer kept (draft-reply human gate needs it)
- Progress events simplified — write to chat history inline, not separate event table

### SPEC-037 Changes
- Kept as-is — these are the first templates the agent will iterate on
- Markdown files, not Python code

## Phase 3 Specs (to be written)

### SPEC-038: bwrap Sandbox Provisioning
- Per-user Linux namespace via bubblewrap
- Filesystem layout: /system/ (ro), /user/ (rw, git-tracked), /tools/ (ro), /tmp/ (rw)
- Persistent disk (provider-agnostic — Fly volume or Hetzner block storage)
- CLI tool binaries mounted read-only
- Credential injection via scoped env vars (not filesystem)
- Hydrate user tree from Supabase Storage on first provision

### SPEC-039: Security Boundary + Self-Improvement
- Immutable security layer (read-only bind mounts, kernel-enforced)
- Agent writes to /user/ only — allowlists/tiers in /system/ (immutable)
- Git tracks all changes — changelog = git log, rollback = git revert
- Diff-based approval flow for non-security config changes
- Auto-rollback on behavioral metric degradation
- Sync changes back to Supabase Storage

### SPEC-040: Introspection Loop
- Scheduled workflow (runs on SPEC-036 engine)
- Reviews agent performance, proposes prompt adjustments
- Creates new workflows, capability requests (subject to security boundary)
- Changelog view via git history
- Disclosure model tied to trust tier

## Progress Log

| Date | Event |
|------|-------|
| 2026-04-06 | Plan created. Wave 1 agents spawned. |
