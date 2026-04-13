# Backend Message Flow: User to Agent and Back

## Overview

Every user message — whether from the web UI, Telegram, or a scheduled run — follows the same conceptual path: **authenticate → load agent → wrap tools → invoke → normalize response → return**. In practice, each channel reimplements this pipeline independently, with significant code duplication.

This document traces the flow for each channel, identifies the shared components, and proposes simplifications.

---

## Components

### Entry Points (one per channel)

| Channel | Entry Point | File |
|---------|------------|------|
| Web | `POST /api/chat` | `chatServer/main.py:273` |
| Telegram | `handle_message()` handler | `chatServer/channels/telegram_bot.py:242` |
| Scheduled | `BackgroundTaskService._execute_scheduled_agent()` | `chatServer/services/background_tasks.py:190` |
| Heartbeat | Same as Scheduled (config flag) | Same |

### Core Pipeline

```
┌──────────────┐    ┌────────────────┐    ┌──────────────────┐    ┌────────────┐
│   Channel    │───▶│  Agent Loader  │───▶│  Tool Wrapping   │───▶│  Invoke    │
│  (auth +     │    │  (config +     │    │  (approval tier  │    │  (LangChain│
│   session)   │    │   tools + prompt│    │   enforcement)   │    │   ainvoke) │
└──────────────┘    └────────────────┘    └──────────────────┘    └────────────┘
                                                                        │
                                                                        ▼
                                                                  ┌────────────┐
                                                                  │ Normalize  │
                                                                  │ Response   │
                                                                  └────────────┘
```

### Shared Services

| Service | Purpose | File |
|---------|---------|------|
| `DatabaseManager` | psycopg connection pool (min 2, max 10) | `chatServer/database/connection.py` |
| `SupabaseManager` | Supabase-py async client | `chatServer/database/supabase_client.py` |
| `AgentConfigCacheService` | TTL cache for `agent_configurations` rows (600s) | `chatServer/services/agent_config_cache_service.py` |
| `ToolCacheService` | TTL cache for `tools` + `agent_tools` join (300s) | `chatServer/services/tool_cache_service.py` |
| `UserInstructionsCacheService` | TTL cache for `user_agent_prompt_customizations` (120s) | `chatServer/services/user_instructions_cache_service.py` |
| `PromptBuilder` | Assembles system prompt from soul + identity + channel + instructions + tools | `chatServer/services/prompt_builder.py` |
| `ApprovalContext` + `wrap_tools_with_approval` | Intercepts tool `_arun` with tier check | `chatServer/security/tool_wrapper.py` |
| `AGENT_EXECUTOR_CACHE` | TTLCache (100 entries, 15 min) keyed by `(user_id, agent_name)` | `chatServer/main.py:75` |
| `BackgroundTaskService` | Session cleanup, cache eviction, scheduled runs, reminders | `chatServer/services/background_tasks.py` |

---

## Flow 1: Web (`POST /api/chat`)

