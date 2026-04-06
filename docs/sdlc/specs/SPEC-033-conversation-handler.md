# SPEC-033: Conversation Handler — Replace LangChain AgentExecutor with Anthropic Messages API

> **Status:** Draft
> **Author:** Claude (Spec Writer)
> **Created:** 2026-04-06
> **Updated:** 2026-04-06
> **PRD:** Architecture Proposal (Phase 0, Item 2)

## Goal

Replace LangChain's `AgentExecutor` with a direct Anthropic Messages API tool-loop (`ConversationHandler`). This is the highest-risk change in the rearchitecture — it touches every user message across web, Telegram, and scheduled channels. The new handler is ~200 LOC, eliminates LangChain content block normalization hacks, provides native SSE streaming, and produces predictable API responses without framework abstraction layers.

The handler runs behind a feature flag alongside the existing `ChatService` so both paths coexist during migration. Once validated, the old path is removed (separate cleanup PR, not in this spec).

## Background

The current message flow passes through five LangChain abstractions:

```
ChatService.process_chat()
  → AsyncConversationBufferWindowMemory (LangChain)
  → CustomizableAgentExecutor (extends AgentExecutor)
    → ChatPromptTemplate + MessagesPlaceholder (LangChain)
    → RunnablePassthrough | ToolsAgentOutputParser (LangChain)
    → ChatAnthropic (langchain-anthropic wrapper)
      → Anthropic Messages API (actual work)
```

The raw API loop is three steps:
1. Send messages + tools to Anthropic
2. If response has `tool_use` blocks, execute them, append results
3. Repeat until `end_turn`

LangChain wraps this in `AgentExecutor`, `RunnableSequence`, callback managers, and content block normalization — adding complexity without value. The content block normalization issues (list-of-dicts vs strings, `chatServer/services/chat.py:306-310`) are LangChain-specific. The raw API is predictable.

### Relationship to SPEC-035 (Assistant-UI Alignment)

SPEC-035 FU-1 specs backend SSE streaming using "LangChain's `astream_events()` or callback handler." This spec supersedes that approach — streaming comes natively from the Anthropic SDK's `messages.stream()`, which is simpler and eliminates the callback layer. SPEC-035 FU-1 should be updated to reference the ConversationHandler's stream output rather than LangChain internals. The SSE event format (using `assistant-stream` encoder) remains the same.

### Relationship to SPEC-034 (Capability Gateway)

SPEC-034 replaces `BaseTool` subclasses with a Capability Gateway. Until SPEC-034 ships, the ConversationHandler must work with existing `BaseTool` tools via a bridge layer. This spec defines that bridge: convert `BaseTool` schemas to Anthropic-native format for the API call, dispatch to `BaseTool._arun()` on tool use, convert results back to API format.

## Dependencies

| Dependency | What It Provides | Status |
|-----------|-----------------|--------|
| `anthropic` Python SDK (≥0.49) | Messages API, streaming, tool use | Available (add to requirements) |
| Existing `prompt_builder.py` | System prompt assembly (framework-agnostic) | Complete |
| Existing `chat_message_history` table | Message persistence | Complete |
| Existing `BaseTool` subclasses | Tool implementations (bridged) | Complete |
| Existing `approval_tiers.py` + `tool_wrapper.py` | Approval checking (adapted) | Complete |
| SPEC-035 | SSE format consumed by frontend (`assistant-stream`) | In progress (can develop in parallel) |

## Acceptance Criteria

### FU-1: ConversationHandler Core

