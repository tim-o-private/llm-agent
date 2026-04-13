# Architecture Fidelity Review — SPECs 033-040

> **Date:** 2026-04-06
> **Reviewer:** Claude (Principal Engineer)
> **Branch:** `feat/SPEC-033-conversation-handler`
> **Scope:** All commits on branch vs `main` (28 commits, 103 files, ~14,500 LOC)
> **Compared against:** `PRODUCT-BEHAVIOR-SPEC-next-architecture.md`, `ARCHITECTURE-DESIGN-v0.1.md`

---

## Overall Assessment

The branch implements significant new infrastructure across SPECs 033-040. The core architectural patterns — direct Anthropic API tool-loop, LangGraph workflow engine, bwrap sandbox, git-tracked self-improvement — are **structurally faithful** to the proposal. Individual components are well-built in isolation. But **Phase 1 was skipped entirely**, creating a coherence problem: Phase 2-3 components execute through the old tool model via a bridge layer, and the new ConversationHandler can't actually dispatch workflows.

**Verdict: CONDITIONAL PASS** — the implemented components are sound, but the system isn't connected end-to-end due to the missing Capability Gateway.

---

## What's Faithfully Implemented

### ConversationHandler (Q1) — PASS

The tool-loop in `chatServer/services/conversation_handler.py` is exactly the "simple while loop" the proposal advocated. Clean separation of streaming (`run_stream()`) and non-streaming (`run()`) paths. SSE formatting in `sse_stream.py` is straightforward. Feature flag routing alongside old ChatService is correct.

**Key files:** `conversation_handler.py`, `conversation_handler_builder.py`, `sse_stream.py`

### Config Service (Q3 Phase A) — PASS with caveats

Overlay resolution in `chatServer/services/config_service.py` is correct: user path shadows system, Supabase Storage bucket, cache with invalidate-on-write. Simple and appropriate for MVP. See "Best Practices Issues" for caveats.

**Key files:** `config_service.py`, `20260406000001_config_bucket_rls.sql`

### Workflow Engine (Q4) — PASS

Template parser, `GraphBuilder`, `AnthropicEngine`, `AsyncPostgresSaver` checkpointer, `WorkflowRunManager` with background execution, human gates via `interrupt_before`. Solid port of the HQ model adapted for server-side multi-tenant execution.

**Key files:** `workflows/builder.py`, `workflows/engine.py`, `workflows/template_parser.py`, `workflows/checkpointer.py`, `workflows/run_manager.py`, `workflows/dispatch.py`

### bwrap Sandbox (Q3 Phase B) — PASS with caveat

Per-user namespace with ro-bind for system, rw for user, ro for tools, tmpfs scratch. Git-versioned user tree. Provisioner handles hydration from ConfigService. See network isolation issue below.

**Key files:** `sandbox/bwrap.py`, `sandbox/provisioner.py`, `sandbox/hydrator.py`

### Security Boundary + Self-Improvement — PASS with bug

Application-level path classification as defense-in-depth, propose/approve/reject flow, git-tracked changes. `DisclosureModel` correctly maps trust tiers to notification verbosity (Inform = full, Recommend = summary, Act = silent). See notification type bug below.

**Key files:** `sandbox/security_boundary.py`, `sandbox/self_improvement.py`, `sandbox/disclosure.py`, `sandbox/git_tracker.py`, `sandbox/changelog.py`

### Introspection Loop (Phase 3) — PASS

Workflow template with gather/analyze/propose/apply steps. Service nodes for signal gathering and change application. Step prompts are well-crafted with anti-pattern guidance.

**Key files:** `workflows/templates/introspection.py`, `workflows/nodes/gather_metrics.py`, `workflows/nodes/apply_improvements.py`

---

## Where There's Drift

### 1. BLOCKER: Capability Gateway was skipped entirely

The architecture proposal identified the Capability Gateway as one of three "key shifts":

> *"Capability Gateway replaces custom tool classes. Instead of BaseTool subclasses with embedded business logic, tools become thin wrappers that delegate to CLI tools or service endpoints. Auth tokens injected server-side, never exposed to the agent context."*

**What was built instead:** `LangChainToolBridge` (`langchain_tool_bridge.py`) — a temporary adapter converting existing `BaseTool` instances to Anthropic format. The builder (`conversation_handler_builder.py`) still:

