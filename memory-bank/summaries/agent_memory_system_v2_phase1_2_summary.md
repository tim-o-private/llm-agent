# Agent Memory System v2 - Phase 1 & 2 Implementation Summary

**Date:** 2024-08-04

## 1. Overview

This document summarizes the implementation details of Phases 1 and 2 of the Agent Memory System v2. The goal of this system is to provide agents with both long-term memory (LTM) and an efficient way to handle short-term conversation context, minimizing database writes per turn.

**Key Architectural Decisions:**
*   **Long-Term Memory (LTM):** Stored in a dedicated Supabase table (`agent_long_term_memory`), managed by agents via a specific tool (`ManageLongTermMemoryTool`). LTM is unstructured natural language.
*   **Short-Term Memory (STM) / Recent Conversation History:**
    *   A server-side cache (`server_session_cache` in `chatServer/main.py`) holds messages for the *current* interaction (Phase 1 setup).
    *   Client-side buffering (`useChatStore.ts`) holds messages for the active UI session.
    *   Batched archival of client-side messages directly to a Supabase table (`recent_conversation_history`) for persistence, triggered by timers or browser events (Phase 2).
*   **Database Interaction:** Direct client-to-Supabase writes for `recent_conversation_history` (leveraging RLS) were chosen over an API endpoint for simplicity and to avoid an extra network hop for this specific data.

## 2. Phases Implemented

### Phase 1: Backend Foundation - LTM & Short-Term Cache Core

*   **Objective:** Establish the backend infrastructure for Long-Term Memory and a basic server-side cache for short-term messages.
*   **Status:** COMPLETE

### Phase 2: Client-Side Buffering & Direct DB Archival

*   **Objective:** Implement client-side handling of chat messages, including buffering, and a mechanism for batch-archiving them directly to Supabase.
*   **Status:** COMPLETE (Testing of archival triggers is the immediate next step)

## 3. Files and Components Created/Modified

Below is a breakdown of significant files and functions created or modified, along with their purpose.

---

### 3.1. Supabase Migrations

#### a. `supabase/migrations/{timestamp}_agent_memory_v2_schemas.sql` (Phase 1)
*   **Purpose:** Defines the database schema for Long-Term Memory.
*   **Key DDL:**
    *   **Table: `agent_long_term_memory`**
        *   `user_id` (uuid, FK to `auth.users`)
        *   `agent_id` (text)
        *   `notes_content` (text)
        *   `created_at` (timestamptz, default now())
        *   `updated_at` (timestamptz, default now())
        *   Primary Key: `user_id, agent_id`
        *   RLS Policies: Enable users to CRUD their own LTM entries.
        *   Trigger: `handle_updated_at` to automatically update `updated_at` column.
    *   **Table: `agent_sessions`** (Kept from V1, `IF NOT EXISTS`)
        *   Used for managing agent session identifiers. (Note: Its full role in V2 is still evolving, primarily supporting LTM context for now).
        *   RLS Policies: Enable users to CRUD their own sessions.

#### b. `supabase/migrations/{timestamp}_recent_conversation_history_schema.sql` (Phase 2)
*   **Purpose:** Defines the database schema for storing batched recent conversation history from the client.
*   **Key DDL:**
    *   **Table: `recent_conversation_history`**
        *   `id` (uuid, primary key, default `gen_random_uuid()`)
        *   `session_id` (uuid, indexed)
        *   `user_id` (uuid, FK to `auth.users`, indexed)
        *   `agent_id` (text, indexed)
        *   `message_batch_jsonb` (jsonb) - Stores an array of `ChatMessage` objects.
        *   `batch_start_timestamp` (timestamptz)
        *   `batch_end_timestamp` (timestamptz)
        *   `archived_at` (timestamptz, default now()) - Server timestamp of archival.
        *   `created_at` (timestamptz, default now())
        *   RLS Policies: Enable users to insert their own conversation history. Select access (if any) would also be user-scoped.
        *   Indexes: On `user_id, agent_id, batch_end_timestamp DESC` for efficient querying if needed.

---

### 3.2. Backend (`src/` and `chatServer/`)

