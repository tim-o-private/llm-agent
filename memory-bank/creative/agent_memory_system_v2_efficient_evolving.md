# 🎨 CREATIVE PHASE: Architecture Design - Agent Memory System v2 (Efficient & Evolving)

**Date:** 2025-05-21
**Associated Task in `tasks.md`:** Refactor: Implement Robust Short-Term Memory (STM) with Persistent `session_id`
**Supersedes in part:** `agent_memory_solution_design_v1.md` (specifically regarding persistence strategy and short-term memory approach).

## 1. Component Description (Revised for Robust STM)

This document outlines a revised architecture for the AI agent's memory system. The primary goals are to:
1.  **Implement a robust, persistent Short-Term Memory (STM)** using `langchain-postgres`, ensuring conversation continuity.
2.  Manage `session_id` lifecycle effectively through a combination of client-side logic, a dedicated Supabase table (`user_agent_active_sessions`), and `localStorage`.
3.  Implement a flexible, natural language-based long-term memory (LTM) store that agents can curate over time (remains a goal, LTM mechanism unchanged by this STM refactor).
4.  Ensure agents maintain robust short-term conversational context via the `langchain-postgres` integration.

This design prioritizes stability and persistence for STM, leveraging standard LangChain components for chat message history.

## 2. Core Requirements & Constraints (Re-emphasized for STM)

*   **N1: Persistent STM:** Conversational history must persist across browser sessions, page reloads, and ideally across devices for the same user/agent.
*   **N2: Reliable `session_id` Management:** A consistent `session_id` must be available and used for each user-agent conversational thread.
*   **N3: Standard Tooling:** Utilize `langchain-postgres` for managing chat message history directly in the database.
*   **N4: Client-Side Session Initiation:** The client is responsible for initiating or retrieving the correct `session_id`.
*   **N5: Supabase Integration:** Leverage Supabase for storing `session_id` metadata and the chat message history itself.
*   **N6: LangChain Compatibility:** The STM solution must integrate seamlessly with LangChain agents (e.g., `ConversationBufferWindowMemory`).

## 3. Recommended Architecture: Client-Managed `session_id` with `langchain-postgres` STM

This architecture centralizes STM in Supabase via `langchain-postgres`, with the client orchestrating `session_id` management.

### 3.1. Client-Side `session_id` Management (`webApp`)

*   **Role:** The client (`webApp`) is responsible for ensuring a valid `session_id` is available for any given user-agent interaction and passing it to the backend with each chat request.
*   **Mechanism (`useChatStore.ts`, `useChatSessionHooks.ts`):**
    1.  **Initialization (`initializeSessionAsync` in `useChatStore`):**
        a.  Determine `userId` (from auth) and `agentName`.
        b.  Construct `localStorageKey = \`chatSession_${userId}_${agentName}\``.
        c.  **Attempt 1: `localStorage` Lookup:** Try to retrieve `persistedSessionId` from `localStorage`.
            *   If found, validate this `persistedSessionId` against the `user_agent_active_sessions` table in Supabase (fetch by `userId`, `agentName`). If the `persistedSessionId` matches the `active_session_id` in the DB, it's considered valid.
            *   If `localStorage` ID is invalid or not found in DB, clear it from `localStorage`.
        d.  **Attempt 2: DB Lookup (`useFetchActiveChatSession`):** If no valid `session_id` from `localStorage`, query `user_agent_active_sessions` for the most recent `active_session_id` for the current `userId` and `agentName`.
            *   If found, use this `session_id` and store it in `localStorage`.
        e.  **Attempt 3: Generate New `session_id`:** If no `session_id` is found via `localStorage` or DB lookup:
            *   Generate a new `session_id` (e.g., UUID v4 using `generateNewSessionId()`).
            *   Store this new `session_id` in `localStorage`.
            *   Upsert this new `session_id` into the `user_agent_active_sessions` table as the `active_session_id` for the `userId` and `agentName` (using `useUpsertActiveChatSession`).
    2.  **Storage:** The determined `session_id` is stored in the Zustand `useChatStore` and in `localStorage`.
    3.  **API Calls:** The `session_id` from `useChatStore` is included in every `/api/chat` request to `chatServer`.
