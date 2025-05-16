# Active Context - Post-VAN Assessment

## Project Status:
The project involves two main components: a CLI LLM environment and the "Clarity" web application.
Current active work, as indicated by `tasks.md`, is primarily focused on:
1.  **Clarity Web Application UI/UX:** Specifically, the "Prioritize" flow of the Cyclical Flow Implementation (Task 4.1.UI.5) and related sub-tasks like `TaskCard.tsx` refactoring. Chat panel UI is complete, awaiting backend integration.
2.  **Agent Memory & Tooling Enhancement (Supabase Integration):** Schema design for agent memory and prompts is a key ongoing task, critical for the Clarity chat panel and future agent capabilities.

## VAN Mode Completion:
VAN mode assessment complete. All core Memory Bank files (`projectbrief.md`, `productContext.md`, `systemPatterns.md`, `techContext.md`, `activeContext.md`, `progress.md`, `tasks.md`, `style-guide.md`) are present. `tasks.md` indicates substantial ongoing work.

## Next Step:
Transitioning to PLAN mode to refine current objectives from `tasks.md` or select the next specific task for development.

**Overall Goal:** UI/UX Overhaul for Clarity web application, focusing on implementing the Cyclical Flow (Prioritize, Execute, Reflect) and enhancing core usability features like Fast Task Entry, Task Detail Views, and keyboard navigation.

**Current State & Last Session Summary:**

*   **Theming Strategy (Task II.1):** COMPLETED.
*   **Keyboard Navigability (Task II.2 - General Audit & Shell):** COMPLETED.
*   **Drag-and-Drop Task Reordering (Task II.3):** COMPLETED.
*   **Fast Task Entry (Task II.4.1.UI.1):** COMPLETED. Input field at top of TodayView, 'T' hotkey, parsing, creation, and focus on new task are functional.
*   **TaskDetailView (Task II.4.1.UI.2):** COMPLETED.
    *   Core modal structure with form for Title, Description, Notes, Status, Priority is implemented.
    *   Save functionality using `useUpdateTask` is working.
    *   Delete functionality via `onDeleteTaskFromDetail` is implemented.
    *   Triggering from `TaskCard` (click on title area or dedicated edit icon) is implemented.
    *   Triggering from 'E' key on a focused task is implemented.
    *   `Textarea.tsx` and `webApp/src/lib/utils.ts` (for `cn`) were created to support this.
    *   A schema cache issue related to `subtask_position` was resolved (ensuring DDL was applied to the DB).
*   **Enhanced Keyboard Navigation in TodayView (Task II.4.1.UI.3):** COMPLETED.
    *   Initial focus on first task.
    *   'N'/'P' keys for next/previous task focus (direction corrected).
    *   Visual focus indicator on `TaskCard` (styles adjusted for dark mode visibility).
    *   'E' key to edit focused task (opens `TaskDetailView`).
    *   'T' key for `FastTaskInput` focus.
    *   Focus automatically moves to newly created tasks.
*   **Prioritize View Modal (Task II.4.1.UI.5):** In Progress.
    *   Basic modal created with fields for motivation, completion note, session breakdown, timer duration.
    *   Integrated into `TodayView.tsx` with "Focus" button from `TaskCard` triggering it.
    *   Working on implementing the actual transition to "Execute" phase.
*   **Chat Panel (Task II.4.1.UI.8):** COMPLETED.
    *   Basic UI with title, close button, message area, input field.
    *   Toggle functionality in `TodayView`.
    *   Main content area adjusts when panel is open.
    *   Close button using Radix icons properly implemented.

**Recent Bug Fixes:**
*   **Fixed infinite render loop in TodayView.tsx** by restructuring how displayTasks are calculated and managed, breaking dependency cycles between state variables.
*   **Fixed Chat Panel close functionality** by implementing a proper close button with Radix Cross1Icon.
*   **Fixed icon consistency** across components by standardizing on Radix icons (replaced Lucide Trash2Icon with Radix TrashIcon in TaskDetailView).
*   **Fixed React state management practices** by using useMemo and careful useEffect dependencies.

**Immediate Next Steps for New Session:**

*   **Continue implementation of Prioritize View Modal (Task II.4.1.UI.5)**:
    *   Test the entire flow from task selection to focus session initiation.
    *   Implement the transition to "Execute" phase/view from the modal.
    *   Ensure all event handlers are properly connected to the Backend API.
*   **Implement full chat functionality in Chat Panel (Task II.4.1.UI.8)**:
    *   Add message state management.
    *   Implement sending/receiving messages.
    *   Connect to agent/backend through API.
*   **Begin work on Subtask Display & Interaction Logic (Task II.4.1.UI.4)**:
    *   Determine strategy for fetching/displaying subtasks.
    *   Create SubtaskCard and SubtaskList components.
    *   Modify TaskCard to show subtask accordion.

**Key Relevant Documents for Next Task:**

