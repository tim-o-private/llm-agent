# Implementation Plan: Agent Memory System v2 (Efficient & Evolving)

**Date:** {datetime.now().isoformat()}
**Associated Creative Design:** `memory-bank/creative/agent_memory_system_v2_efficient_evolving.md`
**Complexity Level:** 4 (Complex System)

## 1. Requirements Analysis (Summary from Creative Design v2)

The primary goal is to refactor the agent memory system to:
*   Minimize database writes per conversational turn.
*   Implement an evolving, natural language-based Long-Term Memory (LTM) store, agent-curated.
*   Leverage client-side state for buffering active conversation messages, enabling batched persistence.
*   Ensure agents maintain robust short-term context and can recall long-term preferences/knowledge.
*   Utilize Supabase for persistence and integrate with LangChain patterns where beneficial.

## 2. Components Affected & Scope

This is a significant architectural change impacting multiple parts of the system:

*   **Client-Side (Web App):**
    *   `webApp/src/stores/useChatStore.ts`: Will manage the live conversation buffer and initiate batch archival.
    *   New API call logic for batch archival.
    *   Logic to handle `session_id` and potentially load initial recent history.
*   **Server-Side (`chatServer/main.py`):**
    *   New API endpoint: `/api/chat/session/archive_messages`.
    *   Modification to `/api/chat` to work with client-sent new messages and server-side short-term cache.
    *   Implementation of the server-side short-term session cache (`server_session_cache`).
    *   Logic for interacting with the new LTM Supabase table.
*   **Agent Core (`src/core/`):
    *   `agent_loader.py`: Modified to fetch LTM for agents.
    *   `CustomizableAgent` (or similar in `src/core/agents/`): Modified to incorporate LTM into prompts and use the new short-term context mechanism.
    *   New Agent Tool: `ManageLongTermMemoryTool` (`src/core/tools/memory_tools.py`).
*   **Database (Supabase):**
    *   New Table: `recent_conversation_history` (for batched raw messages).
    *   New Table: `agent_long_term_memory` (for natural language LTM).
    *   New Table (Optional): `agent_sessions` (for session metadata, if not just using `session_id` strings).
    *   Schema migrations and RLS policies for these tables.
*   **Superseded/Modified from `agent_memory_solution_design_v1.md`:**
    *   The `SupabaseChatMessageHistory` class (from `src/core/memory/supabase_chat_history.py`) writing individual messages to an `agent_chat_messages` table is **superseded** by the new batch archival to `recent_conversation_history` and client/server caching. The `agent_chat_messages` table as a per-message log will likely be **removed or repurposed**.
    *   The direct use of LangChain's `ConversationBufferMemory` pointing to a per-message SQL store will change. Agents will receive short-term history constructed by `chatServer`.
    *   The concept of session summarization in `agent_sessions.summary` (from v1 design) can still be a future enhancement but is not the primary LTM mechanism now.

## 3. Implementation Strategy & Phasing

Given the complexity, a phased approach is recommended:

**Phase 1: Backend Foundation - LTM & Short-Term Cache Core**
*   Goal: Establish the LTM store and the server-side short-term caching mechanism. Enable agents to read/write LTM.
*   Key Steps:
    1.  Database: Define and migrate schemas for `agent_long_term_memory` and `agent_sessions` (if used). Implement RLS.
    2.  `chatServer`: Implement `server_session_cache` (in-memory dict).
    3.  Tool: Create `ManageLongTermMemoryTool` with basic `read` and `overwrite`/`append` operations for `agent_long_term_memory`.
    4.  Agent Core: Modify `agent_loader.py` to fetch LTM. Modify `CustomizableAgent` to inject LTM into prompts and utilize the `ManageLongTermMemoryTool`.
    5.  Testing: Unit tests for the tool, integration tests for agent LTM read/write via CLI or direct API calls (simulating client).

**Phase 2: Client-Side Buffering & Batch Archival API**
*   Goal: Implement client-side message buffering and the API for batch archival of recent conversations.
*   Key Steps:
    1.  Database: Define and migrate schema for `recent_conversation_history`. Implement RLS.
    2.  `chatServer`: Create `/api/chat/session/archive_messages` endpoint to receive message batches and save them to `recent_conversation_history`.
    3.  Client (`useChatStore.ts` & API logic): Implement client-side triggers (close, navigate, periodic) to call the archival API.
    4.  Testing: Test client triggers, API endpoint functionality, and correct batch storage in Supabase.

