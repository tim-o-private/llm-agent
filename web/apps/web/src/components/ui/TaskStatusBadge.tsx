import React from 'react';
import clsx from 'clsx';

export type TaskStatus = 'upcoming' | 'in-progress' | 'completed' | 'skipped' | 'due';

interface TaskStatusBadgeProps {
  status: TaskStatus;
  className?: string;
}

const TaskStatusBadge: React.FC<TaskStatusBadgeProps> = ({ status, className }) => {
  const baseStyle = "px-2.5 py-0.5 rounded-full text-xs font-medium whitespace-nowrap";

  const statusStyles: Record<TaskStatus, { text: string; classes: string }> = {
    upcoming: {
      text: "Upcoming",
      classes: "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300",
    },
    'in-progress': {
      text: "In Progress",
      classes: "bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-300",
    },
    completed: {
      text: "Completed",
      classes: "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300",
    },
    skipped: {
      text: "Skipped",
      classes: "bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300",
    },
    due: {
        text: "Due",
        classes: "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300",
    }
  };

  const currentStatus = statusStyles[status] || statusStyles.upcoming; // Default to upcoming if somehow invalid

  return (
    <span className={clsx(baseStyle, currentStatus.classes, className)}>
      {currentStatus.text}
    </span>
  );
};

export default TaskStatusBadge; 