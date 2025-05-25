import datetime

# Active Context & Current Focus

This document outlines the current high-priority task, relevant files, and key considerations for the AI agent.

**Last Updated:** {{iso_timestamp}}

## Current High-Priority Task:

**1. CRUD Tool Migration to DB Configuration**

*   **Status:** Completed
*   **Objective:** Move all CRUD tool logic (table, method, field_map, etc.) to the `agent_tools` table as config. Only the generic `CRUDTool` class remains in code. Loader instantiates tools from DB config and runtime values. No code changes are needed to add new CRUD tools.
*   **Key Points:**
    *   All CRUD tool definitions (table, method, field_map) are now stored in the `config` column of `agent_tools`.
    *   The loader reads these configs and instantiates the generic `CRUDTool` with runtime values (`user_id`, `agent_id`, `supabase_url`, `supabase_key`).
    *   The registry only needs to include `CRUDTool` (and any custom tools).
    *   To add a new CRUD tool, insert a row in `agent_tools` with the correct config—no code changes required.
    *   Refactored `src/core/tools/crud_tool.py`: Removed redundant `None` checks in the `_run` method for `data_for_processing` and `final_data_payload`, relying on earlier Pydantic/loader validations and the robustness of internal helper methods like `_prepare_data_payload`.
    *   See `tool-creation-pattern.md` for the new pattern and example inserts.

**2. Refactor: Implement Robust Session Management & Agent Executor Caching**

*   **Status:** Implementation, Documentation, and Reflection Complete. See `memory-bank/clarity/references/guides/memory_system_v2.md` and `memory-bank/reflection/reflection-session-mgmt-v2.md`.
*   **Objective:** Implement a stable and persistent chat session management system using the `chat_sessions` table, and optimize server performance by caching AgentExecutors based on active client sessions.
*   **Core Logic:** See new guide for details.
*   **Next Steps:** Integration testing and future enhancements.
*   **Recent Fixes:**
    *   Resolved `NameError` on server startup by reordering scheduled task definitions.
    *   Refactored client-side API call for sending messages into a `useSendMessageMutation` hook.
    *   Prevented multiple session instance creation on chat open with an `isInitializingSession` flag in `useChatStore`.
*   **Design Document:** `session_management_and_executor_caching_plan.md`
*   **Task Breakdown:** See `memory-bank/tasks.md` for detailed phases and sub-tasks.

## Key Focus Areas for Implementation:

1.  **CRUD Tool System:**
    *   All CRUD tool logic is now DB-driven. No code changes are needed to add new CRUD tools—just DB inserts.
    *   Loader and registry are minimal and generic.
    *   See `tool-creation-pattern.md` for details.
2.  **Client-Side (`webApp`):**
    *   `webApp/src/api/hooks/useChatApiHooks.ts`: Implemented `useSendMessageMutation`.
    *   `webApp/src/stores/useChatStore.ts`: Refactored store state and logic for session initialization (including `isInitializingSession` fix), message handling (heartbeat), and session deactivation.
    *   `webApp/src/components/ChatPanel.tsx`: Integrated new mutation hook, manages session lifecycle (init, heartbeat, unload).