```
Client POST /api/chat {agent_name, session_id, message}
  │
  ├── Auth: get_current_user (ES256 JWT from Authorization header)
  ├── DB conn: get_db_connection (psycopg pool)
  ├── Agent loader: get_agent_loader (returns `core.agent_loader` module)
  │
  ▼
ChatService.process_chat()
  │
  ├── 1. create_chat_memory(session_id, pg_conn)
  │      └── PostgresChatMessageHistory → AsyncConversationBufferWindowMemory (k=50)
  │
  ├── 2. get_or_load_agent_executor(user_id, agent_name, session_id, loader, memory)
  │      ├── Check AGENT_EXECUTOR_CACHE[(user_id, agent_name)]
  │      ├── Cache miss → async_load_agent_executor()
  │      │     └── load_agent_executor_db_async()
  │      │           ├── get_cached_agent_config(agent_name)     ─┐
  │      │           ├── get_cached_tools_for_agent(agent_id)     │ asyncio.gather()
  │      │           ├── get_cached_user_instructions(user_id)    │
  │      │           └── _fetch_memory_notes_async(user_id)      ─┘
  │      │           ├── load_tools_from_db() → instantiate tool classes
  │      │           ├── build_agent_prompt(soul, identity, channel, ...)
  │      │           └── CustomizableAgentExecutor.from_agent_config()
  │      │                 ├── Create LLM (ChatAnthropic or ChatGoogleGenerativeAI)
  │      │                 ├── Build ChatPromptTemplate
  │      │                 ├── Bind tools to LLM
  │      │                 └── RunnablePassthrough | prompt | llm_with_tools | ToolsAgentOutputParser
  │      └── Set executor.memory = this session's memory
  │
  ├── 3. Wrap tools with approval
  │      ├── Create ApprovalContext(user_id, session_id, agent_name, ...)
  │      └── wrap_tools_with_approval(executor.tools, context)
  │            └── For each tool: monkey-patch _arun with tier check
  │
  ├── 4. Execute: agent_executor.ainvoke({"input": message})
  │      └── LangChain AgentExecutor loop:
  │            ├── Load chat_history from memory (async)
  │            ├── Format prompt with system + history + input + scratchpad
  │            ├── Call LLM → get tool calls or final answer
  │            ├── If tool call: execute tool (through approval wrapper) → add to scratchpad → loop
  │            └── Return {"output": ..., "intermediate_steps": [...]}
  │
  ├── 5. Normalize response
  │      ├── Handle content block lists: list[{"text": ..., "type": "text"}] → string
  │      └── Extract tool info from intermediate_steps
  │
  ├── 6. Push to Telegram (best-effort, if user has linked account)
  │
  └── 7. Return ChatResponse{session_id, response, tool_name, tool_input, error}
```

---

## Flow 2: Telegram (`handle_message`)

```
Telegram webhook POST /api/telegram/webhook
  │
  ├── telegram_router passes update to TelegramBotService.process_update()
  │     └── aiogram Dispatcher.feed_update() → routes to handle_message()
  │
  ▼
handle_message(message)
  │
  ├── 1. Look up user_id from chat_id in user_channels table
  │
  ├── 2. Find or create session
  │      ├── Look up most recent web session for cross-channel sharing
  │      └── Ensure chat_sessions row exists
  │
  ├── 3. Load agent (SYNC, blocking event loop!)
  │      └── loop.run_in_executor(None, load_agent_executor_db(...))
  │            └── Same DB loading as web, but uses SYNC path
  │                (creates new Supabase client, no cache services)
  │
  ├── 4. Wrap tools with approval (same pattern as web, reimplemented)
  │
  ├── 5. Set up memory (reimplements ChatService.create_chat_memory)
  │      └── PostgresChatMessageHistory → AsyncConversationBufferWindowMemory
  │
  ├── 6. Execute: agent_executor.ainvoke({"input": message.text})
  │
  ├── 7. Normalize response (reimplements content block handling)
  │
  └── 8. Send response to Telegram (split at 4000 chars)
```

---

## Flow 3: Scheduled / Heartbeat

```
BackgroundTaskService.run_scheduled_agents() (every 60s)
  │
  ├── Reload schedules from agent_schedules table (every 1 min)
  ├── Check cron expressions for due schedules
  │
  ▼
_execute_scheduled_agent(schedule)
  │
  ├── If email digest → EmailDigestService (separate path)
  └── Otherwise → ScheduledExecutionService.execute(schedule)
        │
        ├── 1. Load agent (SYNC — load_agent_executor_db, no cache)
        ├── 2. Optional model override
        ├── 3. Create chat_sessions row
        ├── 4. Wrap tools with approval (reimplemented again)
        ├── 5. Build effective prompt (heartbeat gets checklist)
        ├── 6. Execute: agent_executor.ainvoke(...)
        ├── 7. Normalize response (reimplemented again)
        ├── 8. Store result in agent_execution_results
        ├── 9. Notify user (unless HEARTBEAT_OK)
        └── 10. Mark session inactive
```