*   `memory-bank/tasks.md` (Sections II.4.1.UI.4, II.4.1.UI.5)
*   `memory-bank/creative/creative-PER-cycle.md` (For P-P-E-R design, Prioritize View and Subtask display specs)
*   `memory-bank/style-guide.md` (For UI consistency)
*   `memory-bank/techContext.md` (Core Data Models for tasks/subtasks)
*   `webApp/src/components/features/PrioritizeView/PrioritizeViewModal.tsx`
*   `webApp/src/pages/TodayView.tsx`
*   `webApp/src/components/ui/TaskCard.tsx`
*   `webApp/src/components/ChatPanel.tsx`
*   `data/db/ddl.sql` (Reference for task/subtask fields)
*   `webApp/src/api/types.ts` (Task, Subtask related types)
*   `webApp/src/api/hooks/useTaskHooks.ts`

**Process Reminder from Last Session:**
*   Ensure DDL changes are applied to the Supabase instance if schema cache errors occur.
*   Verify UI component import paths and aliases carefully.

**🛑 CRITICAL REMINDERS FOR AGENT 🛑**

*   **ALWAYS consult `memory-bank/tasks.md` BEFORE starting any implementation.** Verify if the task or a similar one is already documented. Do NOT duplicate effort.
*   **Strictly adhere to `ui-dev` rule, especially Pattern 2:** Use `@radix-ui/react-*` primitives for UI component behavior and `@radix-ui/react-icons` as the PRIMARY icon library. `lucide-react` is acceptable as a secondary source if an icon is not available in Radix. DO NOT attempt to import icons from non-existent paths.
*   **Follow proper React state management practices:**
    * Avoid state management loops by ensuring useEffect dependencies are properly managed
    * Do not include state updater functions in dependency arrays unless they are wrapped in useCallback
    * Use useMemo to derive complex values from props or state to prevent unnecessary recalculations
    * When state updates depend on previous states, use functional updates (e.g., `setPrevState(prev => ...)`)
*   **Keyboard shortcuts must work consistently:**
    * Ensure no infinite re-rendering loops by properly managing useEffect dependencies
    * Check if modals or dialogs are open before handling keyboard events
    * Ensure focus states are correctly managed between React state and DOM reality
*   **Modal and dialog management:**
    * Always include close buttons that work correctly in modals/dialogs/panels
    * Use Radix UI primitives for accessible modal behavior when possible
    * Verify that all modals can be opened AND closed properly

**Recent Bug Fixes Reference:**
* Fixed infinite state update loop in TodayView.tsx by separating displayTasks calculation and updating focusedTaskId handling
* Fixed ChatPanel close button by using proper Radix icons and ensuring functional close button
* Fixed icon consistency across components by standardizing on Radix icon usage

*   **Verify all changes against existing functionality described as COMPLETED in this `activeContext.md` file.** Do not break completed features.
*   **Update `tasks.md` and `memory-bank/clarity/progress.md` diligently AFTER completing any part of a task.**

# Active Context - Transition to IMPLEMENT Mode (TodayView State Refactor)

## Current Goal:
Refactor `TodayView.tsx` state management by implementing and integrating a new Zustand store (`useTaskViewStore.ts`).

## Reason for Refactor:
To resolve persistent "Maximum update depth exceeded" errors, simplify the component's internal logic, enhance maintainability, and improve clarity for future development (both human and AI-assisted).

## Key Planning Decisions (Option C from PLAN mode):
1.  **`useTaskViewStore.ts` Creation:** This new store will manage core UI states for `TodayView`:
    *   `rawTasks: Task[]` (synced from React Query)
    *   `focusedTaskId: string | null`
    *   `selectedTaskIds: Set<string>` (for future batch actions, checkbox will act as selector)
    *   `isFastInputFocused: boolean`
    *   Modal states: `detailViewTaskId: string | null`, `prioritizeModalTaskId: string | null`
    *   Actions for optimistic UI updates (e.g., `reorderRawTasks` for DND).
2.  **`TodayView.tsx` Refactoring:**
    *   Will fetch API data using existing React Query hooks (`useFetchTasks`, mutation hooks).
    *   Will sync `tasksFromApi` to `useTaskViewStore` via a `setRawTasks` action.
    *   Will consume UI state (`rawTasks`, `focusedTaskId`, etc.) from `useTaskViewStore`.
    *   API-calling event handlers (`handleMarkComplete`, `handleDeleteTask`, etc.) will remain in `TodayView.tsx`, using React Query mutations.
    *   `displayTasks: TaskCardProps[]` will be computed within `TodayView.tsx` using `useMemo`. This `useMemo` hook will depend on state from `useTaskViewStore` (e.g., `rawTasks`, `focusedTaskId`, `selectedTaskIds`) and the component's own memoized API/modal handlers.
    *   Other `useEffect` hooks (keyboard navigation, initial focus) will be refactored to use store state and actions.
3.  **`TaskCard.tsx` Refactoring:**
    *   Checkbox will reflect selection state from `props.isSelected` (derived from `store.selectedTaskIds`).
    *   Checkbox `onChange` will trigger `props.onSelectTask`.
    *   An explicit "Mark Complete" button/icon will be added, triggering `props.onMarkComplete`.

## Current Mode & Phase:
IMPLEMENT Mode - Build Phase 1: Create `useTaskViewStore.ts`.

## Next Steps in Build:
1.  Implement `src/stores/useTaskViewStore.ts`.
2.  Refactor `webApp/src/pages/TodayView.tsx`.
3.  Refactor `webApp/src/components/ui/TaskCard.tsx`.
4.  Document and conduct thorough testing. 