3.  **Server-Side (`chatServer/main.py`):**
    *   Adapted `AGENT_EXECUTOR_CACHE` to use `(user_id, agent_name)` as key and remove self-TTL.
    *   Ensured `/api/chat` uses `chat_sessions.chat_id` (from request's `session_id` field) for `PostgresChatMessageHistory`.
    *   Implemented background tasks (and fixed startup error) to deactivate stale `chat_session_instances` and evict corresponding inactive `AgentExecutors` from the cache.

## Relevant Files (Under Active Development/Review):

*   `tool-creation-pattern.md` (CRUD tool pattern)
*   `session_management_and_executor_caching_plan.md` (Primary Plan)
*   `memory-bank/tasks.md` (Detailed Task List)
*   `chatServer/main.py` (Server-side logic)
*   `webApp/src/api/hooks/useChatApiHooks.ts` (Client-side Supabase hooks & mutations)
*   `webApp/src/stores/useChatStore.ts` (Client-side state management)
*   `webApp/src/components/ChatPanel.tsx` (Client-side UI and interaction)
*   `DDL for public.chat_sessions` (Database schema - already implemented by user)

## Key Constraints & Considerations:

*   **Minimal Server Endpoints:** Client-side logic handles direct DB interactions with `chat_sessions` via RLS.
*   **CRUD Tool Extensibility:** All CRUD tools are now DB-configured. No code changes required for new tools.
*   **Idempotency & Race Conditions:** Addressed a key race condition in `initializeSessionAsync`.
*   **TTL Management:** Client-side heartbeats and server-side scheduled tasks will manage session and executor liveness.
*   **Clarity of IDs:**
    *   `chat_sessions.id`: PK, unique identifier for a specific client engagement/session instance.
    *   `chat_sessions.chat_id`: Foreign key (conceptually) to a persistent chat conversation/memory.
    *   `/api/chat` request body's `session_id` field will carry the `chat_sessions.chat_id` value.

## Previous Context (To be phased out or archived as new implementation progresses):

*   Old `user_agent_active_sessions` table and associated logic.
*   Previous `TTLCache` implementation in `chatServer/main.py` based on `(user_id, agent_name, session_id)`.

**Last Task Archived:** Task 9: Architect and Implement `useEditableEntity` Hook & Refactor `TaskDetailView`
**Archive Document:** `memory-bank/archive/archive-task9.md`

**Immediate Focus / Next Steps:**
1.  **[ACTIVE] CRUD Tool Migration to DB Configuration**
    *   **Objective:** Complete migration and test adding new CRUD tools via DB only.
    *   **Objective:** Review `crud_tool.py` for further simplification, particularly making `agent_name` filtering/payload injection fully configuration-driven via a DB flag (e.g., `apply_agent_name_context`).
2.  **[ACTIVE] Refactor: Implement Robust Session Management & Agent Executor Caching**
    *   **Objective:** Complete implementation and thoroughly test the new session management system.

**Mode Recommendation:** TESTING (CRUD Tool Migration & Session Management)

**General Project Goal:** Deliver a stable, extensible, and performant chat and agent tool system.

**Pending Decisions/Questions:**
*   None immediately critical; focus is on testing the current implementation.

**Previous Focus (Completed/Superseded in this context):**
*   CLI/Core Backend MVP Testing (Task 3.1 from `memory-bank/tasks.md`):
    *   Core agent memory persistence via Supabase (original V1 approach) was working.
    *   RuntimeError during tool execution was resolved.
    *   Prompt customization persistence verified.
*   Agent Memory System v1 Design & Implementation (Superseded by V2)
*   Linter error fixes in `useTaskHooks.ts` and `types.ts`.
*   Refactor `useChatApiHooks.ts` for direct Supabase writes.
*   Update `useChatStore.ts` to use direct archival logic.
*   UI integration of `agentId` for `ChatPanel` and `useChatStore` initialization.

**Upcoming Focus (Post Agent Memory V2 - Phase 2 UI Integration & Testing):**
*   Agent Memory System v2 - Phase 4: Refinements, Advanced LTM & Pruning

**Key Files Recently Modified/Reviewed (related to Gemini error resolution):**
*   `src/core/agents/customizable_agent.py` (Formatter and Output parser updated)

**Open Questions/Considerations:**
*   How are `session_id`s currently generated and managed on the client and server?
*   What is the expected lifecycle of a `session_id`?
*   Where in the database schema is `session_id` meant to be linked to a user or a specific conversation thread for persistence?

Last updated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

**Mode Recommendation:** IMPLEMENT (Robust STM - Debugging `session_id` persistence and latency)

**General Project Goal:** Complete Agent Memory System v2 implementation. Enable robust, evolving agent memory and conversational capabilities. **Updated Goal: Achieve stable and persistent short-term memory, resolve `session_id` persistence, and address chat latency.**

**Pending Decisions/Questions:**
*   Strategy for ensuring `session_id` correctly links to `chat_message_history` and potentially a user/agent session table.