import React from 'react';
import TaskListGroup from '../components/tasks/TaskListGroup';
import { TaskCardProps } from '@/components/ui';
import FABQuickAdd from '../components/tasks/FABQuickAdd';
/* import { useOverlayStore } from '../stores/useOverlayStore'; */

import { useFetchTasks, useUpdateTask } from '../api/hooks/useTaskHooks';
import type { Task } from '../api/types';
import { Spinner } from '@/components/ui';

const TodayView: React.FC = () => {
/*  const { openOverlay } = useOverlayStore(); */
  const { data: tasks, isLoading: isLoadingTasks, error: fetchTasksError } = useFetchTasks();
  const { mutate: updateTask } = useUpdateTask();

  const handleToggleTask = (taskId: string, currentCompletedState: boolean) => {
    updateTask({ id: taskId, updates: { completed: !currentCompletedState } });
  };
/* TODO: Re-implement task detail tray
  const handleOpenTaskDetailFromCard = (task: Task) => {
    openOverlay('taskDetailTray', { 
        taskId: task.id, 
        initialTitle: task.title, 
        initialNotes: task.notes, 
        initialCategory: task.category,
        initialTimePeriod: task.time_period,
    });
  };
*/
  const mapTaskToTaskCardProps = (task: Task): TaskCardProps => ({
    id: task.id,
    title: task.title,
    time: task.due_date ? new Date(task.due_date).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : undefined,
    category: task.category || undefined,
    completed: task.completed,
    notes: task.notes || undefined,
    onToggleComplete: () => handleToggleTask(task.id, task.completed),
  });

  const allTasks = tasks?.map(mapTaskToTaskCardProps) || [];
  const allTasksCount = allTasks.length;

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
      <h1 className="text-2xl font-semibold text-gray-900 dark:text-white mb-6">Today's Tasks</h1>

      {allTasksCount === 0 ? (
        <div className="flex-grow flex flex-col items-center justify-center text-gray-500 dark:text-gray-400">
          <svg xmlns="http://www.w3.org/2000/svg" className="h-16 w-16 mb-4 opacity-50" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 8h14M5 8a2 2 0 110-4h14a2 2 0 110 4M5 8v10a2 2 0 002 2h10a2 2 0 002-2V8m-9 4h4" />
          </svg>
          <p className="text-lg">Your day is clear!</p>
          <p>Add some tasks to get started.</p>
        </div>
      ) : (
        <div className="flex-grow overflow-y-auto space-y-8">
          <TaskListGroup title="All Tasks" tasks={allTasks} />
        </div>
      )}

      <FABQuickAdd />

      <div 
        className="hidden md:block fixed top-1/3 right-6 bg-white dark:bg-gray-800 p-4 rounded-lg shadow-xl border border-gray-200 dark:border-gray-700 w-64 h-auto"
      >
        {/* Placeholder for CoachCard content */}
      </div>
    </div>
  );
};

export default TodayView; 