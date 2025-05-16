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

**Current State & Last Session Summary (Refer to specific task archives for detailed history of completed items like TodayView Refactor):**

*   **Theming Strategy (Task II.1):** COMPLETED.
*   **Keyboard Navigability (Task II.2 - General Audit & Shell):** COMPLETED.
*   **Drag-and-Drop Task Reordering (Task II.3):** COMPLETED.
*   **Fast Task Entry (Task II.4.1.UI.1):** ARCHIVED (See archive-clarity-ui-todayview-state-refactor-for-4.1.UI.1-and-4.1.UI.3.md)
*   **TaskDetailView (Task II.4.1.UI.2):** COMPLETED.
*   **Enhanced Keyboard Navigation in TodayView (Task II.4.1.UI.3):** ARCHIVED (See archive-clarity-ui-todayview-state-refactor-for-4.1.UI.1-and-4.1.UI.3.md)
*   **Prioritize View Modal (Task II.4.1.UI.5):** In Progress.
*   **Chat Panel (Task II.4.1.UI.8):** COMPLETED.

**Immediate Next Steps for New Session:**

*   **Continue implementation of Prioritize View Modal (Task II.4.1.UI.5)**.
*   **Implement full chat functionality in Chat Panel (Task II.4.1.UI.8)**.
*   **Begin work on Subtask Display & Interaction Logic (Task II.4.1.UI.4)**.


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