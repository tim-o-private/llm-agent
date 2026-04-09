# SPEC-043: Deep Agents Runtime — Replace ConversationHandler with LangChain Deep Agent

> **Status:** Draft
> **Author:** Claude (spec-writer) + Claude (architect review)
> **Created:** 2026-04-07
> **Updated:** 2026-04-07
> **Supersedes:** SPEC-042 (Sandbox Config Authority)
> **Builds on:** SPEC-033 (ConversationHandler — already shipped), SPECs 038-041 (sandbox infrastructure — already shipped)
> **References:** ARCHITECTURE-PROPOSAL-next-gen.md, PRODUCT-BEHAVIOR-SPEC-next-architecture.md, `.claude/skills/deep-agents/` (verified API reference)

---

## Goal

Replace the custom ConversationHandler v2 (a ~530 LOC Anthropic Messages API while-loop) with a LangChain Deep Agent instance. Deep Agents is LangChain's port of the Claude Code agent harness onto LangGraph. It provides built-in file tools (`read_file`, `write_file`, `edit_file`, `ls`, `glob`, `grep`), skill discovery (SKILL.md format), planning tools (`write_todos`), subagent spawning (`task`), middleware stack, and auto-summarization.

**Why this matters:** The current agent is a dumb tool-loop. It can search Gmail and create tasks but cannot read its own configuration, discover skills, write observations, or improve itself. The architecture proposal calls for hq-like autonomy: file-based config, self-improvement, introspection. Building this capability piecemeal means reimplementing what Deep Agents provides out of the box.

**Why Deep Agents over Agent SDK:** Deep Agents is model-agnostic (supports Anthropic, OpenAI, Google via LangGraph). The Agent SDK locks to Anthropic and spawns CLI subprocesses, making it unsuitable for multi-tenant web. Deep Agents runs in-process as a LangGraph `CompiledStateGraph`.

**Why now:** SPECs 038-041 built the sandbox infrastructure (bwrap, provisioner, git tracker, security boundary). SPEC-042 drafted the file-based config loading. Deep Agents renders the custom config-loading machinery unnecessary because it provides skill discovery, file I/O, and prompt assembly natively. We get further faster by adopting Deep Agents than by continuing to build custom equivalents.

**Package:** `deepagents` v0.5.0 (Beta, MIT, Python >=3.11). `pip install deepagents`. Returns a `CompiledStateGraph` — all LangGraph primitives (`.stream()`, `.ainvoke()`, checkpointing, human-in-the-loop) work on the result.

---

## What Changes and What Stays

### Replaced (deleted or deprecated)

| Component | LOC | Replaced By |
|-----------|-----|-------------|
| `chatServer/services/conversation_handler.py` | 529 | Deep Agent instance (`CompiledStateGraph`) |
| `chatServer/services/conversation_handler_builder.py` | 246 | `build_deep_agent()` (new) |
| `chatServer/services/prompt_builder.py` | 329 | Deep Agents' skill loading + `system_prompt` parameter |
| `chatServer/services/langchain_tool_bridge.py` | 75 | Deleted — Deep Agents accepts `BaseTool` natively via `tools=` |
| `src/core/agent_loader_db.py` (v1 AgentExecutor path) | 999 | Deprecated entirely — no reason to keep two legacy paths |
| SPEC-042 (Sandbox Config Authority) | spec | Superseded — Deep Agents provides the READ PATH natively |

### Stays unchanged

| Component | LOC | Notes |
|-----------|-----|-------|
| `chatServer/tools/*.py` (all BaseTool subclasses) | 3,188 | Deep Agents accepts `BaseTool` via `tools=` parameter natively |
| `chatServer/services/` (all business services) | ~6,229 | notification, OAuth, audit, task, briefing, etc. |
| `chatServer/sandbox/` (bwrap infrastructure) | 1,474 | Remains the WRITE PATH for self-improvement |
| `chatServer/workflows/` (LangGraph workflow engine) | 1,617 | Deep Agents IS LangGraph; workflows coexist |
| `chatServer/services/sse_stream.py` | 64 | Adapted to wrap Deep Agent stream events (not deleted) |
| `chatServer/services/message_history_adapter.py` | ~120 | Still loads/saves to `chat_message_history` |
| `chatServer/services/config_service.py` | 254 | Backs the custom `BackendProtocol` implementation |
| `chatServer/security/tool_wrapper.py` | ~110 | Approval wrapping still applies to BaseTool instances |
| All DB tables | — | 88% unchanged. `agent_configurations`, `tools`, `agent_tools` become secondary to file-based config |
| All routers | — | Call sites change from ConversationHandler to Deep Agent |
| All callers (main.py, telegram_bot.py, session_open_service.py, scheduled_execution_service.py) | — | Import changes only |

### Modified (adapter changes)

| Component | Change |
|-----------|--------|
| `chatServer/main.py` (chat endpoint, lines 300-406) | Replace `build_conversation_handler` with `build_deep_agent`; adapt SSE streaming |
| `chatServer/channels/telegram_bot.py` (line 530-565) | Replace `build_conversation_handler` with `build_deep_agent` |
| `chatServer/services/session_open_service.py` (line 182-202) | Replace `_invoke_v2` internals |
| `chatServer/services/scheduled_execution_service.py` (line 254-289) | Replace `_execute_v2` internals |
| `chatServer/config/settings.py` | New feature flag `DEEP_AGENT_ENABLED` alongside existing `CONVERSATION_HANDLER_V2` |

---

## Acceptance Criteria

### Deep Agent Core

