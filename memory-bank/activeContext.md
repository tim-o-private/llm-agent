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
IMPLEMENTATION / PENDING TESTING

## Current Focus

**Task 7: Abstract TaskDetailView State Management into Reusable Hooks**

The development and initial integration of the `useObjectEditManager` and `useReorderableList` hooks into `webApp/src/components/features/TaskDetail/TaskDetailView.tsx` are now largely complete. Previously blocking linter errors related to this integration have been resolved, and unused resources in the hook files and `TaskDetailView.tsx` have been cleaned up. The documentation for the hooks in `memory-bank/clarity/references/patterns/reusable-ui-logic-hooks.md` has been updated to reflect their current implemented APIs.

**Immediate Blocker:**
None currently identified for this specific task. The primary path forward is testing.

**Secondary Considerations (Previously addressed or will need re-verification after unblocking):**
*   Verification that all unused variables/imports introduced during refactoring have been removed from `TaskDetailView.tsx`, `useObjectEditManager.ts`, and `useReorderableList.ts` (This has been completed).

**Next Steps Upon Resuming:**
1.  **Perform Thorough Integration Testing:** Execute the manual test plan in `memory-bank/clarity/testing/task-detail-view-test-plan.md` to verify all parent task and subtask functionalities in the refactored `TaskDetailView.tsx`.
2.  **Address Issues:** Resolve any bugs or unexpected behaviors identified during integration testing.
3.  **Write Unit Tests:** Implement unit tests for `useObjectEditManager.ts` and `useReorderableList.ts` as outlined in `tasks.md` (Task 7, Phases 1 & 2).
4.  **Finalize Task 7:** Proceed with Phase 6 (Documentation Update & Cleanup) of Task 7, which includes a final review of `TaskDetailView.tsx` and consideration of example usage for the hooks.

**🛑 CRITICAL REMINDERS FOR AGENT 🛑**
*   **ALWAYS consult `memory-bank/tasks.md` and `reusable-ui-logic-hooks.md` before resuming work on Task 7.**
*   **The source of truth for hook APIs is `reusable-ui-logic-hooks.md`.**
*   **Prioritize systematic testing and issue resolution.**
*   **Update `tasks.md` and `memory-bank/progress.md` diligently as Task 7 progresses post-testing.**