---

## Agent Loading: Two Paths

There are two complete implementations of agent loading:

| | Sync (`load_agent_executor_db`) | Async (`load_agent_executor_db_async`) |
|---|---|---|
| **File** | `src/core/agent_loader_db.py:433` | `src/core/agent_loader_db.py:678` |
| **Used by** | Telegram, Scheduled | Web (via `ChatService`) |
| **Supabase client** | Creates new `create_client()` per call | Uses shared `get_supabase_client()` |
| **Caching** | Has its own cache path with `asyncio.run()` inside sync fn | Uses cache services natively |
| **Agent config** | Direct DB query | `AgentConfigCacheService` |
| **Tools** | `ToolCacheService` (via `asyncio.run()`) or fallback | `ToolCacheService` (native async) |
| **User instructions** | Direct DB query via sync Supabase | `UserInstructionsCacheService` |
| **Memory notes** | Direct DB query via sync Supabase | Async DB query |
| **Prompt assembly** | `build_agent_prompt()` | `build_agent_prompt()` (same) |
| **Lines of code** | ~245 | ~120 |

---

## Tool Instantiation

Tools are loaded from DB and instantiated via a registry pattern:

1. `agent_tools` (join table) links agents to `tools` table
2. `TOOL_REGISTRY` maps type strings → Python classes
3. CRUDTool gets special treatment: dynamic Pydantic model generation from `runtime_args_schema` JSON
4. Non-CRUD tools get their DB config merged into constructor kwargs
5. All tools receive `user_id`, `agent_name`, `supabase_url`, `supabase_key`

The tool loading is always synchronous (`load_tools_from_db`) regardless of which agent loading path is used.

---

## Caching Layers

```
Request
  │
  ├── AGENT_EXECUTOR_CACHE (main.py, TTLCache, 15min, 100 entries)
  │     Key: (user_id, agent_name) → CustomizableAgentExecutor
  │     Note: Memory is swapped per-request, so cached executor shares LLM + tools
  │
  ├── AgentConfigCacheService (600s TTL, background refresh)
  │     Key: agent_name → agent_configurations row
  │
  ├── ToolCacheService (300s TTL, background refresh)
  │     Key: agent_id → list of tool configs
  │
  └── UserInstructionsCacheService (120s TTL, on-demand)
        Key: "user_id:agent_name" → instructions text
```

The AGENT_EXECUTOR_CACHE sits on top: if it hits, none of the other caches matter for that request. Only when building a *new* executor do the lower caches participate.

---

## Problems and Simplification Opportunities

### 1. Three channels, three separate pipelines (HIGH)

The Telegram handler (`telegram_bot.py:242-408`) and `ScheduledExecutionService` each reimplement the full pipeline that `ChatService.process_chat()` already handles:
- Session lookup/creation
- Agent loading
- Tool approval wrapping
- Memory setup
- Agent invocation
- Response normalization

**Proposal:** Extract a `AgentInvocationService` (or expand `ChatService`) with a single method:

```python
async def invoke_agent(
    user_id: str,
    agent_name: str,
    session_id: str,
    message: str,
    channel: str = "web",
    chat_history: list | None = None,  # None = load from DB, [] = fresh
) -> AgentResponse:
```

All three channels call this. Channel-specific concerns (auth, session creation, response formatting) stay in the channel layer.

### 2. Sync agent loading is a dead weight (HIGH)

`load_agent_executor_db` (sync, 245 lines) exists alongside `load_agent_executor_db_async` (120 lines). The sync version creates throwaway Supabase clients and calls `asyncio.run()` to access the async cache services from sync context — which is fragile and blocks the event loop when called from Telegram's `run_in_executor`.