- Loads tools from DB via `load_tools_from_db()`
- Instantiates `BaseTool` subclasses with embedded business logic
- Wraps them with `wrap_tools_with_approval()` (the old approval system)
- Translates via the bridge

**None of the gateway's responsibilities exist:** no allowlist check, no tier enforcement, no credential injection, no tool-definition-as-config.

**Impact:** Every new component (ConversationHandler, AnthropicEngine, workflow dispatch) must go through the old tool model. The new architecture's security and trust enforcement model doesn't exist.

### 2. Phase ordering was violated

The proposal specified Phase 0 → 1 → 2 → 3 with explicit dependencies:

| Phase | Proposed | Actual |
|-------|----------|--------|
| **0** | Config Service + ConversationHandler + Audit expansion | Config Service + ConversationHandler (**no audit**) |
| **1** | Capability Gateway + Trust Tiers + Remove LangChain | **Skipped entirely** |
| **2** | Workflow Engine | Done (SPEC-036/037) |
| **3** | bwrap + Security + Self-improvement | Done (SPEC-038/039/040) |

Phase 1 was the load-bearing phase — the one that replaces the old tool model before building on top of it. By skipping it, Phase 2-3 components are structurally correct but run through the legacy tool model via a bridge.

### 3. LangChain is not phased out

**Proposal:** *"LangChain is phased out. Keep only ChatMessageHistory temporarily."*

**Reality:**
- `session_open_service.py` still imports `AIMessage` from `langchain_core` and uses `load_agent_executor_db_async`
- The ConversationHandler exists **alongside** the old system, not replacing it
- Every tool is still a `BaseTool` subclass
- The bridge layer is explicitly labeled "temporary" but has no successor
- `langchain-anthropic` remains a dependency

### 4. `dispatch_workflow` is a stub in the ConversationHandler

`conversation_handler.py:89-93`:
```python
DISPATCH_WORKFLOW_RESPONSE = (
    "Workflow dispatch is not yet available. "
    "I'll handle this conversationally instead."
)
```

The tool is registered on every ConversationHandler instance but returns a hardcoded rejection. The real `dispatch.py` exists with a working implementation but isn't wired into the ConversationHandler's tool executors. The core architectural concept — *"one agent that sometimes talks and sometimes orchestrates"* — isn't connected end-to-end.

### 5. Workflow templates are Python modules, not config files

**Proposal:** Templates as Markdown files in Supabase Storage (`/system/workflows/`), discoverable via the Config Service, customizable via user overlay.

**Reality:** Python modules in `chatServer/workflows/templates/*.py` with `TEMPLATE` string constants. This means:

- Templates can't be modified by users via the file browser
- Templates don't participate in the overlay system
- The config-as-files vision doesn't extend to workflows
- User customization requires code changes, not config changes

### 6. No audit log expansion

Phase 0 item 3 called for audit entries on all capability invocations and config change tracking. This wasn't built. The `config_change_proposals` table captures self-improvement proposals, but general capability invocation auditing is absent.

---

## Best Practices Issues

### Duplicated tool-loop code

`ConversationHandler.run()` (~90 lines), `ConversationHandler.run_stream()` (~70 lines), and `AnthropicEngine.run()` (~80 lines) each implement the same Anthropic Messages API tool-loop independently. `_extract_text()` and `_content_to_dicts()` are copy-pasted between `conversation_handler.py:509-529` and `engine.py:184-204`.

**Recommendation:** Extract a shared Anthropic tool-loop primitive. The three implementations differ only in streaming vs. non-streaming and tool scoping (all tools vs. step-specific). A shared function would eliminate ~150 lines.

### ConfigService: sync calls inside async methods

`config_service.py:76-79,152`: `self._bucket().upload()`, `self._bucket().download()`, `self._bucket().list()` are called without `await` despite the methods being declared `async`. If `supabase-py`'s Storage API is synchronous, these block the event loop under load.

**Recommendation:** Verify whether these are actually async. If not, wrap in `asyncio.to_thread()` or use the async Supabase client's storage methods.

### ConfigService: no TTL on cache

The module-level `_cache` dict (`config_service.py:19`) has no TTL. The architecture proposal specified *"in-memory per user, TTL 60s."* In a multi-worker deployment, stale cache entries persist until explicit invalidation or restart.

**Recommendation:** Replace with `cachetools.TTLCache` (already a dependency) or add TTL-based expiry.

### WorkflowRunManager created per dispatch

