# Implementation Plan: State Management Architecture with Zustand and Eventual Sync

## Task: Implement Task Store with New Architecture

### Description
Refactor the existing task management to use a consistent Zustand-based state management approach with local-first operations and eventual sync with the database.

### Complexity
Level: 3
Type: Intermediate Feature

### Technology Stack
- State Management: Zustand + Immer
- API/Caching: React Query
- Database: Supabase
- UI Notification: Radix UI Toast (preferred, `react-hot-toast` mentioned in example to be updated or noted)
- Build Tool: Vite
- Framework: React

### Technology Validation Checkpoints
- [x] Zustand with Immer middleware verified
- [x] React Query for initial data fetching confirmed
- [x] Supabase client integration tested
- [x] Reference implementation created and reviewed
- [x] Design document completed

### Status
- [x] Initialization complete
- [x] Planning complete
- [x] Technology validation complete
- [ ] Implementation in progress

### Implementation Plan

#### Phase 1: Core Store Implementation
1. **Create Production `useTaskStore.ts`**
   - Create file at `webApp/src/stores/useTaskStore.ts`
   - Implement store based on reference implementation
   - Define interfaces: `TaskStore`, `PendingChange`, etc.
   - Implement basic CRUD operations (create, update, delete)
   - Add optimistic UI updates
   - Implement background sync mechanism
   - Add conflict resolution for concurrent updates
   - Add error handling for sync failures

2. **Implement Hydration Logic**
   - Create `initializeStore` function to load data on app start
   - Implement intelligent re-fetching policies
   - Add hooks for component integration

3. **Build Supporting Utilities**
   - Create helper functions for store normalization
   - Implement retry mechanism for failed syncs
   - Add selectors for common data access patterns (getTaskById, getSubtasksByParentId)

#### Phase 2: Component Migration (TodayView)
1. **Update `TodayView.tsx`**
   - Update imports to use new store
   - Replace React Query direct calls with store actions
   - Modify task loading logic to use store's `isLoading` state
   - Update task creation flow with optimistic UI
   - Update task update/delete operations

2. **Update `TaskCard.tsx`**
   - Modify to work with the new store's task format
   - Update event handlers to use store actions
   - Ensure proper re-rendering on state changes

3. **Implement Background Sync Indicators**
   - Add UI feedback for sync status (pending/in-progress/complete)
   - Display toast notifications for sync success/failure (using Radix UI Toast, or approved alternative)
   - Add error recovery UI where appropriate

#### Phase 3: TaskDetail Integration
1. **Update `TaskDetailView.tsx`**
   - Modify to use tasks from store instead of direct API calls
   - Replace `useFetchTaskById` with store selectors
   - Update save/update logic to use store actions
   - Ensure proper handling of optimistic updates
   - Add sync status indicators

2. **Update Subtask Management**
   - Implement subtask CRUD operations using the store
   - Update `SubtaskItem.tsx` to use store actions
   - Ensure proper parent/child relationship management
   - Implement position/order handling through the store

#### Phase 4: Testing and Verification

**Objective:** Ensure the new task and subtask management system using Zustand and eventual sync is robust, reliable, and provides a good user experience across various scenarios, including offline and concurrent operations.

**Scope:** This phase covers functional testing, UI/UX testing, basic performance checks, and error handling related to task and subtask operations within `TodayView`, `TaskCard`, `TaskDetailView`, and `SubtaskItem` components.

**I. Functional Testing - Core Task Operations (TodayView & TaskCard)**

*   **Test Case 4.1.1: Create New Task (Fast Input)**
    *   **Steps:**
        1.  In `TodayView`, use the "Fast Task Input".
        2.  Enter a task title and submit.
    *   **Expected:**
        *   Task appears immediately in "Today's Tasks" list (`TaskListGroup`).
        *   Task data is correctly saved in Zustand store.
        *   Background sync to Supabase is initiated (verify via network tools/logs if possible).
        *   Input field clears, focus may shift (verify defined behavior).
*   **Test Case 4.1.2: Create New Task (Button)**
    *   **Steps:**
        1. In `TodayView`, click the "+ New Task" button.
        2. Focus shifts to Fast Input.
        3. Enter a task title and submit.
    *   **Expected:** Same as 4.1.1.
