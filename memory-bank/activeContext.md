# Active Context Update - 2025-05-16

## Recently Completed & Archived
*   **Task II.4.1.UI.9: Implement Subtask Creation & Display UI** - Enhancement is now complete and archived.
    *   **Archive:** `memory-bank/archive/archive-II.4.1.9.md`
    *   **Reflection:** `memory-bank/reflection/reflection-II.4.1.9.md`

## Current Mode
ARCHIVE mode completed. Resetting for next task.

## Current Focus

### State Management Architecture Redesign

The project is currently focused on creating a consistent, robust state management pattern for the application to replace the current mix of approaches:

**Problem:** Different components use different approaches to state management (React Query direct calls, Zustand, component local state), creating inconsistency and complexity in the codebase.

**Solution:** A unified architecture using Zustand stores with local-first state and eventual sync with the database:

1. **Entity-Centric Stores:** Each entity type (tasks, subtasks, etc.) has its own Zustand store
2. **Local-First:** Changes are applied immediately to the local store for instant UI updates
3. **Background Sync:** Changes are synchronized with the database every 5-10 seconds
4. **Optimistic Updates:** UI updates immediately with rollback mechanisms for failed syncs

**Resources:**
- Design Document: `memory-bank/clarity/state-management-design.md`
- Reference Implementation: `memory-bank/clarity/state-management-example.ts`
- Component Example: `memory-bank/clarity/state-management-component-example.tsx`

**Next Steps:**
1. Implement the Task Store using the new architecture
2. Refactor task-related components (TodayView, TaskDetail) to use the new store
3. Extend the pattern to other entity types

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