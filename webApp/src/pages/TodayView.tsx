import React, { useEffect, useCallback, useMemo, useRef, useState } from 'react';
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  DragEndEvent,
} from '@dnd-kit/core';
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  verticalListSortingStrategy,
} from '@dnd-kit/sortable';
import TaskListGroup from '@/components/tasks/TaskListGroup';
import { FastTaskInput } from '@/components/features/TodayView/FastTaskInput';
import { TaskDetailView } from '@/components/features/TaskDetail/TaskDetailView';
import { PrioritizeViewModal } from '@/components/features/PrioritizeView/PrioritizeViewModal';
import { PlusIcon } from '@radix-ui/react-icons';
import { Button } from '@/components/ui/Button';

import { useTaskStore } from '@/stores/useTaskStore';
import { useTaskStoreInitializer } from '@/hooks/useTaskStoreInitializer';
import { useTaskKeyboardNavigation } from '@/hooks/useTaskKeyboardNavigation';
import { useTaskModalManagement } from '@/hooks/useTaskModalManagement';

import { useCreateFocusSession, useUpdateTaskOrder } from '@/api/hooks/useTaskHooks';
import type { Task } from '@/api/types';
import { Spinner } from '@/components/ui';

import { toast } from '@/components/ui/toast';
import { useTaskViewStore } from '@/stores/useTaskViewStore';

