# State Diagram: Generalized Modal Editor Flow (with React Hook Form)

**Objective:** Illustrate the user-perceived states and transitions for a modal editor that uses React Hook Form (RHF) for managing the primary entity's fields and allows for independent operations on child/related items.

```mermaid
graph TD
    A[Modal Closed] -->|User Action: Open Editor (e.g., Click Edit Task)| B(Opening Modal);

    B --> C{Data Loaded & RHF Initialized?};
    C -- Yes --> D[Modal Open: Pristine];
    C -- No (Loading/Error) --> E[Modal Open: Loading/Error State];
    E --> D; % Assuming eventual load or user closes/retries

    D -->|User Edits Parent Fields| F[Modal Open: Parent Dirty];
    F -->|User Reverts Parent Fields to Original| D;

    D -->|User Performs Child Operation (e.g., Add Subtask - Auto-saves)| G[Modal Open: Pristine + Child Op Occurred];
    F -->|User Performs Child Operation (e.g., Add Subtask - Auto-saves)| H[Modal Open: Parent Dirty + Child Op Occurred];
    G -->|User Edits Parent Fields| H;
    H -->|User Reverts Parent Fields to Original| G;


    %% Save Action Paths
    D -- User Clicks 'Save Changes' (Button should be Disabled) --> I_D[Save Action: No Parent Changes];
    I_D -->|Toast: "No changes to save"| D; %% Stays open

    F -- User Clicks 'Save Changes' --> J_F[Save Action: Parent Dirty];
    J_F --> K_F{Saving Parent...};
    K_F -- Success --> L_F[Parent Saved Successfully];
    L_F -->|Toast: "Saved", Reset RHF, Reset Child Op Flag| A; %% Closes
    K_F -- Error --> M_F[Save Error: Parent];
    M_F -->|Toast: "Error Saving"| F; %% Stays open, parent still dirty

    G -- User Clicks 'Save Changes' (Button should be Disabled if no parent changes logic is strict) --> I_G[Save Action: No Parent Changes, Child Op Occurred];
    I_G -->|Toast: "Child items saved automatically. No parent changes." Reset Child Op Flag| D; % Stays open, parent pristine

    H -- User Clicks 'Save Changes' --> J_H[Save Action: Parent Dirty, Child Op Occurred];
    J_H --> K_H{Saving Parent...};
    K_H -- Success --> L_H[Parent Saved Successfully];
    L_H -->|Toast: "Saved", Reset RHF, Reset Child Op Flag| A; %% Closes
    K_H -- Error --> M_H[Save Error: Parent];
    M_H -->|Toast: "Error Saving"| H; %% Stays open, parent dirty, child op occurred


    %% Cancel Action Paths
    D -- User Clicks 'Cancel/Close' --> A; %% No changes, closes directly

    F -- User Clicks 'Cancel/Close' --> N_F{Prompt: "Discard Parent Changes?"};
    N_F -- Confirms Discard --> O_F[Changes Discarded];
    O_F -->|Reset RHF| A; %% Closes
    N_F -- Cancels Discard --> F; % Stays open, parent dirty

    G -- User Clicks 'Cancel/Close' --> N_G{Prompt: "Recent child activity. Close?"}; %% Or, if child ops are minor, just close like D
    N_G -- Confirms Close --> O_G[Child Ops Acknowledged];
    O_G -->|Reset Child Op Flag| A; % Closes
    N_G -- Cancels Close --> G; % Stays open, child op occurred

    H -- User Clicks 'Cancel/Close' --> N_H{Prompt: "Discard Parent Changes & Acknowledge Child Activity?"};
    N_H -- Confirms Discard/Close --> O_H[Changes Discarded, Child Ops Acknowledged];
    O_H -->|Reset RHF, Reset Child Op Flag| A; %% Closes
    N_H -- Cancels Discard/Close --> H; % Stays open, parent dirty, child op occurred

    %% Style Notes
    classDef default fill:#ECECFF,stroke:#999,stroke-width:2px;
    classDef state fill:#FFF,stroke:#333,stroke-width:2px;
    classDef prompt fill:#FFEBCC,stroke:#FFA500,stroke-width:2px;
    classDef action fill:#E0F2F7,stroke:#007BFF,stroke-width:2px;

    class A,B,C,D,E,F,G,H,L_F,L_H,O_F,O_G,O_H state;
    class I_D,J_F,I_G,J_H action;
    class K_F,K_H,M_F,M_H state; %% intermediate/error states
    class N_F,N_G,N_H prompt;
```

**Key States & Flags:**

*   **Modal Open: Pristine:** RHF `formState.isDirty` is `false`. `childOperationOccurredInSessionRef.current` is `false`.
*   **Modal Open: Parent Dirty:** RHF `formState.isDirty` is `true`.
*   **Modal Open: Child Op Occurred:** `childOperationOccurredInSessionRef.current` is `true`. (Parent can be pristine or dirty).
*   **`childOperationOccurredInSessionRef`:** A `useRef(false)` flag that is set to `true` if any child item (e.g., subtask) is successfully added, deleted, or reordered *during the current modal session*. It's reset when the modal opens and potentially after a "Save" action that acknowledges these child changes.

**Save Logic Summary:**

1.  **Parent Changes (`isDirty` = true):**
    *   Submit parent form data via RHF's `handleSubmit`.
    *   On successful parent save: Toast success, reset RHF (to pristine), reset `childOperationOccurredInSessionRef`, close modal.
    *   On parent save error: Toast error, keep modal open, RHF remains dirty.
2.  **No Parent Changes (`isDirty` = false):**
    *   "Save Changes" button should ideally be disabled.
    *   If clicked:
        *   If `childOperationOccurredInSessionRef` is true (and child ops are auto-saved): Toast "Child items saved. No parent changes." Reset `childOperationOccurredInSessionRef`. Keep modal open (or close if preferred UX).
        *   If `childOperationOccurredInSessionRef` is false: Toast "No changes to save." Keep modal open.

**Cancel/Close Logic Summary:**

1.  If `formState.isDirty` (parent) is `true` OR `childOperationOccurredInSessionRef.current` is `true`:
    *   Show a confirmation prompt ("You have unsaved changes... Are you sure?").
    *   User Discards: Reset RHF (if dirty), reset `childOperationOccurredInSessionRef`, close modal.
    *   User Cancels Prompt: Modal remains open.
2.  Otherwise (no parent changes AND no child operations in session):
    *   Close modal directly without a prompt.

This diagram provides a good conceptual basis for the refactor. 