- [ ] **AC-01:** A `build_deep_agent()` function exists at `chatServer/services/deep_agent_builder.py` that constructs a configured Deep Agent (`CompiledStateGraph`) given `(user_id, agent_name, session_id, channel)`. Uses `create_deep_agent()` from the `deepagents` package. [A1, A11]
- [ ] **AC-02:** Deep Agent is instantiated with a custom `BackendProtocol` implementation that provides per-user file isolation. The backend implements all 6 required methods (`ls`, `read`, `write`, `edit`, `grep`, `glob`) backed by `ConfigService` (Supabase Storage). [A8, A13]
- [ ] **AC-03:** Deep Agent discovers and loads `SKILL.md` files via the `skills=["/skills/"]` parameter. System skills (soul, identity, safety, tool-guidance, operating-model) come from Supabase Storage `/system/skills/`; user skills from `/users/{user_id}/skills/`. [A2, A13]
- [ ] **AC-04:** User skills with the same name as system skills override (shadow) them. This is enforced by the backend's overlay resolution: user path checked first, system path as fallback. Deep Agents' `last source wins` precedence handles the rest. [A13]
- [ ] **AC-05:** The Deep Agent's system prompt is assembled from discovered skills plus a `system_prompt=` parameter for channel-specific guidance. The assembled prompt produces equivalent behavioral output to the current `build_agent_prompt()` for the same inputs (soul, identity, channel guidance, tool guidance, memory notes, user instructions). [S1]
- [ ] **AC-06:** Existing `BaseTool` subclasses from `chatServer/tools/*.py` are registered with the Deep Agent via `tools=[...]` without modification to the tool classes themselves. [A6, A14]

### Skill Seeding

- [ ] **AC-07:** A seed script `scripts/seed_skills.py` extracts current behavioral content from `agent_configurations` table columns (`soul`, `identity`, `prompt_template`) and writes them as `SKILL.md` files to Supabase Storage at `system/skills/`. [A2]
- [ ] **AC-08:** Seed script creates at minimum: `clarity-soul/SKILL.md`, `clarity-identity/SKILL.md`, `safety-guidelines/SKILL.md`, `tool-guidance/SKILL.md`, `operating-model/SKILL.md`, `channel-guidance/SKILL.md`. Each has YAML frontmatter with `name` and `description` fields (description capped at 1024 chars per Deep Agents spec). [A2]
- [ ] **AC-09:** Seed script converts existing `user_agent_prompt_customizations` rows into user-layer skill files at `users/{user_id}/skills/communication-preferences/SKILL.md`. [A13]
- [ ] **AC-10:** Seed script is idempotent (uses `ConfigService.write_system()` / `ConfigService.write()` with upsert semantics). [S1]

### Security Boundary

- [ ] **AC-11:** Deep Agent file tools (`read_file`, `write_file`, `edit_file`, `ls`, `glob`, `grep`) operate within the user's backend namespace. The agent cannot read or write files outside its namespace. Enforced by the `BackendProtocol` implementation, not by middleware. [A8, A12]
- [ ] **AC-12:** System skills namespace is read-only to the agent. Write/edit operations targeting `/system/` paths are rejected by the backend implementation before execution, returning an error result. [A12]
- [ ] **AC-13:** The `SecurityBoundary` class from `chatServer/sandbox/security_boundary.py` is called within the backend's `write()` and `edit()` methods to classify paths as immutable/mutable. Mutable paths: `/user/**`. Immutable paths: `/system/**`. [A12]
- [ ] **AC-14:** File write operations to mutable paths trigger the existing `SelfImprovementService` flow: commit via `GitTracker`, generate diff, send approval notification, revert on rejection. This is triggered by the backend's `write()` and `edit()` methods, not middleware. [A12]

### Streaming & Channel Integration

- [ ] **AC-15:** The chat endpoint (`POST /api/chat` with `Accept: text/event-stream`) returns SSE events from the Deep Agent's `.stream()` method. Event format is compatible with the existing frontend contract: `text_delta`, `tool_start`, `tool_result`, `message_complete`, `error`. Stream uses `stream_mode=["updates", "messages"]` and `version="v2"`. [A7]
- [ ] **AC-16:** Non-streaming chat endpoint (`POST /api/chat`) returns a complete `ChatResponse` with the Deep Agent's final text response via `.ainvoke()`. [A7]
- [ ] **AC-17:** Telegram channel (`_handle_telegram_v2`) works with Deep Agent via `.ainvoke()`, producing a complete text response. [A7]
- [ ] **AC-18:** Scheduled execution (`_execute_v2`) works with Deep Agent via `.ainvoke()`, producing a complete text response for notification delivery. [A7]
- [ ] **AC-19:** Session open (`_invoke_v2`) works with Deep Agent via `.ainvoke()`, supporting both bootstrap (new user) and returning-user flows. [A7]

### Feature Flag & Fallback

- [ ] **AC-20:** A new feature flag `DEEP_AGENT_ENABLED` (env var, default `false`) controls Deep Agent activation. When `false`, the system uses the existing ConversationHandler v2 path. [A14]
- [ ] **AC-21:** The feature flag is checked at the same routing point as `CONVERSATION_HANDLER_V2` in `chatServer/main.py` (line 278). The three-way routing is: Deep Agent > ConversationHandler v2 > ChatService v1. [A14]
- [ ] **AC-22:** When Deep Agent is enabled but construction fails (e.g., `deepagents` library error, backend unavailable), the system falls back to ConversationHandler v2 with a warning log. No user-visible error. [A14]

### Introspection Loop Fixes (ported from SPEC-042 FU-4/5/6)

