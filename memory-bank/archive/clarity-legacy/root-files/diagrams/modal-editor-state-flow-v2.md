%% Notes:
%% takeSnapshot captures the current state of parents and children
%% Save does not immediately trigger a synch to the database, but 

flowchart TD
    openModal[User Opens Modal] --> takeSnapshot[Snapshot initial state of parents & children]
    takeSnapshot --> isStateDirty{Did user make any changes to parents or children?}
    isStateDirty -- No --> stateIsPristine[State is pristine]
    isStateDirty -- Yes --> isDirty[State is dirty]
    stateIsPristine --> pristineExit{User clicks cancel, Save, or close}
    pristineExit --> discardSnapshot[Discard Snapshot, Close Modal]
    isDirty --> dirtyCancel{User clicks cancel}
    dirtyCancel --> discardPrompt[Prompt: 'Discard changes?' Options: Yes, Cancel]
    discardPrompt -- Yes --> discardSnapshot
    discardPrompt -- Cancel --> K[Return to modal]
    isDirty --> L{User clicks Save}
    L -- Any --> M[Persist state, reset dirty flag, close modal]
