# 🎨 CREATIVE PHASE: Architecture Design - Agent Memory System v2 (Efficient & Evolving)

**Date:** ''' + '''{datetime.now().isoformat()}''' + '''
**Associated Task in `tasks.md`:** BRAINPLN-001 / PLAN-STEP-2 (Revisiting Agent Memory Solution)
**Supersedes in part:** `agent_memory_solution_design_v1.md` (specifically regarding persistence strategy and long-term memory approach).

## 1. Component Description (Revised)

This document outlines a revised architecture for the AI agent's memory system. The primary goals are to:
1.  Drastically reduce database write operations per conversational turn compared to storing every message individually in real-time.
2.  Implement a flexible, natural language-based long-term memory (LTM) store that agents can curate over time.
3.  Ensure agents maintain robust short-term conversational context.
4.  Leverage client-side state for buffering active conversation messages, enhancing UI responsiveness and enabling batched data persistence.

This design prioritizes efficiency, cost-effectiveness (reducing DB load and potentially LLM processing on overly verbose histories), and an evolutionary approach to how agents store and utilize long-term knowledge about users.

## 2. Core Requirements & Constraints (Re-emphasized)

*   **N1: Minimize DB Writes Per Turn:** Avoid multiple direct database write requests to Postgres for a single conversational turn involving user input, agent response, and tool calls.
*   **N2: Evolving Natural Language LTM:** Start with an unstructured (natural language text) format for LTM, allowing agents to define what and how they remember, with the possibility of adding more structure later.
*   **N3: Client-Side Buffering:** Utilize client-side state (e.g., Zustand store) to manage the active conversation log, with client-initiated triggers for persisting this data.
*   **N4: Robust Short-Term Context:** Agents must have access to the immediate preceding conversation to maintain coherence and understand the current turn.
*   **N5: Cross-Session Preference Persistence:** The system must allow agents to remember user needs, preferences, and key information across sessions.
*   **N6: Efficient Pruning & Focus:** Memory (both short-term and long-term) should be manageable to maintain relevancy and control costs.
*   **N7: Supabase Integration:** Leverage Supabase for persistent storage.
*   **N8: LangChain Compatibility:** Integrate with LangChain patterns where beneficial, but adapt where necessary to meet core requirements (e.g., memory persistence).
*   **N9: Scalability (Future Consideration):** While not an immediate P0, the design should not fundamentally prevent future horizontal scaling of `chatServer`.

## 3. Recommended Architecture: Client-Buffered Interaction with Batched Persistence & Evolving LTM

This architecture distributes memory management across the client, the `chatServer`, and Supabase, optimizing for different needs at each layer.

### 3.1. Client-Side Message Buffering (`webApp/src/stores/useChatStore.ts`)

*   **Role:** `useChatStore` acts as the primary, real-time buffer for all messages (user and AI) within the active, visible chat session. This ensures immediate UI updates and a responsive user experience.
*   **Structure:** Adheres to `ChatMessage` interface (`id`, `text`, `sender`, `timestamp`).
    ```typescript
    // From useChatStore.ts
    interface ChatMessage {
      id: string;
      text: string;
      sender: 'user' | 'ai';
      timestamp: Date;
    }
    ```
*   **Principles (`zustand-store-design.md`):**
    *   **Scope:** Manages UI state for the chat panel and the list of active messages.
    *   **Actions:** `addMessage` for new messages, `toggleChatPanel`, etc.
    *   **Immutability:** Uses Zustand's default mechanisms (implicitly with `immer` if configured globally, or by spreading state).
*   **Data Flow:** New messages are added here first. This store represents the "source of truth" for the *currently displayed conversation*.

### 3.2. Client-Initiated Batch Archival of Recent Conversation History

*   **Role:** To persist the conversational record from `useChatStore` to long-term storage in Supabase in a batched manner, reducing write frequency.
*   **Triggers (Client-Side):**
    1.  User explicitly closes the chat panel/window.
    2.  User navigates away from the page (e.g., using `navigator.sendBeacon()` in a `beforeunload` event listener for reliability).
    3.  Periodically, if the chat session is long-running (e.g., every N messages accumulated in `useChatStore` or every M minutes – configurable).