- [ ] **AC-23:** `gather_metrics` and `apply_improvements` service nodes are registered with `GraphBuilder` so the introspection workflow can execute. [S1]
- [ ] **AC-24:** The introspection template's step prompts reference actual skill file paths (`/user/skills/communication-preferences/SKILL.md`) instead of non-existent paths. Steps 1 and 4 are `node_type: service`, steps 2 and 3 are LLM steps. [S1]
- [ ] **AC-25:** `gather_metrics` reads skill files from the user's backend namespace (via direct `ConfigService.read()` call, not through Deep Agent's file tools). [S1]
- [ ] **AC-26:** `apply_improvements` writes `SKILL.md` files through the SelfImprovementService approval flow. [A12]
- [ ] **AC-27:** An API endpoint `POST /api/introspection/trigger` allows manual introspection triggering for testing. Gated on `ENVIRONMENT != "production"`. [S1]
- [ ] **AC-28:** A job handler `handle_introspection` in `job_handlers.py` triggers the introspection workflow for a given user via the job queue. Default schedule: weekly. [A11]

### Legacy Cleanup

- [ ] **AC-29:** `src/core/agent_loader_db.py` v1 path (AgentExecutor construction) is deprecated: marked with a deprecation warning, not deleted. All callers (session_open_service `_invoke_v1`, chat.py `process_chat`) still work but log deprecation. [A14]
- [ ] **AC-30:** `chatServer/services/langchain_tool_bridge.py` is deleted. No remaining callers after Deep Agent adoption (Deep Agents accepts `BaseTool` natively). [A14]

---

## Scope

### Files to Create

| File | Purpose |
|------|---------|
| `chatServer/services/deep_agent_builder.py` | `build_deep_agent()` — constructs Deep Agent via `create_deep_agent()` |
| `chatServer/services/deep_agent_backend.py` | `ClarityBackend` — implements `BackendProtocol` (6 methods) backed by ConfigService, with security boundary enforcement in `write()`/`edit()` |
| `chatServer/services/deep_agent_stream.py` | SSE adapter: Deep Agent `.stream()` v2 events → existing SSE format |
| `scripts/seed_skills.py` | Extracts DB content into SKILL.md files in Supabase Storage |
| `tests/chatServer/services/test_deep_agent_builder.py` | Unit tests for builder |
| `tests/chatServer/services/test_deep_agent_backend.py` | Unit tests for backend (all 6 protocol methods + security) |
| `tests/chatServer/services/test_deep_agent_stream.py` | Unit tests for stream adapter |

### Files to Modify

| File | Change |
|------|--------|
| `chatServer/main.py` | Add Deep Agent routing branch in chat endpoint |
| `chatServer/channels/telegram_bot.py` | Replace `build_conversation_handler` call in `_handle_telegram_v2` |
| `chatServer/services/session_open_service.py` | Replace `build_conversation_handler` call in `_invoke_v2` |
| `chatServer/services/scheduled_execution_service.py` | Replace `build_conversation_handler` call in `_execute_v2` |
| `chatServer/config/settings.py` | Add `deep_agent_enabled` flag |
| `chatServer/workflows/nodes/gather_metrics.py` | Update to read from ConfigService (skill file paths) |
| `chatServer/workflows/nodes/apply_improvements.py` | Update to write through SelfImprovementService |
| `chatServer/workflows/templates/introspection.py` | Fix step prompts and node types |
| `chatServer/services/job_handlers.py` | Add `handle_introspection` handler |
| `requirements.txt` (root) | Add `deepagents>=0.5.0,<0.6.0` |
| `chatServer/requirements.txt` (Docker) | Add `deepagents>=0.5.0,<0.6.0` |

### Files to Delete

| File | Reason |
|------|--------|
| `chatServer/services/langchain_tool_bridge.py` | Deep Agents accepts `BaseTool` natively |

### Out of Scope

- **Capability Gateway (SPEC-034)** — The gateway replaces BaseTool subclasses with thin executors. This spec keeps BaseTool subclasses as-is and registers them with Deep Agents directly. The gateway is a separate, independent effort.
- **Frontend changes** — SSE event format stays the same. No React component changes needed. The frontend is unaware of the runtime swap.
- **Workflow engine changes** — The existing `chatServer/workflows/` engine coexists with Deep Agents. Both run on LangGraph. The workflow engine handles multi-step graph workflows (email triage, briefings); Deep Agents handles the conversational agent loop. The `dispatch_workflow` tool bridges them.
- **bwrap process sandbox** — The bwrap infrastructure stays for write-path isolation. Deep Agents' file tools use the `ClarityBackend` (Supabase Storage), not the bwrap filesystem. When bwrap is enabled in the future, the backend can be swapped for a `FilesystemBackend`.
- **Database schema changes** — No migrations. The `agent_configurations`, `tools`, and `agent_tools` tables remain. They become the fallback data source during the transition period.
- **Multi-model support** — Deep Agents supports multiple LLM providers, but this spec uses Anthropic only (matching the current ConversationHandler behavior). Model-switching is a future capability.
- **Subagent spawning** — Deep Agents supports subagents via `task` tool, but this spec does not configure `subagents=`. The single-agent conversational model stays. Subagents are a Phase 3 (PRD-003) feature.
- **Config file browser API** — SPEC-035 covers the REST API for browsing/editing config files. Not in scope here.

---

## Technical Approach

### 1. Custom Backend Implementation (FU-1)

Deep Agents requires a backend implementing `BackendProtocol` — 6 methods that the built-in file tools (`read_file`, `write_file`, `edit_file`, `ls`, `glob`, `grep`) delegate to. Security enforcement lives here, not in middleware.

