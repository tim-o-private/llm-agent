import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
import { immer } from 'zustand/middleware/immer';
import { enableMapSet } from 'immer';
// import type { Task } from '@/api/types'; // Task type no longer needed directly in store state

enableMapSet(); // Initialize Immer's MapSet plugin

export interface TaskViewState {
  // rawTasks: Task[]; // Removed
  focusedTaskId: string | null;
  selectedTaskIds: Set<string>;
  
  // Keyboard shortcut related state
  currentNavigableTasks: Array<{ id: string }>;
  isSystemBusy: boolean; // True if an input is focused or a modal is open
  inputFocusCount: number; // Count of focused inputs
  activeModalIdentifiers: Set<string>; // IDs of currently open modals
  
  // UI Action Requests - store signals, UI components react
  requestOpenDetailForTaskId: string | null;
  requestFocusFastInput: boolean;

  // Old state, to be reviewed if still needed or can be derived/managed differently
  // isFastInputFocused: boolean; // Potentially replaced by requestFocusFastInput + component state
  // detailViewTaskId: string | null; // Potentially replaced by requestOpenDetailForTaskId + component state
  // prioritizeModalTaskId: string | null; // Needs to integrate with activeModalIdentifiers
}

export interface TaskViewActions {
  // setRawTasks: (tasks: Task[]) => void; // Removed
  clearTaskRelatedState: () => void; // Renamed from clearRawTasks, focuses on UI state
  setFocusedTaskId: (taskId: string | null) => void;
  toggleSelectedTask: (taskId: string) => void;
  addSelectedTask: (taskId: string) => void;
  removeSelectedTask: (taskId: string) => void;
  clearSelectedTasks: () => void;

  // Context from UI
  setCurrentNavigableTasks: (tasks: Array<{ id: string }>) => void;
  setInputFocusState: (isFocused: boolean) => void; // Called by inputs onFocus/onBlur
  setModalOpenState: (modalIdentifier: string, isOpen: boolean) => void; // Called by modals onOpen/onClose

  // Responding to UI after a shortcut request
  clearDetailOpenRequest: () => void;
  clearFocusFastInputRequest: () => void;

  // Keyboard handling lifecycle and processing
  initializeListener: () => void;
  destroyListener: () => void;
  _processKeyDown: (event: KeyboardEvent) => void; // Internal, called by the global listener

  // Actions to be reviewed based on new request patterns
  // openDetailModal: (taskId: string) => void; // Should now use requestOpenDetailForTaskId
  // closeDetailModal: () => void; // Should use setModalOpenState
  // openPrioritizeModal: (taskId: string) => void; // Should use setModalOpenState + potentially a request
  // closePrioritizeModal: () => void; // Should use setModalOpenState
  // setFastInputFocused: (isFocused: boolean) => void; // Likely remove, use requestFocusFastInput
}

const initialState: TaskViewState = {
  // rawTasks: [], // Removed
  focusedTaskId: null,
  selectedTaskIds: new Set(),
  currentNavigableTasks: [],
  isSystemBusy: false,
  inputFocusCount: 0,
  activeModalIdentifiers: new Set(),
  requestOpenDetailForTaskId: null,
  requestFocusFastInput: false,
  // Legacy state initialization removed
};

// Define the store type including actions
type TaskViewStore = TaskViewState & TaskViewActions;

// This function is defined outside the create callback so it's stable
// and can be added/removed as the event listener.
const handleGlobalKeyDown = (event: KeyboardEvent) => {
  useTaskViewStore.getState()._processKeyDown(event);
};