*   **Test Case 4.1.3: Mark Task Complete (from TaskCard)**
    *   **Steps:**
        1.  On a `TaskCard`, click the "Mark complete" (check circle) icon.
    *   **Expected:**
        *   Task appearance changes (e.g., strikethrough, dimmed).
        *   `completed` status is true, `status` is 'completed' in Zustand.
        *   Task is removed from `selectedTaskIds` in `useTaskViewStore`.
        *   Sync to Supabase.
*   **Test Case 4.1.4: Delete Task (from TaskCard)**
    *   **Steps:**
        1.  On a `TaskCard`, click the "Delete" (trash) icon.
        2.  Confirm deletion if prompted.
    *   **Expected:**
        *   Task is removed from the UI.
        *   Task is removed from Zustand store.
        *   If it was the `currentDetailTaskId`, the detail view closes.
        *   If it was the `focusedTaskId`, focus is cleared or shifts.
        *   Task is removed from `selectedTaskIds`.
        *   Sync to Supabase.
*   **Test Case 4.1.5: Start Task (Legacy "Start" button on TaskCard)**
    *   **Steps:**
        1.  On a `TaskCard` (for a task not 'in_progress' or 'completed'), click the "Start" button.
    *   **Expected:**
        *   Task status in Zustand updates to 'in_progress'.
        *   `createFocusSession` API call is made.
        *   UI reflects "In Progress" status (e.g., border, text).
        *   Toast notification for focus session start (success/error).
        *   If API error, status reverts (e.g., to 'planning').
        *   Sync to Supabase.
*   **Test Case 4.1.6: Open Task Detail View (from TaskCard edit icon)**
    *   **Steps:**
        1.  On a `TaskCard`, click the "Edit" (pencil) icon.
    *   **Expected:**
        *   `TaskDetailView` modal opens with the correct task's details loaded.
        *   `currentDetailTaskId` in `TodayView` is set.
        *   `modalOpenState` for this task ID in `useTaskViewStore` is true.
*   **Test Case 4.1.7: Open Task Detail View (from TaskCard click)**
    *   **Steps:**
        1. Click on the main body of a `TaskCard` (not an interactive element).
    *   **Expected:** Same as 4.1.6.
*   **Test Case 4.1.8: Open Prioritize View Modal (from TaskCard focus icon)**
    *   **Steps:**
        1.  On a `TaskCard`, click the "Prepare & Focus" (play) icon.
    *   **Expected:**
        *   `PrioritizeViewModal` opens for the correct task.
        *   `currentPrioritizeTaskId` in `TodayView` is set.
        *   `modalOpenState` for this task ID in `useTaskViewStore` is true.
*   **Test Case 4.1.9: Task Selection (TaskCard checkbox)**
    *   **Steps:**
        1. Click the checkbox on a `TaskCard`.
        2. Click it again.
    *   **Expected:**
        *   Task ID is added/removed from `selectedTaskIds` in `useTaskViewStore`.
        *   Checkbox reflects selected state.
*   **Test Case 4.1.10: Task Reordering (Drag and Drop in TodayView)**
    *   **Steps:**
        1.  Drag a `TaskCard` and drop it to a new position in the list.
    *   **Expected:**
        *   Task visually moves to the new position.
        *   `position` property of the dragged task and affected tasks are updated in Zustand.
        *   Sync to Supabase.
        *   Order is maintained after a page refresh (once sync is complete).
*   **Test Case 4.1.11: Keyboard Navigation & Actions (if implemented)**
    *   **Steps:** (Assuming keyboard navigation is set up via `useTaskViewStore` and `setCurrentNavigableTasks`)
        1. Navigate between tasks using keyboard.
        2. Trigger "open detail" shortcut.
        3. Trigger "focus fast input" shortcut.
    *   **Expected:**
        *   Focus moves correctly between tasks.
        *   `TaskDetailView` opens for the focused task.
        *   Fast input field receives focus.

**II. Functional Testing - Task Detail View (`TaskDetailView`)**

