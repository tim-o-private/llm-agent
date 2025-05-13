# UI Implementation Plan

This document outlines the implementation plan for the Clarity web application, following the phased approach defined in the feature roadmap.

**IMPORTANT NOTE ON UI COMPONENT LOCATION (October 2024):** The project is currently undergoing a refactor to merge the `web/packages/ui` library directly into the `web/apps/web` application. Shared UI components will reside in `web/apps/web/src/components/ui/` and their base styles in `web/apps/web/src/styles/ui-components.css`. File paths and statuses in this document are being updated to reflect this change.

## Phase 0: Infrastructure & Foundations (v0.1 Alpha)

### Goal: Set up project infrastructure and core UI components

#### 1. Project Setup
- **Goal:** Initialize the monorepo structure and development environment
- **Files:**
  - `web/pnpm-workspace.yaml`
  - `web/apps/web/package.json`
  - `web/apps/api/package.json`
  - `web/packages/ui/package.json`
- **Key Functionality:**
  - Monorepo configuration ✅
  - Shared package setup ✅
  - Development environment ✅
- **Tech Stack:** pnpm, TypeScript, Vite, ESLint, Prettier
- **AI Assistance Guidance:** Set up base configuration files with proper TypeScript and linting rules
- **Testing:** Verify workspace setup and package dependencies

#### 2. Authentication Foundation
- **Goal:** Implement OAuth authentication flow
- **Files:**
  - `web/apps/web/src/features/auth/`
  - `web/apps/api/src/auth/`
  - `web/packages/ui/src/auth/`
- **Key Functionality:**
  - Supabase auth integration ✅
  - OAuth providers (Google, Apple) ✅
  - Protected routes ✅
  - Auth state management ✅
- **Tech Stack:** Supabase Auth, React Query, Zustand
- **AI Assistance Guidance:** Implement secure token handling and session management
- **Testing:** Auth flow testing, token validation, session persistence

#### 3. Core UI Components
- **Goal:** Build foundational UI components
- **Files:**
  - `web/apps/web/src/components/ui/` (Migrated from `web/packages/ui/src/components/`) ✅
  - `web/apps/web/src/hooks/` (Relevant hooks from `packages/ui` migrated here) ✅
  - `web/apps/web/src/styles/ui-components.css` (Consolidating styles from `web/packages/ui/src/styles/`) ✅
- **Key Functionality:**
  - Design system setup ✅ (TailwindCSS with semantic color tokens defined in `apps/web/tailwind.config.js`)
  - Atomic components (Button, Card, Input, Label, Modal, Spinner) - ✅ Migrated and consolidated
  - Custom hooks (useToggle, useDebounce, useTheme) - ✅ Migrated
  - Theme support (light/dark) ✅ (Basic structure via Tailwind, semantic tokens aid theming, useTheme hook migrated)
- **Tech Stack:** TailwindCSS, Headless UI, Radix UI
- **AI Assistance Guidance:** Create accessible, reusable components following atomic design
- **Testing:** Component unit tests, accessibility testing

#### 4. Layout & Navigation
- **Goal:** Implement core application layout
- **Files:**
  - `web/apps/web/src/layouts/AppShell.tsx` (New for AppShell)
  - `web/apps/web/src/components/navigation/SideNav.tsx` (New for SideNav)
  - `web/apps/web/src/components/navigation/TopBar.tsx` (New for TopBar)
  - `web/apps/web/src/layouts/`
  - `web/apps/web/src/navigation/`
  - `web/apps/web/src/routes/`
- **Key Functionality:**
  - Responsive layout ✅
  - Navigation structure ✅
  - Route configuration ✅
  - Error boundaries ✅
  - **NEW:** Implement `AppShell` as the main application wrapper (left nav, top bar, content area). ✅
  - **NEW:** Implement `SideNav` component with primary navigation links (Today, Focus, Coach, Settings). ✅
  - **NEW:** Implement `TopBar` component (current date, streak, profile/mode). ✅
- **Tech Stack:** React Router, Framer Motion, TailwindCSS
- **AI Assistance Guidance:** Implement responsive layouts with proper navigation patterns. Create the `AppShell`, `SideNav`, and `TopBar` components ensuring they are integrated and manage application states (e.g., current view).
- **Testing:** Layout testing, navigation flow testing, component tests for AppShell, SideNav, TopBar.

### Detailed Implementation Steps for Phase 0, Item 4: Layout & Navigation (New Components)

**Preamble: Context**
This section details the implementation of the core application shell and navigation components. These are foundational for all subsequent page and feature development. They should be designed to be configurable and adaptable for different screen contents and responsive layouts.

--- 

**Sub-Item: Implement `AppShell.tsx` Component**
- **Goal:** Create the main application shell component that orchestrates the overall layout including the side navigation, top bar, and main content area. ✅
- **File(s):** 
  - `web/apps/web/src/layouts/AppShell.tsx` (New)
- **Key Functionality:**
  - Define distinct regions for `SideNav`, `TopBar`, and a main content area (where page components will be rendered).
  - Use CSS (e.g., Flexbox or Grid) for arranging these regions.
  - The main content area should accept children (React components) to render the current page.
  - Ensure the shell is responsive (e.g., `SideNav` might be collapsible or behave differently on smaller screens).
  - Potentially manage global layout states (e.g., if `SideNav` is open/closed on mobile).
- **Tech Stack:** React, TypeScript, TailwindCSS.
- **AI Assistance Guidance:** "Draft `AppShell.tsx`. Use TailwindCSS for a flexbox or grid layout. It should have clearly marked slots or props for `SideNavComponent`, `TopBarComponent`, and `children` (for main content). Implement basic responsiveness for the `SideNav` area (e.g., hidden on small screens, toggleable)."
- **Testing:** 
  - Unit test `AppShell.tsx` to ensure it renders its main regions and children correctly.
  - Test responsiveness with different viewport sizes (e.g., using browser dev tools).
  - Visual verification of the layout structure.

