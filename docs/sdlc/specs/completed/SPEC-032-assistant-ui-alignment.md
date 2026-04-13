# SPEC-032: Assistant-UI Alignment — Replace Hacks with Standard Patterns

> **Status:** Draft
> **Author:** Tim + Claude (Product)
> **Created:** 2026-02-27

## Goal

Eliminate custom workarounds in the assistant-ui integration and replace them with standard library features. The current implementation uses `useExternalStoreRuntime` to feed a Zustand-managed message store into assistant-ui as a "dumb renderer." This creates six categories of hacks: manual scroll management, error boundaries for message crashes, polling-based message sync, no streaming, no tool UI, and fragile message refresh logic. Each of these has a standard assistant-ui solution.

## Background

The assistant-ui integration (ChatPanelV2, SPEC-025) was built incrementally. The initial goal was "get assistant-ui rendering our messages" rather than "use assistant-ui as the state owner." This produced a working system, but one that fights the library at several points:

1. **Zustand owns messages, assistant-ui just renders** — Messages live in `useChatStore`. The `useExternalStoreRuntime` bridge converts them to `ThreadMessageLike` and feeds them in. This means assistant-ui can't manage message IDs, branching, or optimistic updates natively. The `refreshMessages()` function has a 40-line workaround to avoid crashing assistant-ui's `MessageRepository` during ID remapping.

2. **No streaming** — The `/api/chat` endpoint returns a complete JSON response. The user sees nothing until the full response arrives. For long agent responses (tool chains, multi-step reasoning), this creates dead-air UX.

3. **Manual scroll-to-bottom** — A `MutationObserver` watches the viewport DOM and scrolls for 1500ms after session switch. This exists because `useExternalStoreRuntime` renders messages asynchronously and the built-in scroll-to-bottom behavior doesn't reliably fire when the entire message array is replaced at once.

4. **Error boundary for role crashes** — `ThreadErrorBoundary` catches "can't access property 'role'" errors from assistant-ui. Root cause: occasionally the timeline array produces a message that assistant-ui can't parse during the external store sync. Standard runtimes with proper message ownership don't have this failure mode.

5. **No tool call UI** — Tool calls are captured in the response (`tool_name`, `tool_input`) but never rendered. The `makeAssistantToolUI` pattern exists for exactly this.

6. **Approval cards bypass assistant-ui** — `ApprovalInlineMessage` is rendered as a SystemMessage via metadata carrier hack. The `submitResult` pattern in `makeAssistantToolUI` with `status: "requires-action"` is purpose-built for human-in-the-loop approvals.

7. **Custom focus tracking** — Manual `focusin`/`focusout` listeners to detect when the composer is focused. This exists to prevent keyboard shortcuts from firing while typing.

### What's working well (keep)

- `useChatTimeline` merge pattern (A4-compliant: React Query notifications + Zustand messages)
- Notification inline rendering (`NotificationInlineMessage`, `ApprovalInlineMessage`)
- Session lifecycle management (heartbeat, wakeup, beforeunload)
- Custom `Thread.tsx` primitives (well-structured, uses standard primitives correctly)
- ConversationList (thread switching UI)

## Design Decisions

### Migrate from `useExternalStoreRuntime` to `useLocalRuntime`

`useExternalStoreRuntime` was the right choice for "drop assistant-ui into an existing message store." But it creates the impedance mismatch that causes most of our hacks. `useLocalRuntime` lets assistant-ui own message state natively while we control the model adapter (how messages get sent to/from the backend).

The `ChatModelAdapter.run()` method is an async generator that yields `ChatModelRunResult` chunks — exactly what we need for streaming. assistant-ui handles optimistic user messages, message IDs, scroll management, and running state internally.

**What changes:**
- `useChatStore.messages` is no longer the source of truth for the chat timeline. assistant-ui's internal `MessageRepository` owns the canonical message list.
- `useChatStore` retains session management (activeChatId, sessionInstanceId, heartbeat, wakeup) and becomes the "session store" rather than "message store."
- Historical messages loaded on session switch are fed into `useLocalRuntime` via `runtime.thread.import()` or initial messages.
- The `onNew` callback in ChatPanelV2 becomes the `ChatModelAdapter.run()` generator.