**Phase 3: Integrating Short-Term Context Flow**
*   Goal: Connect the client, server-side cache, and agent to ensure seamless short-term conversational context.
*   Key Steps:
    1.  Client (`/api/chat` calls): Modify client to send only *new* messages (and `session_id`, `agent_id`).
    2.  `chatServer` (`/api/chat` endpoint): Refactor to use `server_session_cache` and new client messages to assemble short-term history for the agent. Update `server_session_cache` after agent response.
    3.  `CustomizableAgent`: Ensure it correctly processes the assembled short-term history.
    4.  Testing: End-to-end testing of conversational flow, ensuring context is maintained across turns.

**Phase 4: Refinements, Advanced LTM Operations & Pruning**
*   Goal: Enhance LTM tool, implement pruning strategies, and conduct thorough testing.
*   Key Steps:
    1.  Tool: Enhance `ManageLongTermMemoryTool` with more operations (e.g., section-based editing).
    2.  Pruning: Implement pruning/archival strategies for `recent_conversation_history` (e.g., based on `archived_at`).
    3.  Full Test Plan Execution (see section 5).
    4.  Documentation updates.

## 4. Detailed Steps (per phase)

*(This section will expand significantly with detailed sub-tasks for each phase, covering file modifications, new class/function definitions, API request/response schemas, etc. For brevity here, major actions are listed.)*

### Phase 1: Backend Foundation
1.  **DB Schema (`agent_long_term_memory`):** Define table (id, user_id, agent_name, notes TEXT, timestamps). Add RLS.
2.  **DB Schema (`agent_sessions` - optional):** Define table (session_id, user_id, agent_name, timestamps). Add RLS.
3.  **`chatServer` (`server_session_cache`):** Implement as `Dict[str, List[SerializedBaseMessage]]`.
4.  **Tool (`ManageLongTermMemoryTool` in `src/core/tools/memory_tools.py`):**
    *   Implement `_run` and `_arun`.
    *   Initial operations: `read`, `overwrite`, `append` notes in `agent_long_term_memory` table.
5.  **`agent_loader.py`:** Add logic to fetch LTM notes for `user_id/agent_name` on agent load.
6.  **`CustomizableAgent`:** Modify prompt assembly to include LTM notes. Ensure tool is available.

### Phase 2: Client-Side Buffering & Batch Archival API
1.  **DB Schema (`recent_conversation_history`):** Define table (id, session_id, user_id, message_batch JSONB, timestamps). Add RLS.
2.  **`chatServer` (`/api/chat/session/archive_messages`):**
    *   Define Pydantic models for request (session_id, messages_batch) and response.
    *   Implement endpoint to insert into `recent_conversation_history`.
3.  **`webApp/src/stores/useChatStore.ts`:**
    *   Add state/logic to track `session_id`.
    *   Implement functions to be called on triggers (close, navigate, periodic).
4.  **Web App API Layer:** Create function to call `/api/chat/session/archive_messages`.

### Phase 3: Integrating Short-Term Context Flow
1.  **Web App API Layer (`/api/chat` call):** Modify to send `{ new_messages, session_id, agent_id }`.
2.  **`chatServer` (`/api/chat` endpoint):**
    *   Retrieve context from `server_session_cache[session_id]`.
    *   Append `new_messages` from request.
    *   Pass combined history to agent.
    *   Update `server_session_cache` with user messages + AI response + tool messages for the turn.
3.  **Session ID Management:** Ensure `session_id` is generated on first client interaction if not existing, and passed consistently.

### Phase 4: Refinements
1.  **`ManageLongTermMemoryTool`:** Add `prepend`, section-based operations.
2.  **Pruning `recent_conversation_history`:** Create a strategy/script (e.g., delete records older than X days).
3.  **Error Handling:** Enhance client/server error handling for new API calls and memory operations.

## 5. Test Plan

### 5.1. Unit Tests
*   **`ManageLongTermMemoryTool`:**
    *   Test `read` operation (empty notes, existing notes).
    *   Test `overwrite` operation.
    *   Test `append` operation.
    *   Test `prepend` operation (Phase 4).
    *   Test section-based operations (Phase 4).
    *   Test with invalid inputs/permissions (mocked RLS if possible).
*   **`chatServer` `/api/chat/session/archive_messages` Endpoint:**
    *   Test successful batch archival.
    *   Test with empty message batch.
    *   Test with invalid `session_id` / `user_id` (auth errors).
*   **`chatServer` Short-Term Cache Logic:**
    *   Test cache initialization for new session.
    *   Test context assembly (cache + new messages).
    *   Test cache update after agent response.
    *   Test sliding window logic if implemented.
*   **Client-Side Archival Trigger Logic (e.g., in `useChatStore` or related services):**
    *   Mock browser events (close, navigate) and verify API call is made.
    *   Test periodic trigger if implemented.

