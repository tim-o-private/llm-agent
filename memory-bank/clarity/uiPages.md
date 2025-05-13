# GitHub Issue Backlog: Clarity MVP

---

## Application Pages & Routes Mapping

This section maps defined application pages to their route paths, primary components, and implementation status.

| Page Name (from Issues) / Implemented Page | Intended/Actual Route Path | Key Components (Defined/Implemented)                                                                                                   | Implementation Status        | Notes                                                                                                                                                                                                     |
| :----------------------------------------- | :------------------------- | :------------------------------------------------------------------------------------------------------------------------------------- | :--------------------------- | :-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Home Page**                              | `/`                        | `Home.tsx` (page component), `Link` (to /login, /dashboard)                                                                            | Implemented                  | Current landing page with welcome message and navigation links.                                                                                                                                             |
| **Login Page**                             | `/login`                   | `Login.tsx` (page component), uses `UserMenu` component directly (unusual for pre-login).                                              | Implemented (Basic)          | Basic login screen structure. `UserMenu` inclusion is odd here. Lacks actual form fields.                                                                                                                   |
| **Dashboard Page**                         | `/dashboard`               | `Dashboard.tsx` (page component). Internally uses basic HTML for cards: "Focus Timer" (static), "Today\'s Tasks" (static), "AI Coach" (static). | Implemented (Placeholder)    | Acts as a very basic placeholder. Shows some concepts from "Today View" (Issue 1) but lacks `AppShell`, `SideNav`, `TopBar`, proper `TaskListGroup`s, `TaskCard`s, `FABQuickAdd`. Styling is Tailwind. |
| **Issue 1: Today View (Planner Screen)**   | `/today` (suggested)       | `AppShell`, `SideNav`, `TopBar`, `TaskListGroup` (x3), `TaskCard`, `FABQuickAdd`, `CoachCard`                                             | Largely Not Implemented      | `Dashboard.tsx` is a rudimentary starting point but misses most key structural and interactive components.                                                                                                    |
| **Issue 3: Focus Mode Screen**             | `/focus/:taskId` (suggested)| `AppShell` (or fullscreen), `FocusHeader`, `FocusTimer`, `ScratchPadToggle`                                                              | Not Implemented              |                                                                                                                                                                                                           |
| **Issue 6: Coach Panel / Chat View**       | `/coach` (suggested)       | `AppShell`, `SideNav`, `TopBar`, `CoachPanel` (partially `ChatPanel.tsx` component), `MessageHeader`, `MessageBubble`, `MessageInput`         | Partially Implemented (Component) | `ChatPanel.tsx` component exists. Needs integration into a page structure, `AppShell`, and its own sub-components (`MessageHeader`, etc.) are not discretely implemented.                                |
| **Issue 7: Settings Screen**               | `/settings` (suggested)    | `AppShell`, `SideNav`, `TopBar`, `SettingsPage` (component), `TimeBlockEditor`, `ToggleField`                                            | Not Implemented              | `ThemeToggle.tsx` (shared UI) exists, which is a specific `ToggleField`.                                                                                                                                  |
| **Issue 8: Done List (Task History View)** | `/history` (suggested)     | `AppShell`, `TaskCard` (with `completed` state), `StreakCounter`                                                                       | Not Implemented              |                                                                                                                                                                                                           |

---
## Key UI States (Modals/Overlays) - Based on `uiPages.md` Issues

| UI State (from Issues)         | Trigger                                          | Key Components (Defined / Existing Primitives)                                       | Implementation Status | Notes                                                                                                   |
| :----------------------------- | :----------------------------------------------- | :--------------------------------------------------------------------------------- | :-------------------- | :------------------------------------------------------------------------------------------------------ |
| **Issue 2: Add Task Tray**       | `FABQuickAdd` click                              | `FABQuickAdd`, `QuickAddTray`, `TaskDetailTray` (Primitives: `Button`, `Input`, `Modal`) | Not Implemented       | Generic `Modal.tsx` could be a base for tray if it\'s modal-like. `Input.tsx` and `Button.tsx` are available. |
| **Issue 4: Scratch Pad Overlay** | `ScratchPadToggle` from Focus Mode, global access | `ScratchOverlay`, `ScratchEntryCard` (Primitives: `Input`, `Card`, `Button`)         | Not Implemented       | `Card.tsx` could be a base for `ScratchEntryCard`.                                                        |
| **Issue 5: Reflection Modal**    | Session end / EOD flow                           | `ReflectionModal`, `MoodPicker`, `TaskOutcomeSelector` (Primitives: `Modal`, `Button`) | Not Implemented       | Generic `Modal.tsx` could be a base for `ReflectionModal`. `Button.tsx` for selectors.                  |