#### a. `src/core/tools/memory_tools.py` (Phase 1)
*   **File Purpose:** Defines tools related to agent memory management.
*   **Class: `ManageLongTermMemoryTool(BaseTool)`**
    *   **Purpose:** Allows agents to read, overwrite, and append to their long-term memory stored in the `agent_long_term_memory` table.
    *   **Constructor (`__init__(self, user_id: str, supabase_client: SupabaseClient)`):**
        *   Takes `user_id` and a Supabase client.
    *   **Method: `_run(self, action: str, agent_id: str, content: Optional[str] = None) -> str`:**
        *   Handles `read`: Fetches LTM for `self.user_id` and `agent_id`.
        *   Handles `overwrite`: Upserts `content` for `self.user_id` and `agent_id`.
        *   Handles `append`: Reads existing LTM, appends new `content`, then upserts. If no LTM, behaves like overwrite.
        *   Uses Supabase client for DB operations. `on_conflict="user_id, agent_id"` is used for upserts.

#### b. `src/core/agent_loader.py` (Phase 1 - Modifications)
*   **File Purpose:** Responsible for loading agent configurations and creating agent executors.
*   **Function: `load_agent_executor(config_path: str, agent_id: str, user_id: str, session_id: str, chat_history: Optional[List[BaseMessage]] = None, explicit_custom_instructions: Optional[Dict[str, str]] = None, server_session_cache: Optional[Dict[str, List[Dict[str, Any]]]] = None) -> CustomizableAgentExecutor`** (Signature might vary slightly based on full context)
    *   **Modifications for LTM:**
        1.  Initializes a Supabase client (sync).
        2.  Fetches LTM notes from `agent_long_term_memory` for the given `user_id` and `agent_id`.
        3.  Instantiates `ManageLongTermMemoryTool` with the `user_id` and Supabase client.
        4.  Adds the LTM tool to the list of tools available to the agent.
        5.  Passes the fetched `ltm_notes_content` to `CustomizableAgentExecutor.from_agent_config`.

#### c. `src/core/agents/customizable_agent.py` (Phase 1 - Modifications)
*   **File Purpose:** Defines the `CustomizableAgent` and `CustomizableAgentExecutor`.
*   **Class: `CustomizableAgent`**
    *   **`__init__`:** Modified to accept `ltm_notes_content: Optional[str]` and `explicit_custom_instructions_dict: Optional[Dict[str, str]]`.
    *   **`_construct_final_prompt_template(self, base_prompt_template_str: str, ...) -> ChatPromptTemplate`:** (Or similar method responsible for system message construction)
        *   Modified to prepend LTM notes (if available) and explicit custom instructions to the agent's system prompt.
        *   Order of prepending: LTM notes, then explicit custom instructions, then base system prompt.
*   **Class: `CustomizableAgentExecutor`**
    *   **`from_agent_config(...)`:**
        *   Modified to receive `ltm_notes_content` and `explicit_custom_instructions_dict`.
        *   Passes these to the `CustomizableAgent` constructor.
        *   The final system message incorporating LTM and explicit instructions is used to build the `ChatPromptTemplate`.
    *   **`ainvoke(...)`:**
        *   Ensures `chat_history` in the input is at least an empty list to prevent errors if `None` is passed.

#### d. `chatServer/main.py` (Phase 1 & 2 - Modifications)
*   **File Purpose:** Main FastAPI application for the chat server.
*   **Global Variable (Phase 1): `server_session_cache: Dict[str, List[Dict[str, Any]]] = {}`**
    *   **Purpose:** Simple in-memory dictionary to store short-term message history per session, keyed by a server-generated `session_id`.
    *   (Note: Full retrieval logic for this cache in Phase 3 is TBD).
*   **Global Variable (Phase 1): `MAX_CACHE_HISTORY_LENGTH = 50`** (or similar)
    *   Purpose: Limits the number of messages stored per session in `server_session_cache`.
*   **Helper Functions (Phase 1): `serialize_message_for_cache`, `deserialize_message_from_cache`**
    *   Purpose: Convert LangChain `BaseMessage` objects to/from JSON-serializable dicts for the cache.