*   **Supabase Table: `user_agent_active_sessions`**
    *   `user_id`: UUID (FK to `auth.users.id`, Part of PK)
    *   `agent_name`: TEXT (Part of PK)
    *   `active_session_id`: TEXT (Stores the current valid `session_id` for this user/agent pair)
    *   `last_active_at`: TIMESTAMPTZ (Defaults to `now()`, updates on upsert)
    *   `created_at`: TIMESTAMPTZ (Defaults to `now()`)

### 3.2. Backend Short-Term Memory (`chatServer/main.py` with `langchain-postgres`)

*   **Role:** To provide persistent short-term memory for the AI agent using `langchain-postgres`, automatically saving and loading conversation history to/from the Supabase database on a per-turn basis.
*   **Mechanism:**
    1.  **`session_id` Reception:** The `chat_endpoint` in `chatServer/main.py` receives the `session_id` from the client in the `ChatRequest`.
    2.  **`PostgresChatMessageHistory` Initialization:**
        *   An instance of `PostgresChatMessageHistory` is created, configured with:
            *   The global `PGEngine` (initialized at startup with DB connection details).
            *   The `session_id` received from the client.
            *   The designated table name (e.g., `chat_message_history`).
    3.  **`ConversationBufferWindowMemory` Wrapper:**
        *   The `PostgresChatMessageHistory` instance is wrapped by `ConversationBufferWindowMemory`.
        *   Configuration:
            *   `k`: Defines the window size (number of past messages to keep in context).
            *   `return_messages=True`: Ensures `BaseMessage` objects are returned.
            *   `memory_key="chat_history"`: Matches the prompt template variable.
            *   `input_key="input"`: Matches the user input key for the agent.
    4.  **Agent Integration:** The `ConversationBufferWindowMemory` instance is assigned to the `memory` attribute of the loaded `CustomizableAgentExecutor`.
    5.  **Automatic Persistence:** `PostgresChatMessageHistory`, when used with `ConversationBufferWindowMemory`, automatically loads messages for the given `session_id` at the start of an interaction and saves new messages (user input, AI response, tool messages) to the `chat_message_history` table in Supabase at the end of the interaction.
*   **Supabase Table: `chat_message_history`**
    *   `id`: SERIAL PRIMARY KEY (or other auto-incrementing type)
    *   `session_id`: TEXT NOT NULL (Index this column)
    *   `message`: JSONB NOT NULL (Stores LangChain `BaseMessage` objects serialized to JSON)
    *   `created_at`: TIMESTAMPTZ DEFAULT `now()` (Optional, but good for auditing)
    *   (RLS policies should be in place, though `langchain-postgres` interacts using the service role or a specified DB user, so application-level session validation is key).

### 3.3. Server-Side Short-Term Cache (`chatServer`) - REMOVED

*   **Status: REMOVED.** The `server_session_cache` (in-memory Python dictionary) is no longer needed. `PostgresChatMessageHistory` directly handles fetching from and saving to the database, providing the necessary persistence and context. The database itself, with appropriate indexing on `session_id` in `chat_message_history`, serves as the "cache" and persistent store.

### 3.4. Evolving Natural Language Long-Term Memory (LTM - Supabase)

*   **Status: Unchanged by this STM refactor.** This component remains as previously designed.
*   **Role:** To store persistent, curated knowledge, preferences, summaries, and standing instructions related to a specific user, as understood and maintained by the agent.
*   **Supabase Table: `agent_long_term_memory`** (Schema and interaction via `ManageLongTermMemoryTool` remain the same).
    *   `id: UUID PK`
    *   `user_id: UUID`
    *   `agent_name: TEXT`
    *   `notes: TEXT`
    *   `created_at: TIMESTAMPTZ`
    *   `updated_at: TIMESTAMPTZ`

