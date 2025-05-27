sequenceDiagram
    actor User
    participant TDV as TaskDetailView
    participant UDSM as useTaskDetailStateManager
    participant UTS as useTaskStore
    participant SB as Supabase

    User->>TDV: Edits a field (e.g., Status)
    TDV->>UDSM: (via RHF) Form value changes
    UDSM->>UDSM: Calculates isModalDirty = true
    Note over TDV,UDSM: "Save Changes" button enabled

    User->>TDV: Clicks "Save Changes"
    TDV->>UDSM: Calls handleSaveChanges()

    UDSM->>UDSM: Verifies isModalDirty is true
    UDSM->>UDSM: Compares current form data with parentTaskSnapshot
    UDSM->>UTS: storeActions.updateTask(taskId, updatePayload)

    UTS->>UTS: Optimistically updates tasks[taskId] in local state (Immer)
    UTS->>UTS: Adds/updates entry in pendingChanges[taskId] (action: 'update')
    Note over UTS: Zustand notifies subscribers. TDV might re-render if subscribed to the specific task, showing optimistic update.

    UTS->>UTS: Schedules syncWithServer() (e.g., via setTimeout)

    loop Occasional Background Sync or Triggered Sync
        UTS->>UTS: syncWithServer() checks pendingChanges
        alt Has 'update' for taskId
            UTS->>SB: supabase.from('tasks').update(updatePayload).eq('id', taskId).select().single()
            SB-->>UTS: Returns { data: updatedTaskFromServer, error }
            alt No Error
                UTS->>UTS: Updates tasks[taskId] = updatedTaskFromServer (server-confirmed data)
                UTS->>UTS: Removes entry from pendingChanges[taskId]
                Note over UTS: Zustand notifies subscribers. UI reflects server-confirmed state.
            else Error
                UTS->>UTS: Handles error (e.g., logs, increments retryCount in pendingChanges)
                UTS->>User: Shows error toast "Failed to sync tasks"
            end
        end
    end

    UDSM->>TDV: onSaveComplete() (called after optimistic updates initiated by UDSM)
    TDV->>TDV: Closes modal (onOpenChange(false))
    TDV->>User: Shows toast "Changes saved!" (from UDSM)


    Note right of User: User later re-opens the same task.
    User->>TDV: Opens modal for the same taskId
    TDV->>UTS: storeParentTask = useTaskStore.getTaskById(taskId)
    Note over TDV,UTS: storeParentTask should now be the server-confirmed version (or latest optimistic if sync hasn't occurred for that specific change but optimistic update did)
    TDV->>TDV: useEffect initializes form with storeParentTask data