const TodayView: React.FC = () => {
  
  const { isLoading: isLoadingTasks, error: fetchError, initialized } = useTaskStoreInitializer();
  const {
    updateTask,
    deleteTask,
    getSubtasksByParentId,
  } = useTaskStore(state => ({
    updateTask: state.updateTask,
    deleteTask: state.deleteTask,
    getSubtasksByParentId: state.getSubtasksByParentId,
  }));
  
  // Subscribe to the actual task data
  const topLevelTasksFromStore = useTaskStore(state => state.getTopLevelTasks());

  // Log topLevelTasksFromStore and taskDataSignature when they change
  useEffect(() => {
    console.log('[TodayView] topLevelTasksFromStore updated:', JSON.stringify(topLevelTasksFromStore.map(t => ({id: t.id, title: t.title, completed: t.completed, status: t.status})), null, 2));
  }, [topLevelTasksFromStore]);

  const { mutate: createFocusSession } = useCreateFocusSession();
  const { mutate: updateTaskOrderMutation } = useUpdateTaskOrder();

  // --- Component Local State for Modal Visibility ---
  const [isFastInputUiFocused, setIsFastInputUiFocused] = useState(false); // Local UI focus state

  // --- Zustand Store Selectors (Non-keyboard navigation) ---
  const selectedTaskIds = useTaskViewStore(state => state.selectedTaskIds);
  const toggleSelectedTask = useTaskViewStore(state => state.toggleSelectedTask);
  const removeSelectedTask = useTaskViewStore(state => state.removeSelectedTask);
  const setInputFocusState = useTaskViewStore(state => state.setInputFocusState);

  const fastInputRef = useRef<HTMLInputElement>(null);
  const isClosingModalRef = useRef(false); // Track when we're closing a modal to prevent auto-focus

  // --- Modal Management Hook ---
  const modalManagement = useTaskModalManagement({
    syncWithStore: true
  });

  // Memoize navigable tasks to prevent unnecessary re-creation
  const navigableTasks = useMemo(() => 
    topLevelTasksFromStore.map(task => ({ id: task.id })), 
    [topLevelTasksFromStore]
  );

  // --- Keyboard Navigation Hook (needs to be early to provide setFocusedTaskId) ---
  const keyboardNavigation = useTaskKeyboardNavigation({
    tasks: navigableTasks,
    isInputFocused: isFastInputUiFocused,
    config: {
      enabled: true,
      autoFocusFirst: true, // Keep this stable to avoid dependency issues
      clearFocusOnEmpty: true,
    }
  });

  // Destructure functions to avoid dependency issues
  const {
    focusedTaskId,
    setFocusedTaskId,
    initializeKeyboardListeners,
    destroyKeyboardListeners,
    requestOpenDetailForTaskId,
    clearDetailOpenRequest,
    requestFocusFastInput,
    clearFocusFastInputRequest,
  } = keyboardNavigation;

  // Custom modal close handler that preserves focus (after setFocusedTaskId is available)
  const handleModalCloseWithFocusRestore = useCallback((isOpen: boolean) => {
    if (!isOpen) {
      // Set flag to prevent auto-focus during modal close
      isClosingModalRef.current = true;
      
      // Get the task ID before closing the modal
      const taskIdToFocus = modalManagement.currentTaskId;
      
      // Close the modal
      modalManagement.closeModal();
      
      // Restore focus to the task that was being edited, but only if it still exists
      if (taskIdToFocus && topLevelTasksFromStore.some(task => task.id === taskIdToFocus)) {
        // Use a longer delay to ensure this runs after any competing auto-focus effects
        setTimeout(() => {
          // Double-check the task still exists before setting focus
          if (topLevelTasksFromStore.some(task => task.id === taskIdToFocus)) {
            setFocusedTaskId(taskIdToFocus);
          }
        }, 20); // Increased delay to ensure it runs after the keyboard navigation auto-focus
      }
      
      // Clear the flag after a brief delay to allow focus restoration to complete
      setTimeout(() => {
        isClosingModalRef.current = false;
      }, 100); // Increased delay to match the focus restoration timing
    }
  }, [modalManagement, setFocusedTaskId, topLevelTasksFromStore]);

  // --- Component-level Handlers ---
  const handleTaskCreatedByFastInput = useCallback((taskId: string) => {
    setIsFastInputUiFocused(false); // Update local UI state
    setInputFocusState(false); // Notify store
    if (taskId) {
      // Will be handled by keyboard navigation hook
    }
  }, [setInputFocusState]);

  const handleMarkComplete = useCallback((taskId: string) => {
    updateTask(taskId, { completed: true, status: 'completed' });
    removeSelectedTask(taskId);
  }, [updateTask, removeSelectedTask]);

  const handleDeleteTask = useCallback((taskId: string) => {
    deleteTask(taskId);
    if (modalManagement.isModalOpenForTask(taskId)) {
      modalManagement.closeModal();
    }
    // Focus clearing will be handled by keyboard navigation hook
    removeSelectedTask(taskId);
  }, [deleteTask, modalManagement, removeSelectedTask]);

  const handleStartTaskLegacy = useCallback((taskId: string) => {
    console.log(`[TodayView] Attempting to start task (legacy): ${taskId}`);
    updateTask(taskId, { status: 'in_progress' });
    createFocusSession(
      { task_id: taskId, planned_duration_minutes: 25 },
      {
        onSuccess: () => {
          toast.success('Focus session started for task.');
        },
        onError: () => {
          toast.error('Error creating focus session.');
          updateTask(taskId, { status: 'planning' });
        },
      }
    );
  }, [updateTask, createFocusSession]);

  const handleStartFocusSessionConfirmed = useCallback(async (task: Task, sessionConfig: { motivation?: string; completionNote?: string }) => {
    toast.success(`Task "${task.title}" ready for focus session.`);
    if (task.status !== 'in_progress' && task.status !== 'planning') {
      updateTask(task.id, { 
        status: 'planning',
        motivation: sessionConfig.motivation, 
        completion_note: sessionConfig.completionNote 
      });
    }
    modalManagement.closeModal();
  }, [updateTask, modalManagement]);
  
  const openDetailModalForTask = useCallback((taskId: string) => {
    modalManagement.detailModal.open(taskId);
  }, [modalManagement]);

  const openPrioritizeModalForTask = useCallback((taskId: string) => {
    modalManagement.prioritizeModal.open(taskId);
  }, [modalManagement]);

  // --- Derived Data (View Models for TaskCards) ---
  const displayTasksWithSubtasks = useMemo(() => {
    console.log('[TodayView] Recalculating displayTasksWithSubtasks...'); // Log when this recalculates
    if (!initialized) return [];
    if (!topLevelTasksFromStore || topLevelTasksFromStore.length === 0) return [];

    return topLevelTasksFromStore.map(task => {
      const subtasks = getSubtasksByParentId(task.id);
      return {
        ...task,
        onStartTask: () => handleStartTaskLegacy(task.id),
        onEdit: () => openDetailModalForTask(task.id),
        onFocus: (taskId: string) => setFocusedTaskId(taskId), // Now setFocusedTaskId is available
        isFocused: task.id === focusedTaskId, // Set focus state directly here
        isSelected: selectedTaskIds.has(task.id),
        onSelectTask: () => toggleSelectedTask(task.id),
        onMarkComplete: () => handleMarkComplete(task.id),
        onDeleteTask: () => handleDeleteTask(task.id),
        onStartFocus: () => openPrioritizeModalForTask(task.id),
        subtasks,
      };
    });
  }, [
    initialized,
    topLevelTasksFromStore,
    getSubtasksByParentId,
    focusedTaskId, // Now we can include focusedTaskId
    selectedTaskIds, 
    handleStartTaskLegacy,
    openDetailModalForTask,
    setFocusedTaskId,
    toggleSelectedTask,
    handleMarkComplete,
    handleDeleteTask,
    openPrioritizeModalForTask
  ]);

  // Use displayTasksWithSubtasks directly since focus is now included
  const displayTasksWithFocus = displayTasksWithSubtasks;

  // Initialize keyboard listeners on mount
  useEffect(() => {
    initializeKeyboardListeners();
    return () => {
      destroyKeyboardListeners();
    };
  }, [initializeKeyboardListeners, destroyKeyboardListeners]);

  // Handle keyboard shortcut requests
  useEffect(() => {
    if (requestOpenDetailForTaskId) {
      openDetailModalForTask(requestOpenDetailForTaskId);
      clearDetailOpenRequest();
    }
  }, [requestOpenDetailForTaskId, clearDetailOpenRequest, openDetailModalForTask]);

  useEffect(() => {
    if (requestFocusFastInput) {
      setIsFastInputUiFocused(true);
      if (fastInputRef.current) {
        fastInputRef.current.focus();
      }
      clearFocusFastInputRequest();
    }
  }, [requestFocusFastInput, clearFocusFastInputRequest]);

  // Handle task creation - focus the newly created task
  const handleTaskCreatedByFastInputWithFocus = useCallback((taskId: string) => {
    handleTaskCreatedByFastInput(taskId);
    if (taskId) {
      setFocusedTaskId(taskId);
    }
  }, [handleTaskCreatedByFastInput, setFocusedTaskId]);

  // DND functionality sensors (removed redundant focus management effect)
  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  );

  function handleDragEnd(event: DragEndEvent) {
    const { active, over } = event;

    if (active.id !== over?.id && over) {
      const currentTasks = topLevelTasksFromStore;
      const oldIndex = currentTasks.findIndex(task => task.id === active.id);
      const newIndex = currentTasks.findIndex(task => task.id === over.id);

      if (oldIndex === -1 || newIndex === -1) {
        console.warn('[TodayView] handleDragEnd: Task not found in current list. Aborting.');
        return;
      }

      // 1. Create the new optimistic order
      const optimisticallyReorderedTasks = arrayMove(currentTasks, oldIndex, newIndex);

      // 2. Optimistically update the Zustand store IMMEDIATELY
      // This ensures that topLevelTasksFromStore selector will return the new order quickly.
      optimisticallyReorderedTasks.forEach((task, index) => {
        if (task.position !== index) { // Check if position actually changed
          // Call the existing updateTask which handles local state and pendingChanges for sync
          useTaskStore.getState().updateTask(task.id, { position: index });
        }
      });

      // 3. Prepare updates for the backend batch operation
      const taskOrderUpdatesForBackend: Array<{ id: string; position: number }> = optimisticallyReorderedTasks.map((task, index) => ({
        id: task.id,
        position: index,
      }));
      
      // 4. Call the mutation to update backend
      if (taskOrderUpdatesForBackend.length > 0) {
        console.log('[TodayView] Calling updateTaskOrderMutation with:', taskOrderUpdatesForBackend);
        updateTaskOrderMutation(taskOrderUpdatesForBackend, {
          onSuccess: () => {
            console.log('[TodayView] updateTaskOrderMutation successful. Query invalidation should refresh the store from server.');
            // Query invalidation is handled by the useUpdateTaskOrder hook.
          },
          onError: (error) => {
            console.error('[TodayView] updateTaskOrderMutation failed:', error);
            toast.error("Failed to reorder tasks. Please try again.");
            // Consider a strategy to revert optimistic updates if backend fails, 
            // e.g., by refetching or rolling back store changes if the hook doesn't handle it.
          }
        });
      }
    }
  }

  if (isLoadingTasks) {
    return (
      <div className="flex justify-center items-center h-full">
        <Spinner size={32} /><p className="ml-2">Loading tasks...</p>
      </div>
    );
  }

  if (fetchError) {
    return (
      <div className="text-destructive p-4">
        Error loading tasks: {fetchError instanceof Error ? fetchError.message : String(fetchError)}
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-bold text-text-primary">Today</h1>
        <div className="flex items-center space-x-2">
          <Button variant="outline" onClick={() => {
            setIsFastInputUiFocused(true);
            // FastTaskInput's onFocused will call setInputFocusState(true)
          }}>
            <PlusIcon className="mr-2 h-4 w-4" /> New Task
          </Button>
        </div>
      </div>
      <div className="mb-6">
        <FastTaskInput 
            ref={fastInputRef}
            isFocused={isFastInputUiFocused} 
            onTaskCreated={handleTaskCreatedByFastInputWithFocus} 
            onBlurred={() => {
              setIsFastInputUiFocused(false);
              setInputFocusState(false);
            }}
            onFocused={() => { 
              // setIsFastInputUiFocused(true); // Already set by button click or requestFocusFastInput effect
              setInputFocusState(true);
            }}
        />
      </div>
      {displayTasksWithFocus.length === 0 ? (
        <div className="flex-grow flex flex-col items-center justify-center text-text-muted">
          <svg xmlns="http://www.w3.org/2000/svg" className="h-16 w-16 mb-4 opacity-50" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 8h14M5 8a2 2 0 110-4h14a2 2 0 110 4M5 8v10a2 2 0 002 2h10a2 0 002-2V8m-9 4h4" />
          </svg>
          <p className="text-lg">Your day is clear!</p>
          <p>Add some tasks to get started.</p>
        </div>
      ) : (
        <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
          <SortableContext items={displayTasksWithFocus.map(t => t.id)} strategy={verticalListSortingStrategy}>
            <TaskListGroup tasks={displayTasksWithFocus} title="Today's Tasks" />
          </SortableContext>
        </DndContext>
      )}

      {modalManagement.detailModal.isOpen && (
        <TaskDetailView
          taskId={modalManagement.detailModal.taskId!}
          isOpen={modalManagement.detailModal.isOpen}
          onOpenChange={handleModalCloseWithFocusRestore}
          onTaskUpdated={() => {}} 
          onDeleteTaskFromDetail={handleDeleteTask}
        />
      )}

      {modalManagement.prioritizeModal.isOpen && (
        <PrioritizeViewModal
          taskId={modalManagement.prioritizeModal.taskId!}
          isOpen={modalManagement.prioritizeModal.isOpen}
          onOpenChange={handleModalCloseWithFocusRestore}
          onStartFocusSession={handleStartFocusSessionConfirmed}
        />
      )}
    </div>
  );
};

export default TodayView; 