*   **Agent Interaction (CRUD via Tools):**
    *   **Read:**
        *   On agent initialization for a user (`agent_loader.py` via 
        `chatServer`), the `notes` for the `user_id` and `agent_name` are fetched 
        from `agent_long_term_memory`.
        *   **Presentation to Agent:** Injected into a dedicated section of the 
        agent's prompt template (e.g., a placeholder like `"{long_term_memory_notes}
        "`). The `CustomizableAgent` (from prompt customization design) would 
        manage this injection.
    *   **Write/Update/Delete (via `UpdateLongTermMemoryTool`):**
        *   **Tool Name:** `manage_long_term_memory`
        *   **Tool Input Schema:**
            ```python
            class ManageLTMInput(BaseModel):
                operation: Literal['read', 'overwrite', 'append', 'prepend', 
                'delete_section_by_header', 'replace_section_by_header', 
                'delete_all_notes'] = 'read'
                content: Optional[str] = None # For write operations
                section_header: Optional[str] = None # For section-specific 
                operations
            ```
        *   **Tool Action:**
            *   The tool (running in `chatServer`) interacts with the 
            `agent_long_term_memory` table in Supabase.
            *   `read`: Returns the current `notes`.
            *   `overwrite`: Replaces the entire `notes` field with new `content`.
            *   `append`: Appends `content` to the existing `notes`.
            *   `prepend`: Prepends `content` to the existing `notes`.
            *   `delete_all_notes`: Clears the `notes` field.
            *   Section-based operations would require a simple parsing convention 
            for the `notes` text (e.g., Markdown headers).

### 3.5. Ensuring Short-Term Memory for Agent (Per-Turn Context Flow - REVISED)

This explicitly details how an agent gets its immediate context for responding with the new STM system:
1.  **Client (`useChatStore`, `useChatSessionHooks`):**
    a.  User types a message. It's added to `useChatStore` for UI display.
    b.  Client ensures it has a valid `session_id` through the initialization logic (localStorage -> DB (`user_agent_active_sessions`) -> generate new).
2.  **Client API Call (`POST /api/chat`)**:
    a.  The web app sends the new user message and the active `session_id` to `chatServer`.
    b.  Payload: `{ "message": "User's new input", "session_id": "active-session-uuid", "agent_id": "test_agent" }`.
3.  **`chatServer` Context Assembly & Agent Invocation**:
    a.  `chat_endpoint` receives the request.
    b.  `PostgresChatMessageHistory` is initialized with the `PGEngine` and the provided `session_id`.
    c.  This history object is wrapped in `ConversationBufferWindowMemory`.
    d.  The `ConversationBufferWindowMemory` instance is set as the `.memory` for the `CustomizableAgentExecutor`.
    e.  When `agent_executor.ainvoke({"input": chat_input.message})` is called:
        i.  `ConversationBufferWindowMemory` loads the last `k` messages for that `session_id` from the `chat_message_history` table.
        ii. These messages, along with the current user input, are formatted into the agent's prompt.
4.  **Agent Response & History Save**:
    a.  The agent processes the input and generates a response.
    b.  `ConversationBufferWindowMemory` automatically takes the user's input message and the AI's output message (and any tool messages) and instructs `PostgresChatMessageHistory` to save them to the `chat_message_history` table, associated with the `session_id`.
5.  **Client Receives Response**: The AI's response is sent back to the client and displayed in the UI.

### 3.6. Supabase Realtime (Potential Uses)

*   **Status: Unchanged by this STM refactor.** Remains an option for future enhancements (e.g., multi-device LTM sync). Not critical for the current STM functionality.

## 4. Data Models & Schemas (Key Tables Recap - REVISED)

*   **`user_agent_active_sessions` (Supabase - NEW)**
    *   `user_id: UUID PK` (Links to `auth.users.id`)
    *   `agent_name: TEXT PK`
    *   `active_session_id: TEXT NOT NULL`
    *   `last_active_at: TIMESTAMPTZ DEFAULT now()`
    *   `created_at: TIMESTAMPTZ DEFAULT now()`
*   **`chat_message_history` (Supabase - NEW, for `langchain-postgres`)**
    *   `id: SERIAL PK`
    *   `session_id: TEXT NOT NULL` (Should be indexed)
    *   `message: JSONB NOT NULL` (Stores serialized LangChain `BaseMessage` objects)
    *   `created_at: TIMESTAMPTZ DEFAULT now()`
*   **`recent_conversation_history` (Supabase - DEPRECATED/REMOVED)**
    *   This table and the client-side batch archival mechanism are superseded by the direct, per-turn persistence provided by `PostgresChatMessageHistory` into `chat_message_history`.