*   **Test Case 4.2.1: View Task Details**
    *   **Steps:**
        1.  Open `TaskDetailView` for a task.
    *   **Expected:**
        *   All task fields (title, description, notes, category, due_date, status, priority) are displayed correctly.
        *   Subtasks for the current task are loaded and displayed.
*   **Test Case 4.2.2: Edit Task Fields**
    *   **Steps:**
        1.  Open `TaskDetailView`.
        2.  Modify various fields (title, description, status, priority, due date etc.).
        3.  Click "Save Changes".
    *   **Expected:**
        *   Changes are saved to Zustand store.
        *   Modal closes.
        *   `TodayView` and relevant `TaskCard` update to reflect changes.
        *   `onTaskUpdated` callback is triggered.
        *   Sync to Supabase.
        *   Toast notification for success.
*   **Test Case 4.2.3: Edit Task and Cancel**
    *   **Steps:**
        1.  Open `TaskDetailView`.
        2.  Modify fields.
        3.  Click "Cancel" or close button.
    *   **Expected:**
        *   Changes are NOT saved.
        *   Modal closes.
        *   Original task data remains unchanged in UI and store.
*   **Test Case 4.2.4: Save with No Changes**
    *   **Steps:**
        1. Open `TaskDetailView`.
        2. Click "Save Changes" without making any modifications to parent task or subtasks.
    *   **Expected:**
        *   "No changes to save" toast appears.
        *   Modal does NOT close automatically (unless subtasks were modified and now there are no pending parent changes).
        *   No unnecessary API calls.
*   **Test Case 4.2.5: Delete Task (from TaskDetailView)**
    *   **Steps:**
        1.  Open `TaskDetailView`.
        2.  Click "Delete" button.
        3.  Confirm.
    *   **Expected:**
        *   `onDeleteTaskFromDetail` is called.
        *   Task is removed from UI in `TodayView`.
        *   Task is removed from Zustand.
        *   Modal closes.
        *   Sync to Supabase.
*   **Test Case 4.2.6: Error on Save Task**
    *   **Steps:**
        1. Simulate a network error or backend error for `updateTaskMutation`.
        2. Edit and save a task in `TaskDetailView`.
    *   **Expected:**
        *   Error toast notification is displayed.
        *   Changes might be reverted or kept optimistically with an error state (verify behavior).
        *   Modal remains open or handles error appropriately.

**III. Functional Testing - Subtask Operations (`TaskDetailView` & `SubtaskItem`)**

*   **Test Case 4.3.1: Add New Subtask**
    *   **Steps:**
        1.  Open `TaskDetailView`.
        2.  Enter title in "Add new subtask..." input.
        3.  Click "Add" or press Enter.
    *   **Expected:**
        *   Subtask appears in the subtask list immediately (optimistic update).
        *   `subtask_position` is correctly assigned.
        *   Subtask is saved to Zustand store with correct `parent_task_id`.
        *   Input field clears.
        *   `createTaskMutation` (for subtask) is called.
        *   Sync to Supabase.
        *   `subtasksWereModifiedInThisSessionRef` is set to true.
        *   Toast notification.
*   **Test Case 4.3.2: Edit Subtask Title (`SubtaskItem`)**
    *   **Steps:**
        1.  In `TaskDetailView`, click the edit icon on a `SubtaskItem`.
        2.  Change the title.
        3.  Click save icon or press Enter or blur.
    *   **Expected:**
        *   Title updates in the UI.
        *   Title updates in Zustand store.
        *   `onSubtaskUpdate` callback in `SubtaskItem` is triggered.
        *   `refetchSubtasks` is called in `TaskDetailView` via `onSubtaskUpdate` in its own props.
        *   Sync to Supabase.
        *   `subtasksWereModifiedInThisSessionRef` is set to true.
*   **Test Case 4.3.3: Mark Subtask Complete/Incomplete (`SubtaskItem`)**
    *   **Steps:**
        1.  In `TaskDetailView`, click the checkbox on a `SubtaskItem`.
        2.  Click it again.
    *   **Expected:**
        *   Subtask `status` and `completed` flag toggle in Zustand store.
        *   UI reflects completed state (e.g., strikethrough).
        *   `onSubtaskUpdate` callback is triggered.
        *   Sync to Supabase.
        *   `subtasksWereModifiedInThisSessionRef` is set to true.
