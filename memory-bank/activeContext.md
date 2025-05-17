# Active Context Update - 2025-05-16

## Recently Completed & Archived
*   **Task II.4.1.UI.9: Implement Subtask Creation & Display UI** - Enhancement is now complete and archived.
    *   **Archive:** `memory-bank/archive/archive-II.4.1.9.md`
    *   **Reflection:** `memory-bank/reflection/reflection-II.4.1.9.md`

## Current Mode
IMPLEMENTATION (Verification & Next Steps)

## Current Focus

### State Management Architecture Implementation

The project is now in the implementation phase for the new state management architecture. We have completed Phases 1-3 of the 5-phase plan and are now focusing on Phase 4: Testing and Verification.

**Current Progress:**
1. ✅ **Phase 1: Core Store Implementation** - Completed
   - Created `useTaskStore.ts` with local-first operations and background sync
   - Implemented optimistic UI updates and proper error handling
   - Added normalized data structure for efficient access

2. ✅ **Phase 2: TodayView Component Migration** - Completed
   - Updated FastTaskInput to use the new store
   - Refactored TodayView.tsx to use the store's actions and selectors
   - Implemented consistent store initialization pattern

3. ✅ **Phase 3: TaskDetail Integration** - Completed
   - Updated SubtaskItem to use the task store
   - Implemented consistent data access across components

**Current Focus: Phase 4 - Testing and Verification**
- Testing the new architecture with different scenarios:
  - Network loss during operations
  - Concurrent operations from multiple components
  - Performance with large datasets
  - Consistent behavior across components
  - Edge cases in error recovery

**Next Steps:**
1. Complete testing and verification (Phase 4)
2. Update documentation and add developer guidelines (Phase 5)
3. Extend the pattern to other entity types beyond tasks

**Benefits Realized:**
- Components now share a consistent source of truth
- Local-first operations provide immediate UI feedback
- Background sync creates a smoother user experience
- Reduced API calls through optimistic updates and batching
- Better error handling and recovery mechanisms

**Current Focus:** Preparing for Task 5.2 - Implement Task Store with New Architecture

**Key Details:**
1. **Implementation Plan:** A 5-phase approach has been defined in `memory-bank/clarity/implementation-plan-state-management.md`:
   - Phase 1: Core Store Implementation
   - Phase 2: TodayView Component Migration
   - Phase 3: TaskDetail Integration
   - Phase 4: Testing and Verification
   - Phase 5: Documentation and Cleanup

2. **Architecture Overview:**
   - Entity-centric Zustand stores with normalized data models
   - Local-first operations with optimistic UI updates
   - Background sync with the database every 5-10 seconds
   - Conflict resolution for concurrent modifications
   - Consistent hydration and initialization patterns

3. **Core Challenges Being Addressed:**
   - Race conditions and concurrent updates
   - Network failure resilience
   - Consistent store initialization
   - Offline support
   - Performance optimization

**Estimated Timeline:** 6-9 days for the complete implementation

This work will provide a solid foundation for state management across the application and serve as a reference pattern for future development.

---

# VAN Mode Assessment - Session Start: {datetime.now().isoformat()}

## 1. VAN Mode Initiation
User initiated VAN mode.

## 2. Platform Detection
*   Operating System: Linux (as per user_info)
*   Path Separator: /
*   Command Structure: Standard Linux commands

## 3. Memory Bank Check
*   Core Memory Bank files and directories (`tasks.md`, `activeContext.md`, `progress.md`, `projectbrief.md`, `productContext.md`, `systemPatterns.md`, `techContext.md`, `style-guide.md`, `creative/`, `reflection/`, `archive/`) **verified as existing**.
*   No creation of Memory Bank structure was needed.

## 4. Basic File Verification
*   Essential Memory Bank components and structure are present.