```python
# chatServer/services/deep_agent_backend.py
from deepagents.backends.protocol import (
    BackendProtocol, WriteResult, EditResult,
    LsResult, ReadResult, GrepResult, GlobResult,
    FileInfo, GrepMatch,
)
from chatServer.services.config_service import ConfigService
from chatServer.sandbox.security_boundary import SecurityBoundary

class ClarityBackend:
    """BackendProtocol implementation backed by Supabase Storage.

    - Reads use overlay resolution: user path > system fallback
    - Writes are restricted to /user/ namespace (SecurityBoundary)
    - Writes to mutable paths trigger SelfImprovementService
    """

    def __init__(
        self,
        config_service: ConfigService,
        user_id: str,
        security_boundary: SecurityBoundary,
        self_improvement_service: SelfImprovementService | None = None,
    ):
        self._config = config_service
        self._user_id = user_id
        self._boundary = security_boundary
        self._improvement = self_improvement_service

    def ls(self, path: str) -> LsResult:
        """Merged listing: user files shadow system files of same name."""
        # List from both system/ and users/{user_id}/ prefixes
        # Merge with user-wins precedence
        ...

    def read(self, file_path: str, offset: int = 0, limit: int = 2000) -> ReadResult:
        """Read with overlay: user path -> system fallback."""
        content = self._config.read(file_path, self._user_id)  # overlay built-in
        ...

    def write(self, file_path: str, content: str) -> WriteResult:
        """Write to user namespace only. Rejects /system/ paths."""
        classification = self._boundary.classify(file_path)
        if classification == "immutable":
            return WriteResult(success=False, error=f"Cannot write to immutable path: {file_path}")
        # Write via ConfigService to users/{user_id}/ namespace
        self._config.write(file_path, self._user_id, content)
        # Trigger self-improvement flow if service available
        if self._improvement:
            self._improvement.propose_change(
                file_path=file_path,
                new_content=content,
                description=f"Agent modification to {file_path}",
            )
        return WriteResult(success=True)

    def edit(self, file_path: str, old_string: str, new_string: str, replace_all: bool = False) -> EditResult:
        """Edit file in user namespace. Same security as write()."""
        classification = self._boundary.classify(file_path)
        if classification == "immutable":
            return EditResult(success=False, error=f"Cannot edit immutable path: {file_path}")
        # Read current content, apply edit, write back
        ...

    def grep(self, pattern: str, path: str | None = None, glob: str | None = None) -> GrepResult:
        """Search file contents across user + system namespaces."""
        ...

    def glob(self, pattern: str, path: str = "/") -> GlobResult:
        """Pattern-match filenames across user + system namespaces."""
        ...
```

The `ConfigService` at `chatServer/services/config_service.py` already implements overlay resolution (user path > system fallback) at lines 46-70. The `ClarityBackend` adapts this to `BackendProtocol`'s 6-method interface and adds security enforcement at the storage layer.

**Return types:** Each method returns a specific result type (`LsResult`, `ReadResult`, etc.) imported from `deepagents.backends.protocol`. These include `FileInfo(path, is_dir, size, modified_at)` for listings and `GrepMatch(path, line, text)` for search results.

**Why a custom backend instead of `StoreBackend`?** `StoreBackend` uses LangGraph's `BaseStore` abstraction which has a key-value API, not a file-tree API. Our data lives in Supabase Storage (bucket-based file storage), which maps better to `BackendProtocol`'s file-oriented methods. A custom backend also lets us embed security enforcement (immutable path rejection, self-improvement triggers) directly in the storage layer — defense at the deepest possible point.

### 2. Security via Backend (FU-2)

Security enforcement is implemented inside `ClarityBackend.write()` and `ClarityBackend.edit()`, not as separate middleware. Deep Agents' middleware system (`FilesystemMiddleware`, `TodoListMiddleware`, etc.) auto-configures built-in tools — there is no generic `before_write` middleware hook.

The security model:

1. **Read/ls/grep/glob**: allowed across both system and user namespaces. The agent can read its own skills and the system defaults.
2. **Write/edit**: allowed in user namespace only. The `SecurityBoundary.classify()` method (already implemented at `chatServer/sandbox/security_boundary.py`) rejects `/system/**` paths.
3. **Self-improvement flow**: writes to mutable paths optionally trigger `SelfImprovementService.propose_change()` which commits via `GitTracker`, generates a diff, and sends an approval notification.

This is defense-in-depth: Supabase Storage RLS provides namespace isolation at the database layer, and `SecurityBoundary` provides path classification at the application layer.

**Note on middleware:** Deep Agents auto-injects `FilesystemMiddleware`, `TodoListMiddleware`, `SubAgentMiddleware`, and `SummarizationMiddleware` by default. We don't need custom middleware for security — but we may want to configure:
- `ModelCallLimitMiddleware(run_limit=25)` to cap agent turns per request
- `SummarizationMiddleware` trigger thresholds tuned for our context window budget

These are configured in FU-4 (builder) as part of `create_deep_agent()` parameters, not as a separate FU.

### 3. Skill Seeding (FU-3)

The seed script extracts content from the `agent_configurations` table and creates SKILL.md files in Supabase Storage. Content mapping:

| DB Column | Skill File |
|-----------|-----------|
| `agent_configurations.soul` | `system/skills/clarity-soul/SKILL.md` |
| `agent_configurations.identity` (JSON) | `system/skills/clarity-identity/SKILL.md` |
| Safety content from `prompt_builder.py` constants | `system/skills/safety-guidelines/SKILL.md` |
| `OPERATING_MODEL` from `prompt_builder.py` | `system/skills/operating-model/SKILL.md` |
| `CHANNEL_GUIDANCE` from `prompt_builder.py` | `system/skills/channel-guidance/SKILL.md` |
| Tool `prompt_section()` outputs | `system/skills/tool-guidance/SKILL.md` |
| `INTERACTION_LEARNING_GUIDANCE` from `prompt_builder.py` | `system/skills/interaction-learning/SKILL.md` |
| `user_agent_prompt_customizations.instructions` | `users/{user_id}/skills/communication-preferences/SKILL.md` |

