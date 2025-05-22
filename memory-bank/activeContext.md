import datetime

# Active Context

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