## 5. Early Complexity Determination
*   **Analysis of `memory-bank/tasks.md`:** Current primary tasks include "Implement Prioritize View (Modal)" (Task II.4.1.UI.5 under "Cyclical Flow Implementation") and "Agent Memory & Tooling Enhancement (Supabase Integration)" (Task III).
*   **Complexity Level:** Assessed as **Level 3 (Intermediate Feature) / Level 4 (Complex System)** due to the nature and scope of these tasks.
*   **VAN Mode Outcome:** As per `isolation_rules/visual-maps/van_mode_split/van-mode-map.mdc`, Level 2-4 complexity requires a transition from VAN to PLAN mode.

## 6. Next Step
Transition to PLAN mode.

# Active Context - Post-VAN Assessment

## Project Status:
The project involves two main components: a CLI LLM environment and the "Clarity" web application.
Current active work, as indicated by `tasks.md`, is primarily focused on:
1.  **Clarity Web Application UI/UX:** Specifically, the "Prioritize" flow of the Cyclical Flow Implementation (Task 4.1.UI.5) and related sub-tasks. Chat panel UI is complete, awaiting backend integration.
2.  **Agent Memory & Tooling Enhancement (Supabase Integration):** Schema design for agent memory and prompts is a key ongoing task, critical for the Clarity chat panel and future agent capabilities.

## VAN Mode Completion & Transition:
**Date:** (Current Date)
**VAN Assessment Summary:**
*   VAN mode initiated by user.
*   Platform Detection: Linux. Standard commands apply.
*   Memory Bank Check: Core Memory Bank structure and files verified as present and populated.
*   Early Complexity Determination: Based on `tasks.md` (e.g., "Implement Prioritize View (Modal)" - Task 4.1.UI.5, Supabase integration), the project complexity is Level 3-4.

**Transition:** As per `isolation_rules/visual-maps/van_mode_split/van-mode-map`, for Level 2-4 complexity, VAN mode transitions to PLAN mode.

**Current Mode: REFLECT**

**Task for Reflection:** II.4.1.9 - Implement Subtask Creation & Display UI

**Summary of Reflection for II.4.1.9:**
The reflection for Task II.4.1.9, documented in `memory-bank/reflection/reflection-II.4.1.9.md`, covers the implementation of subtask creation, display, and drag-and-drop reordering in both `TaskDetailView` and `TaskCard`. Key challenges included DND state synchronization, UI "pop" effects, and a "Maximum update depth exceeded" error. These were resolved through a significant state management refactor (favoring React Query over direct Zustand manipulation for server state, removing `rawTasks` from `useTaskViewStore`), and implementing optimistic updates for subtask reordering in `TaskCard`. The reflection highlights the complexities of managing hierarchical, interactive state and the benefits of React Query for server state and optimistic updates.

**Current Mode: CREATIVE**

**Goal for CREATIVE Mode:**
Define and document a consistent storage and state management strategy for Tasks (including Subtasks) and TaskDetails. This will focus on solidifying the patterns for using React Query (for server state, caching, mutations, optimistic updates) and Zustand (for global UI state, if necessary), and how they interact. The aim is to ensure clarity, prevent future synchronization issues, and provide a clear reference for ongoing development.

**Current Storage & State Management Strategy (Summary for Discussion and Refinement):**

*   **Server State & Caching (Primary Mechanism):**
    *   **Tool:** `React Query` (`@tanstack/react-query`).
    *   **Usage:** All CRUD operations for tasks and subtasks (fetch, create, update, delete) are managed via React Query hooks (e.g., `useFetchTasks`, `useUpdateTaskOrder`, `useUpdateSubtaskOrder`).
    *   **Caching:** React Query handles caching of task data. Cache keys (e.g., `['tasks', userId]`) are used to manage and invalidate data.
    *   **Mutations:** Updates to the backend are performed via mutation hooks.
        *   `onSuccess`: Typically invalidates relevant queries (e.g., `queryClient.invalidateQueries(['tasks', userId])`) to trigger re-fetches and UI updates with fresh data.
        *   `onMutate`, `onError`, `onSettled`: Used for implementing optimistic updates.
            *   `onMutate`:
                *   Cancels ongoing queries for the same data.
                *   Snapshots the previous state from the cache.
                *   Optimistically updates the cache (`queryClient.setQueryData`) with the new expected state.
                *   Returns a context object with the snapshotted state.
            *   `onError`:
                *   Rolls back the cache to the snapshotted state using the context from `onMutate`.
            *   `onSettled`:
                *   Invalidates the relevant queries to ensure eventual consistency with the server.
    *   **Current Optimistic Implementation Example:** `useUpdateSubtaskOrder` optimistically updates the `['tasks', userId]` query cache by directly manipulating the `subtasks` array of the parent task within the cached data.

