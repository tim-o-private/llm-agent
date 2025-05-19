```mermaid
sequenceDiagram
    participant TDV as TaskDetailView
    participant RHF_OEM as useObjectEditManager (RHF)
    participant RL as useReorderableList
    participant TDSM as useTaskDetailStateManager
    participant EEM as useEntityEditManager
    participant Store as useTaskStore

    alt Initialization (Modal Open / TaskID Change)
        TDV->>Store: Get storeParentTask, storeSubtasks
        Store-->>TDV: ParentTask, Subtasks Data
        TDV->>RHF_OEM: resetParentForm(parentData)
        TDV->>RL: setLocalSubtasks(storeSubtasks)
        TDV->>TDSM: initializeState(parentFormData, localSubtasks)
        TDSM->>EEM: genericInitializeState({parentTask, subtasks})
        EEM->>EEM: setSnapshot(cloneDeep(data))
        EEM->>EEM: setIsDirty(false)
    end

    alt User Edits Parent Task
        TDV->>RHF_OEM: User interacts with form fields
        RHF_OEM->>RHF_OEM: Updates RHF form state (isDirty)
    end

    alt User Edits Subtasks (e.g., DND, Add, Local Edit)
        TDV->>RL: User interacts with subtask list (DND, add, etc.)
        RL->>RL: Updates localSubtasks state
        RL-->>TDV: Exposes updated localSubtasks
    end
    
    alt Dirty Check (Ongoing)
        TDSM->>EEM: (Internally EEM does this)
        EEM->>RHF_OEM: (via TDSM.getLatestData.parentTask) getParentFormValues()
        RHF_OEM-->>EEM: Current Parent Form Data
        EEM->>RL: (via TDSM.getLatestData.subtasks) localSubtasks
        RL-->>EEM: Current Subtasks Data
        EEM->>EEM: newDirtyState = !isEqual(latestData, snapshot)
        EEM->>EEM: setIsDirty(newDirtyState)
        EEM-->>TDSM: Exposes isDirty (as isModalDirty)
        TDSM-->>TDV: Exposes isModalDirty
    end

    alt Save Changes
        TDV->>TDSM: handleSaveChanges()
        TDSM->>EEM: handleSaveChanges()
        EEM->>EEM: Calls configured saveHandler (taskSaveHandler in TDSM) with latestData, snapshot, storeActions
        Note over EEM,TDSM: taskSaveHandler in TDSM:
        TDSM->>TDSM: Compare currentParentFormData with snapshot
        opt Parent Task Changed
            TDSM->>Store: updateTask(taskId, parentUpdatePayload)
        end
        TDSM->>TDSM: Compare currentLocalSubtasks with snapshot
        loop For each Subtask Change (Delete, Create, Update)
            TDSM->>Store: deleteTask(subId) / createTask(newSub) / updateTask(subId, subUpdatePayload)
        end
        EEM->>EEM: setSnapshot(cloneDeep(latestData))
        EEM->>EEM: setIsDirty(false)
        EEM-->>TDSM: (Save successful)
        TDSM->>TDV: Calls onSaveComplete() (closes modal)
    end

    alt Cancel/Close Modal
        TDV->>TDV: handleModalCancelOrClose()

        alt isModalDirty (from TDSM) is true
            TDV->>User: window.confirm("Discard changes?")
            opt User confirms
                TDV->>TDV: onOpenChange(false)
                TDV->>TDSM: resetState() is called upon close if modal closes
                TDSM->>EEM: genericResetState()
                EEM->>EEM: setSnapshot(initialData from TDSM)
                EEM->>EEM: setIsDirty(false)
            end
        else isModalDirty (from TDSM) is false
            TDV->>TDV: onOpenChange(false)
            TDV->>TDSM: resetState() is called upon close if modal closes
            TDSM->>EEM: genericResetState()
            EEM->>EEM: setSnapshot(initialData from TDSM)
            EEM->>EEM: setIsDirty(false)
        end
    end
```

### Hook Interaction Summary:

*   **`TaskDetailView (TDV)`**: Orchestrator.
    *   Gets initial data from `useTaskStore`.
    *   Uses `useObjectEditManager (RHF_OEM)` for parent task form state.
    *   Uses `useReorderableList (RL)` for subtask list local state and DND.
    *   Uses `useTaskDetailStateManager (TDSM)` for overall dirty state, snapshotting, and save logic.
*   **`useObjectEditManager (RHF_OEM)`**: Manages React Hook Form state for the parent task. Returns form methods and RHF's `isDirty`.
*   **`useReorderableList (RL)`**: Manages the local list of subtasks, DND events, and local CRUD on that list.
*   **`useTaskDetailStateManager (TDSM)`**:
    *   Wraps `useEntityEditManager (EEM)`.
    *   Prepares composite data (`TaskDetailData` = parent + subtasks) for EEM.
    *   Defines `getLatestData` for EEM by fetching current parent form values from RHF_OEM and current subtasks from RL.
    *   Defines `taskSaveHandler` for EEM, which calculates deltas and calls `useTaskStore` actions for persistence.
*   **`useEntityEditManager (EEM)`**:
    *   Core generic logic for snapshotting, dirty checking (`isDataEqual`), and invoking a `saveHandler`.
    *   Manages `snapshot` and `isDirty` state.
*   **`useTaskStore (Store)`**: Zustand store, the single source of truth for task data and persistence to backend. Provides actions like `getTaskById`, `getSubtasksByParentId`, `updateTask`, `createTask`, `deleteTask`.

This setup aims for separation of concerns:
*   RHF for form details.
*   DND-kit for list reordering.
*   EEM for generic entity edit lifecycle (snapshot, dirty, save delegation).
*   TDSM to specialize EEM for the `TaskDetailData` structure and its specific save logic via `useTaskStore`.
*   TDV to integrate these hooks and manage the UI. 