**What this fixes:**
- Scroll management (assistant-ui handles it natively with `useLocalRuntime`)
- Error boundary crashes (no more external array sync mismatches)
- Message refresh/ID remapping workaround (assistant-ui manages IDs)
- Running state (assistant-ui tracks it internally via the generator lifecycle)

### Add streaming via `assistant-stream`

The backend already returns structured responses. Adding SSE streaming is a backend change (FU-1) that the frontend consumes via `assistant-stream`'s `AssistantStream` decoder inside the `ChatModelAdapter.run()` generator.

**Streaming format:** Use `assistant-stream`'s `AssistantTransportEncoder/Decoder` (native format, not AI SDK data stream). This avoids coupling to Vercel's SDK and gives us full control over tool call streaming, reasoning tokens, and custom events.

**Backend change:** The `/api/chat` endpoint gains an `Accept: text/event-stream` header option. When present, it streams the response as SSE events using `assistant-stream`'s `AssistantTransportEncoder`. When absent, it returns the current JSON response (backward compatibility for Telegram and non-web clients).

**Frontend change:** The `ChatModelAdapter.run()` generator fetches with `Accept: text/event-stream`, reads the response via `AssistantStream.fromResponse()`, and yields `ChatModelRunResult` chunks as they arrive. Text appears character-by-character. Tool calls render progressively.

### Add tool call UI via `makeAssistantToolUI`

Register tool UI components for agent tools so users can see what the agent is doing. Each tool gets a renderer that shows:
- **While running:** Tool name + streaming args (if available)
- **Complete:** Tool name + result summary
- **Error:** Tool name + error message

Start with a generic `ToolFallback` component for all tools, then add specific renderers for high-value tools (Gmail, search, memory) in follow-ups.

### Migrate approval cards to `makeAssistantToolUI` with `submitResult`

The assistant-ui `makeAssistantToolUI` pattern supports `status: "requires-action"` with a `submitResult(result)` callback. This is exactly the approval flow pattern. Instead of our metadata-carrier hack (converting approvals to SystemMessages), approvals become proper tool call UI components.

**How it works:**
1. Backend returns a tool call with `status: "requires-action"` when approval is needed
2. The tool UI component renders approve/reject buttons
3. On approve: `submitResult({ approved: true })` → triggers backend execution
4. On reject: `submitResult({ approved: false, reason: "..." })` → notifies agent

**Why this is better:** The approval card becomes part of the message tree, supports branching (edit + re-approve), and the agent continuation happens naturally through the tool result flow rather than a side-channel chat message.

**Migration note:** This requires the backend to return approval requests as tool calls rather than notifications. This is a meaningful architectural shift. If the backend change is too large for this spec, keep the current notification-based approach but render approval notifications via `makeAssistantToolUI` by name-matching the `action_tool_name`.

### Keep notification timeline merge, render via `MessagePrimitive.Content` components

Notifications that aren't approvals (info, heartbeat results, digests) continue to arrive via React Query polling and merge into the timeline. But instead of the SystemMessage metadata carrier hack, register them as custom content part types rendered via `MessagePrimitive.Content` components.

### Remove manual scroll management

With `useLocalRuntime`, delete the entire `MutationObserver` scroll block (ChatPanelV2 lines 275-315). assistant-ui's `ThreadPrimitive.Viewport` handles scroll-to-bottom natively for messages added through the runtime.

For historical message hydration on session switch, use the runtime's message import API rather than setting an external array.

### Remove `ThreadErrorBoundary`

The "can't access property 'role'" crashes stem from the external store sync producing malformed messages. With `useLocalRuntime`, messages are created through the proper runtime API and this class of error disappears. Keep a generic React error boundary at the app level, but remove the thread-specific one.

### Simplify `useChatStore` to session-only concerns

Strip message management from `useChatStore`. It becomes:

```typescript
interface ChatSessionStore {
  activeChatId: string | null;
  currentSessionInstanceId: string | null;
  currentAgentName: string | null;
  isInitializingSession: boolean;
  lastWakeupAt: number | null;
  isChatPanelOpen: boolean;
  // Session lifecycle methods (no message methods)
  initializeSessionAsync: (agentName: string) => Promise<void>;
  clearCurrentSessionAsync: () => Promise<void>;
  startNewConversationAsync: (agentName: string) => Promise<void>;
  switchToConversationAsync: (chatId: string) => Promise<HistoricalMessage[]>;
  sendHeartbeatAsync: () => Promise<void>;
  triggerWakeup: () => Promise<WakeupResult | null>;
  toggleChatPanel: () => void;
  setChatPanelOpen: (isOpen: boolean) => void;
}
```