*   **Global UI State (Secondary / Ancillary):**
    *   **Tool:** `Zustand`.
    *   **Usage:** Intended for global UI state that doesn't directly map to server data or when cross-component state needs to be shared without prop drilling, and React Query's cache isn't the right fit.
    *   **Current Status:** Usage has been significantly reduced for task/subtask data itself. The `useTaskViewStore` previously held `rawTasks` which caused synchronization issues. This has been removed.
    *   **Potential Future Use:** Managing transient UI states like modal visibility, selected items not yet persisted, or complex form states before submission if not co-located with the component.
    *   **Guideline:** Avoid duplicating server state in Zustand. Rely on React Query as the source of truth for server-persisted data.

*   **Local Component State:**
    *   **Tool:** `React.useState`, `React.useReducer`.
    *   **Usage:** For component-specific UI state that doesn't need to be shared globally or isn't tied to server data (e.g., input field values before validation/submission, toggle states for UI elements within a single component).

**Key Principles from Recent Refactor:**
1.  **React Query as Source of Truth for Server Data:** Task and subtask data displayed in the UI should primarily flow from React Query's cache.
2.  **Minimize Direct Store Manipulation for Server Data:** Avoid actions in Zustand stores that directly set or modify data that mirrors server state. Instead, mutations should go through React Query hooks, which then update the cache and/or invalidate queries.
3.  **Optimistic Updates for Responsiveness:** Implement optimistic updates via React Query for operations like reordering to improve perceived performance.
4.  **Clear Separation:** Maintain a clear distinction between server state (React Query) and purely client-side UI state (Zustand, local state).

**Items for Creative Discussion:**
*   Further standardization of optimistic update patterns (e.g., helper functions, consistent cache update logic).
*   Defining clear boundaries for when to use Zustand vs. local state for UI concerns.
*   Documentation of these patterns for the team (e.g., in `memory-bank/techContext.md` or a dedicated state management guide).
*   Review if any remaining parts of `useTaskViewStore` (or other stores) could be further simplified or if their current role is appropriate.

**🛑 CRITICAL REMINDERS FOR AGENT 🛑**

*   **ALWAYS consult `memory-bank/tasks.md` BEFORE starting any implementation.**
*   **Strictly adhere to `ui-dev` rule (Radix UI, Radix Icons).**
*   **Follow proper React state management practices (Zustand, React Query).**
*   **Ensure Keyboard shortcuts work consistently.**
*   **Verify Modal and dialog management.**
*   **Update `tasks.md` and `memory-bank/progress.md` diligently.**

---

### Proposal for Systematizing Development Practices (Memory Bank Update)

Based on the recent TodayView refactor session and user feedback, the following documentation should be created/updated in the `memory-bank` to prevent similar state management issues and ensure consistency:

1.  **Page Component Best Practices (`memory-bank/clarity/pageComponentBestPractices.md`):**
    *   **Separation of Concerns:** Emphasize lean pages, delegation to hooks.
    *   **UI State Management Strategy:** Guidelines for `useState` vs. Zustand.
    *   **Data Fetching & Caching:** Mandate React Query.
    *   **Derived State:** Use `useMemo`.
    *   **Minimize Logic in Render.**
    *   **Note on `TodayView.tsx`:** Plan further refactoring into custom hooks.

2.  **Zustand Store Design Guidelines (`memory-bank/clarity/zustandStoreDesign.md`):**
    *   **Scope:** Cohesive, domain-specific stores.
    *   **State Structure:** Normalized; `Set`/`Map` with `enableMapSet()`.
    *   **Actions:** Clear, specific; only way to modify state.
    *   **Immutability:** Immer middleware is standard.
    *   **Selectors:** Encourage use for specific state subscription.
    *   **No API Calls in Stores:** Stores hold state; API calls are side effects managed by React Query.
    *   **Middleware:** `devtools`, `persist` (judiciously), `immer`.

