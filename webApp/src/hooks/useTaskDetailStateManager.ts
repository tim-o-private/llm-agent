import { useCallback } from 'react';
import { isEqual, cloneDeep } from 'lodash-es';
import { Task, UpdateTaskData, NewTaskData, TaskPriority, TaskStatus } from '@/api/types';
import { TaskFormData } from '@/components/features/TaskDetail/TaskDetailView';
import { 
  useEntityEditManager, 
  EntityEditManagerOptions,  
} from '@/hooks/useEntityEditManager';

// Define the structure for store actions more explicitly
interface StoreActions {
  updateTask: (taskId: string, updates: UpdateTaskData) => void;
  deleteTask: (taskId: string) => void;
  createTask: (taskData: Omit<NewTaskData, 'user_id'>) => string;
}

// Define the composite data structure for the task detail view
export interface TaskDetailData {
  parentTask: TaskFormData;
  subtasks: Task[];
}

export interface UseTaskDetailStateManagerOptions {
  taskId: string | null;
  storeParentTask: Task | undefined;
  getParentFormValues: () => TaskFormData;
  localSubtasks: Task[];
  storeActions: StoreActions;
  onSaveComplete: () => void;
}

export interface UseTaskDetailStateManagerResult {
  isModalDirty: boolean;
  initializeState: (currentParentFormData: TaskFormData, currentSubtasks: Task[]) => void;
  resetState: () => void;
  handleSaveChanges: () => Promise<void>;
}

// Helper to prepare the initial data for the generic hook
const prepareInitialTaskDetailData = (
  parentTaskData: Task | undefined,
  initialParentFormData: TaskFormData | undefined, // from RHF defaultValues
  initialLocalSubtasks: Task[] // Changed parameter name for clarity
): TaskDetailData | undefined => {
  if (!parentTaskData && !initialParentFormData) return undefined;
  
  const parentForm = initialParentFormData ? cloneDeep(initialParentFormData) :
    parentTaskData ? {
      title: parentTaskData.title,
      description: parentTaskData.description || '',
      notes: parentTaskData.notes || '',
      category: parentTaskData.category || '',
      due_date: parentTaskData.due_date || null,
      status: parentTaskData.status || ('pending' as TaskStatus),
      priority: parentTaskData.priority || (0 as TaskPriority),
    } : {
      title: '',
      description: '',
      notes: '',
      category: '',
      due_date: null,
      status: 'pending' as TaskStatus,
      priority: 0 as TaskPriority,
    };

  return {
    parentTask: parentForm,
    subtasks: cloneDeep(initialLocalSubtasks), // Use the passed local subtasks
  };
};