**Proposal:** Delete the sync path. Telegram and Scheduled should use the async path directly. The CLI can use `asyncio.run()` at the outermost layer if needed. This eliminates ~245 lines and one entire Supabase client lifecycle.

### 3. Memory is swapped on every request (MEDIUM)

The executor cache stores `(user_id, agent_name) → executor`, then *every request* replaces `executor.memory` with a new session-specific memory object. This works but is surprising — the "cached executor" is really just a cached LLM + tool binding, not a complete executor.

**Proposal:** Cache the LLM binding + tool list separately from the executor. Create the executor fresh per request with the correct memory. This makes the caching semantic honest and avoids mutating a shared object.

### 4. Response normalization is duplicated 3x (LOW)

The content-block-list → string normalization:
```python
if isinstance(output, list):
    output = "".join(block.get("text", "") ...)
```
Appears in:
- `chatServer/services/chat.py:318-322`
- `chatServer/channels/telegram_bot.py:395-401`
- `chatServer/services/scheduled_execution_service.py:140-149`

**Proposal:** Extract to a utility function `normalize_agent_output(raw) -> str`.

### 5. Approval wrapping is duplicated 3x (LOW)

The pattern of creating `AuditService` → `PendingActionsService` → `ApprovalContext` → `wrap_tools_with_approval` appears in:
- `chatServer/services/chat.py:291-308`
- `chatServer/channels/telegram_bot.py:339-353`
- `chatServer/services/scheduled_execution_service.py:103-121`

**Proposal:** Move into `AgentInvocationService` (see #1) or extract a `create_approval_context()` factory.

### 6. Two database clients, two connection patterns (MEDIUM)

The system uses both:
- **psycopg `AsyncConnectionPool`** (`DatabaseManager`) — used for chat history, cache services, direct queries
- **supabase-py async client** (`SupabaseManager`) — used for approval system, audit, notifications, tool execution, session management

These serve the same Postgres database. The supabase-py client provides PostgREST ORM-like syntax (`db.table("x").select("*").eq("y", z).execute()`), while psycopg is raw SQL.

**Proposal:** This isn't necessarily wrong (PostgREST for simple CRUD, psycopg for complex queries), but the lack of a clear rule means new code randomly picks one. Document a rule:
- **psycopg:** Chat history (LangChain requirement), cache service bulk fetches, anything needing transactions
- **supabase-py:** Simple single-table CRUD where RLS is desired, tool implementations that already use it

### 7. `AGENT_REGISTRY` / `create_specialized_agent` is unused (LOW)

`agent_loader_db.py:58-87` defines an agent registry and factory for specialized agents, but `AGENT_REGISTRY` is empty and `create_specialized_agent` is never called.

**Proposal:** Remove dead code.

### 8. `get_customizable_agent_executor` helper is redundant (LOW)

`customizable_agent.py:137-161` is a wrapper that just calls `from_agent_config()`. It handles a non-dict case that logs an error and proceeds anyway.

**Proposal:** Remove and call `from_agent_config()` directly.

### 9. `ConfigLoader` is initialized but unused (LOW)

`main.py:118-123` creates `GLOBAL_CONFIG_LOADER` from `utils.config_loader.ConfigLoader()` but nothing references it.

**Proposal:** Remove.

---

## Recommended Execution Order

1. **Extract `normalize_agent_output`** — trivial, immediate deduplication (PR 1)
2. **Extract `AgentInvocationService`** — unifies the three pipelines, biggest value (PR 2)
3. **Delete sync agent loading path** — only possible after #2 makes Telegram/Scheduled use async (PR 3)
4. **Remove dead code** (AGENT_REGISTRY, GLOBAL_CONFIG_LOADER, get_customizable_agent_executor) (PR 4)
5. **Document DB client rule** — add to CLAUDE.md (PR 5)
6. **Reconsider executor caching** — lower priority, works today (future)
