import datetime

# Active Context & Current Focus

This document outlines the current high-priority task, relevant files, and key considerations for the AI agent.

**Last Updated:** {{iso_timestamp}}

## Current High-Priority Task:

**Refactor: Implement Robust Session Management & Agent Executor Caching**

*   **Status:** Commencing Implementation Phase.
*   **Objective:** Implement a stable and persistent chat session management system using the `chat_sessions` table, and optimize server performance by caching AgentExecutors based on active client sessions.
*   **Core Logic:** Utilize the `public.chat_sessions` table as the source of truth for active client engagement. The `AgentExecutor` cache on the server will be keyed by `(user_id, agent_name)` and its liveness determined by `chat_sessions.is_active` and `chat_sessions.updated_at`.
*   **Design Document:** `session_management_and_executor_caching_plan.md`
*   **Task Breakdown:** See `memory-bank/tasks.md` for detailed phases and sub-tasks.

## Key Focus Areas for Implementation:

1.  **Client-Side (`webApp`):**
    *   `webApp/src/api/hooks/useChatSessionHooks.ts`: Adapt hooks to manage `chat_id` (persistent chat identifier) and `chat_sessions.id` (session instance identifier).
    *   `webApp/src/stores/useChatStore.ts`: Refactor store state and logic for session initialization, message handling (heartbeat), and session deactivation.
    *   `webApp/src/components/ChatPanel.tsx`: Integrate new store logic, manage session lifecycle (init, heartbeat, unload).
2.  **Server-Side (`chatServer/main.py`):**
    *   Adapt `AGENT_EXECUTOR_CACHE` to use `(user_id, agent_name)` as key and remove self-TTL.
    *   Ensure `/api/chat` uses `chat_sessions.chat_id` (from request's `session_id` field) for `PostgresChatMessageHistory`.
    *   Implement background tasks to deactivate stale `chat_session_instances` and evict corresponding inactive `AgentExecutors` from the cache.

## Relevant Files (Under Active Development/Review):

*   `session_management_and_executor_caching_plan.md` (Primary Plan)
*   `memory-bank/tasks.md` (Detailed Task List)
*   `chatServer/main.py` (Server-side logic)
*   `webApp/src/api/hooks/useChatSessionHooks.ts` (Client-side Supabase hooks)
*   `webApp/src/stores/useChatStore.ts` (Client-side state management)
*   `webApp/src/components/ChatPanel.tsx` (Client-side UI and interaction)
*   `DDL for public.chat_sessions` (Database schema - already implemented by user)

## Key Constraints & Considerations:

*   **Minimal Server Endpoints:** Client-side logic handles direct DB interactions with `chat_sessions` via RLS.
*   **Idempotency & Race Conditions:** Consider potential race conditions in client-side session management and heartbeat mechanisms.
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
1.  **[ACTIVE] Refactor: Implement Robust Short-Term Memory (STM) with Persistent `session_id` Strategy**
    *   **Objective:** Ensure reliable agent short-term memory using `langchain-postgres` and a consistent `session_id` management flow.
    *   **Current Phase:** Phase 4 (Testing & Refinement) - CORE FUNCTIONALITY WORKING, NEW ISSUES IDENTIFIED.
    *   **Key Outcomes & Current State:**
        *   **RESOLVED:** Major PostgreSQL connection issues (incorrect DB URL).
        *   **Short-term memory (STM):** VERIFIED WORKING (messages save/retrieve during session).
        *   **Long-term memory (LTM) DB writes:** VERIFIED WORKING (conceptual).
        *   **NEW ISSUE:** `session_id` persistence across sessions/restarts is NOT working.
        *   **NEW ISSUE:** Chat response latency is high.
    *   **Next Steps (User Action):** User to continue testing plan in the morning.
    *   **Next Steps (System Action):** Investigate `session_id` persistence, add timestamps to server logs for latency analysis.

2.  **[PREP] Code Health & Type Safety:**
    *   Address linter errors and type issues in `webApp/src/api/hooks/useTaskHooks.ts` and `webApp/src/api/types.ts` (as needed).

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