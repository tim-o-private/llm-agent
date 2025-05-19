# Test Plan: TaskDetailView Functionality

**Objective:** Verify the correct functionality of the `TaskDetailView.tsx` component after its refactor to use React Hook Form for parent task management and simplified save/close logic.

**Pre-conditions:**
*   Ensure tasks and some subtasks exist in the database.
*   User is logged in.
*   `TodayView` is accessible and displays tasks.

---

## I. Parent Task - Core CRUD & Form Behavior (using React Hook Form)

*   PASS **Test Case PT-1: Open Task Detail & Verify Data Population**
    *   **Steps:**
        1.  Click a task in `TodayView` to open `TaskDetailView`.
    *   **Expected:**
        *   Modal opens.
        *   All parent task fields (Title, Description, Notes, Status, Priority, Category, Due Date) are correctly populated with the task's current data using React Hook Form `defaultValues` or `reset`.
        *   "Save Changes" button is initially disabled (React Hook Form `formState.isDirty` should be `false`).

*   PASS **Test Case PT-2: Edit Parent Task Field & Verify Dirty State**
    *   **Steps:**
        1.  Open modal for a task.
        2.  Modify the "Title" field.
    *   **Expected:**
        *   "Save Changes" button becomes enabled (due to `formState.isDirty` becoming `true`).

*   PASS **Test Case PT-3: Edit Parent Task & Save**
    *   **Steps:**
        1.  Open modal.
        2.  Modify "Title" and "Description" fields.
        3.  Click "Save Changes".
    *   **Expected:**
        *   The modal closes automatically.
        *   The `TodayView` list reflects the updated title/description on the corresponding `TaskCard`.
        *   (Optional Manual Check) Verify data persistence in the database.

*   PASS **Test Case PT-4: Edit Parent Task & Cancel**
    *   **Steps:**
        1.  Open modal.
        2.  Modify the "Title" field (making `formState.isDirty` true).
        3.  Click the "Cancel" button (or 'X' icon, or press the Esc key).
    *   **Expected:**
        *   A confirmation prompt appears (e.g., "You have unsaved changes. Are you sure you want to discard them?").
        *   Click "OK" (or confirm the discard action on the prompt): Modal closes. Changes are NOT saved. `TodayView` shows the original title.
        *   Click "Cancel" (or the option to not discard, effectively cancelling the close action): The prompt closes. The modal remains open with the dirty changes.

*   PASS **Test Case PT-5: Open, No Changes, Click Save**
    *   **Steps:**
        1.  Open modal.
        2.  Ensure no fields are modified (`formState.isDirty` is `false`).
        3.  Click "Save Changes".
    *   **Expected (New Architecture):**
        *   "Save Changes" button should be disabled.
        *   If the button were somehow enabled and clicked with no actual field differences, the `onValidParentSubmit` function should calculate an empty `updates` object.
        *   No backend API call should be made if the `updates` object is empty.
        *   A toast like "No changes to save" should appear, or no toast if no action is taken.
        *   The modal should remain open or close based on defined behavior for "no changes". (Preference: remain open, toast "No changes").

*   PASS **Test Case PT-6: Open, No Changes, Click Cancel**
    *   **Steps:**
        1.  Open modal.
        2.  Ensure no fields are modified.
        3.  Click "Cancel" (or 'X', or Esc).
    *   **Expected:**
        *   Modal closes immediately without any confirmation prompt.

*   FAIL **Test Case PT-7: Test All Parent Field Types**
    *   **Steps:**
        1.  Open modal.
        2.  Systematically edit values for each parent task field:
            *   Title (Input)
            *   Description (Textarea)
            *   Notes (Textarea)
            *   Status (Select)
            *   Priority (Select)
            *   Category (Input)
            *   Due Date (Date Input)
        3.  Click "Save Changes".
    *   **Expected:**
        *   All changes are saved correctly.
        *   Modal closes.
        *   Re-opening the modal for the same task shows the newly saved values.
        *   Data is correctly persisted in the database.