export const useTaskViewStore = create<TaskViewStore>()(
  devtools(
    immer((set, get) => ({
      ...initialState,
      // setRawTasks: (tasks) => set(state => { state.rawTasks = tasks; }), // Removed
      clearTaskRelatedState: () => set(state => { 
        // state.rawTasks = []; // Removed
        state.focusedTaskId = null; 
        state.selectedTaskIds.clear(); 
        state.currentNavigableTasks = [];
        // state.isSystemBusy = false; // Recalculated by focus/modal state
        // state.inputFocusCount = 0; // Resetting these might be too aggressive here
        // state.activeModalIdentifiers.clear(); 
        state.requestOpenDetailForTaskId = null;
        state.requestFocusFastInput = false;
        // No need to reset legacy state here as it's removed
      }),
      setFocusedTaskId: (taskId) => set(state => { state.focusedTaskId = taskId; }),
      toggleSelectedTask: (taskId) => set(state => {
        if (state.selectedTaskIds.has(taskId)) {
          state.selectedTaskIds.delete(taskId);
        } else {
          state.selectedTaskIds.add(taskId);
        }
      }),
      addSelectedTask: (taskId) => set(state => { state.selectedTaskIds.add(taskId); }),
      removeSelectedTask: (taskId) => set(state => { state.selectedTaskIds.delete(taskId); }),
      clearSelectedTasks: () => set(state => { state.selectedTaskIds.clear(); }),

      setCurrentNavigableTasks: (tasks) => set(state => { state.currentNavigableTasks = tasks; }),
      
      setInputFocusState: (isFocused) =>
        set((state) => {
          if (isFocused) {
            state.inputFocusCount += 1;
          } else {
            state.inputFocusCount = Math.max(0, state.inputFocusCount - 1);
          }
          state.isSystemBusy = state.inputFocusCount > 0 || state.activeModalIdentifiers.size > 0;
        }),

      setModalOpenState: (modalIdentifier, isOpen) =>
        set((state) => {
          if (isOpen) {
            state.activeModalIdentifiers.add(modalIdentifier);
          } else {
            state.activeModalIdentifiers.delete(modalIdentifier);
          }
          state.isSystemBusy = state.inputFocusCount > 0 || state.activeModalIdentifiers.size > 0;
          
          // If a modal is opening, clear any pending detail request unless it's the detail modal itself.
          // This handles cases where a shortcut might have requested a detail view, but another modal pops up first.
          if (isOpen && state.requestOpenDetailForTaskId && modalIdentifier !== state.requestOpenDetailForTaskId) {
             // Assuming modalIdentifier for detail view would be the task ID or a specific string like 'taskDetailModal'
             // This logic might need refinement based on how detail modals are identified.
          }
          // If a modal is closing, and it was the one requested, clear the request.
          if (!isOpen && state.requestOpenDetailForTaskId === modalIdentifier) {
            // This also needs careful thought on how `requestOpenDetailForTaskId` relates to `modalIdentifier`
            // state.requestOpenDetailForTaskId = null; 
          }
        }),
      
      clearDetailOpenRequest: () => set((state) => { state.requestOpenDetailForTaskId = null; }),
      clearFocusFastInputRequest: () => set((state) => { state.requestFocusFastInput = false; }),

      initializeListener: () => {
        if (!(window as any).__taskViewStoreListenerAttached) {
          window.addEventListener('keydown', handleGlobalKeyDown);
          (window as any).__taskViewStoreListenerAttached = true;
          console.log('[TaskViewStore] Global keyboard listener initialized.');
        }
      },
      destroyListener: () => {
        if ((window as any).__taskViewStoreListenerAttached) {
          window.removeEventListener('keydown', handleGlobalKeyDown);
          (window as any).__taskViewStoreListenerAttached = false;
          console.log('[TaskViewStore] Global keyboard listener destroyed.');
        }
      },

      _processKeyDown: (event: KeyboardEvent) => {
        const state = get();

        // Always allow Escape for modals to handle themselves, or for global deselect/defocus
        if (event.key === 'Escape') {
            if (state.activeModalIdentifiers.size > 0) {
                // Modals should handle their own escape. Store doesn't interfere.
                return;
            }
            // If no modals, Escape could clear focus or selection
            if (state.focusedTaskId) {
                event.preventDefault();
                set({ focusedTaskId: null });
                return;
            }
            if (state.selectedTaskIds.size > 0) {
                event.preventDefault();
                get().clearSelectedTasks();
                return;
            }
            // Potentially close other UI elements if any are "escape-closable" via store
            return; 
        }
        
        // If system is busy (input focus or modal open), ignore other shortcuts
        if (state.isSystemBusy) {
          // Check if the event target is an input/textarea. If so, allow typing.
          // The onFocus/onBlur of these elements should correctly set inputFocusCount.
          if (
            event.target instanceof HTMLInputElement ||
            event.target instanceof HTMLTextAreaElement ||
            (event.target instanceof HTMLElement && event.target.isContentEditable)
          ) {
            // Typing is allowed. The inputFocusCount handles isSystemBusy.
            return;
          }
          console.log('[TaskViewStore] System busy, ignoring key:', event.key);
          return;
        }

        const { currentNavigableTasks, focusedTaskId } = state;
        const hasTasks = currentNavigableTasks.length > 0;
        const focusedIndex = focusedTaskId && hasTasks
          ? currentNavigableTasks.findIndex((t) => t.id === focusedTaskId)
          : -1;

        let newFocusedId: string | null = null;

        switch (event.key.toLowerCase()) {
          case 'arrowdown':
          case 'j':
            event.preventDefault();
            if (hasTasks) {
              if (focusedIndex === -1 || focusedIndex === currentNavigableTasks.length - 1) {
                newFocusedId = currentNavigableTasks[0].id; // Loop to start or select first
              } else {
                newFocusedId = currentNavigableTasks[focusedIndex + 1].id;
              }
              set({ focusedTaskId: newFocusedId });
            }
            break;
          case 'arrowup':
          case 'k':
            event.preventDefault();
            if (hasTasks) {
              if (focusedIndex === -1 || focusedIndex === 0) {
                newFocusedId = currentNavigableTasks[currentNavigableTasks.length - 1].id; // Loop to end or select last
              } else {
                newFocusedId = currentNavigableTasks[focusedIndex - 1].id;
              }
              set({ focusedTaskId: newFocusedId });
            }
            break;
          case 'enter':
          case 'e':
            if (focusedTaskId) {
              event.preventDefault();
              set({ requestOpenDetailForTaskId: focusedTaskId });
            } else if (hasTasks && currentNavigableTasks[0]?.id) { // Open first task if none focused
              event.preventDefault();
              set({ requestOpenDetailForTaskId: currentNavigableTasks[0].id })
            }
            break;
          case ' ': // Spacebar
            if (focusedTaskId) {
              event.preventDefault();
              get().toggleSelectedTask(focusedTaskId);
            }
            break;
          case 'a':
          case 't':
            if (!event.ctrlKey && !event.metaKey) {
              event.preventDefault();
              set({ requestFocusFastInput: true });
            }
            break;
          default:
            // Allow other keys to bubble up if not handled
            return; 
        }
      },

      // Legacy/Review actions
      // These should be re-evaluated. Components should react to `requestOpenDetailForTaskId` or use `setModalOpenState`.
      // openDetailModal: (taskId) => {
      //   console.warn("Legacy openDetailModal called. Use requestOpenDetailForTaskId pattern.");
      //   set(state => { 
      //     state.requestOpenDetailForTaskId = taskId;
      //     // Also need to set modal open state if this direct action is kept
      //     // state.activeModalIdentifiers.add(taskId); // Or a generic 'detailModal' identifier
      //     // state.isSystemBusy = true;
      //     state.detailViewTaskId = taskId; // Legacy
      //   });
      // },
      // closeDetailModal: () => {
      //   console.warn("Legacy closeDetailModal called. Use setModalOpenState pattern.");
      //   set(state => {
      //     // const modalId = state.detailViewTaskId; // Or generic 'detailModal'
      //     // if (modalId) state.activeModalIdentifiers.delete(modalId);
      //     // state.isSystemBusy = state.inputFocusCount > 0 || state.activeModalIdentifiers.size > 0;
      //     state.detailViewTaskId = null; // Legacy
      //     if (state.requestOpenDetailForTaskId === state.detailViewTaskId) { // Check if this was the requested one
      //       state.requestOpenDetailForTaskId = null;
      //     }
      //   });
      // },
      // openPrioritizeModal: (taskId) => {
      //   console.warn("Legacy openPrioritizeModal called. Use setModalOpenState pattern.");
      //   set(state => {
      //     state.activeModalIdentifiers.add(taskId); // Or 'prioritizeModal'
      //     state.isSystemBusy = true;
      //     state.prioritizeModalTaskId = taskId; // Legacy
      //   });
      // },
      // closePrioritizeModal: () => {
      //   console.warn("Legacy closePrioritizeModal called. Use setModalOpenState pattern.");
      //   set(state => {
      //     // const modalId = state.prioritizeModalTaskId; // Or 'prioritizeModal'
      //     // if (modalId) state.activeModalIdentifiers.delete(modalId);
      //     // state.isSystemBusy = state.inputFocusCount > 0 || state.activeModalIdentifiers.size > 0;
      //     state.prioritizeModalTaskId = null; // Legacy
      //   });
      // },
      // setFastInputFocused: (isFocused) => {
      //   console.warn("Legacy setFastInputFocused called. Use requestFocusFastInput pattern.");
      //   set(state => {
      //      state.isFastInputFocused = isFocused; // Legacy
      //      if(isFocused) state.requestFocusFastInput = true;
      //      // This doesn't correctly interact with inputFocusCount for isSystemBusy
      //   });
      // }
    })),
    { name: 'TaskViewStore' }
  )
);

// Old useKeyboardShortcuts hook removed entirely.
// All related imports like useEffect from react (if only used by this hook) are also removed or would be by a linter.

// Remove the invalidateTasksQuery helper from here if it's causing issues or is duplicated.
// It relies on useQueryClient and useAuthStore, which might be better scoped elsewhere or passed in.
// export const invalidateTasksQuery = () => {
//   const queryClient = useQueryClient();
//   const userId = useAuthStore.getState().user?.id;
//   if (userId) {
//     queryClient.invalidateQueries({ queryKey: ['tasks', userId] });
//   }
// }; 