*   **Test Case 4.3.4: Delete Subtask (`SubtaskItem`)**
    *   **Steps:**
        1.  In `TaskDetailView`, click the delete icon on a `SubtaskItem`.
        2.  Confirm if prompted.
    *   **Expected:**
        *   Subtask is removed from UI.
        *   Subtask is removed from Zustand store.
        *   `onSubtaskUpdate` callback is triggered.
        *   Sync to Supabase.
        *   `subtasksWereModifiedInThisSessionRef` is set to true.
*   **Test Case 4.3.5: Reorder Subtasks (Drag and Drop in `TaskDetailView`)**
    *   **Steps:**
        1.  In `TaskDetailView`, drag a `SubtaskItem` and drop it to a new position.
    *   **Expected:**
        *   Subtask visually reorders (optimistic update in `optimisticSubtasks`).
        *   `updateSubtaskOrderMutation` is called with correct parent and ordered subtask IDs/positions.
        *   On success, `refetchSubtasks` is called, `subtasksWereModifiedInThisSessionRef` is true, toast shown.
        *   On error, optimistic update is reverted to server state (`subtasks`), toast shown.
        *   Order is maintained after closing and reopening `TaskDetailView` (once sync is complete).
*   **Test Case 4.3.6: Subtask changes trigger "Save Changes" button enablement in TaskDetailView**
    *   **Steps:**
        1. Open `TaskDetailView`. Make no changes to parent task.
        2. Add a subtask.
        3. Edit a subtask.
        4. Delete a subtask.
        5. Reorder subtasks.
    *   **Expected:**
        *   After each subtask modification that should persist, the "Save Changes" button in `TaskDetailView` should be enabled (due to `subtasksWereModifiedInThisSessionRef`).
        *   Clicking "Save Changes" when only subtasks were modified should close the modal and potentially trigger `onTaskUpdated` if designed to do so, or simply acknowledge that subtask changes are already persisted via their own mutations. Verify the flow here - currently, `handleSave` only proceeds with parent task updates if `actualParentHasChanges` is true. If not, it checks `subtasksWereModifiedInThisSessionRef` and closes. This seems correct.

**IV. Functional Testing - Subtask Display (`TaskCard`)**

*   **Test Case 4.4.1: Expand/Collapse Subtasks on `TaskCard`**
    *   **Steps:**
        1.  Ensure a task has subtasks.
        2.  In `TodayView`, find the `TaskCard`.
        3.  Click the expand/collapse chevron icon.
    *   **Expected:**
        *   Subtask list appears/disappears below the parent task.
        *   `isSubtasksExpanded` state in `TaskCard` toggles.
        *   Subtasks are rendered as `SubtaskItem` components.
*   **Test Case 4.4.2: Reorder Subtasks (Drag and Drop in `TaskCard`)**
    *   **Steps:**
        1. Expand subtasks on a `TaskCard`.
        2. Drag a subtask and drop it to a new position within that card's subtask list.
    *   **Expected:**
        *   Subtask visually reorders.
        *   `handleSubtaskDragEnd` in `TaskCard` is called.
        *   `updateSubtaskOrderMutation` is called.
        *   Data is refetched by `TodayView` (triggering a re-render of `TaskCard` with new `initialSubtasks` prop).
        *   Order is consistent if `TaskDetailView` is opened for this task.
