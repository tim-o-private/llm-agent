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
import { PlusIcon, ChatBubbleIcon, DoubleArrowRightIcon } from '@radix-ui/react-icons';
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

  // --- Zustand Store Selectors for UI state ---
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
  const removeSelectedTask = useTaskViewStore(state => state.removeSelectedTask);

  // Local state for optimistic UI updates for main task drag, if needed
  // This will be set on drag start and cleared on drag end (success/error of mutation)
  // Or, we can rely purely on React Query's refetch for simplicity first.
  // For now, let's remove direct optimistic updates here and rely on RQ refetch.

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
  const displayTasksWithSubtasks = useMemo(() => {
    console.log('[TodayView] Recalculating displayTasksWithSubtasks. tasksFromAPI:', JSON.stringify(tasksFromAPI.map(t => ({id: t.id, title: t.title, parent_id: t.parent_task_id, subtask_pos: t.subtask_position, main_pos: t.position}))));
    if (!tasksFromAPI || tasksFromAPI.length === 0) {
      return [];
    }

    const tasksById = new Map(tasksFromAPI.map(task => [task.id, { ...task, subtasks: [] as Task[] }]));
    const rootTasks: Array<Task & { subtasks: Task[] }> = [];

    tasksFromAPI.forEach(task => {
      const taskWithSubtasks = tasksById.get(task.id)!;
      if (task.parent_task_id && tasksById.has(task.parent_task_id)) {
        tasksById.get(task.parent_task_id)!.subtasks.push(taskWithSubtasks);
      } else {
        rootTasks.push(taskWithSubtasks);
      }
    });

    tasksById.forEach(taskEntry => {
      if (taskEntry.subtasks.length > 0) {
        taskEntry.subtasks.sort((a, b) => 
          (a.subtask_position ?? Infinity) - (b.subtask_position ?? Infinity) || 
          new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
        );
      }
    });
    
    const mappedRootTasks = rootTasks.map(task => 
      mapTaskToTaskCardViewModel(
        task, 
        handleStartTaskLegacy,
        openDetailModal,
        task.id === focusedTaskId,
        selectedTaskIds.has(task.id),
        toggleSelectedTask,
        handleMarkComplete,
        handleDeleteTask,
        openPrioritizeModal,
        task.subtasks
      )
    );
    console.log('[TodayView] Finished recalculating displayTasksWithSubtasks. Result count:', mappedRootTasks.length);
    return mappedRootTasks;
  }, [
    tasksFromAPI,
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
    if (tasksFromAPI.length > 0 && focusedTaskId === null) {
      setFocusedTaskId(tasksFromAPI[0].id);
    } else if (tasksFromAPI.length > 0 && focusedTaskId !== null) {
      const focusedTaskExists = tasksFromAPI.some(task => task.id === focusedTaskId);
      if (!focusedTaskExists) {
        setFocusedTaskId(tasksFromAPI[0].id);
      }
    } else if (tasksFromAPI.length === 0 && focusedTaskId !== null) {
      setFocusedTaskId(null);
    }
  }, [tasksFromAPI, focusedTaskId, setFocusedTaskId]);

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
          else if (displayTasksWithSubtasks.length > 0) openDetailModal(displayTasksWithSubtasks[0].id);
          break;
        case 'n':
          if (displayTasksWithSubtasks.length > 0) {
            const currentIndex = displayTasksWithSubtasks.findIndex(item => item.id === focusedTaskId);
            if (currentIndex === -1) {
              setFocusedTaskId(displayTasksWithSubtasks[0].id);
            } else if (currentIndex < displayTasksWithSubtasks.length - 1) {
              setFocusedTaskId(displayTasksWithSubtasks[currentIndex + 1].id);
            }
          }
          break;
        case 'p':
          if (displayTasksWithSubtasks.length > 0) {
            const currentIndex = displayTasksWithSubtasks.findIndex(item => item.id === focusedTaskId);
            if (currentIndex === -1) {
              setFocusedTaskId(displayTasksWithSubtasks[displayTasksWithSubtasks.length - 1].id);
            } else if (currentIndex > 0) {
              setFocusedTaskId(displayTasksWithSubtasks[currentIndex - 1].id);
            }
          }
          break;
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [displayTasksWithSubtasks, focusedTaskId, detailViewTaskId, prioritizeModalTaskId, setFocusedTaskId, openDetailModal, setFastInputFocused]);

  // DND setup for main tasks
  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  );

  function handleDragEnd(event: DragEndEvent) {
    const { active, over } = event;
    if (active.id !== over?.id && tasksFromAPI && over) {
      const oldIndex = tasksFromAPI.findIndex((task) => task.id === active.id);
      const newIndex = tasksFromAPI.findIndex((task) => task.id === over.id);
      
      if (oldIndex === -1 || newIndex === -1) return;

      // Optimistic update could be done here using React Query's context if desired,
      // or simply rely on the refetch after mutation success.
      // For now, we are not doing a direct optimistic update of tasksFromAPI in component state.
      // const locallyReorderedTasks = arrayMove(tasksFromAPI, oldIndex, newIndex);
      // If we had local state for optimistic display: setOptimisticDisplayTasks(locallyReorderedTasks);
      
      const newOrderedTasksForBackend = arrayMove([...tasksFromAPI], oldIndex, newIndex);
      const taskOrderUpdates = newOrderedTasksForBackend.map((task, index) => ({
        id: task.id,
        position: index + 1, 
      }));
      
      console.log("[TodayView] handleDragEnd - Calling updateTaskOrder with:", taskOrderUpdates);
      updateTaskOrder(taskOrderUpdates, {
        // onSuccess and onError are handled by the hook itself (toast, query invalidation)
      }); 
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
          </div>
        </div>
        <div className="mb-6">
          <FastTaskInput 
              isFocused={isFastInputFocused} 
              onTaskCreated={handleTaskCreatedByFastInput} 
              onBlurred={() => setFastInputFocused(false)}
          />
        </div>
        {tasksFromAPI.length === 0 ? (
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

      {/* Revised Persistent Chat Panel Area with Integrated Toggle Button */}
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