--- 

**Sub-Item: Implement `SideNav.tsx` Component**
- **Goal:** Create the primary side navigation component with links to different sections of the application. ✅
- **File(s):** 
  - `web/apps/web/src/components/navigation/SideNav.tsx` (New)
  - (Potentially a configuration file for navigation links, e.g., `web/apps/web/src/navigation/navConfig.ts`)
- **Key Functionality:**
  - Display a list of navigation items (e.g., "Today", "Focus", "Coach", "Settings") with icons and text.
  - Use `NavLink` (from React Router) or similar for client-side navigation, highlighting the active route.
  - Fetch navigation items from a configuration array/object for easy management.
  - Style for vertical layout, clear visual hierarchy, and accessibility.
  - Handle responsive behavior (e.g., full display on larger screens, icon-only or collapsed on smaller screens if `AppShell` dictates).
- **Tech Stack:** React, TypeScript, TailwindCSS, React Router (`NavLink`).
- **AI Assistance Guidance:** "Create `SideNav.tsx`. Define a `navItems` array (e.g., `[{ path: '/today', label: 'Today', icon: <SomeIcon /> }]`). Map this array to `NavLink` components. Style the navigation links, including active states. Consider how it will receive props or context from `AppShell` regarding its display state (e.g., collapsed/expanded)."
- **Testing:** 
  - Unit test `SideNav.tsx` for rendering navigation items and active link highlighting.
  - Test navigation to different routes by clicking links.
  - Test responsiveness if applicable (e.g., collapsed state).

--- 

**Sub-Item: Implement `TopBar.tsx` Component**
- **Goal:** Create the top bar component to display contextual information like the current date, user streak, and potentially profile/mode indicators. ✅
- **File(s):** 
  - `web/apps/web/src/components/navigation/TopBar.tsx` (New)
  - (May integrate `UserMenu.tsx` if that component is intended for the top bar profile section)
- **Key Functionality:**
  - Display the current date (e.g., formatted string).
  - Placeholder for a "streak progress" indicator (functionality to be added later).
  - Placeholder or integration point for a user profile menu/avatar (potentially using the existing `UserMenu.tsx`).
  - Optional area for a mode indicator if the application has different modes (e.g., "Focus Mode Active" - though this might also be part of the `FocusHeader` specifically).
  - Style for horizontal layout, clear information display.
- **Tech Stack:** React, TypeScript, TailwindCSS, `date-fns` (or similar for date formatting).
- **AI Assistance Guidance:** "Create `TopBar.tsx`. Add elements to display the current date (use `new Date().toLocaleDateString()`). Add placeholder divs for 'Streak Progress' and 'User Menu'. Style it as a horizontal bar with items spaced appropriately."
- **Testing:** 
  - Unit test `TopBar.tsx` for rendering date and placeholder elements.
  - Verify correct date display and formatting.
  - Visual verification of layout.

--- 

**Sub-Item: Integrate `AppShell`, `SideNav`, and `TopBar`**
- **Goal:** Ensure the `AppShell` correctly incorporates and renders `SideNav` and `TopBar`, and that the main application routing uses `AppShell` to wrap page content. ✅
- **File(s):** 
  - `web/apps/web/src/layouts/AppShell.tsx`
  - `web/apps/web/src/App.tsx` (or your main application component where routing is set up)
  - `web/apps/web/src/routes/index.tsx` (or wherever your main routes are defined)
- **Key Functionality:**
  - Modify `AppShell.tsx` to import and render `SideNav` and `TopBar` components in their designated regions.
  - Update the main application component (`App.tsx` or similar) so that routes rendering page-level components are wrapped by `AppShell`. For example, a route for `/today` would render `<AppShell><TodayViewPage /></AppShell>` or `AppShell` would be part of a layout route.
  - Ensure props or context are passed appropriately if `AppShell` needs to control aspects of `SideNav` or `TopBar` (e.g., mobile navigation toggle).
- **Tech Stack:** React, TypeScript, TailwindCSS, React Router.
- **AI Assistance Guidance:** "Modify `AppShell.tsx` to import and place `SideNav` and `TopBar` components. In `App.tsx` (or main router setup), ensure that page routes are rendered as children of `AppShell`."
- **Testing:** 
  - Manually navigate through the application (once pages like `TodayView.tsx` are placeholders or exist) to verify `AppShell`, `SideNav`, and `TopBar` are consistently present and functional.
  - Test any interaction between `AppShell` and its navigation children (e.g., mobile menu toggle).

#### 5. Specialized Shared UI Components (NEW SECTION)
- **Goal:** Develop more specialized, reusable UI components based on `uiComponents.md`.
- **Status:** ✅ Completed & Migrated
- **Files:**
  - `web/apps/web/src/components/ui/TaskCard.tsx` ✅ (Migrated)
  - `web/apps/web/src/components/ui/TaskStatusBadge.tsx` ✅ (Migrated)
  - `web/apps/web/src/components/ui/ToggleField.tsx` ✅ (Migrated)
  - `web/apps/web/src/components/ui/FAB.tsx` ✅ (Migrated)
- **Key Functionality:**
  - `TaskCard`: Display task details (checkbox, time, title, category). ✅ (Implemented, reviewed, migrated)
  - `TaskStatusBadge`: Inline badge for task status. ✅ (Implemented, reviewed, migrated)
  - `ToggleField`: Generic toggle for settings. ✅ (Implemented using Headless UI, reviewed, migrated)
  - `FAB`: Reusable floating action button. ✅ (Implemented, reviewed, fixed positioning, migrated)
- **Tech Stack:** TailwindCSS, Headless UI / Radix UI (if applicable for accessibility)
- **AI Assistance Guidance:** Create these components with variants and states as needed. Ensure they are easily themeable and composable.
- **Testing:** Unit tests for each component, covering different props and states. Visual regression testing.

### Detailed Implementation Steps for Phase 0, Item 5: Specialized Shared UI Components