Each SKILL.md follows Deep Agents' frontmatter spec:

```yaml
---
name: clarity-soul
description: >
  Core behavioral philosophy for the Clarity agent.
  Defines personality, values, and interaction style.
---

# Clarity Soul

[content extracted from DB]
```

The `description` field is capped at 1024 characters per the Deep Agents spec. The seed script uses `ConfigService.write_system()` and `ConfigService.write()` which have upsert semantics (Supabase Storage `file_options={"upsert": "true"}`), making it idempotent.

### 4. Deep Agent Builder (FU-4)

The builder replaces `conversation_handler_builder.py` (246 LOC). It uses `create_deep_agent()` from the `deepagents` package.

```python
# chatServer/services/deep_agent_builder.py
from deepagents import create_deep_agent
from chatServer.services.deep_agent_backend import ClarityBackend

async def build_deep_agent(
    user_id: str,
    agent_name: str,
    session_id: str,
    channel: str = "web",
) -> CompiledStateGraph:
    """Build a Deep Agent for a user session.

    Parallels conversation_handler_builder.build_conversation_handler()
    but produces a CompiledStateGraph via create_deep_agent().
    """
    # 1. Load agent config from DB cache (model, temperature, etc.)
    agent_db_config = await get_cached_agent_config(agent_name)
    llm_config = agent_db_config.get("llm_config", {})
    model = llm_config.get("model", "claude-sonnet-4-5-20250514")

    # 2. Parallel fetch: tools, user instructions, memory notes
    cached_tools_data, user_instructions, memory_notes = await asyncio.gather(
        get_cached_tools_for_agent(str(agent_db_config["id"])),
        get_cached_user_instructions(user_id, agent_name),
        _prefetch_memory_notes(memory_client),
    )

    # 3. Instantiate + wrap tools
    instantiated_tools = load_tools_from_db(cached_tools_data, user_id, ...)
    wrap_tools_with_approval(instantiated_tools, approval_context)

    # 4. Create backend with security enforcement
    config_service = get_config_service()
    boundary = SecurityBoundary()
    backend = ClarityBackend(
        config_service=config_service,
        user_id=user_id,
        security_boundary=boundary,
        self_improvement_service=get_self_improvement_service(),
    )

    # 5. Build channel-specific system prompt (non-skill content)
    channel_prompt = _build_channel_prompt(channel, memory_notes, user_instructions)

    # 6. Create Deep Agent
    agent = create_deep_agent(
        model=f"anthropic:{model}",
        tools=instantiated_tools,           # BaseTool instances accepted natively
        system_prompt=channel_prompt,        # channel + memory + instructions
        backend=backend,                     # ClarityBackend (file tools delegate here)
        skills=["/skills/"],                 # auto-discover SKILL.md files via backend
        checkpointer=postgres_checkpointer,  # for human-in-the-loop / session persistence
    )

    return agent
```

**Key integration points:**

- `model=` uses `"provider:model"` format (e.g., `"anthropic:claude-sonnet-4-5-20250514"`)
- `tools=` accepts `BaseTool` instances directly — no conversion needed
- `backend=` receives our custom `ClarityBackend` — all file tools delegate to it
- `skills=["/skills/"]` tells Deep Agents to discover SKILL.md files under `/skills/` in the backend. Deep Agents reads these via `backend.read()`, which hits our overlay resolution (user skills shadow system skills)
- `system_prompt=` provides channel-specific, memory, and user instruction content that doesn't belong in skill files
- `checkpointer=` enables session persistence and human-in-the-loop (existing Postgres checkpointer from workflow engine)

**Invocation pattern:**

```python
# Non-streaming (Telegram, session_open, scheduled)
result = await agent.ainvoke(
    {"messages": [{"role": "user", "content": user_message}]},
    config={"configurable": {"thread_id": session_id}},
)
response_text = result["messages"][-1].content

# Streaming (web chat) — see FU-5
async for chunk in agent.astream(
    {"messages": messages},
    stream_mode=["updates", "messages"],
    config={"configurable": {"thread_id": session_id}},
    version="v2",
):
    yield translate_to_sse(chunk)
```

The builder preserves the caching pattern from `conversation_handler_builder.py` (TTLCache with 15-min TTL per `(user_id, agent_name)` key at line 30).

### 5. SSE Stream Adapter (FU-5)

Deep Agents streams via LangGraph's `.astream()` with `version="v2"` event format. The adapter translates these into the existing SSE event contract:

| Deep Agent Event (v2) | SSE Event Type | Notes |
|----------------------|---------------|-------|
| `type: "messages"`, message chunk with text | `text_delta` | `{"type": "text_delta", "text": "..."}` |
| `type: "updates"`, tool call start | `tool_start` | `{"type": "tool_start", "tool_name": "...", "tool_call_id": "..."}` |
| `type: "updates"`, tool call result | `tool_result` | `{"type": "tool_result", "tool_call_id": "...", "result": "..."}` |
| Stream complete | `message_complete` | `{"type": "message_complete", "token_usage": {...}}` |
| Error | `error` | `{"type": "error", "message": "..."}` |

**Event identification:** v2 events include `ns` (namespace tuple) — `()` for the main agent, `("tools:<id>",)` for subagent events. For this spec (no subagents), only `ns == ()` events are forwarded.

The existing `sse_stream.py` (64 LOC) defines `_format_sse()` which converts `StreamEvent` dataclasses to SSE lines. The adapter produces `StreamEvent` instances from Deep Agent events, so the formatting layer stays unchanged.

### 6. Caller Integration (FU-6)

