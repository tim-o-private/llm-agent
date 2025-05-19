**Task 7: Abstract TaskDetailView State Management into Reusable Hooks**

Following the successful refactor of `TaskDetailView.tsx` to use React Hook Form for its main form state (Task 6), the next major initiative is to abstract the complex state management and interaction logic into reusable custom hooks. This aims to significantly simplify `TaskDetailView.tsx`, making it more of a presentational component, and to create generalizable solutions for object editing and reorderable list management across the application.

**Key Objectives for Task 7:**
1.  **Develop `useObjectEditManager` Hook:** This hook will manage the lifecycle of editing a single data object, integrating with React Hook Form, handling data fetching (via a provided query hook), mutations (update/create), and save/cancel logic (including dirty checking and confirmation).
2.  **Develop `useReorderableList` Hook:** This hook will manage a list of items that can be reordered using `dnd-kit`. It will handle list fetching, optimistic updates for reordering, committing order changes, and potentially adding/editing items within the list.
3.  **Refactor `TaskDetailView.tsx`:** Systematically replace its internal logic for parent task editing with `useObjectEditManager` and its subtask management logic with `useReorderableList`.

**Conceptual Design & API Proposal:**
*   The detailed design for these hooks, including proposed API signatures and features, is documented in `memory-bank/clarity/references/patterns/reusable-ui-logic-hooks.md`.

**Next Steps:**
1.  [DONE] Finalize the API design for `useObjectEditManager` and `useReorderableList` based on the proposal.
2.  [DONE] Begin implementation of `useObjectEditManager` (Phase 1 of Task 7).
3.  [DONE] Follow with the implementation of `useReorderableList` (Phase 2 of Task 7).
4.  [IN PROGRESS] Proceed with the phased refactoring of `TaskDetailView.tsx` (Phases 3 & 4 of Task 7).
5.  Thoroughly test the refactored component and the new hooks (Phase 5 of Task 7).

This abstraction is a critical step towards improving code quality, reusability, and maintainability in the Clarity application.

**🛑 CRITICAL REMINDERS FOR AGENT 🛑**
*   **ALWAYS consult `memory-bank/tasks.md` and the new `reusable-ui-logic-hooks.md` BEFORE starting implementation of Task 7.**
*   **Adhere to `ui-dev` rule (Radix UI, Radix Icons, Tailwind CSS).**
*   **Prioritize generic, reusable design for the new hooks.**
*   **Ensure comprehensive unit testing for the hooks.**
*   **Update `tasks.md` and `memory-bank/progress.md` diligently as Task 7 progresses.**

---

# Active Context Update - 2024-07-18 (End of Session)

## Current Mode
ANALYSIS / DOCUMENTATION

## Current Focus
**Task: Capture Current State & Document Hook Patterns (User Request)**

Following a user report of issues with a previous chat session, the current focus is to thoroughly review and document the state of development, particularly concerning the custom hooks used in `TaskDetailView.tsx`.

**Activities Completed:**
1.  Reviewed `memory-bank/clarity/chatHistory` to understand the preceding context.
2.  Read and analyzed the following hook files:
    *   `webApp/src/hooks/useEntityEditManager.ts`
    *   `webApp/src/hooks/useObjectEditManager.ts`
    *   `webApp/src/hooks/useReorderableList.ts`
    *   `webApp/src/hooks/useTaskDetailStateManager.ts`
3.  Read and analyzed `webApp/src/components/features/TaskDetail/TaskDetailView.tsx` to understand its interaction with these hooks.
4.  Documented the established patterns and created a MermaidJS sequence diagram illustrating the data flow. This has been saved to `memory-bank/clarity/diagrams/hook-data-flow-tdv.md`.

**Task 7: Abstract TaskDetailView State Management into Reusable Hooks (Status Update)**

The development and initial integration of `useObjectEditManager`, `useReorderableList`, and the orchestrating `useTaskDetailStateManager` (which uses `useEntityEditManager`) into `TaskDetailView.tsx` are confirmed to be largely complete based on code review.

**Immediate Blocker:**
None for the current documentation task. For Task 7, the next step remains comprehensive testing.

**Next Steps Upon Resuming (for Task 7):**
1.  **Perform Thorough Integration Testing:** Execute the manual test plan in `memory-bank/clarity/testing/task-detail-view-test-plan.md` to verify all parent task and subtask functionalities in the refactored `TaskDetailView.tsx`.
2.  **Address Issues:** Resolve any bugs or unexpected behaviors identified during integration testing (e.g., issues noted in `tasks.md` like ST-6, OT-1 if still relevant after recent refactors).
3.  **Write Unit Tests:** Implement unit tests for `useObjectEditManager.ts`, `useReorderableList.ts`, `useEntityEditManager.ts`, and `useTaskDetailStateManager.ts`.
4.  **Finalize Task 7 Documentation:** Update `reusable-ui-logic-hooks.md` if any further API refinements occur during testing. Ensure all related documentation is consistent.

**🛑 CRITICAL REMINDERS FOR AGENT 🛑**
*   **ALWAYS consult `memory-bank/tasks.md` and the new `memory-bank/clarity/diagrams/hook-data-flow-tdv.md` before resuming work on Task 7 or related UI tasks.**
*   **The source of truth for hook APIs is the code itself and its accompanying documentation (`reusable-ui-logic-hooks.md` and `hook-data-flow-tdv.md`).**
*   **Prioritize systematic testing and issue resolution for Task 7.**
*   **Update `tasks.md` and `memory-bank/progress.md` diligently as Task 7 progresses post-testing.**