**Preamble: Context**
These components are more specialized than basic atomic components but are intended for reuse across different features (e.g., `TaskCard` in Today View, Done List; `ToggleField` in Settings). They should be designed with clear props and a focus on reusability. They will reside in `web/packages/ui/src/components/`.

--- 

**Sub-Item: Implement `TaskCard.tsx` Component**
- **Goal:** Create a reusable card component to display task information. ✅ (Implemented, reviewed, migrating)
- **File(s):**
  - `web/apps/web/src/components/ui/TaskCard.tsx` (Migrating from `web/packages/ui/src/components/TaskCard.tsx`)
- **Key Functionality:**
  - Accept props for task details: `id` (string), `title` (string), `time` (optional string, e.g., "10:00 AM" or "2h"), `category` (optional string), `completed` (boolean).
  - Display a checkbox (state controlled by `completed` prop and an `onToggleComplete` callback prop).
  - Display task title, time, and category pill/tag if provided.
  - Style differently based on the `completed` state (e.g., strikethrough title, faded appearance).
  - Use the generic `Card.tsx` from Phase 0, Item 3 as a base or inspiration for the outer container if suitable.
- **Tech Stack:** React, TypeScript, TailwindCSS.
- **AI Assistance Guidance:** "Draft `TaskCard.tsx`. Define props for task details (id, title, time, category, completed, onToggleComplete). Implement a checkbox and display other task information. Apply conditional styling for completed tasks. Use TailwindCSS for styling."
- **Testing:** 
  - Unit test `TaskCard.tsx` with various prop combinations (e.g., with/without time/category, completed/incomplete).
  - Test checkbox interaction and `onToggleComplete` callback.
  - Visual verification of different states.

--- 

**Sub-Item: Implement `TaskStatusBadge.tsx` Component**
- **Goal:** Create a small, inline badge to display task status (e.g., Upcoming, In Progress, Completed, Skipped). ✅ (Implemented, reviewed, migrating)
- **File(s):**
  - `web/apps/web/src/components/ui/TaskStatusBadge.tsx` (Migrating from `web/packages/ui/src/components/TaskStatusBadge.tsx`)
- **Key Functionality:**
  - Accept a `status` prop (e.g., an enum or string like 'upcoming', 'in-progress', 'completed', 'skipped').
  - Display the status text.
  - Apply different background colors/styles based on the status (e.g., blue for upcoming, green for completed, gray for skipped).
- **Tech Stack:** React, TypeScript, TailwindCSS.
- **AI Assistance Guidance:** "Create `TaskStatusBadge.tsx`. It should take a `status` prop. Use a switch statement or object mapping to determine the text and TailwindCSS classes for different statuses. Ensure good color contrast and readability."
- **Testing:** 
  - Unit test `TaskStatusBadge.tsx` for rendering different statuses with correct styles and text.
  - Visual verification of badge appearance for all statuses.

--- 

**Sub-Item: Implement `ToggleField.tsx` Component (Generic Toggle)**
- **Goal:** Create a reusable, accessible toggle switch component for settings or boolean preferences. ✅ (Implemented using Headless UI, reviewed, migrating)
- **File(s):**
  - `web/apps/web/src/components/ui/ToggleField.tsx` (Migrating from `web/packages/ui/src/components/ToggleField.tsx`)
- **Key Functionality:**
  - Accept props for `label` (string), `checked` (boolean), `onChange` (callback function), `disabled` (optional boolean).
  - Render a label and a visually distinct toggle switch.
  - Ensure accessibility (e.g., using appropriate ARIA attributes, keyboard navigable).
  - Consider using a headless UI library (like Headless UI Switch or Radix UI Switch) as a base for accessibility and state management, then style with TailwindCSS.
  - This should be more generic than the existing `ThemeToggle.tsx` if that component is very specific to theme switching.
- **Tech Stack:** React, TypeScript, TailwindCSS, Headless UI or Radix UI (recommended for switch primitive).
- **AI Assistance Guidance:** "Draft `ToggleField.tsx`. Use Headless UI Switch or Radix UI Switch as a base. Implement the label, checked state, onChange handler, and disabled state. Style the switch with TailwindCSS to look like a modern toggle."
- **Testing:** 
  - Unit test `ToggleField.tsx` for state changes, callback invocation, and disabled state.
  - Accessibility testing (keyboard navigation, screen reader compatibility).
  - Visual verification.

--- 

**Sub-Item: Implement `FAB.tsx` Component (Floating Action Button Base)**
- **Goal:** Create a generic, reusable Floating Action Button component. ✅ (Implemented, reviewed, positioning fixed, migrating)
- **File(s):**
  - `web/apps/web/src/components/ui/FAB.tsx` (Migrating from `web/packages/ui/src/components/FAB.tsx`)
- **Key Functionality:**
  - Accept props for `onClick` (callback), `icon` (ReactNode), `aria-label` (string), `tooltip` (optional string), `position` (optional, e.g., 'bottom-right', defaults to bottom-right).
  - Render a circular button, typically with an icon, styled to float above other content.
  - Apply fixed positioning based on the `position` prop.
  - Display a tooltip on hover if provided.
- **Tech Stack:** React, TypeScript, TailwindCSS.
- **AI Assistance Guidance:** "Create `FAB.tsx`. It should be a button styled to be circular and elevated (shadow). Accept an `icon` prop. Implement basic fixed positioning (e.g., `fixed bottom-4 right-4`). Handle the `onClick` event."
- **Testing:** 
  - Unit test `FAB.tsx` for rendering, icon display, and click handling.
  - Visual verification of appearance and positioning.
  - Tooltip display if implemented.

## Phase 0.5: Core Task Management UI (NEW PHASE)

### Goal: Implement the primary task viewing and management interface ("Today View")

#### 1. Today View Page (Replaces/Evolves `Dashboard.tsx`)
- **Goal:** Build the main "Today View" screen for daily task management. (Corresponds to `uiPages.md` Issue 1)
- **Files:**
  - `web/apps/web/src/pages/TodayView.tsx` (New or evolves `Dashboard.tsx`)
  - `web/apps/web/src/components/tasks/TaskListGroup.tsx` (New)
