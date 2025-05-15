# Creative Design: Prioritize-Execute-Reflect (P-P-E-R) Cycle & Task Management

This document outlines the UI/UX design for the **Prioritize-Execute-Reflect (P-P-E-R)** cycle and core task management features within the Clarity web application. It incorporates user feedback to refine previous P-E-R concepts and aligns with `memory-bank/style-guide.md` and `memory-bank/productContext.md`.

**Terminology Note:** The broader cycle is "Plan - Prioritize - Execute - Reflect." This document focuses on the daily operational loop of **Prioritize, Execute, and Reflect**.

## 1. Core Task Management Enhancements

### 1.1. Fast Task Entry

*   **Goal:** Allow rapid task capture from almost anywhere, especially the "Today View."
*   **Mechanism:**
    *   A dedicated single-line input field prominently displayed at the top of the "Today View."
    *   **Hotkey Access:** Pressing a key (e.g., `T` for Task) automatically focuses this input field.
    *   **Inline Property Flagging:** Users can type natural language cues or shortcuts to set properties during entry:
        *   Priority: `task title p1` or `task title /priority 1`
        *   Due Date: `task title due:tmrw` or `task title :mon`
        *   (Future: Tags, Projects `task title #projectX`)
    *   Pressing `Enter` creates the task with parsed properties and adds it to the Today View (or a default list/inbox if not on Today View).
*   **UI:** Minimalist input field, perhaps with subtle cues or autocomplete for property flags as typing occurs.

### 1.2. Task Detail View

*   **Goal:** Provide a comprehensive view to see and edit all properties of a task.
*   **Trigger:** Clicking a task title/card in Today View (or an explicit "Details" button/icon).
*   **Container:** Likely a modal (Radix Dialog) or a dedicated right-side panel that slides in, compressing the Today View.
*   **Content:**
    *   Editable fields for all `Task` properties: `title`, `description` (multi-line textarea), `notes`, `category`, `status`, `priority`, `due_date` (date picker), `time_period`.
    *   Display `created_at`, `updated_at` (read-only).
    *   Section for `Subtasks` (see 1.3).
    *   (Future: Links to `Projects`, `linked_doc_url`, `value_tag`, `reward_trigger`, etc.)
*   **Actions:** Save, Cancel, Delete Task.

### 1.3. Subtasks

*   **Data Model Implication:** Tasks need a `parent_task_id` (nullable) and potentially a `subtask_position` for ordering. (Requires DDL update if not already implicitly supported by `position` and a self-referencing FK).
*   **Display in Today View / Task Card:**
    *   If a task has subtasks, display an accordion toggle (e.g., `<ChevronDownIcon />`).
    *   Expanding the accordion shows a list of its subtasks, each potentially a simplified `TaskCard` itself.
*   **Interaction:**
    *   Subtasks can be marked complete independently.
    *   **Crucially: If a task has subtasks, only the subtasks can be "Started" / "Focused" on for the P-P-E-R cycle.** The parent task's status might become derived from its subtasks' statuses.
    *   Subtasks can be added/edited via the `TaskDetailView` of the parent task.

### 1.4. Chat Panel

*   **Location:** A collapsible panel on the right-hand side of the "Today View" (and potentially other key views).
*   **Trigger:** An icon button in the main application header or sidebar to toggle visibility.
*   **Functionality:** Standard chat interface for interacting with the AI Coach.

## 2. Prioritize-Execute-Reflect (P-P-E-R) Flow

This flow is engaged when a user decides to work on a specific task (or subtask).

### 2.1. PRIORITIZE Task View (Formerly "Plan Task" View)

This phase is about focused preparation immediately before execution.

*   **Trigger:**
    *   From `TaskCard.tsx` (for a task *without* subtasks, or for a specific subtask) in "Today View" - a "Focus" or "Deep Work" button.
    *   Implicitly, if a user adjusts timer settings before starting a task.
