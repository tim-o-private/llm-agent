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
      classes: "bg-info-subtle text-info-strong",
    },
    'in-progress': {
      text: "In Progress",
      classes: "bg-warning-subtle text-warning-strong",
    },
    completed: {
      text: "Completed",
      classes: "bg-success-subtle text-success-strong",
    },
    skipped: {
      text: "Skipped",
      classes: "bg-neutral-subtle text-neutral-strong",
    },
    due: {
        text: "Due",
        classes: "bg-destructive-subtle text-destructive-strong",
    }
  };

  const currentStatus = statusStyles[status] || statusStyles.upcoming;

  return (
    <span className={clsx(baseStyle, currentStatus.classes, className)}>
      {currentStatus.text}
    </span>
  );
};

export default TaskStatusBadge; 