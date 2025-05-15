import React from 'react';
import { Card } from './Card'; // Only import Card
import { Checkbox } from './Checkbox'; // Import the new Checkbox
import clsx from 'clsx';

// Define Task interface locally for now
export interface TaskCardProps {
  id: string;
  title: string;
  time?: string;
  category?: string;
  notes?: string;
  completed: boolean;
  onToggleComplete: (id: string) => void;
  className?: string;
}

// Changed to a named export
export const TaskCard: React.FC<TaskCardProps> = ({
  id,
  title,
  time,
  category,
  notes,
  completed,
  onToggleComplete,
  className,
}) => {
  return (
    <Card 
      className={clsx(
        "mb-3 transition-all hover:shadow-md", 
        // For completed tasks, use a subtler background from the theme and opacity
        completed && "bg-ui-bg-alt opacity-70", 
        className
      )}
      // The Card component itself has p-6 padding by default, so content is directly inside.
    >
      <div className="flex items-start">
        {/* Checkbox Container */}
        <div className="flex items-center h-5 mt-0.5 mr-3"> {/* Adjusted margin & alignment slightly */}
          <Checkbox
            checked={completed}
            onCheckedChange={() => onToggleComplete(id)}
            aria-label={`Mark task ${title} as ${completed ? 'incomplete' : 'complete'}`}
          />
        </div>
        {/* Text Content Container */}
        <div className="flex-1">
          <label
            className={clsx(
              "block text-sm font-medium cursor-pointer",
              completed ? "line-through text-text-muted" : "text-text-primary"
            )}
          >
            {title}
          </label>
          {(time || category) && (
            <div className="mt-1 flex items-center space-x-2 text-xs text-text-muted">
              {time && <span>{time}</span>}
              {category && (
                <span className="px-2 py-0.5 bg-accent-subtle text-text-accent-strong rounded-full">
                  {category}
                </span>
              )}
            </div>
          )}
          {/* Display notes if they exist - simple version */}
          {notes && (
            <p className="mt-1 text-xs text-text-muted">
              {notes}
            </p>
          )}
        </div>
      </div>
      {/* Footer content can be added here if needed later */}
    </Card>
  );
}; 