- **Key Functionality:**
  - Display tasks segmented by time blocks (Morning, Afternoon, Evening) using `AppShell`.
  - Use `TaskListGroup` component to hold `TaskCard`s for each time block.
  - Integrate `FABQuickAdd` for new task entry.
  - Show empty state prompts if no tasks.
  - Display `CoachCard` (placeholder initially, to be connected in Phase 1).
- **Tech Stack:** React, TypeScript, TailwindCSS, Zustand (for state if needed)
- **AI Assistance Guidance:** Structure the `TodayView.tsx` page, integrate `AppShell`, `SideNav`, `TopBar`. Develop `TaskListGroup` to render `TaskCard`s. Manage task data fetching and state.
- **Testing:** Page-level tests, integration of child components, task rendering, empty state.

#### 2. Add Task Tray (Quick + Detailed View)
- **Goal:** Implement the quick and detailed task addition flow. (Corresponds to `uiPages.md` Issue 2)
- **Files:**
  - `web/apps/web/src/components/tasks/FABQuickAdd.tsx`
  - `web/apps/web/src/components/tasks/QuickAddTray.tsx`
  - `web/apps/web/src/components/tasks/TaskDetailTray.tsx` (Could use shared `Modal` as a base)
- **Key Functionality:**
  - `FABQuickAdd`: Expands to show `QuickAddTray`. ✅ (Implemented, uses FAB base component)
  - `QuickAddTray`: Inline form for task name, time, priority, reminders. ✅ (Implemented, basic animation added)
  - `TaskDetailTray`: Expanded form for more task details (potentially reusing fields from `QuickAddTray`). ✅ (Implemented, wired up)
  - Adherence to `OpenedFAB.pdf` mockup.
- **Tech Stack:** React, TypeScript, TailwindCSS, Framer Motion (for animations), Zustand (for form state). (Note: `packages/ui` dependencies will become direct imports from `web/apps/web/src/components/ui/` after merge)
- **AI Assistance Guidance:** Develop the three components. Manage form state and submission. Implement transitions for FAB expansion. Ensure `Modal` component from `packages/ui` is leveraged if suitable for `TaskDetailTray`.
- **Testing:** Component tests for FAB, QuickAddTray, TaskDetailTray. Form validation and submission testing. Animation testing.

#### 3. Chat Interface
- **Goal:** Build the AI coaching chat interface. (Corresponds to `uiPages.md` Issue 6)
- **Files:**
  - `web/apps/web/src/components/ChatPanel.tsx` (Existing - needs integration)
  - `web/apps/web/src/pages/CoachPage.tsx` (New - to host ChatPanel within AppShell)
  - `web/packages/ui/src/components/chat/MessageHeader.tsx` (New) -> `web/apps/web/src/components/ui/chat/MessageHeader.tsx`
  - `web/packages/ui/src/components/chat/MessageBubble.tsx` (New) -> `web/apps/web/src/components/ui/chat/MessageBubble.tsx`
  - `web/packages/ui/src/components/chat/MessageInput.tsx` (New - specialized from `packages/ui/src/components/Input.tsx`) -> `web/apps/web/src/components/ui/chat/MessageInput.tsx`
  - `web/packages/ui/src/components/CoachCard.tsx` (New - for summarized suggestions, potentially used on Today View too) -> `web/apps/web/src/components/ui/CoachCard.tsx`
  - `web/apps/web/src/stores/useChatStore.ts` (Existing)
  - `web/apps/api/main.py` (Existing)
- **Key Functionality:**
  - Chat UI components: ✅ (`ChatPanel.tsx` base exists)
  - **NEW:** Create `CoachPage.tsx` to embed `ChatPanel.tsx` within the `AppShell`.
  - **NEW:** Develop `MessageHeader`, `MessageBubble`, and `MessageInput` as reusable components for the chat interface.
  - **NEW:** Develop `CoachCard` component for brief AI suggestions.
  - Message handling (display & local state): ✅
  - Backend API for chat: ✅
  - Frontend to Backend API connection: ✅
  - Real-time updates via LLM: ✅
  - Message persistence: ✅
  - Future Refinement: (Existing)
- **Tech Stack:** React Query, Zustand, FastAPI, WebSocket (Future), Supabase (Future for memory/prompts), TailwindCSS
- **AI Assistance Guidance:** Implement the new sub-components (`MessageHeader`, `MessageBubble`, `MessageInput`, `CoachCard`). Integrate `ChatPanel` into `CoachPage` with `AppShell`. Ensure chat state management is robust.
- **Testing:** Chat flow testing, message persistence, component tests for new chat sub-components.

#### 4. Focus Mode Screen & Components (Combines Focus Timer & Focus View, Corresponds to `uiPages.md` Issue 3)
- **Goal:** Build the task execution view (Focus Mode) with integrated timer.
- **Files:**
  - `web/apps/web/src/pages/FocusModeScreen.tsx` (New)
  - `web/packages/ui/src/components/timer/FocusTimer.tsx` (Evolves from `web/packages/ui/src/timer/`) -> `web/apps/web/src/components/ui/timer/FocusTimer.tsx`
  - `web/apps/web/src/components/focus/FocusHeader.tsx` (New)
  - `web/apps/web/src/components/focus/ScratchPadToggle.tsx` (New)
- **Key Functionality:**
  - `FocusModeScreen`: Page to host the focus session, using `AppShell` or a fullscreen override.
  - `FocusHeader`: Displays task name and category.
  - `FocusTimer`: Circular timer with countdown, play/pause, complete button (visual and functional).
  - `ScratchPadToggle`: Button to open the `ScratchOverlay`.
  - Session tracking and break management (from existing Focus Timer plan).