*   **Container:** Modal (Radix UI Dialog Primitive).
    *   **Header:** "Prepare: [Task Title]"
    *   **Body:**
        *   **Motivation (Review/Edit):**
            *   Label: "Why is this task important right now?"
            *   Input: Textarea (Radix UI TextArea), pre-filled if `tasks.motivation` exists.
            *   Data: `tasks.motivation`
        *   **Definition of Done (Review/Edit):**
            *   Label: "What does 'done' look like for this session/task?"
            *   Input: Textarea, pre-filled if `tasks.completion_note` exists.
            *   Data: `tasks.completion_note`
        *   **Breakdown (Display/Quick Add for *this session*):**
            *   Label: "Key steps for this focus session:"
            *   Display: If `tasks.breakdown` (parent task's overall breakdown) exists, show relevant parts or allow user to quickly jot down 2-3 micro-steps for the *imminent session*.
            *   Input: Simple Textarea or a few distinct short text inputs.
            *   *Note: This is distinct from the main `tasks.description` or a formal subtask list. It's about micro-planning the immediate focus block.*
        *   **Timer Configuration:**
            *   Label: "Focus Session Duration:"
            *   Input: Slider or preset buttons (e.g., 25min, 45min, 60min) for Pomodoro timer. Default from user preferences.
        *   **(Display Only - if applicable and data exists on the task):**
            *   `value_tag`, `linked_doc_url`, `reward_trigger`.
    *   **Footer:**
        *   Button: "Start Focus Session" (Primary accent color) - Saves any changes, transitions to Execute view with configured timer.
        *   Button: "Cancel" (Tertiary/Link) - Closes modal.

### 2.2. EXECUTE Task View (Focus Window)

*   **Context:** A dedicated, minimal view/window/overlay designed for deep work.
*   **Layout:**
    *   **Central Element: Pomodoro Timer**
        *   Large, prominent digital display of time remaining (e.g., `<h2>24:17</h2>`).
        *   Visual progress indicator (circular or bar).
        *   Controls: "Pause" / "Resume", "End Session Early".
    *   **Top Area (Minimal):**
        *   Current Task Title (or Subtask Title).
    *   **Right Expandable Panel (Agent & Scratch Pad):**
        *   Trigger: Icon button (e.g., `<SparklesIcon /> Agent & Notes`).
        *   Panel Content:
            *   **Agent Chat:** A compact version of the main Chat Panel for quick interactions with the AI coach during the session.
            *   **Scratch Pad:**
                *   Label: "Session Scratch Pad for [Task Title]"
                *   Input: Textarea for `scratch_pad_entries.content`.
                *   Save: Auto-save. Entries associated with `focus_session_id` AND `task_id`.
    *   **Subtle Info (Optional, Collapsible):**
        *   Display `motivation` and session-specific `breakdown` from the Prioritize phase.

### 2.3. REFLECT on Session View

*   **Trigger:** Timer completion or manual "End Session Early."
*   **Container:** Modal (Radix UI Dialog Primitive).
    *   **Header:** "Session Reflection: [Task Title]"
    *   **Body:** (Largely as previously designed, with potential for future AI chat-driven reflection)
        *   Display `completion_note` (Definition of Done from Prioritize phase) for context.
        *   **Reflection Notes:** Label: "How did the session go? What was achieved? Any roadblocks?"
            *   Input: Textarea. Data: `focus_sessions.notes`.
        *   **Mood:** Label: "Session Mood?" Input: Segmented control/Radio Group (😊, 🙂, 😐, 😕, 😩).
            *   Data: `focus_sessions.mood`.
        *   **Session Outcome:** Label: "Outcome?" Input: Segmented control/Radio Group (✅ Completed, 👍 Progress, 🔄 Blocked/Switched, ❌ Abandoned).
            *   Data: `focus_sessions.outcome`.
    *   **Footer:**
        *   Button: "Save Reflection & Close" (Primary) - Saves, updates task status, closes.
        *   (Future: AI Coach summary of reflection, next step suggestions).

## 3. Data Flow & Model Implications (Summary of Changes)

*   **`tasks` table:**
    *   Needs `description TEXT`. (DONE in DDL)
    *   Consider `parent_task_id UUID NULL REFERENCES public.tasks(id)` for subtasks.
    *   Consider `subtask_position INTEGER` for ordering subtasks.
*   **Fast Task Entry:** Requires parsing logic for inline properties.
*   **`scratch_pad_entries`:** Confirm `task_id` can be populated even if `session_id` is not yet known (e.g., general scratchpad before focus session starts). Current DDL allows this.
*   **P-P-E-R State Management:** A Zustand store (e.g., `useAppCycleStore` or `useFocusSessionStore`) will likely be needed to manage the current phase (Prioritize, Execute, Reflect), active task for focus, timer state, etc.

## 4. Open Questions & Iteration Points

*   **Subtask DDL:** Finalize DDL for subtasks (`parent_task_id`, `subtask_position`).
*   **Focus View Implementation:** Still: Dedicated route vs. enhanced state/modal overlay? (Leaning towards a more immersive overlay/mode that takes over the screen but isn't a full route change, to maintain context of Today View easily).
*   **AI Coach Integration Points:** Specific prompts and interactions for each phase, especially during Prioritization (help with motivation/breakdown) and Reflection (summarizing, suggesting next steps).
*   **Inline Property Parsing for Fast Entry:** Define supported shortcuts and parsing robustness.

This revised document reflects the new direction. Further refinement will occur during implementation planning and prototyping. 