*   **`agent_long_term_memory` (Supabase - Unchanged)**
    *   (Schema remains as previously defined)
*   **`agent_sessions` (Supabase - DEPRECATED/REMOVED or REPURPOSED)**
    *   The role of this table for managing session metadata is largely replaced by `user_agent_active_sessions`. If it existed, its direct use for STM is removed.

## 5. API Endpoints (Key New/Modified - REVISED)

*   **`POST /api/chat` (Existing, Modified Interaction)**
    *   Client sends `{ "message": "User's new input", "session_id": "active-session-uuid", "agent_id": "test_agent" }`. (Note: `agent_id` here is the agent's name/identifier).
    *   `chatServer` uses the provided `session_id` to initialize `PostgresChatMessageHistory` and `ConversationBufferWindowMemory`, which then handles STM.
*   **`POST /api/chat/session/archive_messages` (DEPRECATED/REMOVED)**
    *   This endpoint is no longer needed as `PostgresChatMessageHistory` handles per-turn persistence.

## 6. Implementation Guidelines & Considerations (REVISED)

*   **`webApp` (`useChatStore.ts`, `useChatSessionHooks.ts`, `ChatPanel.tsx`):**
    *   Ensure robust implementation of the `session_id` lifecycle: `localStorage` check, DB lookup in `user_agent_active_sessions`, new ID generation, and persistence of the chosen/new ID back to `localStorage` and `user_agent_active_sessions`.
    *   The `session_id` must be correctly passed in all `/api/chat` calls.
*   **`chatServer/main.py`:**
    *   Properly initialize `PGEngine` at startup using environment variables for DB connection.
    *   In `/api/chat` endpoint:
        *   Receive `session_id` from the client.
        *   Instantiate `PostgresChatMessageHistory` with the engine, `session_id`, and table name.
        *   Wrap with `ConversationBufferWindowMemory`.
        *   Assign memory to the agent executor.
    *   Remove any old `server_session_cache` logic.
    *   Remove the `/api/chat/session/archive_messages` endpoint.
*   **Database (`ddl.sql`):**
    *   Ensure DDL for `user_agent_active_sessions` and `chat_message_history` is correct and applied.
    *   Include RLS policies as appropriate (though `PGEngine` typically uses a privileged DB role).
    *   Comment out or remove DDL for `recent_conversation_history` and potentially `agent_sessions` if fully deprecated.
*   **Error Handling:**
    *   Client: Handle potential errors during `session_id` fetching/creation.
    *   Server: Robust error handling for `PGEngine` initialization and any issues during agent interaction with memory.
*   **Testing (Phase 4):**
    *   Verify `session_id` persistence across browser refreshes and new sessions for the same user/agent.
    *   Confirm different agents for the same user get different `session_id`s (based on `agent_name` in `user_agent_active_sessions` primary key).
    *   Test conversation continuity using the `chat_message_history` table.
    *   Ensure data in `chat_message_history` is correctly associated with `session_id`.

## 7. Verification Checkpoint (REVISED)

*   **Persistent STM:** YES (via `langchain-postgres` and `chat_message_history` table).
*   **Reliable `session_id` Management:** YES (Client logic + `user_agent_active_sessions` table).
*   **Standard Tooling for STM:** YES (`langchain-postgres`, `ConversationBufferWindowMemory`).
*   **Client-Side Session Initiation:** YES.
*   **Minimize DB Writes Per Turn (for STM):** NO - This has changed. `langchain-postgres` writes per turn to ensure persistence. The previous goal of batching STM writes is superseded by the goal of robust, standard, per-turn persistence for STM. LTM updates remain discrete.
*   **Agent Has Short-Term Context:** YES (Loaded by `ConversationBufferWindowMemory` from `PostgresChatMessageHistory`).
*   **Cross-Session Preference Persistence:** YES (Via LTM - unchanged by STM refactor).

This revised design provides a more robust and standard approach to Short-Term Memory using `langchain-postgres`, simplifying server-side logic by removing custom caching and client-side batching for STM.

---
🎨🎨🎨 **EXITING CREATIVE PHASE: Architecture Design - Agent Memory System v2** 🎨🎨🎨 