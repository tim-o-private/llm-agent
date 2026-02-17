# Keyboard Shortcut Management Guide

## Guiding Principles
Keyboard shortcuts enhance user productivity and accessibility. They should be implemented consistently and predictably, with clear separation of concerns between global and view-specific shortcuts.

## 1. Scope of Shortcuts
*   **Local (View-Specific) Shortcuts:** These are shortcuts that are active only when a specific view or component is active and in focus (or a designated part of it is). Most shortcuts will fall into this category.
    *   Example: 'n'/'p' for next/previous task in `TodayView.tsx`.
*   **Global Shortcuts:** These are shortcuts that should be active throughout the application, regardless of the current view (unless an input field or modal has focus and explicitly traps key events).
    *   Example: A hypothetical Ctrl+K for a command palette (if implemented).
    *   **Caution:** Use global shortcuts sparingly to avoid conflicts and user confusion.

## 2. Implementation Strategy
*   **`useEffect` for Event Listeners:** The primary mechanism for implementing keyboard shortcuts is a `useEffect` hook in the relevant component (for local shortcuts) or a global layout component (for global shortcuts).
    *   The hook should add a `keydown` event listener to `document` or a specific container `ref`.
    *   **Cleanup:** CRITICAL - The `useEffect` hook MUST return a cleanup function that removes the event listener to prevent memory leaks and duplicate listeners.

    ```typescript
    useEffect(() => {
      const handleKeyDown = (event: KeyboardEvent) => {
        // ... logic ...
      };
      document.addEventListener('keydown', handleKeyDown);
      return () => {
        document.removeEventListener('keydown', handleKeyDown);
      };
    }, [/* dependencies */]);
    ```

*   **Checking for Active Inputs/Modals:** Before processing a shortcut, always check if an input field, textarea, or an active modal dialog has focus. If so, the shortcut should generally be ignored to allow normal text input or modal-specific interactions.

    ```typescript
    const handleKeyDown = (event: KeyboardEvent) => {
      const activeElement = document.activeElement;
      const isInputFocused = activeElement instanceof HTMLInputElement || 
                             activeElement instanceof HTMLTextAreaElement || 
                             (activeElement && activeElement.getAttribute('role') === 'dialog');

      if (isInputFocused && event.key !== 'Escape') { // Allow Escape for modals
        return; // Don't process app-level shortcuts if typing in an input/modal
      }

      switch(event.key.toLowerCase()) {
        // ... case statements ...
      }
    };
    ```

*   **`event.preventDefault()`:** Call `event.preventDefault()` for shortcuts that are handled by the application to prevent default browser actions (e.g., 't' in some contexts might try to open a new tab, or arrow keys might scroll the page).

*   **`event.stopPropagation()` (Use Sparingly):** Only use `event.stopPropagation()` if you are certain that no parent components should also react to this specific key event. Overuse can make debugging event flow difficult.

## 3. State Interaction
*   **Dispatch Actions to Stores:** When a keyboard shortcut needs to modify shared application state, it should dispatch an action to the relevant Zustand store.
    *   Example: 't' key in `TodayView.tsx` calls `setFastInputFocused(true)` which is an action from `useTaskViewStore`.
*   **Call Local State Setters:** For purely local UI changes triggered by a shortcut, call the component's local state setter function.

## 4. Consistency & Discoverability
*   **Standard Keys (When Applicable):** Use common conventions where possible (e.g., 'Escape' to close modals, 'Enter' to submit forms if a submit button is focused).
*   **Clear Focus Indication:** Ensure that it's visually clear which element or section has focus, especially for shortcuts that operate on a focused item (e.g., 'e' to edit the focused task).
*   **Documentation (Future):** Consider a user-facing help section or tooltips to make shortcuts discoverable.

## 5. Example: `TodayView.tsx` Keyboard Shortcuts
*   **Event Listener:** `useEffect` in `TodayView.tsx` adds a `keydown` listener to `document`.
*   **Input Check:** The handler checks `document.activeElement`.
*   **Shortcut Logic (`switch` statement):**
    *   `'t'`: Sets `isFastInputFocused` in `useTaskViewStore` to true.
    *   `'e'`: Opens the detail modal for the `focusedTaskId` from `useTaskViewStore`.
    *   `'n'/'p'`: Finds the current index of `focusedTaskId` in `displayTasks`, calculates the next/previous ID, and calls `setFocusedTaskId` in `useTaskViewStore`.
*   **Dependencies:** The `useEffect` hook correctly lists dependencies like `focusedTaskId`, `displayTasks`, and store actions to ensure the handler always has the latest data and functions. 