# SPEC-012: Unified Agent Invocation Service

> **Status:** Draft
> **Author:** Tim
> **Created:** 2026-02-19
> **Updated:** 2026-02-19

## Goal

Extract the duplicated agent invocation pipeline (load agent → wrap tools → set up memory → invoke → normalize response) into a single `AgentInvocationService`, then refactor all three channels (web, Telegram, scheduled) to use it. Remove the sync agent loading path and dead code along the way.

This reduces ~300 lines of duplicated logic to one authoritative implementation, eliminating a class of bugs where channels diverge (e.g., Telegram uses sync loading and misses cache services, scheduled runs skip the executor cache entirely).

## Acceptance Criteria

- [ ] AC-1: A single `AgentInvocationService.invoke()` method handles agent loading, tool wrapping, memory setup, invocation, and response normalization
- [ ] AC-2: `POST /api/chat` uses `AgentInvocationService` instead of inline pipeline in `ChatService.process_chat()`
- [ ] AC-3: Telegram `handle_message()` uses `AgentInvocationService` instead of its inline pipeline
- [ ] AC-4: `ScheduledExecutionService.execute()` uses `AgentInvocationService` instead of its inline pipeline
- [ ] AC-5: The sync `load_agent_executor_db()` function is deleted from `src/core/agent_loader_db.py`
- [ ] AC-6: The sync `load_agent_executor()` wrapper is deleted from `src/core/agent_loader.py`
- [ ] AC-7: Dead code removed: `AGENT_REGISTRY`, `create_specialized_agent`, `register_specialized_agent` from `agent_loader_db.py`
- [ ] AC-8: Dead code removed: `get_customizable_agent_executor` from `customizable_agent.py`
- [ ] AC-9: Dead code removed: `GLOBAL_CONFIG_LOADER` from `main.py`
- [ ] AC-10: All existing tests pass; new unit tests cover `AgentInvocationService`
- [ ] AC-11: `normalize_agent_output()` utility extracted and used by all paths

## Scope

### Files to Create

| File | Purpose |
|------|---------|
| `chatServer/services/agent_invocation_service.py` | Unified invoke pipeline |
| `chatServer/utils/response_utils.py` | `normalize_agent_output()` utility |
| `tests/chatServer/services/test_agent_invocation_service.py` | Unit tests |

### Files to Modify

| File | Change |
|------|--------|
| `chatServer/services/chat.py` | Slim down to delegate to `AgentInvocationService`; remove inline pipeline |
| `chatServer/channels/telegram_bot.py` | Replace inline pipeline with `AgentInvocationService.invoke()` call |
| `chatServer/services/scheduled_execution_service.py` | Replace inline pipeline with `AgentInvocationService.invoke()` call |
| `chatServer/main.py` | Remove `GLOBAL_CONFIG_LOADER`, remove `AGENT_EXECUTOR_CACHE` (moves into service) |
| `src/core/agent_loader_db.py` | Delete `load_agent_executor_db` (sync), delete `AGENT_REGISTRY` + related functions |
| `src/core/agent_loader.py` | Delete `load_agent_executor` (sync wrapper), keep async only |
| `src/core/agents/customizable_agent.py` | Delete `get_customizable_agent_executor` |

### Out of Scope

- Changing the executor caching strategy (cache LLM binding vs. full executor) — future work
- Changing the two-DB-client pattern (psycopg + supabase-py) — document rule only
- Legacy tool renaming — separate backlog item
- Frontend changes — none needed, API contract unchanged

## Technical Approach

### 1. Extract `normalize_agent_output()` (FU-1)

```python
# chatServer/utils/response_utils.py
def normalize_agent_output(raw_output: Any) -> str:
    """Normalize LangChain agent output to a plain string.

    Handles content block lists from newer langchain-anthropic versions.
    """
    if isinstance(raw_output, list):
        return "".join(
            block.get("text", "") for block in raw_output
            if isinstance(block, dict) and block.get("type") == "text"
        ) or "No text content in response."
    return str(raw_output) if raw_output else "No output from agent."
```

### 2. Create `AgentInvocationService` (FU-2)

```python
# chatServer/services/agent_invocation_service.py

@dataclass
class AgentResponse:
    """Result of an agent invocation."""
    output: str                              # Normalized text response
    session_id: str                          # Echo back for caller
    tool_name: str | None = None             # Last tool called (if any)
    tool_input: dict | None = None           # Last tool args (if any)
    error: str | None = None                 # Error message (if any)

class AgentInvocationService:
    def __init__(self, agent_executor_cache: TTLCache):
        self._cache = agent_executor_cache
        self._load_locks: dict[tuple[str, str], asyncio.Lock] = {}

    async def invoke(
        self,
        user_id: str,
        agent_name: str,
        session_id: str,
        message: str,
        channel: str = "web",
        chat_history: list | None = None,  # None = load from DB, [] = fresh
    ) -> AgentResponse:
        """Single entry point for all agent invocations."""
        # 1. Get or load executor (async path only)
        # 2. Create memory (if chat_history is None, use PostgresChatMessageHistory)
        # 3. Wrap tools with approval
        # 4. ainvoke
        # 5. Normalize response
        # 6. Return AgentResponse
```

