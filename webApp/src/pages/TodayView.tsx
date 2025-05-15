import React, { useState, useEffect, useCallback, useRef } from 'react';
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

import TaskListGroup from '../components/tasks/TaskListGroup';
import { TaskCard, TaskCardProps } from '@/components/ui/TaskCard';
import FABQuickAdd from '../components/tasks/FABQuickAdd';
import { FastTaskInput } from '../components/features/TodayView/FastTaskInput';
import { TaskDetailView } from '../components/features/TaskDetail/TaskDetailView';
/* import { useOverlayStore } from '../stores/useOverlayStore'; */

import { useFetchTasks, useUpdateTask, useUpdateTaskOrder, useCreateFocusSession } from '../api/hooks/useTaskHooks';
import type { Task, FocusSession } from '../api/types';
import { Spinner } from '@/components/ui';
import { useQueryClient } from '@tanstack/react-query';
import { useAuthStore } from '../features/auth/useAuthStore';

const mapTaskToTaskCardViewModel = (
  task: Task, 
  onToggle: any, 
  onStart: any, 
  onEdit: (taskId: string) => void,
  isFocused: boolean
): TaskCardProps => ({
  ...task,
  onToggleComplete: onToggle,
  onStartTask: onStart,
  onEdit: () => onEdit(task.id),
  isFocused,
});