3.  **Keyboard Shortcut Management (`memory-bank/clarity/keyboardShortcutGuide.md`):**
    *   **Scope:** Local (view-specific) vs. Global.
    *   **Implementation:** `useEffect` with `keydown`, cleanup, check for active inputs/modals, `event.preventDefault()`.
    *   **State Interaction:** Dispatch actions to stores.
    *   **Consistency & Discoverability.**

This detailed context and the proposed guidelines should help maintain a cleaner and more robust state management approach moving forward.

# Active Context Update - 2024-07-18 (End of Session)

## Current Mode
IMPLEMENTATION (Verification & Next Steps)

## Summary of Recent Activity & Key Decisions

*   **Toast Notification System Overhaul & Verification:**
    *   Successfully refactored `webApp/src/components/ui/toast.tsx` to use `@radix-ui/react-toast` primitives directly, resolving issues with `react-hot-toast` (stacking context, incorrect positioning).
    *   Implemented a simplified imperative API (`toast.success()`, `toast.error()`, `toast.default()`) for triggering toasts.
    *   Corrected Radix primitive imports and ensured the `<ToastPrimitives.Provider>` and `<ToastPrimitives.Viewport>` are correctly used within the `ToasterContainer`.
    *   Updated all relevant files (`useTaskHooks.ts`, `TaskDetailView.tsx`, `TodayView.tsx`, `FastTaskInput.tsx`, `useTaskStore.ts`) to use the new toast API.
    *   Resolved issues related to toast `duration` (now configurable and defaults to `2000ms`, with `Infinity` used for debugging) and styling (background color for default variant using `bg-[var(--color-panel-translucent)]`).
    *   The system is now considered stable and verified.
*   **"Edit Task Save" Modal Closure:** Fixed the bug in `TaskDetailView.tsx` where the modal was not closing upon successful task save. It now correctly calls `onOpenChange(false)`.
*   **Keyboard Shortcut Refactor Follow-ups:** (Previously completed, context for other issues)

## Immediate Next Steps

1.  **Address Task Reordering Regression:** Investigate and fix the critical regression where reordering tasks or subtasks in `TodayView` causes them to revert to their original positions immediately. This was noted as a new regression after the keyboard shortcut fixes.
2.  **Focus Management on Modal Close:** While not explicitly tested as part of the toast/save fix, ensure that when `TaskDetailView` closes, focus returns appropriately to the main application, ideally to the element that triggered its opening or a sensible default in `TodayView.tsx`. (This is a general UX best practice to keep in mind).

## Subsequent Goals

1.  **Continue "Prioritize" Flow Development:** Resume development of the "Prioritize View (Modal)" (`Sub-Task 4.1.UI.5` from `tasks.md`) and other features related to the P-P-E-R cycle.

## Key Files Affected by Recent Toast & Modal Work:
*   `webApp/src/components/ui/toast.tsx` (Majorly refactored and verified)
*   `webApp/src/App.tsx` (Imports `ToasterContainer` from `toast.tsx`)
*   `webApp/src/api/hooks/useTaskHooks.ts` (Updated toast calls)
*   `webApp/src/components/features/TaskDetail/TaskDetailView.tsx` (Updated toast calls, fixed modal close on save)
*   `webApp/src/pages/TodayView.tsx` (Updated toast calls)
*   `webAll/src/components/features/TodayView/FastTaskInput.tsx` (Updated toast calls)
*   `webApp/src/stores/useTaskStore.ts` (Updated toast calls)

**🛑 CRITICAL REMINDERS FOR NEXT SESSION 🛑**
*   **The next major bug to tackle is the task reordering regression.** This is a high priority.
*   Investigate focus management after modal closures as a general UX improvement.
*   Consult `memory-bank/tasks.md` and `memory-bank/progress.md` for detailed task status and context.
*   Adhere to `ui-dev` rule (Radix UI, Tailwind CSS) and project conventions for state management. 