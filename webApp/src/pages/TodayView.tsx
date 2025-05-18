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
import { TaskCardProps } from '@/components/ui/TaskCard';
import { FastTaskInput } from '@/components/features/TodayView/FastTaskInput';
import { TaskDetailView } from '@/components/features/TaskDetail/TaskDetailView';
import { PrioritizeViewModal } from '@/components/features/PrioritizeView/PrioritizeViewModal';
import { ChatPanel } from '@/components/ChatPanel';
import { useChatStore } from '@/stores/useChatStore';
import { PlusIcon, ChatBubbleIcon, DoubleArrowRightIcon } from '@radix-ui/react-icons';
import { Button } from '@/components/ui/Button';

import { useTaskStore } from '@/stores/useTaskStore';
import { useTaskStoreInitializer } from '@/hooks/useTaskStoreInitializer';

import { useCreateFocusSession, useUpdateTaskOrder } from '@/api/hooks/useTaskHooks';
import type { Task, FocusSession } from '@/api/types';
import { Spinner } from '@/components/ui';

import { toast } from '@/components/ui/toast';
import { useTaskViewStore } from '@/stores/useTaskViewStore';

const mapTaskToTaskCardViewModel = (
  task: Task, 
  onStartTask: (id: string) => void,
  onEdit: (taskId: string) => void,
  isFocused: boolean,
  isSelected: boolean,
  onSelectTask: (taskId: string) => void,
  onMarkComplete: (taskId: string) => void,
  onDeleteTask: (taskId: string) => void,
  onStartFocus: (taskId: string) => void,
  processedSubtasks?: Task[]
): TaskCardProps => ({
  ...task,
  onStartTask: () => onStartTask(task.id),
  onEdit: () => onEdit(task.id),
  isFocused,
  isSelected,
  onSelectTask: () => onSelectTask(task.id),
  onMarkComplete: () => onMarkComplete(task.id),
  onDeleteTask: () => onDeleteTask(task.id),
  onStartFocus: () => onStartFocus(task.id),
  subtasks: processedSubtasks,
});