---

## II. Subtask Management

*Note: Subtask operations (add, edit, delete, reorder) are expected to trigger their own immediate mutations. The `childOperationsOccurredInSessionRef` flag is used to track if such operations happened during the modal session, primarily for the "Cancel" prompt logic.*

*   **Test Case ST-1: View Subtasks**
    *   **Steps:**
        1.  Open modal for a task that has existing subtasks.
    *   **Expected:**
        *   Subtasks are listed correctly, displaying their titles and completion status.
        *   Subtasks are in the correct order (as per `subtask_position`).

*   **Test Case ST-2: Add New Subtask (using Enter key)**
    *   **Steps:**
        1.  Open modal.
        2.  Type a title in the "Add new subtask..." input field.
        3.  Press the Enter key.
    *   **Expected:**
        *   The `createTaskMutation` for the subtask is triggered.
        *   The new subtask appears in the list (ideally an optimistic update, then confirmed by refetch). Input field clears.
        *   (Optional) A success toast appears (e.g., "Subtask Added!") - Current: No toast, but UI updates.
        *   The modal remains open.
        *   The "Save Changes" button for the parent task remains enabled/disabled based *only* on the parent task form's `isDirty` state. (Observation: Remained disabled. Follow-up task created to review if child operations should enable parent Save/prompt differently).
        *   The internal `childOperationsOccurredInSessionRef` flag becomes `true`.

*   **Test Case ST-3: Add New Subtask (using "Add" Button)**
    *   **Steps:**
        1.  Open modal.
        2.  Type a title in the "Add new subtask..." input field.
        3.  Click the "Add" button.
    *   **Expected:**
        *   Same as Test Case ST-2.
        *   The "Add" button should be disabled while its `createTaskMutation` is pending.