Four callers currently import and use `build_conversation_handler`:

1. **`chatServer/main.py`** (lines 307, 369) — chat endpoint, streaming and non-streaming
2. **`chatServer/channels/telegram_bot.py`** (line 535) — Telegram handler
3. **`chatServer/services/session_open_service.py`** (line 190) — session open
4. **`chatServer/services/scheduled_execution_service.py`** (line 266) — scheduled/heartbeat runs

Each caller changes from:
```python
from ..services.conversation_handler_builder import build_conversation_handler
handler = await build_conversation_handler(user_id, agent_name, session_id, channel)
result = await handler.run(messages)
```
To:
```python
from ..services.deep_agent_builder import build_deep_agent
agent = await build_deep_agent(user_id, agent_name, session_id, channel)
result = await agent.ainvoke(
    {"messages": messages},
    config={"configurable": {"thread_id": session_id}},
)
```

The feature flag in `chatServer/main.py` (line 278) adds a third routing tier:
```python
if settings.deep_agent_enabled:
    # Deep Agent path
elif settings.conversation_handler_v2:
    # ConversationHandler v2 path
else:
    # Legacy ChatService v1 path
```

### 7. Introspection Loop Fixes (FU-7)

Ported from SPEC-042 FU-4/5/6. Three changes:

1. **Register service nodes** (`chatServer/workflows/run_manager.py`): Register `gather_metrics` and `apply_improvements` with `GraphBuilder` so the introspection workflow template can reference them.

2. **Fix template** (`chatServer/workflows/templates/introspection.py`): Update step definitions. Steps 1 and 4 are `node_type: service` (Python functions, not LLM calls). Steps 2 and 3 are LLM steps that receive step 1's output as context. Remove references to non-existent custom `read_file`/`write_file` tools — the introspection LLM steps don't need file tools because the service nodes handle file I/O directly.

3. **Add trigger** (`chatServer/services/job_handlers.py`): New `handle_introspection(user_id)` function that starts the introspection workflow. Register as a job handler for weekly scheduling. Add a debug API endpoint at `POST /api/introspection/trigger` (non-production only).

### Dependencies

| Dependency | What It Provides | Status |
|-----------|-----------------|--------|
| `deepagents>=0.5.0,<0.6.0` | `create_deep_agent()`, `BackendProtocol`, middleware stack | Pre-v1, add to both requirements.txt files |
| `langgraph>=1.1.6` | Already in requirements.txt | Available |
| `ConfigService` (SPEC-035) | Supabase Storage overlay resolution | **Implemented** at `chatServer/services/config_service.py` |
| `SecurityBoundary` (SPEC-039) | Path classification (immutable/mutable) | **Implemented** at `chatServer/sandbox/security_boundary.py` |
| `SelfImprovementService` (SPEC-039) | Proposal → commit → approve/reject flow | **Implemented** at `chatServer/sandbox/self_improvement.py` |
| `GitTracker` (SPEC-041) | Git versioning of config changes | **Implemented** at `chatServer/sandbox/git_tracker.py` |
| Supabase Storage bucket (`config`) | File storage | Created by `ConfigService.ensure_bucket()` |
| Python >= 3.11 | Required by `deepagents` package | **Verify** current project Python version |

---

## Testing Requirements

### Unit Tests (required)

Every new file gets unit tests. Key test scenarios:

| Test File | Covers |
|-----------|--------|
| `test_deep_agent_backend.py` | `ClarityBackend`: all 6 protocol methods, overlay resolution (user > system), security boundary enforcement (reject `/system/` writes, allow `/user/` writes), self-improvement trigger on write |
| `test_deep_agent_builder.py` | `build_deep_agent()`: correct `create_deep_agent()` call with expected params, tool registration, skill path config, cache behavior, fallback on failure |
| `test_deep_agent_stream.py` | SSE adapter: v2 event type mapping, namespace filtering, token usage forwarding, error handling |

### Integration Tests (required for API/DB changes)

- **Seed script**: run seed → verify files exist in Storage → run seed again → verify idempotent
- **End-to-end chat**: Deep Agent receives message → calls a tool → returns response (mocked LLM)
- **SSE streaming**: Deep Agent streams → SSE events match expected format
- **Security boundary**: write to `/system/` via backend → rejected; write to `/user/` → accepted
- **Fallback**: Deep Agent construction fails → graceful fallback to ConversationHandler v2

### AC-to-Test Mapping

| AC | Unit Test | Integration Test |
|----|-----------|-----------------|
| AC-01 | `test_build_deep_agent_returns_compiled_graph` | — |
| AC-02 | `test_backend_user_isolation` | — |
| AC-03 | `test_skill_discovery_both_namespaces` | `test_seed_then_discover_skills` |
| AC-04 | `test_user_skill_overrides_system` | — |
| AC-05 | `test_prompt_equivalence` | — |
| AC-06 | `test_basetool_registration` | `test_tool_call_roundtrip` |
| AC-07-10 | `test_seed_script_*` | `test_seed_idempotent` |
| AC-11-12 | `test_backend_namespace_isolation`, `test_backend_rejects_system_write` | — |
| AC-13 | `test_backend_uses_security_boundary` | — |
| AC-14 | `test_backend_write_triggers_self_improvement` | — |
| AC-15-16 | `test_sse_event_mapping` | `test_chat_endpoint_streaming` |
| AC-17 | — | `test_telegram_deep_agent` |
| AC-18 | — | `test_scheduled_deep_agent` |
| AC-19 | — | `test_session_open_deep_agent` |
| AC-20-22 | `test_feature_flag_routing` | `test_fallback_on_failure` |
| AC-23-28 | `test_introspection_*` | `test_introspection_trigger_endpoint` |
| AC-29 | `test_v1_deprecation_warning` | — |
| AC-30 | — (deletion) | — |