`dispatch.py:45` constructs a new `WorkflowRunManager` for every `dispatch_workflow` call. Each instance has its own `_active_tasks` dict, so `cancel_run()` can never find a task that another instance started. The `GraphBuilder` is also re-created unnecessarily.

**Recommendation:** Make `WorkflowRunManager` a singleton or scope it per-user at the lifespan level.

### Notification type bug

`self_improvement.py:276`:
```python
notification_type = "silent" if trust_tier == "recommend" else "silent"
```

This is always `"silent"` regardless of trust tier. Inform tier should use `"notify"`.

### bwrap shares host network

`bwrap.py:139`: `--share-net` is included in the bwrap arguments. The architecture proposal stated *"NOT mounted: secrets, tokens, credentials, open network."* The behavior spec (Section 8) says *"Agents cannot make arbitrary HTTP requests."* Sharing the network contradicts both documents.

**Recommendation:** Remove `--share-net`. If specific network access is needed (e.g., for CLI tools calling APIs), use a proxy or allowlist at the network level, not blanket network sharing.

### GitTracker PATH restriction

`git_tracker.py:148`: `"PATH": "/usr/bin:/bin"` — excludes `/usr/local/bin`, which is where `git` lives on many systems (macOS, some Linux distros, Docker images).

**Recommendation:** Include `/usr/local/bin` or resolve the git binary path at init time.

### Template parser fragility

The regex-based Markdown parser (`template_parser.py`) uses fixed patterns like `### step-\d+:` and `- **key:**`. If a template doesn't match these exact patterns, it silently produces empty results. No validation errors for malformed steps.

**Recommendation:** When templates move to config files, use YAML or JSON — simpler to parse, more robust, better error messages.

---

## Simplification Opportunities

1. **Shared Anthropic tool-loop primitive.** The three tool-loop implementations differ only in streaming and scoping. A shared function eliminates ~150 lines of duplication and ensures bug fixes apply everywhere.

2. **YAML workflow templates.** Drop the custom Markdown parser. YAML is simpler to parse, more robust, and aligns with the config-as-files model where templates should live in Supabase Storage.

3. **Minimal Capability Gateway now.** Even a thin version (tool schemas as JSON config, executor dispatch table, no credential injection yet) would let you remove the bridge layer, stop instantiating `BaseTool` subclasses for the ConversationHandler path, and unblock the dispatch_workflow wiring.

4. **Simplify the builder.** `conversation_handler_builder.py` (216 lines) duplicates `agent_loader_db.py`'s loading logic. With a gateway, building a handler would be: read config → get tool schemas → create handler (~50 lines).

---

## Scorecard

| Component | Fidelity | Quality | Notes |
|-----------|----------|---------|-------|
| ConversationHandler | Faithful | Good | Clean tool-loop, streaming, error handling |
| Config Service | Faithful | Fair | Sync-in-async, no TTL, but correct pattern |
| Workflow Engine | Faithful | Good | Well-structured port from HQ |
| Workflow Templates | **Drifted** | Fair | Python modules instead of config files |
| bwrap Sandbox | Faithful | Good | Network isolation gap |
| Security Boundary | Faithful | Good | Correct path classification model |
| Self-Improvement | Faithful | Good | Notification bug, otherwise solid |
| Introspection Loop | Faithful | Good | Well-crafted prompts |
| **Capability Gateway** | **Missing** | N/A | Phase 1 skipped entirely |
| **LangChain removal** | **Not started** | N/A | Still primary code path |
| **dispatch_workflow wiring** | **Stub** | N/A | Real impl exists but not connected |
| **Audit expansion** | **Missing** | N/A | Phase 0 item 3 not built |

---

## Recommended Next Steps

1. **Wire `dispatch_workflow`** — Connect `workflows/dispatch.py` to the ConversationHandler's tool executors. This is the smallest change with the most architectural impact: it makes the "conversation + orchestration" vision real.

2. **Build minimal Capability Gateway** — Tool schemas as JSON, executor dispatch, allowlist stub. Removes bridge layer and unblocks trust tier enforcement.

3. **Move templates to config** — Migrate Python template modules to YAML/Markdown files in Supabase Storage. Enables user overlay customization.

4. **Fix bugs** — Notification type (always silent), bwrap network sharing, ConfigService async/TTL issues.

5. **Extract shared tool-loop** — Deduplicate the three Anthropic API tool-loop implementations.