*   **Test Case ST-4: Attempt to Add Empty Subtask**
    *   **Steps:**
        1.  Open modal.
        2.  With the "Add new subtask..." input field empty, click the "Add" button or press Enter.
    *   **Expected:**
        *   No subtask is added.
        *   The "Add" button might be disabled if the input is empty.
        *   No error toast, unless a backend error occurs (which it shouldn't for an empty title).

*   **Test Case ST-5: Subtask Reordering (Drag and Drop)**
    *   **Steps:**
        1.  Open modal for a task with multiple subtasks.
        2.  Drag a subtask and drop it into a new position in the list.
    *   **Expected:**
        *   The subtask visually moves to the new position (optimistic update).
        *   The `updateSubtaskOrderMutation` is triggered.
        *   On success, the new order is persisted.
        *   A success toast appears (e.g., "Subtask order saved!").
        *   The modal remains open.
        *   The internal `childOperationsOccurredInSessionRef` flag becomes `true`.

*   **Test Case ST-6: Edit Subtask (Inline - via `SubtaskItem`)**
    *   *(This assumes `SubtaskItem.tsx` has its own internal edit state or a way to trigger an edit mode, potentially managed by `useReorderableList` or the `TaskDetailView` if item-specific edit logic is passed down)*
    *   **Status:** FAIL
    *   **Steps:**
        1.  Open the modal for a task that has at least one subtask.
        2.  Locate a subtask in the list.
        3.  Click the "Edit" icon/button associated with that subtask.
    *   **Expected:**
        *   The `TaskDetailView` modal REMAINS OPEN.
        *   The specific subtask item becomes editable inline (e.g., its text turns into an input field).
        *   Alternatively, a small, focused editor for just that subtask might appear (though inline is preferred for simplicity if feasible).
        *   Changes to the subtask can be saved (e.g., by pressing Enter or blurring the input) or cancelled.
        *   The `updateTaskMutation` (or a specific `updateSubtaskMutation`) is triggered upon saving the subtask.
    *   **Actual:**
        *   Clicking the subtask's "Edit" icon/button closes the entire `TaskDetailView` modal.
    *   **Notes:** This is a significant bug preventing subtask editing.

*   **Test Case ST-7: Delete Subtask**
    *   **Status:** PASS
    *   **Steps:**
        1.  Open modal.
        2.  Delete an existing subtask using controls within its `SubtaskItem`.
    *   **Expected:**
        *   The subtask is removed from the list.
        *   The internal `childOperationsOccurredInSessionRef` flag becomes `true`.
        *   If parent task was NOT modified AND no child operations occurred: Modal closes without prompt.
    *   **Note:** Behavior to be revisited as per user feedback.

*   **Test Case ST-8: Add/Modify Subtasks, then Cancel Parent Edit**
    *   **Steps:**
        1.  Open modal for a task.
        2.  Add one or two new subtasks (which are persisted immediately).
        3.  (Optional) Modify the parent task's title field (so `formState.isDirty` is true).
        4.  Click the "Cancel" button (or 'X', or Esc).
    *   **Expected:**
        *   If parent task was modified OR `childOperationsOccurredInSessionRef` is true: A confirmation prompt appears ("You have unsaved changes...").
            *   Click "Discard": Modal closes. Parent task changes (if any) are NOT saved. Added/modified subtasks *remain* as they were saved independently.
            *   Click "Cancel" (on prompt): Modal stays open.
        *   If parent task was NOT modified AND no child operations occurred: Modal closes without prompt.

---

## III. Other Interactions & Edge Cases

*   **Test Case OT-1: Delete Parent Task (from Modal Footer)**
    *   **Status:** FAIL
    *   **Steps:**
        1.  Open modal for an existing task.
        2.  Click the "Delete" button in the modal footer.
    *   **Expected:**
        *   A native browser confirmation prompt (`window.confirm`) appears ("Are you sure...?").
        *   Click "OK": The `onDeleteTaskFromDetail` prop callback is invoked. The task is deleted from the backend. The modal closes. The `TodayView` list updates to remove the task.
        *   Click "Cancel" (on prompt): The prompt closes. The modal remains open.
    *   **Actual Error:** Console reports `Object { code: "23503", details: 'Key is still referenced from table "tasks".', hint: null, message: 'update or delete on table "tasks" violates foreign key constraint "tasks_parent_task_id_fkey" on table "tasks"' }`. This indicates a need for `ON DELETE CASCADE` or similar handling for subtasks when a parent is deleted.

*   **Test Case OT-2: Modal Responsiveness & Max Height with Scrolling**
    *   **Status:** TBD
    *   **Steps:**
        1.  Open modal.
        2.  Ensure there's enough content (e.g., long description, many subtasks) to require vertical scrolling.
    *   **Expected:**
        *   The modal content area scrolls vertically within its defined `max-h-[85vh]`.
        *   The modal layout remains usable and responsive on reasonably smaller viewport widths.
    *   **Status:** Not Tested

*   **Test Case OT-3: Loading States & Error Handling**
    *   **Steps (Simulate or observe if possible):**
        1.  Initial load of task data (`useFetchTaskById`):
            *   Slow network: Observe loading indicator.
            *   Network error: Observe error message displayed within the modal.
        2.  Saving parent task changes (`updateTaskMutation`):
            *   Slow network: Observe "Save Changes" button disabled, spinner active.
            *   Network error: Observe error toast. Modal remains open with unsaved changes. "Save Changes" button re-enabled.
        3.  Adding a subtask (`createTaskMutation` for subtask):
            *   Slow network: Observe "Add" button disabled, spinner active.
            *   Network error: Observe error toast. Modal remains open.
    *   **Expected:**
        *   Appropriate loading indicators (spinners) are shown during data fetching and mutations.
        *   User-friendly error messages or toasts are displayed for API/network errors.
        *   The UI remains stable and allows recovery or retry where appropriate.
    *   **Status:** Not Tested

--- 