### Manual Verification (UAT)

- [ ] Set `DEEP_AGENT_ENABLED=true`, send a message via web chat. Verify response arrives with streaming.
- [ ] Verify agent can read its own skill files (ask "what are your skills?" or similar).
- [ ] Send a message via Telegram. Verify response arrives.
- [ ] Trigger session_open. Verify greeting appears.
- [ ] Trigger scheduled heartbeat. Verify notification delivered.
- [ ] Check SSE stream in browser devtools. Verify event format matches expectations.
- [ ] Set `DEEP_AGENT_ENABLED=false`. Verify ConversationHandler v2 path works unchanged.
- [ ] Trigger introspection via debug endpoint. Verify proposal notification.

---

## Edge Cases

1. **ConfigService unavailable at startup**: `build_deep_agent()` should catch `RuntimeError` from `get_config_service()` and fall back to ConversationHandler v2. Log warning.
2. **Empty skill store**: If no skills are seeded yet, Deep Agent should still function — `create_deep_agent()` works without skills. The `system_prompt=` parameter provides baseline behavior. The builder should provide a hardcoded fallback soul prompt via `system_prompt=`.
3. **Concurrent writes to same skill file**: Supabase Storage upsert is last-write-wins. The GitTracker in the sandbox records the history. Conflict resolution is out of scope (single-agent per user).
4. **Deep Agents library breaking change**: The library is pre-v1. Pin to `>=0.5.0,<0.6.0` to limit blast radius. Version bump requires spec amendment.
5. **Token usage tracking**: Deep Agent's LangGraph runtime tracks token usage in graph state metadata, differently than the direct Anthropic SDK's `response.usage`. The SSE adapter must extract token counts from LangGraph's response metadata. If unavailable, emit `message_complete` without `token_usage` (frontend handles `null` gracefully).
6. **Message format**: Deep Agents expects LangGraph message format (`{"role": "user", "content": "..."}` dicts or `HumanMessage`/`AIMessage` objects). The builder must convert from `chat_message_history` format if needed. The dict format should work directly.
7. **Tool name collision**: Deep Agents auto-injects built-in tools: `read_file`, `write_file`, `edit_file`, `ls`, `glob`, `grep`, `write_todos`, `task`. If any existing `BaseTool` has the same `name` attribute, the collision must be resolved by renaming the existing tool (none of our current tools use these names — verified against `TOOL_REGISTRY`).
8. **Python version**: `deepagents` requires Python >=3.11. Verify project's Python version before starting FU-1. If currently on 3.10 or lower, a Python upgrade is a prerequisite.
9. **`BackendProtocol` sync vs async**: The protocol methods are synchronous (`def`, not `async def`). If `ConfigService` methods are async, the backend implementation will need `asyncio.run()` or a sync wrapper. Verify during FU-1 implementation.

---

## Risk / Mitigation

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| **Deep Agents pre-v1 instability** | High | High | Feature flag (AC-20). Fallback to ConversationHandler v2 (AC-22). Pin version `<0.6.0`. Monitor release notes. |
| **`BackendProtocol` API changes** | Medium | Medium | Adapter pattern isolates the integration to one file (`deep_agent_backend.py`). If the protocol changes, only the backend implementation changes. |
| **Multi-tenant isolation bugs in Deep Agents** | Medium | Critical | Security enforcement at backend level (AC-11-13), not relying on Deep Agents for isolation. Supabase RLS provides additional layer. No known multi-tenant production deployments — we would be early. |
| **Performance regression** | Medium | Medium | LangGraph adds overhead vs direct Anthropic API. Benchmark first-token latency and total response time. Accept up to 500ms additional latency for skill loading. If worse, cache compiled graphs. |
| **Streaming format incompatibility** | Low | High | SSE adapter (FU-5) maps v2 events. If Deep Agents changes event schema, only the adapter file changes. Comprehensive test coverage of event mapping. |
| **`BackendProtocol` sync/async mismatch** | Medium | Medium | Protocol methods are sync. ConfigService may be async. Resolve in FU-1 — if blocking, use `asyncio.run_coroutine_threadsafe()` or convert ConfigService to support sync reads. |
| **Pivot to Agent SDK** | Low | High | If Deep Agents proves unviable after FU-1 (backend doesn't work as documented), the fallback plan is the Anthropic Agent SDK. The backend pattern partially ports — only the runtime integration changes. Decision checkpoint after FU-4. |

---

## Functional Units (Implementation Order)

Each unit gets its own branch and PR. Merge order is sequential (each depends on the prior).

### FU-1: Custom Backend (`ClarityBackend`)
**Branch:** `feat/SPEC-043-backend`
**Files:** `deep_agent_backend.py`, `test_deep_agent_backend.py`
**ACs:** AC-02, AC-04, AC-11, AC-12, AC-13, AC-14
**Why first:** Everything else depends on the backend. This is also the first integration test with the `deepagents` package — if `BackendProtocol` doesn't work as documented, we find out immediately. This FU validates: package installs correctly, protocol types import correctly, the 6-method contract is stable, and sync/async interop works.

### FU-2: Skill Seeding
**Branch:** `feat/SPEC-043-skill-seeding`
**Files:** `scripts/seed_skills.py`, test for seed script
**ACs:** AC-07, AC-08, AC-09, AC-10
**Depends on:** FU-1 (validates backend can read seeded files)

### FU-3: Deep Agent Builder + Feature Flag
**Branch:** `feat/SPEC-043-agent-builder`
**Files:** `deep_agent_builder.py`, `test_deep_agent_builder.py`, `settings.py` (flag)
**ACs:** AC-01, AC-03, AC-05, AC-06, AC-20, AC-22
**Depends on:** FU-1, FU-2 (backend and skills must exist)
**Decision checkpoint:** After FU-3, run manual smoke test. If Deep Agents fundamentally doesn't work (agent doesn't respond, skills don't load, tools don't fire), pivot decision happens here before investing in streaming and caller integration.

