# SPEC-011: Reduce DB Query Latency During Agent Invocation

## Status: In Progress

## Problem

When an agent executor cache miss occurs, `load_agent_executor_db()` makes 3 sequential DB round trips before the LLM call can begin. The function is sync but called from an async context — it uses `asyncio.run()` to call async DB functions, which blocks the event loop and starves other concurrent requests.

### Sequential queries on cache miss:
1. Fetch `agent_configurations` (sync Supabase client) — not cached
2. Fetch tools via `get_cached_tools_for_agent()` (async via `asyncio.run()`) — cached but blocks event loop
3. Fetch `user_agent_prompt_customizations` (sync Supabase client) — not cached

## Solution

### Phase 1: AgentConfigCacheService
- New file: `chatServer/services/agent_config_cache_service.py`
- TTL: 600s, refresh: 120s
- `fetch_all_callback`: SELECT * FROM agent_configurations, keyed by agent_name
- `fetch_single_callback`: single agent_name lookup

### Phase 2: UserInstructionsCacheService
- New file: `chatServer/services/user_instructions_cache_service.py`
- TTL: 120s (short — user edits propagate quickly)
- No `fetch_all_callback` (too many user/agent combinations)
- Cache key: `f"{user_id}:{agent_name}"`

### Phase 3: Async `load_agent_executor_db_async()`
- New async function in `src/core/agent_loader_db.py`
- Eliminates all `asyncio.run()` calls
- Parallelizes tools + user_instructions fetch via `asyncio.gather()`

### Phase 4: Async `get_or_load_agent_executor()`
- Convert to async in `chatServer/services/chat.py`
- On cache miss, `await load_agent_executor_db_async()`

### Phase 5: Async lock for duplicate load prevention
- Per-key `asyncio.Lock` prevents concurrent duplicate loads

## Expected Impact

| Scenario | Before | After |
|----------|--------|-------|
| Executor cache hit | ~0ms | ~0ms |
| Executor miss, sub-caches warm | 150-300ms (3 sequential, blocking) | 5-10ms (3 in-memory, non-blocking) |
| Executor miss, sub-caches miss | 150-300ms (3 sequential, blocking) | 50-100ms (1 cached + 2 parallel, non-blocking) |

## Files

| File | Action |
|------|--------|
| `chatServer/services/agent_config_cache_service.py` | Create |
| `chatServer/services/user_instructions_cache_service.py` | Create |
| `src/core/agent_loader_db.py` | Modify |
| `src/core/agent_loader.py` | Modify |
| `chatServer/services/chat.py` | Modify |
| `chatServer/main.py` | Modify |

## Testing
1. All existing tests must pass
2. Unit tests for new cache services
3. Unit tests for async loader path