`switchToConversationAsync` returns historical messages instead of setting them in state — the caller feeds them to the runtime.

## Acceptance Criteria

### FU-1: Backend Streaming Endpoint

- [ ] **AC-01:** `/api/chat` returns SSE when request includes `Accept: text/event-stream` header. Response uses `assistant-stream` `AssistantTransportEncoder` format with `Content-Type: text/event-stream`. Without the header, returns current JSON response (backward compat). [A1, A7]
- [ ] **AC-02:** SSE stream emits `part-start` (type: text) → `text-delta` events as the agent generates tokens → `message-finish` on completion. Token streaming uses LangChain's `astream_events()` or callback handler to capture incremental output. [A1]
- [ ] **AC-03:** When the agent invokes a tool, the stream emits `part-start` (type: tool-call) with `toolCallId` and `toolName`, then `tool-call-args-text-delta` events as args are assembled, then `result` with the tool's return value. Multiple tool calls in one turn each get their own part. [A6]
- [ ] **AC-04:** When a tool requires approval, the stream emits a tool call part with `status: "requires-action"` instead of a result. The tool call args contain `action_id`, `tool_name`, and `tool_args`. The stream does NOT close — it stays open until the approval resolves or times out. [A12]
- [ ] **AC-05:** `assistant-stream` is added to `chatServer/requirements.txt` and root `requirements.txt`. [Gotcha #1]
- [ ] **AC-06:** Stream supports `AbortSignal` — when the client disconnects, the server cancels the LangChain run. Uses FastAPI's `Request.is_disconnected()` check. [A1]

### FU-2: Frontend Runtime Migration

- [ ] **AC-07:** `ChatPanelV2` uses `useLocalRuntime` instead of `useExternalStoreRuntime`. The `ChatModelAdapter.run()` async generator fetches `/api/chat` with `Accept: text/event-stream` and yields `ChatModelRunResult` chunks from `AssistantStream.fromResponse()`. [A4]
- [ ] **AC-08:** `assistant-stream` is added to `webApp/package.json`. [A4]
- [ ] **AC-09:** On session switch, historical messages are loaded and provided to the runtime via initial messages or `runtime.thread.import()`. The Zustand store's `switchToConversationAsync` returns messages instead of setting them internally. [A4]
- [ ] **AC-10:** The `MutationObserver` scroll-to-bottom block (ChatPanelV2 lines 275-315) is removed. Scroll behavior relies on `ThreadPrimitive.Viewport` native scroll management. [A14]
- [ ] **AC-11:** The `ThreadErrorBoundary` class is removed. A generic error boundary at the app/page level remains. [A14]
- [ ] **AC-12:** The `isRunning` state variable and `setIsRunning` calls are removed. Running state is managed internally by `useLocalRuntime` via the generator lifecycle. [A4]
- [ ] **AC-13:** The `refreshMessages` polling interval (5s) is removed. Cross-channel message sync (Telegram → web) uses the notification polling that already exists, OR a future WebSocket/realtime subscription. Messages from other channels appear as notification-type items in the timeline. [A4]
- [ ] **AC-14:** The `convertMessage` callback is removed. `useLocalRuntime` manages message format internally. Historical messages are converted once during import. [A4]

### FU-3: Tool Call UI

- [ ] **AC-15:** A generic `ToolCallFallback` component is registered via `makeAssistantToolUI` with `toolName: "*"` (or individual registration per known tool). Shows tool name, streaming args while running, result summary when complete. [A13]
- [ ] **AC-16:** Gmail tools (`send_email`, `search_emails`, `create_draft`) get specific `makeAssistantToolUI` renderers showing: recipient/subject while running, sent confirmation when complete. [A13]
- [ ] **AC-17:** Search tools (`web_search`, `web_search_tavily`) get a renderer showing: query while running, result count + snippet when complete. [A13]
- [ ] **AC-18:** Tool UI components are registered inside `AssistantRuntimeProvider` alongside `<Thread />`. [A13]

### FU-4: Approval Flow via Tool UI

- [ ] **AC-19:** When a tool call arrives with `status: "requires-action"`, a `makeAssistantToolUI` component renders the approval card (reuse `ApprovalInlineMessage` visual design). [A12, A13]
- [ ] **AC-20:** The approval component uses `submitResult({ approved: true })` on approve and `submitResult({ approved: false, reason })` on reject. The result flows back through the stream, triggering the agent to continue. [A12]
- [ ] **AC-21:** The backend `/api/chat` streaming endpoint receives the `submitResult` via a follow-up request (or the still-open SSE connection) and executes the tool via `ToolExecutionService`, then resumes streaming the agent's response. [A12]
- [ ] **AC-22:** The current SystemMessage metadata carrier pattern for approvals is removed. Approvals render as tool call UI, not system messages. [A14]

### FU-5: Zustand Store Simplification

- [ ] **AC-23:** `useChatStore` is renamed to `useChatSessionStore` and stripped of message-related state and methods: `messages`, `addMessage`, `refreshMessages` are removed. [A4, A10]
- [ ] **AC-24:** `switchToConversationAsync` returns `Promise<ChatMessage[]>` (the loaded historical messages) instead of setting `messages` in state. The caller (ChatPanelV2) feeds these to the runtime. [A4]
- [ ] **AC-25:** `useChatTimeline` hook is simplified. It no longer merges Zustand messages with React Query notifications. Instead, notifications are injected into the runtime as system messages via the adapter. The hook may be removed entirely if notifications flow through the streaming response. [A4]
- [ ] **AC-26:** The message comparison logic in `refreshMessages` (lines 508-541 of useChatStore.ts) is deleted entirely. No longer needed when assistant-ui owns message state. [A14]

### FU-6: Focus Management Cleanup

- [ ] **AC-27:** The manual `focusin`/`focusout` listener block (ChatPanelV2 lines 235-273) is replaced with assistant-ui's composer focus detection via `useAuiState(s => s.composer.isFocused)` or equivalent, if available. If not available, keep the listener but scope it tighter using `ComposerPrimitive.Root`'s ref rather than global document listeners. [A13]

## Scope

### Packages to Add

| Package | Location | Purpose |
|---------|----------|---------|
| `assistant-stream` | `webApp/package.json` | Streaming protocol decoder |
| `assistant-stream` | `chatServer/requirements.txt` + root `requirements.txt` | Streaming protocol encoder |

### Files to Create

| File | Purpose |
|------|---------|
| `webApp/src/components/assistantui/ToolFallback.tsx` | Generic tool call UI component |
| `webApp/src/components/assistantui/GmailToolUI.tsx` | Gmail-specific tool renderers |
| `webApp/src/components/assistantui/SearchToolUI.tsx` | Search tool renderers |
| `webApp/src/components/assistantui/ApprovalToolUI.tsx` | Approval flow via makeAssistantToolUI |
| `webApp/src/lib/chatModelAdapter.ts` | ChatModelAdapter with streaming fetch |
| `chatServer/services/stream_response.py` | SSE streaming response builder |
| Tests for each new file |

### Files to Modify

| File | Change |
|------|--------|
| `webApp/src/components/ChatPanelV2.tsx` | Replace `useExternalStoreRuntime` with `useLocalRuntime`, remove scroll hack, error boundary, focus listeners, isRunning state |
| `webApp/src/stores/useChatStore.ts` | Strip message state/methods, rename to `useChatSessionStore` |
| `webApp/src/api/hooks/useChatTimeline.ts` | Simplify or remove |
| `chatServer/routers/chat.py` | Add SSE streaming path |
| `chatServer/services/chat_service.py` | Expose token-by-token streaming |
| `webApp/package.json` | Add `assistant-stream` |
| `chatServer/requirements.txt` | Add `assistant-stream` |
| `requirements.txt` | Add `assistant-stream` |

### Files to Delete

| File | Reason |
|------|--------|
| (none immediately — old components kept until migration is verified) | |

### Blast Radius

Files touched by modified components that must be regression-tested:

| File | Risk |
|------|------|
| `webApp/src/components/features/Conversations/ConversationList.tsx` | Uses `useChatStore.switchToConversationAsync` — signature changes |
| `webApp/src/api/hooks/useNotificationHooks.ts` | `useChatTimeline` changes may affect notification polling |
| `chatServer/routers/chat.py` | Streaming path must not break existing JSON path |
| `chatServer/services/pending_actions.py` | Approval flow changes if FU-4 implemented |
| `webApp/src/components/ui/chat/ApprovalInlineMessage.tsx` | Replaced by ApprovalToolUI (FU-4) |
| `webApp/src/components/ui/chat/NotificationInlineMessage.tsx` | May change rendering context |
| Telegram bot message handling | Must continue receiving JSON responses (no SSE) |

## Technical Approach

### FU-1: Backend Streaming (backend-dev)

Add SSE support to the chat endpoint using FastAPI's `StreamingResponse`. The LangChain agent's `astream_events()` (or `astream_log()`) produces incremental events that map to `assistant-stream` transport chunks. The encoder serializes them as `data: {json}\n\n` SSE events.

Key concern: LangChain's streaming APIs vary by executor type. The current `AgentExecutor` supports `astream_events(version="v2")` which emits `on_chat_model_stream` events containing token deltas, and `on_tool_start`/`on_tool_end` for tool calls. Map these to `assistant-stream` events.

### FU-2: Frontend Runtime Migration (frontend-dev)

This is the largest FU. Implement `ChatModelAdapter` as an async generator that:
1. Sends the user message to `/api/chat` with `Accept: text/event-stream`
2. Reads the SSE response via `AssistantStream.fromResponse(response, new AssistantTransportDecoder())`
3. Maps stream events to `ChatModelRunResult` chunks and yields them
4. Handles abort via `AbortSignal`

Historical message loading on session switch uses the runtime's message import. Notification interleaving uses a separate mechanism (custom content parts or side-panel).

### FU-3: Tool Call UI (frontend-dev)

Straightforward `makeAssistantToolUI` registrations. The generic fallback handles unknown tools. Specific tools get richer rendering. All components mounted inside `AssistantRuntimeProvider`.

### FU-4: Approval Flow Migration (backend-dev + frontend-dev)

This is the most architecturally significant change. Requires:
- Backend: Return approval-needed as a tool call with `requires-action` status in the stream
- Frontend: `makeAssistantToolUI` component with `submitResult` callback
- Backend: Resume stream after approval resolution

If the streaming + approval integration proves too complex for this spec, FU-4 can be deferred to a follow-up spec. The notification-based approval flow from SPEC-025 continues to work.

### FU-5: Store Simplification (frontend-dev)

Mechanical refactor once FU-2 is complete. Remove message fields, update callers.

### FU-6: Focus Management (frontend-dev)

Small cleanup. Check if `useAuiState` exposes composer focus. If not, scope the listener to the composer root element.

## Ordering & Dependencies

```
FU-1 (backend streaming) ──┐
                            ├──→ FU-2 (runtime migration) ──→ FU-5 (store simplification)
FU-3 (tool UI) ────────────┘                                       │
                                                                    ├──→ FU-6 (focus cleanup)
FU-4 (approval flow) ── depends on FU-1 + FU-2 ────────────────────┘
```

FU-3 (tool UI) can start in parallel with FU-1 using mock data, but needs FU-2 for live integration.
FU-4 is the riskiest FU. Evaluate after FU-1 + FU-2 whether to include or defer.

## Risks

1. **LangChain streaming compatibility** — `astream_events` behavior varies by chain type. May need custom callback handler instead.
2. **assistant-stream Python package** — Verify it exists and is maintained for Python. If not, implement the SSE encoder manually (the format is simple: `data: {json}\n\n` with defined event types).
3. **Approval flow complexity** — Keeping an SSE connection open while waiting for human approval (potentially hours) is fragile. May need a reconnect-and-resume pattern or a separate approval submission endpoint.
4. **Notification interleaving** — With `useLocalRuntime`, injecting non-message items (notifications) into the thread requires either custom content parts or a parallel rendering channel. The current SystemMessage pattern may need to evolve.
5. **Historical message format** — The backend stores messages in LangChain's format (`{type: "human", data: {content: ...}}`). The `loadHistoricalMessages` parser handles content block arrays. This parsing still needs to happen during runtime import.
6. **Cross-channel sync** — Removing the 5s polling for Telegram messages means we need an alternative. Supabase Realtime subscription on `chat_messages` table or notification-based sync.