### FU-4: SSE Stream Adapter
**Branch:** `feat/SPEC-043-stream-adapter`
**Files:** `deep_agent_stream.py`, `test_deep_agent_stream.py`
**ACs:** AC-15
**Depends on:** FU-3

### FU-5: Caller Integration + Legacy Cleanup
**Branch:** `feat/SPEC-043-caller-integration`
**Files:** `main.py`, `telegram_bot.py`, `session_open_service.py`, `scheduled_execution_service.py`, delete `langchain_tool_bridge.py`
**ACs:** AC-15, AC-16, AC-17, AC-18, AC-19, AC-21, AC-29, AC-30
**Depends on:** FU-3, FU-4

### FU-6: Introspection Loop Fixes
**Branch:** `feat/SPEC-043-introspection`
**Files:** `run_manager.py`, `introspection.py` (template), `gather_metrics.py`, `apply_improvements.py`, `job_handlers.py`, introspection router
**ACs:** AC-23, AC-24, AC-25, AC-26, AC-27, AC-28
**Depends on:** FU-1 (backend for skill file reads)
**Can parallelize with:** FU-4, FU-5 after FU-3 is merged

---

## Postgres Deprecation Path

After FU-5 is validated in production with `DEEP_AGENT_ENABLED=true`:

| Column/Table | Post-Migration Status | Removal Timeline |
|---|---|---|
| `agent_configurations.soul` | Fallback only — primary source is `system/skills/clarity-soul/SKILL.md` | Drop after 2 stable releases |
| `agent_configurations.identity` | Fallback only — primary source is `system/skills/clarity-identity/SKILL.md` | Drop after 2 stable releases |
| `agent_configurations.prompt_template` | Fallback only — Deep Agent assembles from skills | Drop after 2 stable releases |
| `user_agent_prompt_customizations` | Fallback only — primary source is user skill files | Drop after 2 stable releases |
| `agent_configurations.llm_config` | **Keep** — operational config (model, temperature), not behavioral | Stays |
| `tools` table | **Keep** — tool registry, used by builder to instantiate tools | Stays |
| `agent_tools` table | **Keep** — tool assignment per agent | Stays |
| All transactional tables | **Keep** | Stays |

---

## Relationship to Other Specs

| Spec | Relationship |
|------|-------------|
| **SPEC-033** (ConversationHandler) | Already implemented and in production behind `CONVERSATION_HANDLER_V2` flag. This spec replaces it with Deep Agent behind a new `DEEP_AGENT_ENABLED` flag. ConversationHandler becomes the middle tier in a three-way fallback. |
| **SPEC-034** (Capability Gateway) | Independent effort. This spec uses existing `BaseTool` subclasses registered directly with Deep Agent. When SPEC-034 ships, tool registration in the builder changes from `BaseTool` instances to gateway-backed executors. No blocker either direction. |
| **SPEC-035** (Config Service) | Already implemented at `chatServer/services/config_service.py`. This spec builds on it via `ClarityBackend`. |
| **SPEC-036** (Workflow Engine) | Coexists. The workflow engine runs LangGraph graphs for multi-step workflows. Deep Agent runs LangGraph for the conversational loop. The `dispatch_workflow` tool bridges them. |
| **SPEC-038-041** (Sandbox Infrastructure) | Already implemented. This spec integrates the security boundary and self-improvement services into `ClarityBackend`. |
| **SPEC-042** (Sandbox Config Authority) | **Superseded.** SPEC-042's FU-1 (seed), FU-2 (hydrator update), FU-3 (agent loading from file tree) are replaced by Deep Agent's built-in skill loading + `ClarityBackend`. FU-4/5/6 (introspection fixes) are ported to this spec as FU-6. |

---

## Decisions Requiring Your Input

1. **Decision checkpoint timing:** After FU-3, I propose a go/no-go decision on whether Deep Agents is viable. If the builder works and a basic smoke test passes, we proceed. If there are fundamental multi-tenant or stability issues, we pivot to Agent SDK or continue with ConversationHandler v2 + custom skill loading (SPEC-042 approach). Does that checkpoint placement feel right, or would you want it earlier (after FU-1)?

2. **Introspection schedule:** The default introspection frequency is weekly. Should it also be triggerable by user action (e.g., "review yourself" message) or only by scheduled job + debug endpoint?

3. **Python version:** `deepagents` requires Python >=3.11. Need to verify current project version. If upgrade needed, that's a prerequisite task.

---

## Completeness Checklist

- [x] Every AC has a stable ID (AC-01 through AC-30)
- [x] Every AC maps to at least one functional unit
- [x] Every cross-domain boundary has a contract (`BackendProtocol` 6-method interface, SSE event format, `create_deep_agent()` parameter contract)
- [x] Technical approach verified against actual `deepagents` v0.5.0 API (see `.claude/skills/deep-agents/`)
- [x] All import paths, package names, and function signatures verified against published docs and PyPI
- [x] Merge order is explicit and acyclic (FU-1 → FU-2 → FU-3 → FU-4/FU-5/FU-6)
- [x] Out-of-scope is explicit
- [x] Edge cases documented with expected behavior (including sync/async mismatch and Python version)
- [x] Testing requirements map to ACs
- [x] Risk/mitigation documented for pre-v1 dependency
- [x] Superseded specs identified (SPEC-042)
- [x] Relationship to adjacent specs documented
