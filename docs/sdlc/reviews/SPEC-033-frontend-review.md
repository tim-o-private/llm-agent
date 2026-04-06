# SPEC-033 Frontend Impact Review

> **Reviewer:** Frontend Engineer
> **Date:** 2026-04-06
> **Spec:** SPEC-033 — Conversation Handler (Replace LangChain AgentExecutor with Anthropic Messages API)

## Verdict: PASS with CONCERNS

SPEC-033 does not break the frontend. The JSON fallback path (AC-10) preserves the existing `ChatResponse` format exactly. However, the SSE streaming format defined in SPEC-033 diverges from what SPEC-035 (Assistant-UI Alignment) expects, which will create rework.

---

## Files Affected on Frontend

All files that call `/api/chat` or parse its response:

| File | How It Uses `/api/chat` | Impact from SPEC-033 |
|------|------------------------|---------------------|
| `webApp/src/components/ChatPanelV2.tsx` (lines 126-151) | `fetch()` → `await response.json()` in `onNew` callback | **None** — no `Accept: text/event-stream` header sent, so backend returns JSON as before |
| `webApp/src/lib/assistantui/CustomRuntime.ts` (lines 86-107) | `fetch()` → `await httpResponse.json()` in `ChatModelAdapter.run()` | **None** — same JSON path |
| `webApp/src/api/hooks/useChatApiHooks.ts` (lines 55-76) | `fetch()` → `await httpResponse.json()` in `sendMessageApi()` | **None** — same JSON path |
| `webApp/src/lib/chatAPI.ts` (line 13) | `fetch()` → `response.json()` in `ChatAPIClient.sendMessage()` | **None** — note: hits `/chat` not `/api/chat` (different URL, possibly unused legacy) |
| `webApp/src/types/chat.ts` | Defines `ChatResponse` type (`session_id`, `response`, `tool_name`, `tool_input`, `error`) | **None** — JSON mode returns identical `ChatResponse` per AC-10 |
| `webApp/src/stores/useChatStore.ts` (lines 55-112) | `loadHistoricalMessages()` parses LangChain-format messages from `/api/chat/sessions/.../messages` | **None** — message history format unchanged per AC-07 |
| `webApp/src/api/hooks/useChatTimeline.ts` | Merges Zustand chat messages with React Query notifications | **None** — input data unchanged |
| `webApp/src/api/hooks/useChatHistoryHooks.ts` | Fetches session list and messages from `/api/chat/sessions` | **None** — history endpoints not modified by SPEC-033 |

**Bottom line: Zero frontend files need changes for SPEC-033.** The spec correctly marks "Frontend streaming consumer" as out of scope (line 150).

---

## Format Compatibility Analysis

### Current format (JSON response, unchanged)

```
POST /api/chat
Content-Type: application/json

→ Response:
{
  "session_id": "...",
  "response": "Here's what I found...",
  "tool_name": "search_gmail" | null,
  "tool_input": {...} | null,
  "error": null
}
```

The frontend receives the complete response after all tool calls finish. Tool execution is invisible to the user — they only see the final text and optionally the last tool name/input.

### SPEC-033 SSE format (AC-11)

```
data: {"type": "text_delta", "text": "Hello"}
data: {"type": "tool_start", "tool_name": "search_gmail", "tool_call_id": "toolu_01xyz"}
data: {"type": "tool_result", "tool_call_id": "toolu_01xyz", "result": "Found 3 emails..."}
data: {"type": "text_delta", "text": "I found 3 emails..."}
data: {"type": "message_complete", "token_usage": {"input_tokens": 1200, "output_tokens": 350}}
```

### SPEC-035 expected format (AC-01, AC-02)

```
data: {"type": "part-start", ...}    (assistant-stream AssistantTransportEncoder)
data: {"type": "text-delta", ...}
data: {"type": "tool-call-begin", ...}
data: {"type": "tool-call-delta", ...}
data: {"type": "tool-result", ...}
data: {"type": "message-finish", ...}
```

### What breaks?

Nothing breaks today. But **the two specs define incompatible SSE formats**:

- SPEC-033 AC-11 defines: `text_delta`, `tool_start`, `tool_result`, `message_complete`, `error` (custom JSON-per-line)
- SPEC-035 AC-01/AC-02 expects: `assistant-stream` `AssistantTransportEncoder` format (`part-start`, `text-delta`, `tool-call-begin`, etc.)

SPEC-033 Decision #1 explicitly rejects `assistant-stream`: "No assistant-stream protocol dependency." SPEC-035 FU-2 explicitly requires it: "Reads the SSE response via `AssistantStream.fromResponse(response, new AssistantTransportDecoder())`."