const TodayView: React.FC = () => {
/*  const { openOverlay } = useOverlayStore(); */
  const queryClient = useQueryClient();
  const { data: fetchedTasks, isLoading: isLoadingTasks, error: fetchTasksError } = useFetchTasks();
  const { mutate: updateTask } = useUpdateTask();
  const { mutate: updateTaskOrder } = useUpdateTaskOrder();
  const { mutate: createFocusSession } = useCreateFocusSession();
  
  // Local state for tasks to enable client-side reordering
  const [displayTasks, setDisplayTasks] = useState<TaskCardProps[]>([]);
  const [isFastInputFocused, setIsFastInputFocused] = useState(false);
  const [isDetailViewOpen, setIsDetailViewOpen] = useState(false);
  const [selectedTaskIdForDetail, setSelectedTaskIdForDetail] = useState<string | null>(null);
  const [focusedTaskId, setFocusedTaskId] = useState<string | null>(null);

  const handleTaskCreatedByFastInput = (createdTask: Task) => {
    queryClient.invalidateQueries({ queryKey: ['tasks', useAuthStore.getState().user?.id] });
    setIsFastInputFocused(false); 
    if (createdTask && createdTask.id) {
      setFocusedTaskId(createdTask.id);
    }
  };

  const openTaskDetailView = useCallback((taskId: string) => {
    setSelectedTaskIdForDetail(taskId);
    setIsDetailViewOpen(true);
  }, []);

  const handleTaskUpdated = () => {
    queryClient.invalidateQueries({ queryKey: ['tasks', useAuthStore.getState().user?.id] });
  };

  const handleTaskDeleted = () => {
    queryClient.invalidateQueries({ queryKey: ['tasks', useAuthStore.getState().user?.id] });
    setIsDetailViewOpen(false); 
    setSelectedTaskIdForDetail(null);
  };

  const handleToggleTask = useCallback((taskId: string, currentCompletedState: boolean) => {
    const newCompletedStatus = !currentCompletedState;
    const newStatus = newCompletedStatus ? 'completed' : 'pending';

    updateTask(
      { id: taskId, updates: { completed: newCompletedStatus, status: newStatus } }, 
      {
        onSuccess: () => console.log(`Task ${taskId} toggled to ${newCompletedStatus}`),
        onError: (err: Error) => console.error('[TodayView] Error updating task completion:', err),
      }
    );
  }, [updateTask]);

  const handleStartTask = useCallback((taskId: string) => {
    console.log(`[TodayView] Attempting to start task: ${taskId}`);
    updateTask(
      { id: taskId, updates: { status: 'in_progress' } },
      {
        onSuccess: (updatedTask: Task | null) => {
          console.log(`[TodayView] Task ${taskId} status updated to in_progress. Starting focus session.`);
          createFocusSession(
            { task_id: taskId },
            {
              onSuccess: (focusSession: FocusSession | null) => {
                console.log(`[TodayView] Focus session created for task ${taskId}:`, focusSession);
              },
              onError: (err: Error) => {
                console.error('[TodayView] Error creating focus session:', err);
                updateTask(
                  { id: taskId, updates: { status: 'planning' } },
                  {
                    onSuccess: () => console.log(`[TodayView] Task ${taskId} status reverted to planning after focus session failure.`),
                    onError: (revertError: Error) => console.error("[TodayView] Error reverting task status:", revertError),
                  }
                );
              },
            }
          );
        },
        onError: (err: Error) => {
          console.error(`[TodayView] Error updating task status to in_progress for ${taskId}:`, err);
        },
      }
    );
  }, [updateTask, createFocusSession]);

  useEffect(() => {
    if (fetchedTasks) {
      console.log('[TodayView] useEffect triggered. fetchedTasks:', fetchedTasks.map(t => ({id: t.id, title: t.title, position: t.position })));
      const newDisplayTasks = fetchedTasks.map(task => 
        mapTaskToTaskCardViewModel(
          task, 
          handleToggleTask, 
          handleStartTask, 
          openTaskDetailView,
          task.id === focusedTaskId
        )
      );
      console.log('[TodayView] useEffect setting displayTasks. New displayTasks:', newDisplayTasks.map(t => ({id: t.id, title: t.title })));
      setDisplayTasks(newDisplayTasks);

      // Set initial focus to the first task if no task is currently focused
      if (newDisplayTasks.length > 0 && !focusedTaskId) {
        setFocusedTaskId(newDisplayTasks[0].id);
      } else if (newDisplayTasks.length === 0) {
        setFocusedTaskId(null); // Clear focus if no tasks
      }
    }
  }, [fetchedTasks, handleToggleTask, handleStartTask, openTaskDetailView, focusedTaskId]);

  // Hotkey handling - MOVED DOWN
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      const activeElement = document.activeElement;
      const isModalOpen = document.querySelector('[role="dialog"][data-state="open"]');
      const isInputActive = activeElement && (activeElement.tagName === 'INPUT' || activeElement.tagName === 'TEXTAREA');

      if (isModalOpen || isInputActive) {
        return; 
      }

      if (event.key === 't' || event.key === 'T') {
        event.preventDefault();
        setIsFastInputFocused(true);
      } else if (event.key === 'e' || event.key === 'E') {
        if (focusedTaskId && !isDetailViewOpen) { 
          event.preventDefault();
          openTaskDetailView(focusedTaskId);
        } else if (displayTasks.length > 0 && !isDetailViewOpen && !focusedTaskId) {
          event.preventDefault();
          openTaskDetailView(displayTasks[0].id);
        }
      } else if (event.key === 'n' || event.key === 'N') {
        event.preventDefault();
        if (displayTasks.length > 0) {
          const currentIndex = displayTasks.findIndex(task => task.id === focusedTaskId);
          if (currentIndex === -1) {
            setFocusedTaskId(displayTasks[0].id);
          } else if (currentIndex < displayTasks.length - 1) {
            setFocusedTaskId(displayTasks[currentIndex + 1].id);
          }
        }
      } else if (event.key === 'p' || event.key === 'P') {
        event.preventDefault();
        if (displayTasks.length > 0) {
          const currentIndex = displayTasks.findIndex(task => task.id === focusedTaskId);
          if (currentIndex === -1) {
            setFocusedTaskId(displayTasks[displayTasks.length - 1].id);
          } else if (currentIndex > 0) {
            setFocusedTaskId(displayTasks[currentIndex - 1].id);
          }
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [displayTasks, focusedTaskId, isDetailViewOpen, openTaskDetailView, setIsFastInputFocused]); // Added setIsFastInputFocused to deps

  useEffect(() => {
    if (!isFastInputFocused && document.activeElement?.tagName !== 'INPUT') {
    } else if (isFastInputFocused && document.activeElement?.tagName !== 'INPUT') {
        setIsFastInputFocused(false);
    }
  }, [isFastInputFocused]);

  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  );

  function handleDragEnd(event: DragEndEvent) {
    const {active, over} = event;
    
    if (over && active.id !== over.id) {
      setDisplayTasks((items) => {
        const oldIndex = items.findIndex(item => item.id === active.id);
        const newIndex = items.findIndex(item => item.id === over.id);
        const newOrderedItems = arrayMove(items, oldIndex, newIndex);
        
        // Prepare data for backend update
        const taskOrderUpdates = newOrderedItems.map((task, index) => ({
    id: task.id,
          position: index, // Use the new index as the position
        }));
        console.log('[TodayView] Calling updateTaskOrder with:', taskOrderUpdates); // DEBUGGING
        updateTaskOrder(taskOrderUpdates);
        
        return newOrderedItems;
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

  if (fetchTasksError) {
    return (
      <div className="w-full h-full flex flex-col items-center justify-center text-red-600 p-4 md:p-6 lg:p-8">
        <p>Error loading tasks: {fetchTasksError.message}</p>
      </div>
    );
  }

  return (
    <div className="p-4 md:p-6 lg:p-8 h-full flex flex-col">
      <div className="mb-6">
        <FastTaskInput 
            isFocused={isFastInputFocused} 
            onTaskCreated={handleTaskCreatedByFastInput} 
        />
      </div>
      {displayTasks.length === 0 && !isLoadingTasks ? (
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
            items={displayTasks.map(task => task.id)} // Use array of ids for SortableContext
            strategy={verticalListSortingStrategy}
          >
        <div className="flex-grow overflow-y-auto space-y-8">
              <TaskListGroup title="All Tasks" tasks={displayTasks} />
        </div>
          </SortableContext>
        </DndContext>
      )}

      <TaskDetailView 
        taskId={selectedTaskIdForDetail}
        isOpen={isDetailViewOpen}
        onOpenChange={setIsDetailViewOpen}
        onTaskUpdated={handleTaskUpdated}
        onTaskDeleted={handleTaskDeleted}
      />
    </div>
  );
};

export default TodayView; 