- **Tech Stack:** React Query, Zustand, Framer Motion, TailwindCSS
- **AI Assistance Guidance:** Develop `FocusModeScreen.tsx`. Implement the interactive `FocusTimer.tsx` UI and logic. Create `FocusHeader.tsx` and `ScratchPadToggle.tsx`. Manage focus session state.
- **Testing:** Timer accuracy, session tracking, UI interactions for play/pause/complete. `ScratchPadToggle` functionality.

#### 5. Scratch Pad / Brain Dump (Corresponds to `uiPages.md` Issue 4)
- **Goal:** Implement quick capture system (Scratch Pad).
- **Files:**
  - `web/apps/web/src/components/capture/ScratchOverlay.tsx` (New - likely modal/drawer)
  - `web/packages/ui/src/components/capture/ScratchEntryCard.tsx` (New - could use shared `Card` as base) -> `web/apps/web/src/components/ui/capture/ScratchEntryCard.tsx`
  - `web/apps/web/src/features/capture/` (Potentially for state logic if not in component store)
- **Key Functionality:**
  - `ScratchOverlay`: Modal or drawer for capturing thoughts.
  - `ScratchEntryCard`: Displays a single entry with timestamp, edit, convert-to-task, archive buttons.
  - Input box and log of past entries.
  - Auto-saves to local cache/state.
- **Tech Stack:** React Query, Web Speech API (optional voice input), TailwindCSS, Zustand
- **AI Assistance Guidance:** Implement `ScratchOverlay` and `ScratchEntryCard`. Manage state for entries, including local persistence.
- **Testing:** Entry testing, voice recognition (if implemented), convert-to-task/archive functionality.

### Detailed Implementation Steps for Phase 0.5

**Preamble: Prerequisites from Phase 0**

Successful implementation of Phase 0.5 assumes the following components from Phase 0 are substantially complete and available for integration:
- Core Layout: `AppShell.tsx`, `SideNav.tsx`, `TopBar.tsx` (from Phase 0, Item 4).
- Specialized Shared Components: `TaskCard.tsx`, `FAB.tsx` (generic base) (from Phase 0, Item 5).
- Atomic Components: `Modal.tsx`, `Input.tsx`, `Button.tsx`, `Label.tsx` (from Phase 0, Item 3).

--- 

**Item 1: Today View Page (Corresponds to `uiPages.md` Issue 1)**

**Step 1.1: Implement `TaskListGroup.tsx` Component**
- **Goal:** Create a component to group tasks for a specific time block (e.g., Morning, Afternoon, Evening) and display them. ✅
- **File(s):** 
  - `web/apps/web/src/components/tasks/TaskListGroup.tsx` (New)
- **Key Functionality:**
  - Accept a title (e.g., "Morning") and a list of task data objects as props.
  - Render the title.
  - Iterate over the task data and render a `TaskCard.tsx` for each task.
  - If no tasks are provided for the group, display an appropriate message or render nothing for that section (to be decided by parent `TodayView.tsx` based on overall empty state).
- **Tech Stack:** React, TypeScript, TailwindCSS.
- **AI Assistance Guidance:** "Draft the `TaskListGroup.tsx` component. It should take `title: string` and `tasks: Task[]` (define a basic `Task` interface placeholder if not globally available yet, e.g., `{ id: string; title: string; time?: string; category?: string; completed: boolean }`) as props. Map `tasks` to `TaskCard` components. Style the group container and title."
- **Testing:** 
  - Unit test `TaskListGroup.tsx` to ensure it renders the title and the correct number of `TaskCard`s based on input. Test with zero tasks.

**Step 1.2: `TodayView.tsx` - Initial Structure and Layout Integration**
- **Goal:** Create the main page component for the Today View, integrate the core application layout, and set up placeholders for task list groups. ✅
- **File(s):** 
  - `web/apps/web/src/pages/TodayView.tsx` (New, or refactor `Dashboard.tsx`)
  - `web/apps/web/src/routes/` (Update to include route for `/today` or `/`)
- **Key Functionality:**
  - If evolving `Dashboard.tsx`, rename and restructure. Otherwise, create new `TodayView.tsx`.
  - Integrate `AppShell.tsx` to provide the main layout (including `SideNav` and `TopBar`).
  - Structure the main content area to hold three instances of `TaskListGroup.tsx` (for Morning, Afternoon, Evening sections).
  - Pass appropriate titles to each `TaskListGroup`.
  - (Initially, task data can be mocked or empty).
- **Tech Stack:** React, TypeScript, TailwindCSS, React Router.
- **AI Assistance Guidance:** "Create or refactor `TodayView.tsx`. Wrap its content with `AppShell`. Add three `TaskListGroup` instances with titles 'Morning', 'Afternoon', 'Evening'. Ensure basic styling for the page content area."
- **Testing:** 
  - Manually verify the page renders within the `AppShell` with the three `TaskListGroup` placeholders/titles.
  - Test routing to the `TodayView` page.

**Step 1.3: `TodayView.tsx` - Task Data Fetching/Rendering and Empty State Logic**
- **Goal:** Implement logic to fetch (or use mocked) task data and pass it to `TaskListGroup` components, and handle the overall empty state for the page. ✅
- **File(s):** 
  - `web/apps/web/src/pages/TodayView.tsx`
  - (Potentially a new store or hook for task data management e.g., `web/apps/web/src/stores/useTaskStore.ts` or `web/apps/web/src/hooks/useTasks.ts`)
- **Key Functionality:**
  - Define a state management solution for tasks (e.g., Zustand store, React Context, or local state for now).
  - Fetch or initialize mocked task data, categorized by time blocks (Morning, Afternoon, Evening).
  - Pass the filtered task lists to the respective `TaskListGroup` components.
  - Implement logic to display a prominent message or a specific UI if there are no tasks at all for any time block (e.g., "Plan your day!").
