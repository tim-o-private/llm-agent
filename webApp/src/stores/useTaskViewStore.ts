import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
import { immer } from 'zustand/middleware/immer';
import { enableMapSet } from 'immer';
import type { Task } from '@/api/types'; // This path will be correct if this file is in webApp/src/stores/

enableMapSet(); // Initialize Immer's MapSet plugin

export interface TaskViewState {
  rawTasks: Task[];
  focusedTaskId: string | null;
  selectedTaskIds: Set<string>;
  isFastInputFocused: boolean;
  detailViewTaskId: string | null;
  prioritizeModalTaskId: string | null;
}

export interface TaskViewActions {
  setRawTasks: (tasks: Task[]) => void;
  clearRawTasks: () => void;
  setFocusedTaskId: (taskId: string | null) => void;
  setFastInputFocused: (isFocused: boolean) => void;
  toggleSelectedTask: (taskId: string) => void;
  addSelectedTask: (taskId: string) => void;
  removeSelectedTask: (taskId: string) => void;
  clearSelectedTasks: () => void;
  openDetailModal: (taskId: string) => void;
  closeDetailModal: () => void;
  openPrioritizeModal: (taskId: string) => void;
  closePrioritizeModal: () => void;
  reorderRawTasks: (activeId: string, overId: string) => void;
}

const initialState: TaskViewState = {
  rawTasks: [],
  focusedTaskId: null,
  selectedTaskIds: new Set(),
  isFastInputFocused: false,
  detailViewTaskId: null,
  prioritizeModalTaskId: null,
};

// Define the store type including actions
type TaskViewStore = TaskViewState & TaskViewActions;

export const useTaskViewStore = create<TaskViewStore>()(
  devtools(
    immer((set) => ({
      ...initialState,
      setRawTasks: (tasks) => set(state => { state.rawTasks = tasks; }),
      clearRawTasks: () => set(state => { 
        state.rawTasks = []; 
        state.focusedTaskId = null; 
        state.selectedTaskIds.clear(); 
        state.detailViewTaskId = null;
        state.prioritizeModalTaskId = null;
        state.isFastInputFocused = false;
      }),
      setFocusedTaskId: (taskId) => set(state => { state.focusedTaskId = taskId; }),
      setFastInputFocused: (isFocused) => set(state => { state.isFastInputFocused = isFocused; }),
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
      openDetailModal: (taskId) => set(state => { state.detailViewTaskId = taskId; }),
      closeDetailModal: () => set(state => { state.detailViewTaskId = null; }),
      openPrioritizeModal: (taskId) => set(state => { state.prioritizeModalTaskId = taskId; }),
      closePrioritizeModal: () => set(state => { state.prioritizeModalTaskId = null; }),
      reorderRawTasks: (activeId, overId) => set(state => {
        const oldIndex = state.rawTasks.findIndex(task => task.id === activeId);
        const newIndex = state.rawTasks.findIndex(task => task.id === overId);
        if (oldIndex !== -1 && newIndex !== -1 && oldIndex !== newIndex) {
          const reorderedTasks = Array.from(state.rawTasks);
          const [movedItem] = reorderedTasks.splice(oldIndex, 1);
          reorderedTasks.splice(newIndex, 0, movedItem);
          state.rawTasks = reorderedTasks;
        }
      }),
    })),
    { name: 'TaskViewStore' }
  )
);

// Remove the invalidateTasksQuery helper from here if it's causing issues or is duplicated.
// It relies on useQueryClient and useAuthStore, which might be better scoped elsewhere or passed in.
// export const invalidateTasksQuery = () => {
//   const queryClient = useQueryClient();
//   const userId = useAuthStore.getState().user?.id;
//   if (userId) {
//     queryClient.invalidateQueries({ queryKey: ['tasks', userId] });
//   }
// }; 