This means one of:
1. SPEC-033's SSE format gets replaced by `assistant-stream` before SPEC-035 FU-2 starts (rework)
2. SPEC-035 FU-2 builds a translation layer from SPEC-033 format to `assistant-stream` (complexity)
3. SPEC-033 adopts `assistant-stream` format from the start (simplest)

---

## Feature Flag Implications

**The frontend does NOT need its own feature flag.** The mechanism is clean:

1. Backend flag `CONVERSATION_HANDLER_V2` controls which handler processes the request
2. Frontend doesn't send `Accept: text/event-stream` → always gets JSON → same behavior regardless of flag
3. When SPEC-035 adds streaming (frontend sends `Accept: text/event-stream`), the backend already has the SSE path ready
4. Flag is completely transparent to the frontend

This is a good design. No frontend coordination needed during rollout.

---

## Recommended Changes to the Spec

### CONCERN 1: SSE format must align with SPEC-035 (Medium Priority)

SPEC-033 defines a custom JSON-per-line SSE format (AC-11). SPEC-035 expects `assistant-stream` `AssistantTransportEncoder` format. These are different event types, different field names, different serialization.

**Recommendation:** Either:
- **(a)** Update SPEC-033 AC-11 to use `assistant-stream` format from the start (add `assistant-stream` to `requirements.txt`), or
- **(b)** Add an explicit AC to SPEC-033 stating: "The SSE format defined here is a temporary implementation. Before SPEC-035 FU-2, the SSE events will be migrated to `assistant-stream` `AssistantTransportEncoder` format." Make this a known tech debt item.
- **(c)** Update SPEC-035 to consume SPEC-033's simpler format instead of `assistant-stream` (simplest if `assistant-stream` Python package doesn't exist or is poorly maintained — SPEC-035 Risk #2 acknowledges this).

Option (a) is cleanest if the Python `assistant-stream` package works. Option (c) is the pragmatic fallback.

### CONCERN 2: `chatAPI.ts` hits wrong URL (Low Priority)

`webApp/src/lib/chatAPI.ts:13` calls `${this.baseURL}/chat` (no `/api/` prefix). All other callers use `/api/chat`. This file may be unused legacy code, but if it's used anywhere, it won't route through the feature-flagged endpoint.

**Recommendation:** Verify if `chatAPI.ts` is imported anywhere. If not, mark for removal in a cleanup pass. If it is used, fix the URL.

### CONCERN 3: Tool call visibility gap (Informational)

The current JSON response includes only the *last* tool name/input (`tool_name`, `tool_input` fields). When the ConversationHandler executes multiple tools in a multi-turn loop, only the final one is visible in the JSON response. This is the same limitation as today (LangChain path also returns only the final response text), so it's not a regression.

The SSE format (AC-11) solves this by streaming `tool_start`/`tool_result` per tool. SPEC-035 FU-3 adds the UI components. This is correctly sequenced across specs.

### CONCERN 4: `loadHistoricalMessages` parses LangChain format (Informational)

`useChatStore.ts:84-94` parses historical messages by looking for `msgData.type === 'human'` and `dataField.content` — this is the LangChain stored format. SPEC-033 AC-07 correctly preserves this format during migration. When LangChain is eventually removed (post-SPEC-033 cleanup), the message storage format will change and this parser will need updating. This is out of scope for SPEC-033 but worth noting.

---

## Estimate of Frontend Work Needed

**For SPEC-033 itself: Zero frontend changes required.**

The spec correctly scopes frontend streaming to SPEC-035. The JSON fallback path preserves full backward compatibility.

**For SPEC-035 (which depends on SPEC-033's SSE endpoint):**

| Scope | Files | Complexity |
|-------|-------|------------|
| Runtime migration (`useExternalStoreRuntime` → `useLocalRuntime`) | `ChatPanelV2.tsx`, new `chatModelAdapter.ts` | High — core architecture change |
| Streaming consumer | New adapter file + `assistant-stream` integration | Medium — depends on format alignment |
| Remove Zustand message store | `useChatStore.ts`, `ChatPanelV2.tsx` | Medium — large file, many callers |
| Tool call UI | New `ToolCallFallback` component | Low-Medium |
| Remove scroll hack, error boundary, polling | `ChatPanelV2.tsx` | Low — deletion |
| Delete `CustomRuntime.ts` | 1 file | Low — deletion |
| Simplify `useChatTimeline.ts` | 1 file | Low |

Total: ~8-10 files touched, but that's all SPEC-035 scope, not SPEC-033.