- **Tech Stack:** React, TypeScript, TailwindCSS, Zustand (or chosen state management).
- **AI Assistance Guidance:** "In `TodayView.tsx`, set up state for tasks (e.g., using `useState` with a more complex object or a simple Zustand store). Create mock data for tasks, assigning them to 'Morning', 'Afternoon', or 'Evening'. Filter and pass this data to the `TaskListGroup` instances. Implement the page-level empty state."
- **Testing:** 
  - Verify tasks render correctly within their groups.
  - Test the overall empty state when no tasks are present.
  - Test adding/removing mock tasks to see UI updates (if state management allows this interactively).

**Step 1.4: `TodayView.tsx` - Integrate Placeholders for `FABQuickAdd` and `CoachCard`**
- **Goal:** Add placeholders where `FABQuickAdd.tsx` and `CoachCard.tsx` will be integrated later. ✅ (FABQuickAdd integrated)
- **File(s):** 
  - `web/apps/web/src/pages/TodayView.tsx`
- **Key Functionality:**
  - Add a placeholder element (e.g., a simple styled `div` or a comment) for the `FABQuickAdd` component, typically fixed to the bottom-right of the screen.
  - Add a placeholder element for the `CoachCard` component, likely in a sidebar or a designated area on the page as per mockups.
- **Tech Stack:** React, TypeScript, TailwindCSS.
- **AI Assistance Guidance:** "In `TodayView.tsx`, add a `div` styled to be a bottom-right fixed circle as a placeholder for `FABQuickAdd`. Add another `div` as a placeholder for `CoachCard` in the appropriate layout position."
- **Testing:** 
  - Manually verify the placeholders appear in the correct locations.

--- 

**Item 2: Add Task Tray (Corresponds to `uiPages.md` Issue 2)**

**Step 2.1: Implement `FABQuickAdd.tsx` Component**
- **Goal:** Create the Floating Action Button that triggers the task creation UI. ✅ (Implemented, uses FAB base component)
- **File(s):**
  - `web/apps/web/src/components/tasks/FABQuickAdd.tsx`
- **Key Functionality:**
  - Use the generic `FAB.tsx` component from Phase 0 (Item 5) as its base or inspiration.
  - Display an icon (e.g., plus sign).
  - Handle click events to eventually toggle the visibility of `QuickAddTray.tsx`.
  - (Initial implementation might just log to console on click).
- **Tech Stack:** React, TypeScript, TailwindCSS.
- **AI Assistance Guidance:** "Create `FABQuickAdd.tsx`. It should render a button (possibly using a base `FAB.tsx` if available, or style a button directly) with a '+' icon. On click, for now, it can log a message. Position it fixed to the bottom-right."
- **Testing:** 
  - Unit test `FABQuickAdd.tsx` for rendering and click handling.
  - Integrate into `TodayView.tsx` (replacing placeholder) and verify its position and click behavior.

**Step 2.2: Implement `QuickAddTray.tsx` Component (Inline Form)**
- **Goal:** Create the tray/inline form for quickly adding a task. ✅ (Implemented, basic animation added)
- **File(s):**
  - `web/apps/web/src/components/tasks/QuickAddTray.tsx`
- **Key Functionality:**
  - A form with essential input fields: Task Name (text input), Time Period (dropdown/select: Morning, Afternoon, Evening), potentially Priority (dropdown/select), and an "Add Task" button.
  - Initially hidden, shown when `FABQuickAdd` is activated.
  - Manage internal form state (e.g., using local component state or a form library).
  - On submit, it should eventually dispatch an action to add a task (for now, can log form data).
  - Include a "Cancel" button or way to close the tray.
- **Tech Stack:** React, TypeScript, TailwindCSS, (Formik/React Hook Form optional, or Zustand for state).
- **AI Assistance Guidance:** "Create `QuickAddTray.tsx`. Design a form with `Input` for task name, a `select` for Time Period. Add 'Add Task' and 'Cancel' `Button`s. Manage form input values using `useState`. Style it as an overlay or a panel that appears near the FAB or bottom of the screen."
- **Testing:** 
  - Unit test `QuickAddTray.tsx` for form element rendering, input changes, and button clicks.
  - Test form data capture.

**Step 2.3: Implement `TaskDetailTray.tsx` Component (Expanded Form)**
- **Goal:** Create an expanded tray/modal for adding/editing more task details. ✅ (Implemented and wired up)
- **File(s):**
  - `web/apps/web/src/components/tasks/TaskDetailTray.tsx`
- **Key Functionality:**
  - Can be triggered from `QuickAddTray` (e.g., an "Add details" button) or when editing an existing task.
  - Includes more fields than `QuickAddTray`: reminders, notes, subtasks (if planned), etc. It should contain all fields from `QuickAddTray` plus additional ones.
  - Use the shared `Modal.tsx` component from Phase 0 (Item 3) as a base for its presentation if it's a modal.
  - Manage form state for all fields.
  - "Save" and "Cancel" buttons.
- **Tech Stack:** React, TypeScript, TailwindCSS, (Formik/React Hook Form optional, or Zustand for state).
- **AI Assistance Guidance:** "Create `TaskDetailTray.tsx`. Use `Modal.tsx` as the base if it's a modal. Include fields from `QuickAddTray` plus a textarea for notes. Manage its visibility and form state. Implement 'Save' and 'Cancel' buttons."
- **Testing:** 
  - Unit test `TaskDetailTray.tsx` for rendering all form fields and interactions.
  - Test integration with `Modal.tsx` if used.

**Step 2.4: Integrate `FABQuickAdd`, `QuickAddTray`, and `TaskDetailTray` Functionality**
- **Goal:** Connect the components so the FAB opens the QuickAddTray, and potentially QuickAddTray can open TaskDetailTray. Implement basic task addition logic. ✅ (Functionality implemented, basic animations working. Framer-motion added. Resolved multiple React instances. Title validation for opening details removed from QuickAddTray)
- **File(s):**
  - `web/apps/web/src/pages/TodayView.tsx` (to manage visibility state)
  - `web/apps/web/src/components/tasks/FABQuickAdd.tsx`
  - `web/apps/web/src/components/tasks/QuickAddTray.tsx`
  - `web/apps/web/src/components/tasks/TaskDetailTray.tsx`
  - Task state management solution (e.g., `useTaskStore.ts`)