**Key design decisions:**
- `chat_history=None` means "load from PostgresChatMessageHistory for this session_id" (web, Telegram)
- `chat_history=[]` means "fresh context, no history" (scheduled, heartbeat)
- The service owns the `AGENT_EXECUTOR_CACHE` — it moves from `main.py` into this service
- Approval wrapping happens inside `invoke()`, not in the caller
- The pg_connection for chat history is obtained internally (via `get_database_manager()`)

### 3. Refactor channels to use the service (FU-3)

**Web (`chat.py`):** `ChatService.process_chat()` becomes a thin adapter:
- Validates input
- Calls `AgentInvocationService.invoke()`
- Maps `AgentResponse` → `ChatResponse`
- Does best-effort Telegram push

**Telegram (`telegram_bot.py`):** `handle_message()` becomes:
- Look up user_id from chat_id
- Find or create session
- Call `AgentInvocationService.invoke(channel="telegram")`
- Send response

**Scheduled (`scheduled_execution_service.py`):** `execute()` becomes:
- Call `AgentInvocationService.invoke(channel="scheduled"|"heartbeat", chat_history=[])`
- Model override (applied before invoke via a parameter or post-load hook)
- Store result, notify, mark session inactive

### 4. Delete sync loading path + dead code (FU-4)

- Delete `load_agent_executor_db` (~245 lines)
- Delete `load_agent_executor` sync wrapper
- Delete `AGENT_REGISTRY`, `create_specialized_agent`, `register_specialized_agent`
- Delete `get_customizable_agent_executor`
- Delete `GLOBAL_CONFIG_LOADER`

### Dependencies

- SPEC-011 (agent load latency) must be complete — the async loading path and cache services it introduced are prerequisites. **Status: In Progress, cache services already merged.**

## Testing Requirements

### Unit Tests (required)

| Test | What it covers |
|------|---------------|
| `test_invoke_cache_hit` | Executor in cache → skip loading, invoke directly |
| `test_invoke_cache_miss` | Executor not in cache → async load, cache, invoke |
| `test_invoke_approval_wrapping` | Tools get wrapped with approval context |
| `test_invoke_with_history` | `chat_history=None` loads from PostgresChatMessageHistory |
| `test_invoke_fresh_context` | `chat_history=[]` starts clean |
| `test_invoke_normalizes_content_blocks` | List output → string |
| `test_invoke_normalizes_plain_string` | String output passes through |
| `test_invoke_agent_error` | Agent raises → AgentResponse.error populated |
| `test_normalize_agent_output_*` | Unit tests for the utility function |

### Integration Tests

- Existing `tests/chatServer/` tests continue to pass (they test the API contract, which is unchanged)
- Telegram handler tests (if any) continue to pass

### Manual Verification (UAT)

- [ ] Send a message via web UI → get agent response
- [ ] Send a message via Telegram → get agent response
- [ ] Trigger a scheduled run → verify execution result stored
- [ ] Verify executor caching works (second message to same agent is faster)

## Edge Cases

- **Concurrent loads for same (user_id, agent_name):** Per-key `asyncio.Lock` prevents duplicate loads (carried over from current `ChatService`)
- **Approval service unavailable:** Non-fatal warning, tools execute without approval check (current behavior preserved)
- **pg_connection unavailable for memory:** Raises 503 (current behavior preserved)
- **Model override for scheduled runs:** The service accepts the executor post-load; `ScheduledExecutionService` applies the override before calling `invoke()`

## Functional Units (for PR Breakdown)

1. **FU-1: Extract `normalize_agent_output` utility** (`feat/SPEC-012-normalize-output`)
   - Create `chatServer/utils/response_utils.py`
   - Replace inline normalization in `chat.py`, `telegram_bot.py`, `scheduled_execution_service.py`
   - Tests for the utility
   - *No behavior change, pure refactor*

2. **FU-2: Create `AgentInvocationService`** (`feat/SPEC-012-invocation-service`)
   - Create `chatServer/services/agent_invocation_service.py`
   - Move `AGENT_EXECUTOR_CACHE` and load locks from `main.py`/`chat.py` into the service
   - Unit tests
   - *Service exists but nothing uses it yet*

3. **FU-3: Wire channels to `AgentInvocationService`** (`feat/SPEC-012-wire-channels`)
   - Refactor `ChatService.process_chat()` to delegate
   - Refactor `telegram_bot.py:handle_message()` to delegate
   - Refactor `ScheduledExecutionService.execute()` to delegate
   - Verify all existing tests pass
   - *This is the main behavior-preserving refactor*

4. **FU-4: Delete sync path + dead code** (`feat/SPEC-012-cleanup`)
   - Delete `load_agent_executor_db` (sync)
   - Delete `load_agent_executor` (sync wrapper)
   - Delete `AGENT_REGISTRY`, `create_specialized_agent`, `register_specialized_agent`
   - Delete `get_customizable_agent_executor`
   - Delete `GLOBAL_CONFIG_LOADER`
   - Update any remaining references
   - *Only possible after FU-3 removes all sync callers*