*   **Mechanism:**
    1.  The web app (client) gathers the current list of `ChatMessage` objects from `useChatStore.ts`.
    2.  Client makes an API call to `chatServer` (e.g., `POST /api/chat/session/archive_messages`) with the batch of messages and the relevant `session_id`.
    3.  `chatServer` receives this batch and performs a single database operation (e.g., upsert or insert) to store it.
*   **Supabase Table: `recent_conversation_history`**
    *   `id`: Primary Key (UUID)
    *   `session_id`: TEXT or UUID (FK to `agent_sessions` if that table is used for session metadata)
    *   `user_id`: UUID (FK to `users`)
    *   `message_batch`: JSONB (stores an array of serialized `ChatMessage` objects)
    *   `archived_at`: TIMESTAMPTZ (Defaults to `now()`)
    *   `start_timestamp`: TIMESTAMPTZ (Timestamp of the first message in the batch)
    *   `end_timestamp`: TIMESTAMPTZ (Timestamp of the last message in the batch)
*   **Sync Logic Note:** This "client-initiated batch archival" is distinct from the continuous, entity-specific `syncWithServer` pattern described in `state-management-design.md` for stores like `useTaskStore`. It's a bulk save operation for a specific type of data (chat logs) triggered by different events. There isn't a "pending changes" queue for individual messages in `useChatStore` in the same way; the entire current state is archived.

### 3.3. Server-Side Short-Term Cache (`chatServer`)

*   **Role:** To provide the AI agent with the *immediate* conversational context (last few turns of the current exchange) efficiently, without needing to read from Supabase on every single user message. This cache helps bridge the gap between discrete client API calls.
*   **Structure:** A Python dictionary in `chatServer`, e.g., `server_session_cache: Dict[str, List[SerializedBaseMessage]]`. The `session_id` is the key.
    *   `SerializedBaseMessage` would be a dict representation of LangChain's `BaseMessage` objects.
    *   This cache holds a *sliding window* of the most recent messages (e.g., last 5-10 messages or last 2-3 turns).
*   **Population & Interaction:**
    1.  When `chatServer` receives a `/api/chat` request with new user message(s):
        a.  It retrieves the existing cached messages for that `session_id` from `server_session_cache`.
        b.  It appends the new incoming user message(s) to this cached list.
        c.  This combined list forms the short-term history provided to the agent for the current turn.
    2.  After the agent generates a response (and any tool messages):
        a.  The new user message(s), AI response, and any relevant tool messages are used to update the `server_session_cache` for that `session_id`, maintaining the sliding window.
*   **Note on Scaling:** For initial implementation (no horizontal scaling of `chatServer`), this simple dictionary is sufficient. For future scaling, this cache would need to move to a distributed solution (e.g., Redis).

### 3.4. Evolving Natural Language Long-Term Memory (LTM - Supabase)

*   **Role:** To store persistent, curated knowledge, preferences, summaries, and standing instructions related to a specific user, as understood and maintained by the agent.
*   **Supabase Table: `agent_long_term_memory`**
    *   `id`: Primary Key (UUID)
    *   `user_id`: UUID (FK to `users`, part of a composite key with `agent_name`)
    *   `agent_name`: TEXT (e.g., "assistant", "test_agent", part of a composite key with `user_id`)
    *   `notes`: TEXT (Stores the natural language memory content. Can be Markdown for light structure if desired by the agent.)
    *   `created_at`: TIMESTAMPTZ
    *   `updated_at`: TIMESTAMPTZ
    *   (RLS policies must ensure users/agents can only access their respective notes).
