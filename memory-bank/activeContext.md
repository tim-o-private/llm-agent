import datetime

# Active Context

**Last Task Archived:** Task 9: Architect and Implement `useEditableEntity` Hook & Refactor `TaskDetailView`
**Archive Document:** `memory-bank/archive/archive-task9.md`

**Immediate Focus / Next Steps:**
1.  **[ACTIVE] Refactor: Implement Robust Short-Term Memory (STM) with Persistent `session_id` Strategy**
    *   **Objective:** Ensure reliable agent short-term memory using `langchain-postgres` and a consistent `session_id` management flow involving client-side React Query hooks, a Supabase table (`user_agent_active_sessions`), and `localStorage`.
    *   **Current Phase:** Core Implementation (Phases 1-3) Complete. **Next: Phase 4 (Testing & Refinement).**
    *   **Key Components for Phase 4:** End-to-end testing of session persistence, conversation continuity, backend `session_id` usage.
    *   **Previous Related Status:** `SUPABASE_DB_HOST` configuration error resolved. Old STM system (`server_session_cache`, client-side batch archival to `recent_conversation_history`) replaced.

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
*   (None currently related to the resolved STM implementation errors or the new STM plan)

Last updated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

**Mode Recommendation:** IMPLEMENT (Robust STM - Phase 4 Testing & Refinement)

**General Project Goal:** Complete Agent Memory System v2 implementation. Enable robust, evolving agent memory and conversational capabilities. **Updated Goal: Implement a stable and persistent short-term memory solution as a foundation for reliable agent conversations. Next step: Test the implemented solution.**

**Pending Decisions/Questions:**
*   Specific design for a common event-driven sync/archival trigger mechanism for the client-side (if current approach proves insufficient during broader testing).