*   **API Endpoint: `/api/chat` (POST)** (Phase 1 & 2 modifications)
    *   **Original Purpose:** Handles incoming chat messages from the client.
    *   **Modifications:**
        1.  **Session ID Generation (Server-side):** If no `session_id` is provided by client (V2 approach), the server generates/retrieves one (e.g., could be based on `user_id` + `agent_id` or a new UUID per conversation thread, exact logic for V2 still depends on how client manages this concept). For now, it gets `session_id` to interact with `server_session_cache`.
        2.  **Cache Interaction:**
            *   Retrieves recent history for the `session_id` from `server_session_cache`.
            *   Invokes the agent executor (`load_agent_executor`), passing the (potentially cached) history.
            *   Adds the new human message, AI response, and any tool messages to `server_session_cache` for the `session_id`, respecting `MAX_CACHE_HISTORY_LENGTH`.
        3.  **Input Model (`ChatInput`):** Modified to include `agent_id`. `user_id` and `session_id` likely removed from client payload as server derives/manages them.
*   **API Endpoint: `/api/chat/session/archive_messages` (POST)** (Phase 2 - Created, but now DEPRECATED for client direct-to-DB archival)
    *   **Original Purpose:** Intended for the client to send batches of messages for archival.
    *   **Payload Model (`ArchiveMessagesPayload`):** Defined `session_id`, `user_id`, `agent_id`, `messages_to_archive`.
    *   **Functionality:** Would have inserted messages into `recent_conversation_history`.
    *   **Current Status:** Superseded by direct client-to-Supabase writes. Should be marked for removal.
*   **Removed:** `ACTIVE_AGENTS` global cache (implying `load_agent_executor` is called per request for freshness).

---

### 3.3. Web Application (`webApp/src/`)

#### a. `webApp/src/stores/useChatStore.ts` (Phase 2 - Significant Modifications)
*   **File Purpose:** Zustand store for managing chat UI state, messages, and archival logic.
*   **Key State:**
    *   `messages: ChatMessage[]`: Array of chat messages for the current UI session.
    *   `isChatPanelOpen: boolean`
    *   `sessionId: string | null`: Client-generated UUID for the current chat session.
    *   `currentAgentId: string | null`: The ID of the agent currently being interacted with.
    *   `lastArchivedMessageCount: number`: Tracks the number of messages already sent for archival to prevent duplicates.
    *   `isArchiving: boolean`: Flag to prevent concurrent archival attempts.
*   **Key Actions:**
    *   **`addMessage(message: Omit<ChatMessage, 'id' | 'timestamp'>, ...)`:** Adds a new message to the `messages` array with a generated ID and current timestamp.
    *   **`initializeSession(agentId: string, existingSessionId?: string | null, existingMessages?: ChatMessage[])`:**
        *   Sets `currentAgentId`.
        *   Generates a new `sessionId` (UUID v4) if `existingSessionId` is not provided.
        *   Sets initial messages.
        *   Calls internal methods `_setupArchivalListeners()` and `_startPeriodicArchive()`.
    *   **`clearCurrentSession()`:** Attempts a final archive, clears listeners/timers, and resets chat state.
    *   **`archiveChatSession(isUnloading: boolean = false)`:**
        *   Core logic for triggering message archival.
        *   Checks if archival is already in progress or if session/agent IDs are missing.
        *   Slices messages from `lastArchivedMessageCount` to get new messages.
        *   If new messages meet `MIN_MESSAGES_FOR_ARCHIVE`, it calls `doArchiveChatDirect`.
        *   Updates `lastArchivedMessageCount` on successful archival.
        *   Manages `isArchiving` flag.
    *   **`_setupArchivalListeners()`:** Sets up `beforeunload` and `visibilitychange` event listeners that call `archiveChatSession`.
    *   **`_clearArchivalListeners()`:** Removes event listeners.
    *   **`_startPeriodicArchive()`:** Starts an interval timer (`ARCHIVE_INTERVAL`) that calls `archiveChatSession`.
    *   **`_stopPeriodicArchive()`:** Clears the interval timer.
