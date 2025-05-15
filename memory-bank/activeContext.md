# Active Context

**Overall Goal:** UI/UX Overhaul for Clarity web application, focusing on implementing the Cyclical Flow (Prioritize, Execute, Reflect) and enhancing core usability features like Drag-and-Drop task reordering.

**Current State & Last Session Summary:**

*   **Theming Strategy (Task II.1):** COMPLETE. Radix Themes integrated, semantic Tailwind tokens map to Radix CSS variables. Light/dark mode functional. Key learning: direct Radix scale variables (e.g., `var(--indigo-9)`) were required for button styling in `webApp/src/styles/ui-components.css` due to `--accent-*` alias issues in modals. CSS import paths were also a point of confusion, now resolved.
*   **Keyboard Navigability (Task II.2):** COMPLETE. Major issues addressed:
    *   Button focus visibility and styling in modals (e.g., `AddTaskTray`) fixed.
    *   `SideNav` now supports ArrowUp/ArrowDown key navigation with roving tabindex.
    *   Global tab order corrected to `TopBar` -> `SideNav` -> Main Content via `AppShell.tsx` restructure.
    *   Logo moved from `SideNav` to `TopBar`.
    *   Detailed audit of minor, individual components (`Checkbox`, `ToggleField`) remains, but core interactive elements and shell navigation are functional.

**Immediate Next Steps for New Session (Likely IMPLEMENT mode):**

*   Focus on **Drag-and-Drop Task Reordering (Task II.3 in `tasks.md`)** for the "Today View".
    *   Alternative/Next: Begin **Cyclical Flow Implementation (Task II.4 in `tasks.md`)** starting with data structures or "Today View" enhancements for prioritization.

**Key Relevant Documents for Next Task (Drag-and-Drop or Cyclical Flow):**

*   `memory-bank/tasks.md` (Sections II.3 - Drag-and-Drop, II.4 - Cyclical Flow)
*   `memory-bank/style-guide.md` (For UI consistency)
*   `memory-bank/techContext.md` (Reference `dnd-kit` choice, Core Data Models for tasks/reflections)
*   `memory-bank/productContext.md` (For Core User Journey context)
*   `webApp/src/pages/TodayView.tsx` (Primary target for DnD and Prioritization phase UI)
*   `webApp/src/components/tasks/TaskCard.tsx` (Will be the draggable item)
*   `data/db/ddl.sql` (If persisting reordered task positions or defining new cyclical flow models)
*   `webApp/src/stores/` (Relevant Zustand stores for client-side state management of tasks/DnD)

**Process Reminder from Last Session:**
*   If CSS/style changes are not reflected as expected, explicitly re-verify imported file paths in main application entry points (e.g., `main.tsx`, `AppShell.tsx`) *before* extensive debugging. 