export function useTaskDetailStateManager({
  taskId,
  storeParentTask,
  getParentFormValues,
  localSubtasks,
  storeActions,
  onSaveComplete,
}: UseTaskDetailStateManagerOptions): UseTaskDetailStateManagerResult {

  const initialData = prepareInitialTaskDetailData(storeParentTask, getParentFormValues(), localSubtasks);

  const getLatestDataForManager = useCallback((): TaskDetailData => {
    return {
      parentTask: getParentFormValues(),
      subtasks: localSubtasks, 
    };
  }, [getParentFormValues, localSubtasks]);

  const taskSaveHandler = useCallback(async (
    currentData: TaskDetailData,
    originalData: TaskDetailData,
    actions: StoreActions,
    entityId?: string | null // This will be our taskId
  ) => {
    if (!entityId) { // storeParentTask check removed, rely on entityId from generic manager
      console.error("Cannot save, Task ID is missing.");
      return false; // Indicate save was not attempted or failed pre-condition
    }

    const { parentTask: currentParentFormData, subtasks: currentLocalSubtasks } = currentData;
    const { parentTask: originalParentSnapshot, subtasks: originalSubtasksSnapshot } = originalData;

    // 1. Save Parent Task Changes
    if (!isEqual(currentParentFormData, originalParentSnapshot)) {
      const updatePayload: UpdateTaskData = {};
      if (currentParentFormData.title !== originalParentSnapshot.title) updatePayload.title = currentParentFormData.title;
      if (currentParentFormData.description !== originalParentSnapshot.description) updatePayload.description = currentParentFormData.description;
      if (currentParentFormData.notes !== originalParentSnapshot.notes) updatePayload.notes = currentParentFormData.notes;
      if (currentParentFormData.category !== originalParentSnapshot.category) updatePayload.category = currentParentFormData.category;
      const formDueDate = currentParentFormData.due_date ? new Date(currentParentFormData.due_date).toISOString() : null;
      const snapshotDueDate = originalParentSnapshot.due_date ? new Date(originalParentSnapshot.due_date).toISOString() : null;
      if (formDueDate !== snapshotDueDate) updatePayload.due_date = formDueDate;
      if (currentParentFormData.status !== originalParentSnapshot.status) updatePayload.status = currentParentFormData.status;
      if (currentParentFormData.priority !== originalParentSnapshot.priority) updatePayload.priority = currentParentFormData.priority;
      
      if (Object.keys(updatePayload).length > 0) {
        console.log("[TaskDetailStateManager] Updating parent task:", entityId, updatePayload);
        actions.updateTask(entityId, updatePayload);
      }
    }

    // 2. Save Subtask Changes
    // Find deleted subtasks
    originalSubtasksSnapshot.forEach(snapSub => {
      if (!currentLocalSubtasks.find(localSub => localSub.id === snapSub.id)) {
        console.log("[TaskDetailStateManager] Deleting subtask:", snapSub.id);
        actions.deleteTask(snapSub.id);
      }
    });

    // Find new or updated subtasks
    for (const [index, localSub] of currentLocalSubtasks.entries()) {
      const snapSub = originalSubtasksSnapshot.find(s => s.id === localSub.id);
      const newPosition = index + 1;

      if (!snapSub) {
        // New subtask
        const newSubtaskPayload: Omit<NewTaskData, 'user_id'> = {
          title: localSub.title,
          status: localSub.status || 'pending',
          priority: localSub.priority || 0,
          parent_task_id: entityId, 
          subtask_position: newPosition,
          description: localSub.description,
          notes: localSub.notes,
          category: localSub.category,
          due_date: localSub.due_date,
        };
        console.log("[TaskDetailStateManager] Creating subtask:", newSubtaskPayload);
        actions.createTask(newSubtaskPayload);
      } else {
        // Existing subtask, check for updates
        const subtaskUpdatePayload: UpdateTaskData = {};
        if (localSub.title !== snapSub.title) subtaskUpdatePayload.title = localSub.title;
        if (localSub.status !== snapSub.status) subtaskUpdatePayload.status = localSub.status;
        if (localSub.priority !== snapSub.priority) subtaskUpdatePayload.priority = localSub.priority;
        if (newPosition !== snapSub.subtask_position) subtaskUpdatePayload.subtask_position = newPosition;
        if (localSub.description !== snapSub.description) subtaskUpdatePayload.description = localSub.description;
        if (localSub.notes !== snapSub.notes) subtaskUpdatePayload.notes = localSub.notes;
        if (localSub.category !== snapSub.category) subtaskUpdatePayload.category = localSub.category;
        if (localSub.due_date !== snapSub.due_date) subtaskUpdatePayload.due_date = localSub.due_date;

        if (Object.keys(subtaskUpdatePayload).length > 0) {
          console.log("[TaskDetailStateManager] Updating subtask:", localSub.id, subtaskUpdatePayload);
          actions.updateTask(localSub.id, subtaskUpdatePayload);
        }
      }
    }
    return true; // Indicate save was processed
  }, []); // storeParentTask removed from dependencies

  const managerOptions: EntityEditManagerOptions<TaskDetailData, StoreActions> = {
    entityId: taskId,
    initialData,
    storeActions,
    onSaveComplete,
    saveHandler: taskSaveHandler,
    getLatestData: getLatestDataForManager,
    // isDataEqual and cloneData will use lodash-es defaults from the generic hook
  };

  const {
    isDirty: isModalDirty,
    initializeState: genericInitializeState,
    resetState: genericResetState,
    handleSaveChanges,
  } = useEntityEditManager<TaskDetailData, StoreActions>(managerOptions);

  // Adapt initializeState to fit the expected signature if TaskDetailView needs it this way
  // Or, TaskDetailView could be updated to pass a single TaskDetailData object.
  const initializeState = useCallback((currentParentFormData: TaskFormData, currentSubtasks: Task[]) => {
    genericInitializeState({ parentTask: currentParentFormData, subtasks: currentSubtasks });
  }, [genericInitializeState]);

  // resetState can be directly returned if its signature matches or if TaskDetailView doesn't call it with params
  const resetState = useCallback(() => {
    // This resetState from useEntityEditManager will reset based on its own `initialData`.
    // We might need to ensure `initialData` for the generic hook is correctly re-evaluated if the modal
    // is closed and reopened for a *different* task, or if `storeParentTask` / `localSubtasks` (as props) change.
    // The useEffect in useEntityEditManager handling `initialData` prop changes should cover this.
    genericResetState();
  }, [genericResetState]);

  return {
    isModalDirty,
    initializeState,
    resetState, // This is now the reset from the generic manager
    handleSaveChanges, // This is now the save from the generic manager
  };
} 