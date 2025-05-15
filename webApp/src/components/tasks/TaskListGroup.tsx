import React from 'react';
import { TaskCard, TaskCardProps } from '@/components/ui';

interface TaskListGroupProps {
  title: string;
  tasks: TaskCardProps[]; // Using TaskCardProps from the shared UI package
  // onToggleTaskComplete: (id: string) => void; // This will be handled by TaskCard itself via its onToggleComplete prop
}

const TaskListGroup: React.FC<TaskListGroupProps> = ({ title, tasks }) => {
  if (!tasks || tasks.length === 0) {
    return null; // Or a placeholder like <p>No tasks for {title}.</p> if desired per group
  }

  return (
    <div className="mb-8">
      <h2 className="text-xl font-semibold text-gray-800 dark:text-gray-200 mb-4 pb-2 border-b border-gray-200 dark:border-gray-700">
        {title}
      </h2>
      <div className="space-y-3">
        {tasks.map((task) => (
          <TaskCard
            key={task.id}
            {...task} // Spread all props from the task object (TaskCardProps)
            // Individual props below are now redundant due to spread, but ensure onToggleComplete and onStartTask are part of 'task'
            // id={task.id} 
            // title={task.title}
            // category={task.category}
            // completed={task.completed}
            // onToggleComplete={task.onToggleComplete}
            // status={task.status} // Will be spread
            // priority={task.priority} // Will be spread
            // onStartTask={task.onStartTask} // Will be spread
          />
        ))}
      </div>
    </div>
  );
};

export default TaskListGroup; 