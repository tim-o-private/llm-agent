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
        completed && "bg-gray-100 dark:bg-gray-800 opacity-70", // Slightly different completed style for better contrast
        className
      )}
      // The Card component itself has p-6 padding by default, so content is directly inside.
    >
      <div className="flex items-start">
        {/* Checkbox Container */}
        <div className="flex items-center h-5 mt-0.5 mr-3"> {/* Adjusted margin & alignment slightly */}
          <Checkbox
            checked={completed}
            onChange={() => onToggleComplete(id)} // Corrected: Checkbox onChange usually doesn't pass value for native, event instead. This is fine for our controlled component.
            aria-label={`Mark task ${title} as ${completed ? 'incomplete' : 'complete'}`}
          />
        </div>
        {/* Text Content Container */}
        <div className="flex-1">
          <label
            className={clsx(
              "block text-sm font-medium cursor-pointer",
              completed ? "line-through text-gray-500 dark:text-gray-400" : "text-gray-900 dark:text-white"
            )}
          >
            {title}
          </label>
          {(time || category) && (
            <div className="mt-1 flex items-center space-x-2 text-xs text-gray-500 dark:text-gray-400">
              {time && <span>{time}</span>}
              {category && (
                <span className="px-2 py-0.5 bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300 rounded-full">
                  {category}
                </span>
              )}
            </div>
          )}
        </div>
      </div>
      {/* Footer content can be added here if needed later */}
    </Card>
  );
}; 