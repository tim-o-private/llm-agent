import { useCallback } from 'react';
import { useOptimisticState } from './useOptimisticState';
import { useTaskStore } from '@/stores/useTaskStore';
import { Task } from '@/api/types';

export interface SubtaskManagementHook {
  // State
  optimisticSubtasks: Task[] | null;
  isSubtasksDirty: boolean;

  // Handlers for SubtaskList
  handleSubtaskChange: () => void;
  handleSubtaskReorder: (reorderedSubtasks: Task[]) => void;
  handleSubtaskCreate: (subtaskData: Partial<Task>) => void;
  handleSubtaskUpdate: (id: string, updates: Partial<Task>) => void;
  handleSubtaskDelete: (id: string) => void;

  // Save logic
  applyPendingSubtaskChanges: (taskId: string) => Promise<void>;

  // State management
  resetSubtaskState: () => void;
}

export function useSubtaskManagement(taskId: string | null): SubtaskManagementHook {
  const getSubtasks = useCallback(() => {
    return taskId ? useTaskStore.getState().getSubtasksByParentId(taskId) : [];
  }, [taskId]);

  const optimisticState = useOptimisticState<Task>(getSubtasks);

  // Create temp ID generator for subtasks
  const generateTempId = useCallback(() => `temp-${Date.now()}`, []);

  // Create subtask factory
  const createSubtask = useCallback(
    (subtaskData: Partial<Task>, tempId: string): Task => {
      const currentSubtasks = optimisticState.optimisticItems || getSubtasks();
      return {
        id: tempId,
        title: subtaskData.title || '',
        description: subtaskData.description || null,
        status: subtaskData.status || 'pending',
        priority: subtaskData.priority || 0,
        due_date: subtaskData.due_date || null,
        parent_task_id: subtaskData.parent_task_id || null,
        user_id: subtaskData.user_id || '',
        subtask_position: subtaskData.subtask_position || currentSubtasks.length,
        completed: false,
        deleted: false,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        subtasks: [],
      };
    },
    [optimisticState.optimisticItems, getSubtasks],
  );

  // Wrapper handlers that call the optimistic state handlers
  const handleSubtaskChange = useCallback(() => {
    // This is called by SubtaskList to indicate any change occurred
    // The actual dirty state is tracked by the optimistic state hook
  }, []);

  const handleSubtaskReorder = useCallback(
    (reorderedSubtasks: Task[]) => {
      optimisticState.handleReorder(reorderedSubtasks);
    },
    [optimisticState.handleReorder],
  );

  const handleSubtaskCreate = useCallback(
    (subtaskData: Partial<Task>) => {
      optimisticState.handleCreate(subtaskData, generateTempId, createSubtask);
    },
    [optimisticState.handleCreate, generateTempId, createSubtask],
  );

  const handleSubtaskUpdate = useCallback(
    (id: string, updates: Partial<Task>) => {
      optimisticState.handleUpdate(id, updates);
    },
    [optimisticState.handleUpdate],
  );

  const handleSubtaskDelete = useCallback(
    (id: string) => {
      optimisticState.handleDelete(id);
    },
    [optimisticState.handleDelete],
  );

  // Apply all pending changes to the database
  const applyPendingSubtaskChanges = useCallback(
    async (_currentTaskId: string) => {
      if (!optimisticState.isDirty) return;

      const { createTask, updateTask, deleteTask } = useTaskStore.getState();
      const { pendingChanges } = optimisticState;

      // Apply deletes first (but skip temporary IDs)
      for (const deleteId of pendingChanges.deletes) {
        if (!deleteId.startsWith('temp-')) {
          await deleteTask(deleteId);
        }
      }

      // Apply creates
      for (const createData of pendingChanges.creates) {
        if (createData.title && createData.user_id && createData.parent_task_id !== undefined) {
          await createTask(createData as Omit<Task, 'id' | 'created_at' | 'updated_at' | 'completed' | 'subtasks'>);
        }
      }

      // Apply updates (but skip temporary IDs)
      for (const { id, updates } of pendingChanges.updates) {
        if (!id.startsWith('temp-')) {
          await updateTask(id, updates);
        }
      }

      // Apply reorders (latest one)
      if (pendingChanges.reorders.length > 0) {
        const latestReorder = pendingChanges.reorders[pendingChanges.reorders.length - 1];
        const positionUpdates = latestReorder.items
          .map(async (subtask, index) => {
            if (subtask.subtask_position !== index) {
              return updateTask(subtask.id, { subtask_position: index });
            }
          })
          .filter(Boolean);

        await Promise.all(positionUpdates);
      }

      // Clear pending changes
      optimisticState.clearPendingChanges();
    },
    [optimisticState],
  );

  const resetSubtaskState = useCallback(() => {
    optimisticState.resetState();
  }, [optimisticState.resetState]);

  return {
    optimisticSubtasks: optimisticState.optimisticItems,
    isSubtasksDirty: optimisticState.isDirty,
    handleSubtaskChange,
    handleSubtaskReorder,
    handleSubtaskCreate,
    handleSubtaskUpdate,
    handleSubtaskDelete,
    applyPendingSubtaskChanges,
    resetSubtaskState,
  };
}