*   **Agent Interaction (CRUD via Tools):**
    *   **Read:**
        *   On agent initialization for a user (`agent_loader.py` via `chatServer`), the `notes` for the `user_id` and `agent_name` are fetched from `agent_long_term_memory`.
        *   **Presentation to Agent:** Injected into a dedicated section of the agent's prompt template (e.g., a placeholder like `"{long_term_memory_notes}"`). The `CustomizableAgent` (from prompt customization design) would manage this injection.
    *   **Write/Update/Delete (via `UpdateLongTermMemoryTool`):**
        *   **Tool Name:** `manage_long_term_memory`
        *   **Tool Input Schema:**
            ```python
            class ManageLTMInput(BaseModel):
                operation: Literal['read', 'overwrite', 'append', 'prepend', 'delete_section_by_header', 'replace_section_by_header', 'delete_all_notes'] = 'read'
                content: Optional[str] = None # For write operations
                section_header: Optional[str] = None # For section-specific operations
            ```
        *   **Tool Action:**
            *   The tool (running in `chatServer`) interacts with the `agent_long_term_memory` table in Supabase.
            *   `read`: Returns the current `notes`.
            *   `overwrite`: Replaces the entire `notes` field with new `content`.
            *   `append`: Appends `content` to the existing `notes`.
            *   `prepend`: Prepends `content` to the existing `notes`.
            *   `delete_all_notes`: Clears the `notes` field.
            *   Section-based operations would require a simple parsing convention for the `notes` text (e.g., Markdown headers).

### 3.5. Ensuring Short-Term Memory for Agent (Per-Turn Context Flow)

This explicitly details how an agent gets its immediate context for responding:
1.  **Client (`useChatStore`)**: User types a message. It's added to `useChatStore`.
2.  **Client API Call (`POST /api/chat`)**: The web app sends the *new user message(s)* to `chatServer`. (Payload: `{ "new_messages": [SerializedChatMessage], "session_id": "xyz" }`).
3.  **`chatServer` Context Assembly**:
    a.  Retrieves `List[SerializedBaseMessage]` from `server_session_cache[session_id]` (this is the context from the end of the previous turn).
    b.  Appends the `new_messages` from the client payload to this list. This combined list is the full short-term history for the current turn.
4.  **Agent Invocation**: The `CustomizableAgent` is invoked with this assembled short-term history, plus its LTM notes and other prompt customizations.
5.  **`chatServer` Cache Update**: After the agent responds (e.g., with an AI message and maybe tool calls/responses), `chatServer` updates `server_session_cache[session_id]` with the new state of the short-term history (user message, AI response, tool messages if applicable), ready for the next turn.

### 3.6. Supabase Realtime (Potential Uses)

*   If LTM (`agent_long_term_memory.notes`) is updated, Realtime *could* potentially signal other active sessions for the same user/agent (e.g., on a different device) to refresh their LTM. This is an advanced feature.
*   Could signal the client if a background process updates `recent_conversation_history` for the current session (less common).
*   Not strictly necessary for the core loop of this memory design but offers avenues for richer real-time experiences later.

## 4. Data Models & Schemas (Key Tables Recap)

*   **`recent_conversation_history` (Supabase)**
    *   `id: UUID PK`
    *   `session_id: TEXT`
    *   `user_id: UUID`
    *   `message_batch: JSONB` (Array of serialized `ChatMessage`s: `[{id, text, sender, timestamp}, ...]`)
    *   `archived_at: TIMESTAMPTZ`
    *   `start_timestamp: TIMESTAMPTZ`
    *   `end_timestamp: TIMESTAMPTZ`
*   **`agent_long_term_memory` (Supabase)**
    *   `id: UUID PK`
    *   `user_id: UUID`
    *   `agent_name: TEXT`
    *   `notes: TEXT`
    *   `created_at: TIMESTAMPTZ`
    *   `updated_at: TIMESTAMPTZ`
    *   (Composite UNIQUE constraint on `user_id, agent_name`)
*   **`agent_sessions` (Supabase - Optional, for session metadata if needed beyond `session_id` string)**
    *   `session_id: TEXT PK` (Could be UUID string)
    *   `user_id: UUID`
    *   `agent_name: TEXT`
    *   `created_at: TIMESTAMPTZ`
    *   `last_activity_at: TIMESTAMPTZ`
    *   `summary: TEXT (Nullable)` (Could store an overall session summary if desired later)