*   **Test Case 4.4.3: Interactions within SubtaskItem on TaskCard**
    *   **Steps:**
        1. Expand subtasks on TaskCard.
        2. Attempt to edit, complete, delete a subtask directly from the SubtaskItem rendered within TaskCard.
    *   **Expected:**
        *   SubtaskItem's own handlers (edit, complete, delete via `useTaskStore`) should function correctly.
        *   Changes are reflected in Zustand and synced.
        *   `onSubtaskUpdate` on `SubtaskItem` (if called by its internal logic) should trigger appropriate data refresh in `TaskCard` (likely through `TodayView`'s refetch).

**V. Offline Behavior & Sync Testing**

*   **Test Case 4.5.1: Create Task Offline**
    *   **Steps:**
        1.  Disconnect network.
        2.  Create a new task.
    *   **Expected:**
        *   Task appears in UI optimistically.
        *   Task is in Zustand store, marked for pending sync.
        *   No network request is made.
*   **Test Case 4.5.2: Sync Task on Reconnection**
    *   **Steps:**
        1.  Follow 4.5.1.
        2.  Reconnect network.
    *   **Expected:**
        *   Pending task syncs to Supabase automatically.
        *   UI indicator for sync success (if any).
*   **Test Case 4.5.3: Edit Task Offline & Sync**
    *   **Steps:**
        1.  Disconnect network.
        2.  Edit an existing task (e.g., title, status in `TaskDetailView`).
        3.  Save.
        4.  Reconnect network.
    *   **Expected:**
        *   Changes appear optimistically. Stored in Zustand, marked for pending sync.
        *   On reconnection, changes sync to Supabase.
*   **Test Case 4.5.4: Delete Task Offline & Sync**
    *   **Steps:**
        1. Disconnect network.
        2. Delete a task.
        3. Reconnect network.
    *   **Expected:**
        *   Task removed optimistically. Marked for pending sync.
        *   On reconnection, deletion syncs to Supabase.
*   **Test Case 4.5.5: Subtask Operations Offline & Sync (Create, Edit, Delete, Reorder)**
    *   **Steps:**
        1. Disconnect network.
        2. Perform various subtask operations (create, edit title, toggle complete, delete, reorder) within `TaskDetailView` or `TaskCard` (if subtask interactions are enabled there).
        3. Reconnect network.
    *   **Expected:**
        *   All changes appear optimistically. Marked for pending sync.
        *   On reconnection, all subtask changes sync correctly to Supabase, maintaining integrity and order.
*   **Test Case 4.5.6: Conflict Resolution (Conceptual - if manual intervention is possible or to observe automated behavior)**
    *   **Scenario:** Task edited on Device A (offline), then same task edited differently on Device B (online and synced). Device A comes online.
    *   **Expected:**
        *   Observe how the system handles the conflict. (e.g., Last Write Wins, or specific conflict resolution logic implemented in `useTaskStore`). Document the observed behavior. The current plan mentions "conflict resolution for concurrent updates" in Phase 1, so this needs to be tested.

**VI. UI/UX Testing**

*   **Test Case 4.6.1: Loading States**
    *   **Steps:**
        1.  Observe UI when `TodayView` is initially loading tasks.
        2.  Observe UI in `TaskDetailView` when task/subtask data is being fetched.
    *   **Expected:**
        *   Appropriate spinners/loading messages are displayed.
        *   UI is not janky or unresponsive.
*   **Test Case 4.6.2: Error States**
    *   **Steps:**
        1.  Simulate API errors for fetching tasks, updating tasks, creating tasks, deleting tasks.
    *   **Expected:**
        *   User-friendly error messages or toasts are displayed.
        *   Application remains stable and usable where possible.
*   **Test Case 4.6.3: Empty States**
    *   **Steps:**
        1.  View `TodayView` with no tasks.
        2.  Open `TaskDetailView` for a task with no subtasks.
    *   **Expected:**
        *   Clear and helpful empty state messages/UI.
*   **Test Case 4.6.4: Responsiveness**
    *   **Steps:**
        1.  Test on different screen sizes (desktop, tablet, mobile - if applicable).
    *   **Expected:**
        *   Layout adapts correctly. All interactive elements are usable.
*   **Test Case 4.6.5: Focus Management**
    *   **Steps:**
        1. Observe focus behavior after creating a task via Fast Input.
        2. Observe focus behavior when opening/closing modals (`TaskDetailView`, `PrioritizeViewModal`).
        3. Observe focus behavior when using keyboard navigation.
    *   **Expected:**
        *   Focus is managed logically, aiding accessibility and usability.
        *   e.g., after adding a task, focus might go to the new task or back to an input. After closing a modal, focus returns to the triggering element or a sensible default.
*   **Test Case 4.6.6: Toast Notifications**
    *   **Steps:**
        1. Perform actions that trigger toasts (save success, save error, focus session start, etc.).
    *   **Expected:**
        *   Toasts are clear, concise, appropriately styled, and appear/disappear correctly.
        *   Using the `toast` utility from `@/components/ui/toast`.

**VII. Basic Performance Checks**

*   **Test Case 4.7.1: Rendering with Many Tasks**
    *   **Steps:**
        1.  Populate the store with a large number of tasks (e.g., 100-200).
        2.  Scroll through `TodayView`.
    *   **Expected:**
        *   Scrolling is smooth. No noticeable lag in rendering `TaskCard` components. (Virtualization is not mentioned, so this is a direct render test).
*   **Test Case 4.7.2: Rendering with Many Subtasks**
    *   **Steps:**
        1.  Populate a task with many subtasks (e.g., 50-100).
        2.  Open `TaskDetailView` and scroll through subtasks.
        3.  Expand subtasks on `TaskCard` and observe.
    *   **Expected:**
        *   Scrolling is smooth. No noticeable lag.
*   **Test Case 4.7.3: Store Update Performance**
    *   **Steps:**
        1. Perform rapid task/subtask modifications.
    *   **Expected:**
        *   UI remains responsive. Zustand store updates efficiently.
        *   Monitor browser dev tools for CPU usage spikes during these operations.

**VIII. Data Integrity Checks**

*   **Test Case 4.8.1: Consistent Task IDs**
    *   **Steps:**
        1.  Create, update, delete tasks and subtasks.
    *   **Expected:**
        *   IDs are unique and correctly referenced (e.g., `parent_task_id`).
*   **Test Case 4.8.2: Subtask Positions**
    *   **Steps:**
        1.  Create, reorder, delete subtasks.
    *   **Expected:**
        *   `subtask_position` field is consistently and correctly maintained in sequence for all subtasks of a parent.
*   **Test Case 4.8.3: Data Persistence After Refresh**
    *   **Steps:**
        1.  Perform various CRUD operations.
        2.  Allow time for sync (if online).
        3.  Refresh the page.
    *   **Expected:**
        *   All changes are persisted and correctly loaded from Supabase via the store's initialization.

**Test Environment:**
*   Browsers: Latest Chrome, Firefox, Safari (if available).
*   Network conditions: Online (fast, slow), Offline.
*   Supabase backend configured and accessible.

**Reporting:**
*   Any failed test case should be documented with:
    *   Test Case ID
    *   Steps to reproduce
    *   Actual Result
    *   Expected Result
    *   Severity (Critical, High, Medium, Low)
    *   Screenshots/GIFs if helpful.

This detailed test plan will replace the previous, more generic "Manual Testing" and "Monitor Performance" sections in Phase 4.

### Challenges & Mitigations
- **Challenge 1: Race Conditions** - Implement proper synchronization of store updates with optimistic changes and server responses.
  - **Mitigation:** Use transaction IDs or timestamps to track update sequence. Implement a reconciliation mechanism.

- **Challenge 2: Error Handling** - Failed sync operations need proper recovery.
  - **Mitigation:** Implement exponential backoff for retries, clear error states, and provide recovery options to the user.

- **Challenge 3: Initial Data Loading Strategy** - Need to determine when and how to initially populate the store.
  - **Mitigation:** Create an initialization pattern that can be consistently applied across the application, potentially in a common ancestor component.

- **Challenge 4: Offline Support** - Need to handle scenarios where users make changes while offline.
  - **Mitigation:** Persist pending changes in localStorage as backup, implement reconnection sync logic.

- **Challenge 5: Selective Updates** - Need to optimize what data gets synced to avoid unnecessary API calls.
  - **Mitigation:** Track only changed fields in pendingChanges, batch sync operations where possible.

### Dependencies
- Updates to `webApp/src/api/types.ts` might be required to ensure proper typing
- Proper authentication setup to ensure user_id is available for store operations
- Toast notification system for user feedback (Radix UI Toast preferred)

### Implementation Timeline
- Phase 1 (Core Store): 2-3 days
- Phase 2 (TodayView Migration): 1-2 days
- Phase 3 (TaskDetail Integration): 1-2 days
- Phase 4 (Testing): 1 day
- Phase 5 (Documentation): 1 day

**Total Estimated Time: 6-9 days** 