- **Key Functionality:**
  - Clicking `FABQuickAdd` toggles the visibility of `QuickAddTray`.
  - Submitting `QuickAddTray` adds a new task to the state (which should update `TodayView.tsx`) and hides the tray.
  - Cancelling `QuickAddTray` hides it.
  - (Optional for this phase, can be deferred) Implement a way to open `TaskDetailTray` from `QuickAddTray` (e.g., an "Add more details" button that passes current QuickAdd data to DetailTray).
  - Ensure visual adherence to `OpenedFAB.pdf` for transitions and appearance.
- **Tech Stack:** React, TypeScript, TailwindCSS, Framer Motion (for animations), Zustand (or chosen state management).
- **AI Assistance Guidance:** "Modify `TodayView.tsx` to manage the visibility state of `QuickAddTray` and `TaskDetailTray`. Update `FABQuickAdd.tsx` to call the state update function. In `QuickAddTray.tsx`, on submit, call the task store's addTask action and then hide the tray. Implement opening/closing animations using Framer Motion if desired."
- **Testing:** 
  - Full end-to-end manual test: Click FAB -> QuickAddTray appears -> Fill form -> Submit -> Task appears in TodayView, tray hides.
  - Test cancel functionality.
  - Test animations and visual appearance against `OpenedFAB.pdf`.

## Phase 1: AI Coaching & Integrations (v0.2 Beta)

### Goal: Implement AI coaching interface and initial integrations

#### 2. Nudge System
- **Goal:** Implement AI-driven nudge system
- **Files:**
  - `web/apps/web/src/features/nudges/`
  - `web/apps/api/src/nudges/`
  - `web/packages/ui/src/nudges/`
- **Key Functionality:**
  - Nudge triggers
  - Notification system
  - Nudge preferences
  - Timing logic
- **Tech Stack:** React Query, Zustand, date-fns
- **AI Assistance Guidance:** Implement notification system with proper timing
- **Testing:** Nudge trigger testing, notification delivery

#### 3. Google Calendar Integration
- **Goal:** Add Google Calendar sync
- **Files:**
  - `web/apps/web/src/features/calendar/`
  - `web/apps/api/src/calendar/`
  - `web/packages/ui/src/calendar/`
- **Key Functionality:**
  - Calendar sync
  - Event management
  - Two-way updates
  - Conflict resolution
- **Tech Stack:** Google Calendar API, React Query
- **AI Assistance Guidance:** Implement calendar sync with proper error handling
- **Testing:** Sync testing, conflict resolution

#### 4. Google Docs Integration
- **Goal:** Add Google Docs linking
- **Files:**
  - `web/apps/web/src/features/docs/`
  - `web/apps/api/src/docs/`
  - `web/packages/ui/src/docs/`
- **Key Functionality:**
  - Doc linking
  - Preview system
  - Permission handling
  - Quick access
- **Tech Stack:** Google Docs API, React Query
- **AI Assistance Guidance:** Implement doc linking with proper permissions
- **Testing:** Link testing, preview testing

## Phase 2: Smart Productivity Layer (v0.3 Beta)

### Goal: Implement focus and productivity features

#### 3. Reflection Modal & Components (Corresponds to `uiPages.md` Issue 5)
- **Goal:** Build the post-session or end-of-day Reflection Modal.
- **Files:**
  - `web/apps/web/src/components/reflection/ReflectionModal.tsx` (New - uses `packages/ui/Modal.tsx` as base)
  - `web/packages/ui/src/components/MoodPicker.tsx` (New) -> `web/apps/web/src/components/ui/reflection/MoodPicker.tsx`
  - `web/packages/ui/src/components/TaskOutcomeSelector.tsx` (New - uses `packages/ui/Button.tsx`) -> `web/apps/web/src/components/ui/reflection/TaskOutcomeSelector.tsx`
- **Key Functionality:**
  - `ReflectionModal`: Triggered after session or EOD, prompts for feedback.
  - `MoodPicker`: Emoji or word-based mood selection.
  - `TaskOutcomeSelector`: Buttons for "Completed," "Worked on it," "Skipped."
- **Tech Stack:** React, TypeScript, TailwindCSS, Zustand
- **AI Assistance Guidance:** Develop `ReflectionModal.tsx`, `MoodPicker.tsx`, and `TaskOutcomeSelector.tsx`. Manage state for reflection inputs.
- **Testing:** Modal triggering, input selections, data capture.

#### 4. Focus View (Existing - Covered by Focus Mode Screen)
- **Goal:** Create distraction-free mode
- **Files:**
  - `web/apps/web/src/features/focus/`
  - `web/packages/ui/src/focus/` -> `web/apps/web/src/components/ui/focus/`
- **Key Functionality:**
  - Mode switching (Covered by `FocusModeScreen.tsx`)
  - UI simplification (Covered by `FocusModeScreen.tsx`)
  - Progress tracking (Covered by `FocusModeScreen.tsx` & `FocusTimer.tsx`)
  - Quick actions (Potentially in `FocusModeScreen.tsx`)
- **Tech Stack:** React Query, Zustand, Framer Motion
- **AI Assistance Guidance:** (Covered by `FocusModeScreen.tsx` AI assistance)
- **Testing:** (Covered by `FocusModeScreen.tsx` testing)
- **Note:** This item is largely covered by the new "Focus Mode Screen & Components" item. Ensure all its original KFs are met there.

#### 5. Gamification (Existing - to be expanded)
- **Goal:** Add basic reward system.
- **Files:**
  - `web/apps/web/src/features/gamification/` (New or existing)
  - `web/packages/ui/src/components/gamification/StreakCounter.tsx` (New - for `uiPages.md` Issue 8) -> `web/apps/web/src/components/ui/gamification/StreakCounter.tsx`