## 5. API Endpoints (Key New/Modified)

*   **`POST /api/chat` (Existing, Modified Interaction)**
    *   Client sends `{ "new_messages": [SerializedChatMessage], "session_id": "xyz", "agent_id": "test_agent" }`.
    *   `chatServer` uses this, its `server_session_cache`, and LTM to generate a response.
*   **`POST /api/chat/session/archive_messages` (New)**
    *   Client sends `{ "session_id": "xyz", "messages_batch": [SerializedChatMessage] }`.
    *   `chatServer` saves this batch to `recent_conversation_history`.
*   **(Internal to `chatServer` or via agent tools that call `PromptManagerService` or a new LTM service): Endpoints/functions to manage `agent_long_term_memory`.**

## 6. Implementation Guidelines & Considerations

*   **`useChatStore.ts`:**
    *   Implement logic for collecting messages and identifying triggers for calling `/api/chat/session/archive_messages`.
    *   Consider using `navigator.sendBeacon` for `beforeunload` reliability.
*   **`chatServer`:**
    *   Implement the `server_session_cache` (simple Python dict initially). Define its window size.
    *   Implement the `/api/chat/session/archive_messages` endpoint logic.
    *   Implement the `manage_long_term_memory` agent tool, including its Supabase interactions.
    *   Modify `agent_loader.py` to fetch LTM and pass it to `CustomizableAgent`.
*   **`CustomizableAgent`:**
    *   Adapt prompt template to include a section for LTM notes.
    *   Ensure it correctly receives and uses the assembled short-term history.
*   **Session Management:**
    *   `session_id` needs to be generated (client or server on first interaction if not provided) and consistently used. UUIDs are suitable.
    *   Client should store and send the current `session_id`.
*   **Error Handling:**
    *   Client: What if `/api/chat/session/archive_messages` fails? Retry logic? User notification?
    *   Server: Robust error handling for DB interactions and agent tool execution.
*   **Schema Migrations:** For the new Supabase tables.

## 7. Verification Checkpoint

*   **Minimize DB Writes Per Turn:** YES (Client buffers, batch archival for recent history, LTM updates are discrete).
*   **Natural Language LTM:** YES (Dedicated `notes` field, agent CRUD tool).
*   **Agent Has Short-Term Context:** YES (Client new messages + server short-term cache).
*   **Cross-Session Preference Persistence:** YES (Via LTM).
*   **Efficient Pruning:**
    *   `recent_conversation_history`: Can be pruned by `archived_at` date (e.g., keep last X days/months).
    *   `agent_long_term_memory`: Curated by agent tools.
    *   `server_session_cache`: Ephemeral or very short-lived.
*   **Client-Side Buffering:** YES (`useChatStore`).

## 8. Impact on Existing Designs

*   **`agent_memory_solution_design_v1.md`:** This v2 design significantly revises the persistence strategy. The concept of `SupabaseChatMessageHistory` writing every message individually to `agent_chat_messages` is replaced by the batched `recent_conversation_history` and the client/server caching mechanisms. The `agent_chat_messages` table (as a log of individual LangChain `BaseMessage` objects per DB row) may no longer be needed, or its role changes drastically.
*   **`agent_execution_prompt_customization_design_v1.md`:** Largely compatible. The `CustomizableAgent` is still central and will now also be responsible for incorporating LTM `notes` into its prompt, in addition to other prompt customizations. The `manage_long_term_memory` tool fits into the planned tool architecture.
*   **`state-management-design.md`:** The client-initiated batch archival of chat messages is a specific pattern for chat history and differs from the continuous, optimistic sync model proposed for generic entities like tasks. This distinction is important. Chat history is more of an append-only log that gets archived in chunks, whereas tasks have individual CRUD updates that benefit from optimistic UI and pending change queues.

---
🎨🎨🎨 **EXITING CREATIVE PHASE: Architecture Design - Agent Memory System v2** 🎨🎨🎨 