*   **Hook: `useInitializeChatStore(agentId: string)`:**
    *   A React hook that calls `useChatStore.getState().initializeSession(agentId)` on mount and `clearCurrentSession` on unmount. This ensures the store is correctly initialized for the active agent and cleaned up.

#### b. `webApp/src/api/hooks/useChatApiHooks.ts` (Phase 2 - Created/Refactored)
*   **File Purpose:** Contains React Query hooks and related functions for chat API interactions, specifically for direct Supabase archival.
*   **Function: `doArchiveChatDirect(variables: ArchiveChatVariables): Promise<ArchiveChatResult>` (Exported)**
    *   **Purpose:** Directly inserts a batch of chat messages into the `recent_conversation_history` Supabase table.
    *   **Input (`ArchiveChatVariables`):** `sessionId`, `agentId`, `messages`.
    *   **Logic:**
        1.  Gets the current authenticated `user_id` from `supabase.auth.getUser()`.
        2.  Constructs a single record for `recent_conversation_history` containing the `sessionId`, `user_id`, `agent_id`, the array of `messages` (as JSONB), and batch start/end timestamps.
        3.  Uses `supabase.from('recent_conversation_history').insert(...)`.
    *   **Output (`ArchiveChatResult`):** `{ success: boolean, error?: string, archived_count?: number, db_record_ids?: string[] }`.
*   **Hook: `useArchiveChatMutation()`**
    *   **Purpose:** Provides a React Query mutation hook that wraps `doArchiveChatDirect`.
    *   Used by UI components if they need to manually trigger archival with mutation state tracking (though current primary archival triggers are internal to `useChatStore`).

#### c. `webApp/src/components/ChatPanel.tsx` (Phase 2 - Modifications)
*   **File Purpose:** UI component for displaying chat messages and handling user input.
*   **Props:**
    *   Added optional `agentId?: string`.
*   **Modifications:**
    *   Uses the passed `agentId` (or a default from `VITE_DEFAULT_CHAT_AGENT_ID`) to call `useInitializeChatStore(agentId)`. This correctly sets up the chat store for the active agent.
    *   `fetchAiResponse` function:
        *   Sends `agent_id` in the request body to `/api/chat`.
        *   `userId` and `sessionId` are no longer sent in the request body to `/api/chat` as the backend is expected to derive/manage these.

#### d. `webApp/src/pages/TodayView.tsx` (Phase 2 - Modifications)
*   **File Purpose:** Main view component for the "Today" section.
*   **Modifications:**
    *   When rendering `<ChatPanel />`, it now passes the `agentId` prop, using `import.meta.env.VITE_DEFAULT_CHAT_AGENT_ID || "assistant"` as the value.
    *   Corrected a linter error by adding `planned_duration_minutes` to a `createFocusSession` call.

#### e. `webApp/src/lib/supabaseClient.ts` (Reviewed, No V2 Changes)
*   **File Purpose:** Exports the initialized Supabase client instance. Used by `useChatApiHooks.ts` and potentially other parts of the web app.

---

### 3.4. Utility Files & Types

#### a. `webApp/src/api/types.ts` (Phase 2 - Minor Updates)
*   **File Purpose:** TypeScript type definitions for API and data structures.
*   **`ChatMessage.sender`:** Type updated from `'user' | 'ai'` to `'user' | 'ai' | 'tool'` to accommodate tool messages.
*   (Other types like `Task`, `FocusSession` were already present or updated in previous unrelated tasks).

#### b. `node_modules/` (Phase 2 - Additions)
*   Installed `uuid` and `@types/uuid` for generating client-side session IDs.

---

## 4. Key Data Flows (Textual Diagrams)

### 4.1. Long-Term Memory (LTM) - Agent Interaction Flow