const TodayView: React.FC = () => {
  // Chat store
  const isChatPanelOpen = useChatStore((state) => state.isChatPanelOpen);
  const toggleChatPanel = useChatStore((state) => state.toggleChatPanel);
  
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

  // Create a simplified signature of relevant task data
  const taskDataSignature = useMemo(() => {
    if (!initialized || !topLevelTasksFromStore) return '';
    const signature = topLevelTasksFromStore.map(t => t.id + '-' + t.title + '-' + t.completed + '-' + t.status).join('|');
    console.log('[TodayView] taskDataSignature calculated:', signature);
    return signature;
  }, [initialized, topLevelTasksFromStore]);

  // --- Component Local State for Modal Visibility ---
  const [currentDetailTaskId, setCurrentDetailTaskId] = useState<string | null>(null);
  const [currentPrioritizeTaskId, setCurrentPrioritizeTaskId] = useState<string | null>(null);
  const [isFastInputUiFocused, setIsFastInputUiFocused] = useState(false); // Local UI focus state

  // --- Zustand Store Selectors ---
  const focusedTaskId = useTaskViewStore(state => state.focusedTaskId);
  const setFocusedTaskId = useTaskViewStore(state => state.setFocusedTaskId);
  const selectedTaskIds = useTaskViewStore(state => state.selectedTaskIds);
  const toggleSelectedTask = useTaskViewStore(state => state.toggleSelectedTask);
  const removeSelectedTask = useTaskViewStore(state => state.removeSelectedTask);

  // New store interactions for keyboard shortcuts and centralized state management
  const setCurrentNavigableTasks = useTaskViewStore(state => state.setCurrentNavigableTasks);
  const requestOpenDetailForTaskId = useTaskViewStore(state => state.requestOpenDetailForTaskId);
  const clearDetailOpenRequest = useTaskViewStore(state => state.clearDetailOpenRequest);
  const requestFocusFastInput = useTaskViewStore(state => state.requestFocusFastInput);
  const clearFocusFastInputRequest = useTaskViewStore(state => state.clearFocusFastInputRequest);
  const setModalOpenState = useTaskViewStore(state => state.setModalOpenState);
  const setInputFocusState = useTaskViewStore(state => state.setInputFocusState);

  const fastInputRef = useRef<HTMLInputElement>(null);

  // --- Component-level Handlers ---
  const handleTaskCreatedByFastInput = useCallback((taskId: string) => {
    setIsFastInputUiFocused(false); // Update local UI state
    setInputFocusState(false); // Notify store
    if (taskId) {
      setFocusedTaskId(taskId);
    }
  }, [setInputFocusState, setFocusedTaskId]);

  const handleMarkComplete = useCallback((taskId: string) => {
    updateTask(taskId, { completed: true, status: 'completed' });
    removeSelectedTask(taskId);
  }, [updateTask, removeSelectedTask]);

  const handleDeleteTask = useCallback((taskId: string) => {
    deleteTask(taskId);
    if (currentDetailTaskId === taskId) {
      setCurrentDetailTaskId(null);
      setModalOpenState(taskId, false); 
    }
    if (focusedTaskId === taskId) {
      setFocusedTaskId(null);
    }
    removeSelectedTask(taskId);
  }, [deleteTask, currentDetailTaskId, focusedTaskId, setFocusedTaskId, removeSelectedTask, setModalOpenState]);

  const handleStartTaskLegacy = useCallback((taskId: string) => {
    console.log(`[TodayView] Attempting to start task (legacy): ${taskId}`);
    updateTask(taskId, { status: 'in_progress' });
    createFocusSession(
      { task_id: taskId },
      {
        onSuccess: (_focusSession: FocusSession | null) => {
          toast.success('Focus session started for task.');
        },
        onError: (_err: Error) => {
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
    setModalOpenState(task.id, false); 
    setCurrentPrioritizeTaskId(null); // Close local view of this modal
  }, [updateTask, setModalOpenState]);
  
  const openDetailModalForTask = useCallback((taskId: string) => {
      setCurrentDetailTaskId(taskId);
      setModalOpenState(taskId, true);
  }, [setModalOpenState]);

  const openPrioritizeModalForTask = useCallback((taskId: string) => {
      setCurrentPrioritizeTaskId(taskId);
      setModalOpenState(taskId, true);
  }, [setModalOpenState]);

  // --- Derived Data (View Models for TaskCards) ---
  const displayTasksWithSubtasks = useMemo(() => {
    console.log('[TodayView] Recalculating displayTasksWithSubtasks...'); // Log when this recalculates
    if (!initialized) return [];
    if (!topLevelTasksFromStore || topLevelTasksFromStore.length === 0) return [];

    return topLevelTasksFromStore.map(task => {
      const subtasks = getSubtasksByParentId(task.id);
      return mapTaskToTaskCardViewModel(
        task, 
        handleStartTaskLegacy,
        openDetailModalForTask, // Use new handler
        task.id === focusedTaskId,
        selectedTaskIds.has(task.id),
        toggleSelectedTask,
        handleMarkComplete,
        handleDeleteTask,
        openPrioritizeModalForTask, // Use new handler
        subtasks
      );
    });
  }, [
    initialized,
    taskDataSignature, // Using the new signature
    getSubtasksByParentId,
    focusedTaskId, 
    selectedTaskIds, 
    handleStartTaskLegacy,
    openDetailModalForTask,
    toggleSelectedTask,
    handleMarkComplete,
    handleDeleteTask,
    openPrioritizeModalForTask
  ]);

  // Handle focusing the first task if needed
  useEffect(() => {
    if (!focusedTaskId && displayTasksWithSubtasks.length > 0 && !isFastInputUiFocused) {
      setFocusedTaskId(displayTasksWithSubtasks[0].id);
    }
  }, [displayTasksWithSubtasks, focusedTaskId, isFastInputUiFocused, setFocusedTaskId]);

  // Provide current navigable tasks to the store
  useEffect(() => {
    const taskIdsForStore = displayTasksWithSubtasks.map(task => ({ id: task.id }));
    setCurrentNavigableTasks(taskIdsForStore);
  }, [displayTasksWithSubtasks, setCurrentNavigableTasks]);

  // Handle request to open detail view from store shortcut
  useEffect(() => {
    if (requestOpenDetailForTaskId) {
      openDetailModalForTask(requestOpenDetailForTaskId);
      clearDetailOpenRequest();
    }
  }, [requestOpenDetailForTaskId, openDetailModalForTask, clearDetailOpenRequest]);

  // Handle request to focus fast input from store shortcut
  useEffect(() => {
    if (requestFocusFastInput) {
      setIsFastInputUiFocused(true); // Set local UI state
      if (fastInputRef.current) {
        fastInputRef.current.focus();
      }
      // No need to call setInputFocusState(true) here, as FastTaskInput's onFocused will do it.
      clearFocusFastInputRequest();
    }
  }, [requestFocusFastInput, clearFocusFastInputRequest]);

  // DND functionality sensors
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
      const storeUpdates: { [id: string]: Partial<Task> } = {};
      optimisticallyReorderedTasks.forEach((task, index) => {
        if (task.position !== index) { // Check if position actually changed
          storeUpdates[task.id] = { position: index }; // Collect updates for Zustand state
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
      <div className="text-red-500 p-4">
        Error loading tasks: {fetchError instanceof Error ? fetchError.message : String(fetchError)}
      </div>
    );
  }

  return (
    <div className="flex h-full">
      <div className="flex-1 flex flex-col p-4 md:p-6 lg:p-8 overflow-y-auto relative">
        <div className="flex justify-between items-center mb-6">
          <h1 className="text-3xl font-bold text-gray-800 dark:text-white">Today</h1>
          <div className="flex items-center space-x-2">
            <Button variant="secondary" onClick={() => {
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
              onTaskCreated={handleTaskCreatedByFastInput} 
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
        {displayTasksWithSubtasks.length === 0 ? (
          <div className="flex-grow flex flex-col items-center justify-center text-gray-500 dark:text-gray-400">
            <svg xmlns="http://www.w3.org/2000/svg" className="h-16 w-16 mb-4 opacity-50" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 8h14M5 8a2 2 0 110-4h14a2 2 0 110 4M5 8v10a2 2 0 002 2h10a2 2 0 002-2V8m-9 4h4" />
            </svg>
            <p className="text-lg">Your day is clear!</p>
            <p>Add some tasks to get started.</p>
          </div>
        ) : (
          <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
            <SortableContext items={displayTasksWithSubtasks.map(t => t.id)} strategy={verticalListSortingStrategy}>
              <TaskListGroup tasks={displayTasksWithSubtasks} title="Today's Tasks" />
            </SortableContext>
          </DndContext>
        )}

        {currentDetailTaskId && (
          <TaskDetailView
            taskId={currentDetailTaskId}
            isOpen={currentDetailTaskId !== null}
            onOpenChange={(isOpenFromDialog) => { 
              setModalOpenState(currentDetailTaskId, isOpenFromDialog);
              if (!isOpenFromDialog) {
                setCurrentDetailTaskId(null); 
                if (currentDetailTaskId === requestOpenDetailForTaskId) {
                    clearDetailOpenRequest();
                }
              }
            }}
            onTaskUpdated={() => {}} 
            onDeleteTaskFromDetail={handleDeleteTask}
          />
        )}

        {currentPrioritizeTaskId && (
          <PrioritizeViewModal
            taskId={currentPrioritizeTaskId}
            isOpen={currentPrioritizeTaskId !== null}
            onOpenChange={(isOpenFromDialog) => { 
              setModalOpenState(currentPrioritizeTaskId, isOpenFromDialog);
              if (!isOpenFromDialog) {
                setCurrentPrioritizeTaskId(null);
              }
            }}
            onStartFocusSession={handleStartFocusSessionConfirmed}
          />
        )}
      </div>

      {/* Persistent Chat Panel Area with Integrated Toggle Button */}
      <div 
        className={`fixed top-0 right-0 h-full z-50 transition-all duration-300 ease-in-out border-l border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 shadow-xl flex
                    ${isChatPanelOpen ? 'w-full max-w-md md:max-w-sm' : 'w-16'}`}
      >
        {/* Always visible Toggle Button Area */} 
        <button
          onClick={toggleChatPanel}
          className="w-16 h-full flex flex-col items-center justify-center py-4 text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 focus:outline-none flex-shrink-0"
          aria-label={isChatPanelOpen ? "Close chat panel" : "Open chat panel"}
        >
          {isChatPanelOpen ? <DoubleArrowRightIcon className="h-6 w-6" /> : <ChatBubbleIcon className="h-6 w-6" />}
          {!isChatPanelOpen && <span className="text-xs mt-1">Chat</span>} {/* Optional: Text label when collapsed */}
        </button>

        {/* Conditionally rendered ChatPanel content area */}
        {isChatPanelOpen && (
          <div className="flex-grow h-full relative"> {/* Container for ChatPanel to take remaining space */}
            <ChatPanel />
          </div>
        )}
      </div>
    </div>
  );
};

export default TodayView; 