import React, { useEffect, useCallback, useMemo } from 'react';
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
import { PlusIcon, ChatBubbleIcon, Cross1Icon } from '@radix-ui/react-icons';
import { Button } from '@/components/ui/Button';

import { useFetchTasks, useUpdateTask, useUpdateTaskOrder, useCreateFocusSession, useDeleteTask } from '@/api/hooks/useTaskHooks';
import type { Task, FocusSession } from '@/api/types';
import { Spinner } from '@/components/ui';
import { useQueryClient, UseMutationResult } from '@tanstack/react-query';

import { toast } from 'react-hot-toast';
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
  onStartFocus: (taskId: string) => void
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
});

const TodayView: React.FC = () => {
  const queryClient = useQueryClient();
  
  // Chat store
  const isChatPanelOpen = useChatStore((state) => state.isChatPanelOpen);
  const toggleChatPanel = useChatStore((state) => state.toggleChatPanel);
  
  // API hooks
  const { data: tasksFromAPI = [], isLoading: isLoadingTasks, error: fetchError } = useFetchTasks();
  const updateTaskMutation = useUpdateTask();
  const { mutate: updateTaskOrder } = useUpdateTaskOrder();
  const { mutate: createFocusSession } = useCreateFocusSession();
  const deleteTaskMutationHook: UseMutationResult<Task | null, Error, { id: string }, unknown> = useDeleteTask();

  // --- Connect to useTaskViewStore ---
  const rawTasks = useTaskViewStore(state => state.rawTasks);
  const setRawTasks = useTaskViewStore(state => state.setRawTasks);
  const focusedTaskId = useTaskViewStore(state => state.focusedTaskId);
  const setFocusedTaskId = useTaskViewStore(state => state.setFocusedTaskId);
  const selectedTaskIds = useTaskViewStore(state => state.selectedTaskIds);
  const toggleSelectedTask = useTaskViewStore(state => state.toggleSelectedTask);
  const isFastInputFocused = useTaskViewStore(state => state.isFastInputFocused);
  const setFastInputFocused = useTaskViewStore(state => state.setFastInputFocused);
  const detailViewTaskId = useTaskViewStore(state => state.detailViewTaskId);
  const openDetailModal = useTaskViewStore(state => state.openDetailModal);
  const closeDetailModal = useTaskViewStore(state => state.closeDetailModal);
  const prioritizeModalTaskId = useTaskViewStore(state => state.prioritizeModalTaskId);
  const openPrioritizeModal = useTaskViewStore(state => state.openPrioritizeModal);
  const closePrioritizeModal = useTaskViewStore(state => state.closePrioritizeModal);
  const reorderRawTasks = useTaskViewStore(state => state.reorderRawTasks);
  const removeSelectedTask = useTaskViewStore(state => state.removeSelectedTask);

  // Effect to sync API tasks to store
  useEffect(() => {
    // Compare tasksFromAPI with current rawTasks in the store
    // Only update if they are different to prevent infinite loops
    if (tasksFromAPI.length !== rawTasks.length) {
      setRawTasks(tasksFromAPI);
      return;
    }
    // If lengths are the same, check if IDs match in the same order
    for (let i = 0; i < tasksFromAPI.length; i++) {
      if (tasksFromAPI[i].id !== rawTasks[i].id) {
        setRawTasks(tasksFromAPI);
        return;
      }
    }
    // If we reach here, tasks are considered the same, no update needed.
  }, [tasksFromAPI, rawTasks, setRawTasks]); // rawTasks and setRawTasks are now dependencies

  // --- Component-level Handlers (mainly for API calls) ---
  const invalidateTasksQuery = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: ['tasks'] });
  }, [queryClient]);

  const handleTaskCreatedByFastInput = useCallback((createdTask: Task) => {
    invalidateTasksQuery();
    setFastInputFocused(false);
    if (createdTask && createdTask.id) {
      setFocusedTaskId(createdTask.id);
    }
  }, [invalidateTasksQuery, setFastInputFocused, setFocusedTaskId]);

  const handleTaskUpdated = useCallback(() => {
    invalidateTasksQuery();
  }, [invalidateTasksQuery]);

  const handleTaskDeletedFromDetail = useCallback(() => {
    invalidateTasksQuery();
    closeDetailModal();
  }, [invalidateTasksQuery, closeDetailModal]);
  
  const handleMarkComplete = useCallback((taskId: string) => {
    updateTaskMutation.mutate(
      { id: taskId, updates: { completed: true, status: 'completed' } }, 
      {
        onSuccess: () => {
          toast.success('Task marked complete!');
          invalidateTasksQuery();
          removeSelectedTask(taskId);
        },
        onError: (err: Error) => toast.error(`Error marking task complete: ${err.message}`),
      }
    );
  }, [updateTaskMutation, invalidateTasksQuery, removeSelectedTask]);

  const handleDeleteTask = useCallback((taskId: string) => {
    deleteTaskMutationHook.mutate({ id: taskId }, {
      onSuccess: () => {
        toast.success('Task deleted!');
        invalidateTasksQuery();
        if (detailViewTaskId === taskId) {
          closeDetailModal();
        }
        if (focusedTaskId === taskId) {
          setFocusedTaskId(null);
        }
        removeSelectedTask(taskId);
      },
      onError: (err: Error) => toast.error(`Error deleting task: ${err.message}`),
    });
  }, [deleteTaskMutationHook, invalidateTasksQuery, detailViewTaskId, closeDetailModal, focusedTaskId, setFocusedTaskId, removeSelectedTask]);

  const handleStartTaskLegacy = useCallback((taskId: string) => {
    console.log(`[TodayView] Attempting to start task (legacy): ${taskId}`);
    updateTaskMutation.mutate(
      { id: taskId, updates: { status: 'in_progress' } },
      {
        onSuccess: (_updatedTaskResponse: Task | null) => {
          createFocusSession(
            { task_id: taskId },
            {
              onSuccess: (_focusSession: FocusSession | null) => {
                toast.success(`Focus session started for task.`);
                invalidateTasksQuery();
              },
              onError: (_err: Error) => {
                toast.error('Error creating focus session.');
                updateTaskMutation.mutate({ id: taskId, updates: { status: 'planning' } });
              },
            }
          );
        },
        onError: (err: Error) => toast.error(`Error updating task status: ${err.message}`),
      }
    );
  }, [updateTaskMutation, createFocusSession, invalidateTasksQuery]);

  const handleStartFocusSessionConfirmed = useCallback(async (task: Task, sessionConfig: { motivation?: string; completionNote?: string }) => {
    toast.success(`Task "${task.title}" ready for focus session.`);
    if (task.status !== 'in_progress' && task.status !== 'planning') {
      try {
        await updateTaskMutation.mutateAsync({
          id: task.id,
          updates: { 
            status: 'planning',
            motivation: sessionConfig.motivation, 
            completion_note: sessionConfig.completionNote 
          },
        });
        invalidateTasksQuery();
      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : 'Unknown error';
        toast.error(`Failed to update task details for focus session: ${errorMessage}`);
      }
    }
    closePrioritizeModal();
  }, [updateTaskMutation, invalidateTasksQuery, closePrioritizeModal]);

  // --- Derived Data (View Models for TaskCards) ---
  const displayTasks = useMemo(() => {
    if (!rawTasks || rawTasks.length === 0) {
      return [];
    }
    return rawTasks.map(task => 
      mapTaskToTaskCardViewModel(
        task,
        handleStartTaskLegacy,
        openDetailModal,
        task.id === focusedTaskId,
        selectedTaskIds.has(task.id),
        toggleSelectedTask,
        handleMarkComplete,
        handleDeleteTask,
        openPrioritizeModal
      )
    );
  }, [
    rawTasks, 
    focusedTaskId, 
    selectedTaskIds, 
    handleStartTaskLegacy,
    openDetailModal,
    toggleSelectedTask,
    handleMarkComplete,
    handleDeleteTask,
    openPrioritizeModal
  ]);

  // Handle focusing the first task if needed
  useEffect(() => {
    if (rawTasks.length > 0 && focusedTaskId === null) {
      setFocusedTaskId(rawTasks[0].id);
    } else if (rawTasks.length > 0 && focusedTaskId !== null) {
      const focusedTaskExists = rawTasks.some(task => task.id === focusedTaskId);
      if (!focusedTaskExists) {
        setFocusedTaskId(rawTasks[0].id);
      }
    } else if (rawTasks.length === 0 && focusedTaskId !== null) {
      setFocusedTaskId(null);
    }
  }, [rawTasks, focusedTaskId, setFocusedTaskId]);

  // Handle keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      const activeElement = document.activeElement;
      const isDetailModalOpen = detailViewTaskId !== null;
      const isPrioritizeViewOpen = prioritizeModalTaskId !== null;
      const isAnyModalOpen = isDetailModalOpen || isPrioritizeViewOpen || !!document.querySelector('[role="dialog"][data-state="open"]');
      const isInputActive = activeElement instanceof HTMLInputElement || activeElement instanceof HTMLTextAreaElement;

      if (isAnyModalOpen || isInputActive) return;

      switch(event.key.toLowerCase()) {
        case 't':
          event.preventDefault();
          setFastInputFocused(true);
          break;
        case 'e':
          event.preventDefault();
          if (focusedTaskId) openDetailModal(focusedTaskId);
          else if (displayTasks.length > 0) openDetailModal(displayTasks[0].id);
          break;
        case 'n':
          if (displayTasks.length > 0) {
            const currentIndex = displayTasks.findIndex(item => item.id === focusedTaskId);
            if (currentIndex === -1) {
              setFocusedTaskId(displayTasks[0].id);
            } else if (currentIndex < displayTasks.length - 1) {
              setFocusedTaskId(displayTasks[currentIndex + 1].id);
            }
          }
          break;
        case 'p':
          if (displayTasks.length > 0) {
            const currentIndex = displayTasks.findIndex(item => item.id === focusedTaskId);
            if (currentIndex === -1) {
              setFocusedTaskId(displayTasks[displayTasks.length - 1].id);
            } else if (currentIndex > 0) {
              setFocusedTaskId(displayTasks[currentIndex - 1].id);
            }
          }
          break;
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [displayTasks, focusedTaskId, detailViewTaskId, prioritizeModalTaskId, setFocusedTaskId, openDetailModal, setFastInputFocused]);

  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  );

  function handleDragEnd(event: DragEndEvent) {
    const {active, over} = event;
    
    if (over && active.id !== over.id) {
      // The store's reorderRawTasks expects activeId and overId
      // Keep a snapshot of tasks before reordering for backend update
      const currentTasks = [...rawTasks];
      const oldIndex = currentTasks.findIndex((item: Task) => item.id === active.id);
      const newIndex = currentTasks.findIndex((item: Task) => item.id === over.id);
      
      if (oldIndex === -1 || newIndex === -1) return; // Should not happen if IDs are correct

      const newOrderedItems = arrayMove(currentTasks, oldIndex, newIndex);
      
      // Update task order in backend
      const taskOrderUpdates = newOrderedItems.map((task: Task, index: number) => ({
        id: task.id,
        position: index,
      }));
      updateTaskOrder(taskOrderUpdates);
      
      // Update local state using activeId and overId for the store's action
      reorderRawTasks(active.id.toString(), over.id.toString());
    }
  }

  if (isLoadingTasks) {
    return (
      <div className="w-full h-full flex items-center justify-center p-4 md:p-6 lg:p-8">
        <Spinner size={40} />
        <p className="ml-2">Loading tasks...</p>
      </div>
    );
  }

  if (fetchError) {
    return (
      <div className="w-full h-full flex flex-col items-center justify-center text-red-600 p-4 md:p-6 lg:p-8">
        <p>Error loading tasks: {fetchError.message}</p>
      </div>
    );
  }

  return (
    <div className="flex h-full">
      <div className="flex-1 flex flex-col p-4 md:p-6 lg:p-8 overflow-y-auto relative">
        <div className="flex justify-between items-center mb-6">
          <h1 className="text-3xl font-bold text-gray-800 dark:text-white">Today</h1>
          <div className="flex items-center space-x-2">
            <Button variant="secondary" onClick={() => alert('New task (not implemented yet)')}>
              <PlusIcon className="mr-2 h-4 w-4" /> New Task
            </Button>
            <Button variant="secondary" onClick={toggleChatPanel}>
              <ChatBubbleIcon className="h-5 w-5" />
            </Button>
          </div>
        </div>
        <div className="mb-6">
          <FastTaskInput 
              isFocused={isFastInputFocused} 
              onTaskCreated={handleTaskCreatedByFastInput} 
              onBlurred={() => setFastInputFocused(false)}
          />
        </div>
        {rawTasks.length === 0 ? (
          <div className="flex-grow flex flex-col items-center justify-center text-gray-500 dark:text-gray-400">
            <svg xmlns="http://www.w3.org/2000/svg" className="h-16 w-16 mb-4 opacity-50" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 8h14M5 8a2 2 0 110-4h14a2 2 0 110 4M5 8v10a2 2 0 002 2h10a2 2 0 002-2V8m-9 4h4" />
            </svg>
            <p className="text-lg">Your day is clear!</p>
            <p>Add some tasks to get started.</p>
          </div>
        ) : (
          <DndContext 
            sensors={sensors}
            collisionDetection={closestCenter}
            onDragEnd={handleDragEnd}
          >
            <SortableContext 
              items={rawTasks.map(task => task.id)} 
              strategy={verticalListSortingStrategy}
            >
              <div className="flex-grow overflow-y-auto space-y-8">
                <TaskListGroup title="All Tasks" tasks={displayTasks} />
              </div>
            </SortableContext>
          </DndContext>
        )}

        {detailViewTaskId && (
          <TaskDetailView
            taskId={detailViewTaskId}
            isOpen={detailViewTaskId !== null}
            onOpenChange={(isOpenFromDialog) => { if (!isOpenFromDialog) closeDetailModal(); }}
            onTaskUpdated={handleTaskUpdated}
            onTaskDeleted={handleTaskDeletedFromDetail}
            onDeleteTaskFromDetail={handleDeleteTask}
          />
        )}

        {prioritizeModalTaskId && (
          <PrioritizeViewModal
            taskId={prioritizeModalTaskId}
            isOpen={prioritizeModalTaskId !== null}
            onOpenChange={(isOpenFromDialog) => { if (!isOpenFromDialog) closePrioritizeModal(); }}
            onStartFocusSession={handleStartFocusSessionConfirmed}
          />
        )}
      </div>

      {isChatPanelOpen && (
        <div className="fixed top-0 right-0 h-full w-full max-w-md md:max-w-sm bg-white dark:bg-gray-800 shadow-xl z-50 transform transition-transform duration-300 ease-in-out translate-x-0 border-l border-gray-200 dark:border-gray-700">
          <button
            onClick={toggleChatPanel}
            className="absolute top-4 right-4 p-1 rounded-full bg-gray-100 hover:bg-gray-200 dark:bg-gray-700 dark:hover:bg-gray-600 focus:outline-none focus:ring-2 focus:ring-gray-400 z-10"
            aria-label="Close chat panel"
          >
            <Cross1Icon className="h-5 w-5 text-gray-500 dark:text-gray-400" />
          </button>
          <ChatPanel />
        </div>
      )}
    </div>
  );
};

export default TodayView; 