```
Agent Command (e.g., "Remember this: ...", "What do you know about X?")
    |
    v
CustomizableAgentExecutor
    |
    v
ManageLongTermMemoryTool._run(action, agent_id, content)
    |   |
    |   +-- (If action is 'read' or 'append' with existing notes) --> SupabaseClient.select('agent_long_term_memory')
    |                                                                     | Filter: user_id, agent_id
    |                                                                     v
    |                                                                 LTM Notes (if any)
    |   |
    |   +-------------------------------------------------------------> SupabaseClient.upsert('agent_long_term_memory')
    |                                                                     | Data: {user_id, agent_id, notes_content}
    |                                                                     | On Conflict: user_id, agent_id
    v
Tool Result (success/failure message, or LTM content for 'read')
    |
    v
CustomizableAgentExecutor (processes result, generates response)
    |
    v
Agent Response to User
```

### 4.2. LTM - Agent Prompt Injection Flow (On Agent Load)

```
load_agent_executor(user_id, agent_id, ...)
    |
    v
SupabaseClient.select('agent_long_term_memory')
    | Filter: user_id, agent_id
    v
LTM Notes Content (if any)
    |
    v
CustomizableAgentExecutor.from_agent_config(..., ltm_notes_content)
    |
    v
CustomizableAgent.__init__(..., ltm_notes_content)
    |
    v
CustomizableAgent._construct_final_prompt_template()
    |  System Prompt = LTM Notes + Explicit Instructions + Base System Prompt
    v
ChatPromptTemplate (used to initialize LLM Chain)
    |
    v
Agent is ready for interaction
```

### 4.3. Client-Side Chat & Archival Flow

```
UI Interaction (User sends message in ChatPanel.tsx)
    |
    v
ChatPanel.handleSendMessage(messageText)
    |
    v
useChatStore.addMessage({text, sender:'user'}) --> Updates UI
    |
    v
ChatPanel.fetchAiResponse(messageText, userId) --> POST /api/chat {agent_id, message}
    |                                                       |
    |                                                       v
    |                                                 chatServer/main.py @ /api/chat
    |                                                       | 1. Get/Generate server_session_id
    |                                                       | 2. Access server_session_cache[server_session_id] (STM)
    |                                                       | 3. Call load_agent_executor (with cached history)
    |                                                       | 4. Agent processes, AI responds
    |                                                       | 5. Update server_session_cache
    |                                                       v
    |                                                 AI Response from /api/chat
    v
useChatStore.addMessage({text: aiResponse, sender:'ai'}) --> Updates UI
    |
    |-----------------------------------------------------------------------------------------------|
    |                                                                                               |
    v (Periodic Timer in useChatStore OR Browser Event: visibilitychange / beforeunload)            |
useChatStore.archiveChatSession()                                                                   |
    | Condition: New messages exist (messages.length > lastArchivedMessageCount)                    |
    |                                                                                               |
    v                                                                                               |
doArchiveChatDirect({sessionId, agentId, messagesToArchive}) [from useChatApiHooks.ts]              |
    |                                                                                               |
    v                                                                                               |
supabase.from('recent_conversation_history').insert(batch_record_with_messages_array) <-------------|
    |  RLS Policy: Allows insert if auth.uid() matches user_id in record                            |
    |                                                                                               |
    v                                                                                               |
(If successful) useChatStore updates lastArchivedMessageCount                                       |
                                                                                                    |
----------------------------------------------------------------------------------------------------
```

### 4.4. Chat Store Initialization Flow

```
TodayView.tsx renders ChatPanel
    | Props: agentId="some_agent"
    v
ChatPanel.tsx ({ agentId })
    |
    v
useInitializeChatStore(agentId) [React Hook in ChatPanel]
    |
    v (useEffect on mount)
useChatStore.getState().initializeSession(agentId, null, [])
    |
    v
useChatStore (State Update):
    | - currentAgentId = agentId
    | - sessionId = new uuidv4()
    | - messages = []
    | - lastArchivedMessageCount = 0
    | - Calls _setupArchivalListeners()
    | - Calls _startPeriodicArchive()
    v
Chat store is ready for the specified agent.
```

## 5. Next Steps (Post-Summary)

*   Execute the test plan defined in `memory-bank/testing/agent_memory_system_v2_test_plan.md`, focusing on manual E2E tests for client-side archival triggers (Section 5.2.4).
*   Proceed to Phase 3: Integrating Short-Term Context Flow.

--- 