---

## Issue 1: Implement Today View (Planner Screen)
**Labels:** `feature`, `screen`, `frontend`, `MVP`

**Description:**
Build the Today View as designed in `DayPlanner.pdf`.  
This screen displays a vertical schedule segmented into Morning / Afternoon / Evening, with tasks grouped under each.

### Components:
- `AppShell` (with `SideNav` and `TopBar`)
- `TaskListGroup` (Morning / Afternoon / Evening)
- `TaskCard` (shows checkbox, title, time, category)
- `FABQuickAdd` to trigger inline task entry
- `CoachCard` (optional sidebar message)

### Acceptance Criteria:
- Tasks are grouped by time blocks (or user-defined group)
- FAB expands to `QuickAddTray` inline
- Empty state prompts user to begin planning
- Screen is responsive and adheres to low-stim design language

---

## Issue 2: Implement Add Task Tray (Quick + Detailed View)
**Labels:** `component`, `frontend`, `MVP`

**Description:**
Create the Add Task flow triggered from FAB. Supports a default "quick add" input and expandable detailed form.

### Components:
- `FABQuickAdd`
- `QuickAddTray`
- `TaskDetailTray` (for expanded mode)

### Fields:
- Task name (required)
- Time Period (dropdown or time picker)
- Priority level (Low/Med/High)
- Reminder (select or toggle)

### Acceptance Criteria:
- Default tray shows task name and time
- Expandable section shows full task fields
- "Cancel" and "Add Task" buttons always visible
- Matches design in `OpenedFAB.pdf`

---

## Issue 3: Implement Focus Mode Screen
**Labels:** `feature`, `screen`, `frontend`, `MVP`

**Description:**
Build the task execution view, entered when a user starts a task.

### Components:
- `AppShell` layout or fullscreen override
- `FocusHeader` (task name + category)
- `FocusTimer` (with play/pause and complete)
- `ScratchPadToggle` (opens `ScratchOverlay`)

### Acceptance Criteria:
- Timer starts with "Start" and pauses as expected
- User can mark task complete or exit focus
- Coach is quiet unless nudged or idle is detected

---

## Issue 4: Implement Scratch Pad Overlay
**Labels:** `component`, `overlay`, `frontend`, `MVP`

**Description:**
Implement the Scratch Pad overlay to allow users to capture thoughts during Focus Mode or planning.

### Components:
- `ScratchOverlay`
- `ScratchEntryCard`

### Acceptance Criteria:
- Opens as a modal or drawer
- Shows input box and log of past entries
- Supports convert-to-task and archive buttons
- Auto-saves to local cache if offline

---

## Issue 5: Implement Reflection Modal
**Labels:** `component`, `modal`, `frontend`, `MVP`

**Description:**
Build the post-session or end-of-day Reflection Modal.

### Components:
- `ReflectionModal`
- `MoodPicker`
- `TaskOutcomeSelector`

### Acceptance Criteria:
- Triggered after session end or EOD flow
- User can mark task status and write notes
- Mood selection and optional follow-up prompt

---

## Issue 6: Implement Coach Panel / Chat View
**Labels:** `screen`, `AI`, `frontend`, `MVP`

**Description:**
Build a conversational interface for interacting with the assistant.

### Components:
- `CoachPanel`
- `MessageHeader`
- `MessageBubble`
- `MessageInput`

### Acceptance Criteria:
- Chat thread persists over user session
- MessageInput triggers context-aware suggestions
- Coach tone and response style follow user settings

---

## Issue 7: Implement Settings Screen
**Labels:** `screen`, `backend`, `preferences`, `MVP`

**Description:**
Create a user settings screen to configure app tone, time blocks, and reminders.

### Components:
- `SettingsPage`
- `TimeBlockEditor`
- `ToggleField`

### Acceptance Criteria:
- User can set tone, adjust time blocks, and enable/disable reminders
- Includes export/delete data options
- Reflects changes in live behavior without reload

---

## Issue 8: Implement Done List (Task History View)
**Labels:** `screen`, `log`, `frontend`, `MVP`

**Description:**
Create a historical view of completed tasks for review and reward.

### Components:
- `AppShell`
- `TaskCard` (with `completed` state)
- `StreakCounter`

### Acceptance Criteria:
- Shows tasks grouped by date or streak
- Can click into past reflections
- Integrates with coach memory for reward suggestions
"""