- **Key Functionality:**
  - (Existing KFs for Gamification)
  - **NEW:** `StreakCounter` component to display user's current streak (integrates with Done List).
- **Tech Stack:** (Existing + TailwindCSS for new component)
- **AI Assistance Guidance:** (Existing + Develop `StreakCounter.tsx`)
- **Testing:** (Existing + Test `StreakCounter` display and updates)

## Phase 3: Application Polish & Configuration (NEW PHASE)

### Goal: Implement settings, history views, and polish the application.

#### 1. Settings Screen & Components (Corresponds to `uiPages.md` Issue 7)
- **Goal:** Create a user settings screen.
- **Files:**
  - `web/apps/web/src/pages/SettingsScreen.tsx` (New)
  - `web/apps/web/src/components/settings/SettingsPage.tsx` (New - main component for the screen)
  - `web/packages/ui/src/components/settings/TimeBlockEditor.tsx` (New) -> `web/apps/web/src/components/ui/settings/TimeBlockEditor.tsx`
- **Key Functionality:**
  - `SettingsScreen.tsx`: Page to host settings, using `AppShell`.
  - `SettingsPage.tsx`: Component containing different setting sections (tone, structure, reminders, data).
  - `TimeBlockEditor`: UI to manage custom time blocks.
  - `ToggleField` for various preferences.
  - Data export/delete options.
- **Tech Stack:** React, TypeScript, TailwindCSS, Zustand (for settings state)
- **AI Assistance Guidance:** Develop `SettingsScreen.tsx` and `SettingsPage.tsx`. Implement `TimeBlockEditor.tsx`. Manage settings state and persistence.
- **Testing:** Settings changes, persistence, data export/delete functionality (if implemented).

#### 2. Done List (Task History View) (Corresponds to `uiPages.md` Issue 8)
- **Goal:** Create a historical view of completed tasks.
- **Files:**
  - `web/apps/web/src/pages/DoneListScreen.tsx` (New)
  - (Uses `TaskCard` with 'completed' state - from Phase 0.5)
  - (Uses `StreakCounter.tsx` - from Phase 2)
- **Key Functionality:**
  - `DoneListScreen.tsx`: Page to display task history, using `AppShell`.
  - Shows tasks grouped by date or streak.
  - Uses `TaskCard` (completed state).
  - Integrates `StreakCounter`.
  - Link to past reflections (if applicable).
- **Tech Stack:** React, TypeScript, TailwindCSS, Zustand (for fetching/filtering history)
- **AI Assistance Guidance:** Develop `DoneListScreen.tsx`. Implement logic for fetching and displaying task history. Ensure `TaskCard` correctly displays completed state.
- **Testing:** History display, filtering/grouping, integration of `StreakCounter`.

## Refactor: Merging `packages/ui` into `apps/web`

**Goal:** Simplify the project structure and development workflow by consolidating the `packages/ui` library directly into the `apps/web` application. Shared UI components will reside in `web/apps/web/src/components/ui/` and their base styles in `web/apps/web/src/styles/ui-components.css`. ✅ **COMPLETED**

**Steps:**

1.  **Move Component Files:** ✅ **COMPLETED**
    *   Physically move all remaining component files from `web/packages/ui/src/components/` (and any related files like hooks from `web/packages/ui/src/hooks/`) to the new `web/apps/web/src/components/ui/` directory.
        *   Includes: `Button.tsx`, `Card.tsx`, `Checkbox.tsx`, `CoachCard.tsx`, `FAB.tsx`, `Input.tsx`, `Label.tsx`, `Modal.tsx` (Radix), `Spinner.tsx`, `TaskCard.tsx`, `TaskStatusBadge.tsx`, `ThemeToggle.tsx`, `ToggleField.tsx` (Headless UI), `chat/MessageBubble.tsx`, `chat/MessageHeader.tsx`, `chat/MessageInput.tsx`, and hooks `useDebounce.ts`, `useTheme.ts`, `useToggle.ts`.

2.  **Update Import Paths:** ✅ **COMPLETED**
    *   Globally search and replace import paths in `web/apps/web/src/` that currently point to `@clarity/ui` or `web/packages/ui` to use local paths relative to `web/apps/web/src/components/ui/` (e.g., `import { Button } from '@/components/ui';`).
    *   Updated `web/apps/web/tsconfig.json` to remove `@clarity/ui` path alias.

3.  **Consolidate Styles:** ✅ **COMPLETED**
    *   Ensure all necessary base styles and `@apply` directives from `web/packages/ui/src/styles/index.css` are merged into `web/apps/web/src/styles/ui-components.css`.
    *   Removed the old `web/packages/ui/src/styles/index.css`.

4.  **Tailwind Configuration:** ✅ **COMPLETED**
    *   Update `web/apps/web/tailwind.config.js`:
        *   Ensure the `content` array correctly scans `src/components/ui/**/*.{js,ts,jsx,tsx}`.
        *   Removed the entry for `../../packages/ui/src/**/*.{js,ts,jsx,tsx}`.
    *   Deleted `web/packages/ui/postcss.config.js`.

5.  **Project Configuration Cleanup:** ✅ **COMPLETED**
    *   Removed the `web/packages/ui` directory entirely.
    *   Updated `web/pnpm-workspace.yaml` to remove the `packages/*` entry.
    *   In `web/package.json` (root web workspace):
        *   Removed `dev:ui` script and references from `concurrently` script.
    *   In `web/apps/web/package.json`:
        *   Removed `@clarity/ui` from dependencies.
        *   Added direct dependencies previously in `packages/ui/package.json` (e.g., `@headlessui/react`, `@radix-ui/react-dialog`, `clsx`, `@heroicons/react`, `@radix-ui/react-slot`).
    *   Deleted `web/packages/ui/package.json` and `web/packages/ui/tsup.config.ts`.

6.  **Verification:** ✅ **COMPLETED**
    *   Development server runs. User tested application, components, and functionality.
    *   No console errors or build issues reported by user.