### 5.2. Integration Tests
*   **LTM Read/Write Flow:**
    *   Agent uses tool to write to LTM.
    *   New agent session for same user/agent reads and uses the written LTM in its prompt.
*   **Short-Term Context Maintenance:**
    *   Multi-turn conversation where agent correctly references information from immediate prior turns.
    *   Verify context is maintained even if `server_session_cache` had to be rehydrated (simulated restart, though tricky).
*   **Batch Archival Full Flow:**
    *   Client holds N messages in `useChatStore`.
    *   Client trigger fires (e.g., simulated close).
    *   Verify `/api/chat/session/archive_messages` is called with correct batch.
    *   Verify data is correctly stored in `recent_conversation_history`.
*   **Session Resumption (loading `recent_conversation_history` into client):**
    *   Archive a session.
    *   New client session for same `session_id` (if applicable) or user starts new session that loads prior history.
    *   Verify `useChatStore` is populated correctly from `recent_conversation_history` via an initial load API.

### 5.3. End-to-End (E2E) Tests
*   **Scenario 1: Basic Conversation & LTM Update**
    1.  User starts chat.
    2.  User provides a preference (e.g., "Call me Captain").
    3.  Agent uses `ManageLongTermMemoryTool` to save this preference.
    4.  User ends chat (triggering batch archival of this short convo).
    5.  User starts a *new* chat session later.
    6.  Agent greets user as "Captain" (demonstrating LTM load and use).
*   **Scenario 2: Multi-Turn Short-Term Context**
    1.  User: "What's the capital of France?"
    2.  AI: "Paris."
    3.  User: "What about for Germany?"
    4.  AI: "Berlin." (Demonstrates understanding "for Germany" refers to capital).
    5.  (Verify short-term context was passed correctly turn-to-turn).
*   **Scenario 3: Resilience to Client Closing Unexpectedly (Conceptual)**
    *   If `navigator.sendBeacon` is used, test that messages are archived even if tab is closed abruptly.

### 5.4. Manual Testing Checklist
*   Verify all UI interactions related to chat (sending, receiving, opening/closing panel).
*   Inspect Supabase tables (`recent_conversation_history`, `agent_long_term_memory`) to confirm data integrity after various operations.
*   Test different LTM tool operations manually via agent interaction (if CLI or debug interface allows).
*   Test error conditions (e.g., API down, DB errors) and observe client/server behavior.

## 6. Dependencies & Impact on Other Systems

*   **`agent_execution_prompt_customization_design_v1.md`:** Relies on `CustomizableAgent` which will need modification.
The `PromptManagerService` may be a good candidate to also handle LTM interactions with Supabase if its scope is broadened, or a new dedicated service for LTM can be created.
*   **UI Components:** `ChatPanel.tsx` and related UI will interact with `useChatStore.ts` and trigger archival.
*   **Authentication:** Assumes `user_id` is reliably obtained via JWT for all relevant operations.

## 7. Challenges & Mitigations

*   **Client-Side State Reliability for Archival:** User might close browser before `beforeunload` fires reliably, or network issues during `sendBeacon`.
    *   **Mitigation:** Periodic auto-archival from client for long sessions. Server-side short-term cache provides *some* resilience for in-progress turns. Accept that very last few unarchived messages might be lost in abrupt closes if `sendBeacon` fails.
*   **`server_session_cache` Size/Management:** If not managed, could grow large for very active long sessions.
    *   **Mitigation:** Implement a strict sliding window (e.g., only last N messages or last M kilobytes of serialized messages).
*   **LTM `notes` Field Growing Too Large:** A single TEXT field for LTM could become very large and hard for the agent to parse/use effectively.
    *   **Mitigation:** Encourage agents (via prompt engineering for the `ManageLongTermMemoryTool` or by tool design) to be concise, summarize, and structure their notes (e.g., using Markdown). Future: explore chunking or more structured LTM if this becomes an issue.
*   **Complexity of Orchestration:** Coordinating client state, client API calls, server cache, and DB interactions.
    *   **Mitigation:** Phased implementation, thorough testing at each phase, clear API contracts.
*   **Session ID Management:** Ensuring consistent `session_id` generation and usage between client and server.
    *   **Mitigation:** Client generates UUID on first message of a new chat interaction, stores it (e.g., `sessionStorage` or Zustand), and sends with every API call. Server uses this provided `session_id`.

## 8. Creative Phase Components Flagged

No further creative phases are immediately identified for *this specific memory system refactor*. However, the *evolution* of the LTM (how agents structure their `notes`, if more advanced parsing/querying is needed later) might lead to future creative/design tasks.

## 9. Next Mode Recommendation

**IMPLEMENT MODE** (starting with Phase 1 of this plan). 