- [ ] **AC-01:** A `ConversationHandler` class in `chatServer/services/conversation_handler.py` implements a while-loop over the Anthropic Messages API. It accepts a system prompt (string), conversation history (list of Anthropic message dicts), tool definitions (Anthropic tool format), and model name. It loops until the response has `stop_reason == "end_turn"` or `max_turns` (default 25) is reached. [A1, A14]
- [ ] **AC-02:** The handler uses `anthropic.AsyncAnthropic` client for all API calls. The client is instantiated once at service initialization with the `ANTHROPIC_API_KEY` env var. No LangChain wrappers. [A14]
- [ ] **AC-03:** On each loop iteration, when the API returns `tool_use` content blocks, the handler dispatches each tool call to the appropriate executor and appends tool results as `tool_result` blocks in the next request. Multiple tool calls in a single turn are executed concurrently via `asyncio.gather()`. [A6]
- [ ] **AC-04:** The handler supports both streaming and non-streaming modes. In streaming mode, it uses `client.messages.stream()` and yields `StreamEvent` objects (text deltas, tool use blocks, message completion). In non-streaming mode, it uses `client.messages.create()` and returns the complete response. [A14]
- [ ] **AC-05:** A `BaseTool` bridge adapter (`LangChainToolBridge`) converts existing `BaseTool` instances to Anthropic-native tool schemas for the API call (extracting `name`, `description`, `args_schema` → JSON Schema). On tool dispatch, it calls `tool._arun(**args)` and returns the string result. This bridge is temporary — removed when SPEC-034 ships. [A6, A14]
- [ ] **AC-06:** The handler loads conversation history from the `chat_message_history` table directly via `psycopg` (not via LangChain's `PostgresChatMessageHistory`). Messages are converted from the stored LangChain JSON format (`{"type": "human|ai", "data": {"content": ...}}`) to Anthropic format (`{"role": "user|assistant", "content": ...}`). Last 50 message pairs loaded (matching current `k=50` window). [A3]
- [ ] **AC-07:** After each complete turn (user message → assistant response), the handler persists both messages to `chat_message_history` in the existing format so that LangChain-based channels (during migration) can still read the history. [A7]
- [ ] **AC-08:** Per-message token usage (`input_tokens`, `output_tokens`) is extracted from the API response's `usage` field and logged at INFO level. Cumulative session token counts are tracked on the handler instance and available via a `token_usage` property. [A14]
- [ ] **AC-09:** The handler respects `max_tokens` from the agent configuration (default 4096). The model name comes from agent config's `llm.model` field. Temperature comes from agent config's `llm.temperature` field (default 0.7). [A2]

### FU-2: SSE Streaming Endpoint

- [ ] **AC-10:** The `/api/chat` endpoint supports SSE streaming when the request includes `Accept: text/event-stream` header. Response uses `Content-Type: text/event-stream` with standard SSE format (`data: ...\n\n`). Without the Accept header, returns the current JSON `ChatResponse` (backward compatibility). [A1, A7]
- [ ] **AC-11:** SSE events follow a simple JSON-per-line format: `{"type": "text_delta", "text": "..."}` for text chunks, `{"type": "tool_start", "tool_name": "...", "tool_call_id": "..."}` when a tool begins, `{"type": "tool_result", "tool_call_id": "...", "result": "..."}` when a tool completes, `{"type": "message_complete", "token_usage": {...}}` on finish, `{"type": "error", "message": "..."}` on failure. [A1]
- [ ] **AC-12:** The SSE endpoint uses FastAPI's `StreamingResponse` with `media_type="text/event-stream"`. The response generator wraps the ConversationHandler's streaming output and formats each event as an SSE line. [A1]
- [ ] **AC-13:** Client disconnection (checked via `Request.is_disconnected()`) cancels the in-progress Anthropic API call and cleans up. No orphaned API calls after client disconnect. [A1]
- [ ] **AC-14:** SSE responses include CORS headers matching the existing `/api/chat` endpoint configuration. `Cache-Control: no-cache` and `Connection: keep-alive` headers are set. [A1]

### FU-3: Feature Flag + Routing

- [ ] **AC-15:** An environment variable `CONVERSATION_HANDLER_V2` (default `false`) controls which handler processes messages. When `true`, the `/api/chat` endpoint uses `ConversationHandler`. When `false`, it uses the existing `ChatService`. [A14]
- [ ] **AC-16:** The routing logic lives in the `/api/chat` endpoint in `main.py`, not inside either service. Both services receive the same inputs (user_id, session_id, agent_name, message) and return compatible outputs. [A1]
- [ ] **AC-17:** When the feature flag is `true`, the ConversationHandler builds its tool list by loading tools via the existing `load_tools_from_db()` function, then converting them through the `LangChainToolBridge`. The same tools, same approval wrapping, same user context as the current path. [A6]
- [ ] **AC-18:** Rollback procedure: set `CONVERSATION_HANDLER_V2=false` and restart. No database migration, no data format change, no state cleanup required. The old path works identically to before. [A14]

### FU-4: Channel Adapter Integration

- [ ] **AC-19:** The Telegram handler (`chatServer/channels/telegram_bot.py`) is updated to use the ConversationHandler in non-streaming mode when the feature flag is enabled. Tool wrapping, session management, and memory persistence work identically. Response format unchanged (plain text string). [A7]
- [ ] **AC-20:** The scheduled execution service (`chatServer/services/scheduled_execution_service.py`) uses the ConversationHandler in non-streaming mode when the feature flag is enabled. Model override, approval wrapping, and result storage work identically. [A7]
- [ ] **AC-21:** The session-open service (`chatServer/services/session_open_service.py`) uses the ConversationHandler in non-streaming mode when the feature flag is enabled. Bootstrap context injection and session creation work identically. [A7]
- [ ] **AC-22:** All three channel adapters continue to work with the old `ChatService` when the feature flag is disabled. The flag is read once per invocation, not cached. [A14]

### FU-5: Error Handling + Resilience

- [ ] **AC-23:** Anthropic API errors (rate limit, overloaded, auth failure) are caught and returned as structured error responses. Rate limit errors (`429`) include `retry_after` in the error payload. Overloaded errors (`529`) return a user-friendly message ("I'm thinking hard right now, please try again in a moment"). Auth errors log at ERROR and return 500 (server misconfiguration). [A1]
- [ ] **AC-24:** Tool execution errors are caught per-tool and returned to the API as `tool_result` with `is_error: true`. The conversation loop continues — tool errors don't crash the handler. The model sees the error and can retry or explain. [A6]
- [ ] **AC-25:** If `max_turns` is reached without `end_turn`, the handler returns the last assistant message with an appended note: "[Max tool iterations reached]". This prevents runaway tool loops. [A14]
- [ ] **AC-26:** Request timeout: the handler accepts an optional `timeout_seconds` parameter (default 120). If the total wall time exceeds this, the handler cancels the in-progress API call and returns a timeout error. [A1]
- [ ] **AC-27:** All errors (API, tool, timeout) are logged with the session_id, user_id, and turn number for debugging. Error responses in SSE mode use the `{"type": "error", ...}` event format. Error responses in JSON mode use the existing `ChatResponse(error=...)` format. [A1]

### FU-6: dispatch_workflow Stub

- [ ] **AC-28:** A `dispatch_workflow` tool is defined with schema: `{"name": "dispatch_workflow", "description": "Start a multi-step workflow (email triage, draft reply, etc.). Not yet available — will be implemented in SPEC-035.", "input_schema": {"type": "object", "properties": {"workflow_name": {"type": "string"}, "parameters": {"type": "object"}}, "required": ["workflow_name"]}}`. [A6]
- [ ] **AC-29:** When invoked, the stub returns: `"Workflow dispatch is not yet available. I'll handle this conversationally instead."` The model can then fall back to using individual tools. [A14]
- [ ] **AC-30:** The stub is registered as a tool available to the ConversationHandler (not added to the DB tool registry — it's handler-internal). It is NOT available in the old ChatService path. [A6]

## Scope

### Files to Create

| File | Purpose |
|------|---------|
| `chatServer/services/conversation_handler.py` | ConversationHandler class — Anthropic API tool-loop |
| `chatServer/services/langchain_tool_bridge.py` | Bridge: BaseTool → Anthropic tool schema + dispatch |
| `chatServer/services/message_history_adapter.py` | Load/save messages in Anthropic format from chat_message_history |
| `chatServer/services/sse_stream.py` | SSE response formatter for StreamingResponse |
| `tests/chatServer/services/test_conversation_handler.py` | Unit tests for the handler |
| `tests/chatServer/services/test_langchain_tool_bridge.py` | Unit tests for the bridge |
| `tests/chatServer/services/test_message_history_adapter.py` | Unit tests for message loading |
| `tests/chatServer/services/test_sse_stream.py` | Unit tests for SSE formatting |
| `tests/integration/test_conversation_handler_integration.py` | Integration test: send message, get streamed response |

### Files to Modify

| File | Change |
|------|--------|
| `chatServer/main.py` | Add feature flag routing in `/api/chat` endpoint; add ConversationHandler initialization |
| `chatServer/channels/telegram_bot.py` | Add feature flag branch using ConversationHandler in non-streaming mode |
| `chatServer/services/scheduled_execution_service.py` | Add feature flag branch using ConversationHandler |
| `chatServer/services/session_open_service.py` | Add feature flag branch using ConversationHandler |
| `chatServer/config/settings.py` | Add `conversation_handler_v2: bool` setting |
| `requirements.txt` | Add `anthropic>=0.49` (if not already present) |
| `chatServer/requirements.txt` | Add `anthropic>=0.49` (if not already present) |

### Files NOT Modified (remain as-is for rollback)

| File | Why Kept |
|------|----------|
| `chatServer/services/chat.py` | ChatService stays intact — feature flag routes around it |
| `src/core/agents/customizable_agent.py` | CustomizableAgentExecutor stays — old path still uses it |
| `src/core/agent_loader_db.py` | Tool loading + agent config loading stays — both paths use it |
| `chatServer/protocols/agent_executor.py` | AgentExecutorProtocol stays — old path still uses it |
| `chatServer/security/tool_wrapper.py` | Approval wrapping stays — new path uses adapted version |
| All `chatServer/tools/*.py` | BaseTool subclasses stay — bridge adapter uses them |

### Out of Scope

- **Removing LangChain dependencies.** Both paths coexist. LangChain removal happens after the feature flag is flipped and validated (separate cleanup spec).
- **Tool migration to Capability Gateway.** SPEC-034 replaces `BaseTool` subclasses. This spec bridges them.
- **Workflow engine.** SPEC-035 implements `dispatch_workflow`. This spec only stubs it.
- **Config service / Supabase Storage.** Agent config continues to load from the database via existing mechanisms.
- **Frontend streaming consumer.** SPEC-035 FU-2+ handles `useLocalRuntime` and streaming decode. This spec provides the SSE endpoint they consume.
- **Removing the old ChatService.** Happens in a follow-up after validation.
- **assistant-stream format encoding.** SPEC-035 FU-1 defines the `AssistantTransportEncoder` format. This spec uses a simpler JSON-per-line SSE format that can be adapted to match the assistant-stream protocol in SPEC-035's implementation.

## Technical Approach

### ConversationHandler Design

```python
class ConversationHandler:
    """Direct Anthropic Messages API tool-loop. ~200 LOC."""

    def __init__(
        self,
        client: anthropic.AsyncAnthropic,
        model: str,
        system_prompt: str,
        tools: list[dict],            # Anthropic-native tool schemas
        tool_executors: dict[str, Callable],  # name → async executor fn
        max_turns: int = 25,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        timeout_seconds: float = 120,
    ): ...

    async def run(
        self,
        messages: list[dict],         # Anthropic message format
    ) -> ConversationResult:
        """Non-streaming: returns complete result."""

    async def run_stream(
        self,
        messages: list[dict],
    ) -> AsyncIterator[StreamEvent]:
        """Streaming: yields events as they arrive."""

    @dataclass
    class ConversationResult:
        response_text: str
        tool_calls: list[ToolCallRecord]
        token_usage: TokenUsage
        turn_count: int
        stop_reason: str

    @dataclass
    class TokenUsage:
        input_tokens: int
        output_tokens: int
```

### Tool Bridge Pattern

The bridge converts between LangChain `BaseTool` and Anthropic API format:

```python
class LangChainToolBridge:
    """Temporary bridge — removed when SPEC-034 ships."""

    @staticmethod
    def to_anthropic_schema(tool: BaseTool) -> dict:
        """Convert BaseTool to Anthropic tool definition."""
        return {
            "name": tool.name,
            "description": tool.description,
            "input_schema": tool.args_schema.model_json_schema()
                           if tool.args_schema else {"type": "object"},
        }

    @staticmethod
    async def execute(tool: BaseTool, args: dict) -> str:
        """Dispatch tool call to BaseTool._arun()."""
        return await tool._arun(**args)
```

### SSE Streaming Format

```
data: {"type": "text_delta", "text": "Hello"}

data: {"type": "text_delta", "text": ", how"}

data: {"type": "tool_start", "tool_name": "search_gmail", "tool_call_id": "toolu_01xyz"}

data: {"type": "tool_result", "tool_call_id": "toolu_01xyz", "result": "Found 3 emails..."}

data: {"type": "text_delta", "text": "I found 3 emails..."}

data: {"type": "message_complete", "token_usage": {"input_tokens": 1200, "output_tokens": 350}}
```

### Feature Flag Routing (in main.py)

```python
@app.post("/api/chat")
async def chat_endpoint(
    chat_input: ChatRequest,
    request: Request,
    user_id: str = Depends(get_current_user),
    pg_connection = Depends(get_db_connection),
    agent_loader_module = Depends(get_agent_loader),
):
    settings = get_settings()

    if settings.conversation_handler_v2:
        handler = await build_conversation_handler(
            user_id=user_id,
            agent_name=chat_input.agent_name,
            session_id=chat_input.session_id,
            pg_connection=pg_connection,
            agent_loader_module=agent_loader_module,
        )

        if "text/event-stream" in request.headers.get("accept", ""):
            return StreamingResponse(
                sse_stream(handler, chat_input.message, chat_input.session_id),
                media_type="text/event-stream",
            )
        else:
            result = await handler.run_with_message(chat_input.message)
            return ChatResponse(
                session_id=chat_input.session_id,
                response=result.response_text,
                error=None,
            )
    else:
        # Existing path — unchanged
        chat_service = get_chat_service(AGENT_EXECUTOR_CACHE)
        return await chat_service.process_chat(...)
```

### Message History Adapter

The adapter reads from and writes to the existing `chat_message_history` table, converting between LangChain's stored format and Anthropic's message format:

```
LangChain stored format:
  {"type": "human", "data": {"content": "hello", "type": "HumanMessage", ...}}
  {"type": "ai", "data": {"content": "Hi!", "type": "AIMessage", ...}}

Anthropic API format:
  {"role": "user", "content": "hello"}
  {"role": "assistant", "content": "Hi!"}
```

Messages with tool calls (stored as `AIMessageChunk` with `tool_calls` in data) are converted to Anthropic's `tool_use` content blocks. Tool results (stored as `ToolMessage`) are converted to `tool_result` blocks.

### Approval Integration

The existing approval system wraps `BaseTool._arun()`. Since the bridge calls `_arun()`, approval wrapping works unchanged:

1. Load tools via `load_tools_from_db()`
2. Wrap with `wrap_tools_with_approval(tools, approval_context)` — same as today
3. Convert to Anthropic schemas via `LangChainToolBridge.to_anthropic_schema()`
4. On tool dispatch, `LangChainToolBridge.execute()` calls the wrapped `_arun()`

The approval wrapper intercepts at the `_arun()` level, so it works regardless of whether LangChain's `AgentExecutor` or our `ConversationHandler` is driving the loop.

### Telegram Push (Cross-Channel)

The `_push_to_telegram_if_linked()` logic from `ChatService` is extracted into a shared utility and called from both paths. The ConversationHandler's non-streaming `run()` returns a `ConversationResult` with `response_text` that is passed to the Telegram push function.

## Blast Radius

Every file that touches `ChatService`, `AgentExecutor`, `agent_executor`, LangChain callbacks, or streaming. **All must be regression-tested.**

### Backend Services (directly modified or affected)

| File | Impact | Risk |
|------|--------|------|
| `chatServer/services/chat.py` | NOT modified (old path preserved) | Low — must continue working when flag is off |
| `chatServer/services/session_open_service.py` | Modified: adds v2 branch | Medium — session_open is proactive, errors may be silent |
| `chatServer/services/scheduled_execution_service.py` | Modified: adds v2 branch | Medium — scheduled runs have no user watching |
| `chatServer/services/tool_execution.py` | NOT modified | Low — post-approval execution bypasses both handlers |
| `chatServer/services/prompt_builder.py` | NOT modified (already framework-agnostic) | Low |
| `chatServer/services/agent_config_cache_service.py` | NOT modified | Low — both paths read config the same way |
| `chatServer/services/langchain_auth_bridge.py` | NOT modified | Low — used by tools, not by handler |
| `chatServer/services/notification_service.py` | NOT modified | Low — called from tools, not handler |
| `chatServer/services/pending_actions.py` | NOT modified | Low — called from approval wrapper |

### Core / Agent Loading

| File | Impact | Risk |
|------|--------|------|
| `src/core/agents/customizable_agent.py` | NOT modified | Low — old path still uses it |
| `src/core/agent_loader_db.py` | NOT modified — both paths use `load_tools_from_db()` | Low |
| `src/core/llm_interface.py` | NOT modified | Low — not used by new path |
| `chatServer/dependencies/agent_loader.py` | NOT modified | Low |

### Router / Endpoint

| File | Impact | Risk |
|------|--------|------|
| `chatServer/main.py` | Modified: `/api/chat` gains feature flag routing + SSE path | **HIGH** — every web message flows through here |
| `chatServer/routers/chat_history_router.py` | NOT modified | Low — reads history, doesn't invoke agents |
| `chatServer/routers/session_open_router.py` | NOT modified (calls session_open_service) | Low |

### Channels

| File | Impact | Risk |
|------|--------|------|
| `chatServer/channels/telegram_bot.py` | Modified: adds v2 branch | **HIGH** — Telegram users affected |

### Security / Tools

| File | Impact | Risk |
|------|--------|------|
| `chatServer/security/tool_wrapper.py` | NOT modified — bridge calls wrapped `_arun()` | Medium — must verify wrapping works through bridge |
| `chatServer/security/approval_tiers.py` | NOT modified | Low |
| All `chatServer/tools/*.py` (10 files) | NOT modified — bridge calls `_arun()` directly | Medium — must verify all tool schemas convert correctly |

### Frontend (consumers of `/api/chat`)

| File | Impact | Risk |
|------|--------|------|
| `webApp/src/lib/assistantui/CustomRuntime.ts` | Consumer of `/api/chat` — needs SSE support (SPEC-035 scope) | Medium — JSON mode must work identically |
| `webApp/src/api/hooks/useChatApiHooks.ts` | Consumer of `/api/chat` | Medium — JSON response format unchanged |
| `webApp/src/lib/chatAPI.ts` | Consumer of `/api/chat` | Low — health check unaffected |
| `webApp/src/stores/useChatStore.ts` | NOT modified | Low |
| `webApp/src/components/ChatPanelV2.tsx` | NOT modified by this spec | Low |
| `webApp/src/components/ui/chat/ApprovalInlineMessage.tsx` | NOT modified | Low — approval flow unchanged |

### Models

| File | Impact | Risk |
|------|--------|------|
| `chatServer/models/chat.py` | NOT modified — `ChatResponse` format unchanged for JSON mode | Low |

### Tests (must be updated or verified)

| File | Impact |
|------|--------|
| `tests/chatServer/test_main_chat_logic.py` | Must add v2 path tests |
| `tests/chatServer/services/test_chat.py` | Must verify old path still works |
| `tests/chatServer/services/test_session_open_service.py` | Must add v2 branch test |
| `tests/chatServer/services/test_scheduled_execution_service.py` | Must add v2 branch test |
| `tests/chatServer/services/test_heartbeat_deferral.py` | Verify scheduled path unaffected |
| `tests/chatServer/services/test_background_tasks.py` | Verify old path still works |
| `tests/chatServer/channels/test_telegram_session_creation.py` | Must add v2 branch test |
| `tests/chatServer/protocols/test_agent_executor.py` | NOT modified — old protocol preserved |
| `tests/chatServer/dependencies/test_agent_loader.py` | NOT modified |
| `tests/core/agents/test_customizable_agent.py` | NOT modified — old path preserved |
| `tests/core/test_agent_loader_db.py` | NOT modified |
| `tests/core/test_agent_loader_db_async.py` | NOT modified |
| `tests/uat/conftest.py` | May need update if UAT exercises SSE |
| `tests/uat/test_spec_025_notifications.py` | Verify notifications still work |

## Testing Requirements

### Unit Tests (required)

| Test File | What It Tests | ACs |
|-----------|--------------|-----|
| `test_conversation_handler.py` | Tool-loop: mock Anthropic API, verify loop continues on tool_use, stops on end_turn | AC-01, AC-03, AC-04, AC-08, AC-09 |
| `test_conversation_handler.py` | Max turns: loop stops at max_turns, returns last message | AC-25 |
| `test_conversation_handler.py` | Error handling: API errors, tool errors, timeout | AC-23, AC-24, AC-26 |
| `test_conversation_handler.py` | Token tracking: usage accumulated across turns | AC-08 |
| `test_langchain_tool_bridge.py` | Schema conversion: BaseTool → Anthropic format for each tool type | AC-05 |
| `test_langchain_tool_bridge.py` | Tool dispatch: _arun called with correct args | AC-05 |
| `test_message_history_adapter.py` | History loading: LangChain format → Anthropic format, window of 50 | AC-06 |
| `test_message_history_adapter.py` | History saving: Anthropic format → LangChain format | AC-07 |
| `test_sse_stream.py` | Event formatting: each event type produces correct SSE lines | AC-11, AC-12 |

### Integration Tests (required)

| Test | What It Tests | ACs |
|------|--------------|-----|
| `test_conversation_handler_integration.py` | Send message → get streamed response (mock Anthropic, real DB connection) | AC-10, AC-12 |
| `test_conversation_handler_integration.py` | Feature flag routing: v2=true routes to handler, v2=false routes to ChatService | AC-15, AC-16 |
| `test_conversation_handler_integration.py` | JSON mode: same ChatResponse format as existing endpoint | AC-10 |
| `test_conversation_handler_integration.py` | Tool execution through bridge: mock tool, verify _arun called | AC-03, AC-05 |

### Regression Tests (required)

| Test | What It Verifies |
|------|-----------------|
| `test_chat.py` (existing) | Old ChatService path works identically when flag is off |
| `test_main_chat_logic.py` (existing) | `/api/chat` JSON response format unchanged |
| `test_session_open_service.py` (existing) | Session-open works with both paths |
| `test_scheduled_execution_service.py` (existing) | Scheduled execution works with both paths |
| `test_telegram_session_creation.py` (existing) | Telegram path works with both paths |

### UI Acceptance Tests (Playwright)

| Test | What It Verifies | AC |
|------|------------------|----|
| `test_spec_033_send_message.py` | Send a message in web UI, verify response appears (JSON mode, no streaming yet) | AC-10 |
| `test_spec_033_tool_execution.py` | Ask agent to use a tool, verify response includes tool result | AC-03, AC-05 |

### AC-to-Test Mapping

| AC | Unit Test | Integration Test | Playwright |
|----|-----------|-----------------|------------|
| AC-01 | `test_handler_loop_basic` | — | — |
| AC-02 | `test_handler_uses_async_anthropic` | — | — |
| AC-03 | `test_handler_dispatches_tools` | `test_tool_execution_through_bridge` | `test_spec_033_tool_execution` |
| AC-04 | `test_handler_streaming_mode`, `test_handler_non_streaming_mode` | — | — |
| AC-05 | `test_bridge_schema_conversion`, `test_bridge_dispatch` | `test_tool_execution_through_bridge` | — |
| AC-06 | `test_history_load_langchain_to_anthropic` | — | — |
| AC-07 | `test_history_save_anthropic_to_langchain` | — | — |
| AC-08 | `test_token_tracking_per_turn`, `test_token_tracking_cumulative` | — | — |
| AC-09 | `test_handler_respects_model_config` | — | — |
| AC-10 | — | `test_sse_streaming_endpoint`, `test_json_fallback_endpoint` | `test_spec_033_send_message` |
| AC-11 | `test_sse_event_format_*` (per event type) | — | — |
| AC-12 | `test_sse_streaming_response_headers` | `test_sse_streaming_endpoint` | — |
| AC-13 | `test_client_disconnect_cancels_api_call` | — | — |
| AC-14 | `test_sse_cors_headers` | — | — |
| AC-15 | — | `test_feature_flag_routing_v2`, `test_feature_flag_routing_v1` | — |
| AC-16 | — | `test_feature_flag_routing_v2`, `test_feature_flag_routing_v1` | — |
| AC-17 | — | `test_tool_execution_through_bridge` | — |
| AC-18 | — | `test_feature_flag_routing_v1` (rollback = flag off) | — |
| AC-19 | — | `test_telegram_v2_path` | — |
| AC-20 | — | `test_scheduled_v2_path` | — |
| AC-21 | — | `test_session_open_v2_path` | — |
| AC-22 | — | `test_*_v1_path` (all channels with flag off) | — |
| AC-23 | `test_api_error_rate_limit`, `test_api_error_overloaded`, `test_api_error_auth` | — | — |
| AC-24 | `test_tool_error_continues_loop` | — | — |
| AC-25 | `test_max_turns_reached` | — | — |
| AC-26 | `test_timeout_cancels_request` | — | — |
| AC-27 | `test_error_logging_includes_context` | — | — |
| AC-28 | `test_dispatch_workflow_schema` | — | — |
| AC-29 | `test_dispatch_workflow_stub_response` | — | — |
| AC-30 | `test_dispatch_workflow_only_in_v2` | — | — |

### Manual Verification (UAT)

1. Start servers with `CONVERSATION_HANDLER_V2=true`
2. Send a message via web UI → verify response appears
3. Ask agent to search Gmail → verify tool executes and result is used in response
4. Send a message via Telegram → verify response appears
5. Trigger a scheduled run → verify execution result is stored
6. Switch `CONVERSATION_HANDLER_V2=false` → verify all above still works with old path
7. Compare response quality: same prompt through both paths should produce similar (not identical) responses

## Edge Cases

- **Empty tool args:** Some tools accept no arguments. The bridge must handle `args_schema` being None or having no required fields — converts to `{"type": "object", "properties": {}}`.
- **Tool returns None or empty string:** The handler must convert to a non-empty string (`"(No output)"`) before sending as `tool_result`. The Anthropic API rejects empty tool results.
- **Content block normalization:** LangChain stores assistant messages with tool calls as complex nested objects. The message history adapter must handle: plain text content, list-of-content-blocks, and tool_calls arrays in the stored format.
- **Concurrent tool calls:** If the API returns multiple `tool_use` blocks in one response, all are executed via `asyncio.gather()`. If one fails, the failed result is sent as `is_error: true` and the successful ones as normal results. The loop continues.
- **Large conversation history:** The 50-message window is applied during loading. If messages are very long (e.g., email body tool results), the total token count could exceed the model's context window. The handler should log a warning if history exceeds 80% of the model's context limit but not truncate (let the API handle it — it returns a clear error).
- **Feature flag mid-conversation:** Changing the flag between messages in the same session is safe. Both paths read/write the same message history format. The conversation continues seamlessly.
- **Approval-queued tools in streaming mode:** When a tool is wrapped with approval and returns a "queued for approval" message instead of executing, the handler treats this as a normal tool result. The agent receives the queued message and informs the user. No special handling needed.
- **Telegram push from v2 path:** The `_push_to_telegram_if_linked()` logic is extracted and called from the v2 path's web handler, not just from ChatService. Missing this would break cross-channel sync.

## Functional Units (for PR Breakdown)

All FUs are on a single branch: `feat/SPEC-033-conversation-handler`. Sequential execution — each FU commits before the next starts.

1. **FU-1: ConversationHandler Core + Bridge** (AC-01 through AC-09, AC-28-30)
   - `conversation_handler.py`, `langchain_tool_bridge.py`, `message_history_adapter.py`
   - `dispatch_workflow` stub
   - Unit tests for all three modules
   - **Agent:** backend-dev

2. **FU-2: SSE Streaming Endpoint** (AC-10 through AC-14)
   - `sse_stream.py`, modifications to `main.py`
   - Unit tests for SSE formatting, integration test for streaming endpoint
   - **Agent:** backend-dev
   - **Depends on:** FU-1

3. **FU-3: Feature Flag + Routing** (AC-15 through AC-18)
   - `settings.py` update, `main.py` routing logic
   - Integration tests for both flag states
   - **Agent:** backend-dev
   - **Depends on:** FU-2

4. **FU-4: Channel Adapters** (AC-19 through AC-22)
   - `telegram_bot.py`, `scheduled_execution_service.py`, `session_open_service.py` updates
   - Integration tests for each channel with both flag states
   - **Agent:** backend-dev
   - **Depends on:** FU-3

5. **FU-5: Error Handling + Resilience** (AC-23 through AC-27)
   - Error handling additions to `conversation_handler.py`
   - Unit tests for all error scenarios
   - **Agent:** backend-dev
   - **Depends on:** FU-1 (can be partially developed in parallel)

6. **FU-6: Regression + UAT** (all ACs)
   - Run existing test suite with flag on and off
   - Playwright UAT tests
   - Manual verification steps
   - **Agent:** uat-tester (or backend-dev)
   - **Depends on:** FU-4, FU-5

**Merge order:** FU-1 → FU-5 → FU-2 → FU-3 → FU-4 → FU-6 (FU-5 can merge after FU-1 since it only modifies `conversation_handler.py`)

## Decisions (Resolved)

1. **SSE format: simple JSON-per-line.** No `assistant-stream` protocol dependency. The SSE adapter is ~30 LOC and can be swapped to `assistant-stream` format later if SPEC-035 requires it.

2. **History storage: LangChain format during migration.** No dual-write, no new format. Messages saved in existing LangChain format for backward compat. Format migration happens after LangChain removal (separate cleanup spec).

3. **SPEC-035 FU-1 overlap: coordinated by team lead.** SPEC-035 FU-1 will reference this spec's SSE endpoint rather than building its own LangChain-based streaming.

## Completeness Checklist

- [x] Every AC has a stable ID (AC-01 through AC-30)
- [x] Every AC maps to at least one functional unit
- [x] Every cross-domain boundary has a contract (handler → bridge → BaseTool; handler → SSE → frontend)
- [x] Technical decisions reference principles from architecture-principles skill
- [x] Merge order is explicit and acyclic
- [x] Out-of-scope is explicit
- [x] Edge cases documented with expected behavior
- [x] Testing requirements map to ACs
- [x] Blast radius fully mapped (37 files analyzed)
