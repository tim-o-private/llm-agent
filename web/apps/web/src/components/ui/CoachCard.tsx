import React from 'react';
import { Card } from './Card'; // Relative import from within the same package
import { Button } from './Button'; // Relative import
import clsx from 'clsx';

export interface CoachCardProps {
  title?: string;
  suggestion: React.ReactNode; // Can be simple text or more complex elements
  // Optional actions
  onAccept?: () => void;
  onDismiss?: () => void;
  acceptLabel?: string;
  dismissLabel?: string;
  className?: string;
}

export const CoachCard: React.FC<CoachCardProps> = ({
  title = "AI Coach Suggestion",
  suggestion,
  onAccept,
  onDismiss,
  acceptLabel = "Accept",
  dismissLabel = "Dismiss",
  className,
}) => {
  return (
    <Card className={clsx("shadow-lg", className)}>
      {/* Card already has padding, so we add content directly */}
      <div className="flex flex-col h-full">
        <h3 className="text-md font-semibold text-gray-800 dark:text-white mb-2">
          {title}
        </h3>
        <div className="text-sm text-gray-600 dark:text-gray-300 flex-grow mb-3">
          {suggestion}
        </div>
        {(onAccept || onDismiss) && (
          <div className="flex justify-end space-x-2 pt-2 border-t border-gray-200 dark:border-gray-700 mt-auto">
            {onDismiss && (
              <Button variant="secondary" onClick={onDismiss}>
                {dismissLabel}
              </Button>
            )}
            {onAccept && (
              <Button variant="primary" onClick={onAccept}>
                {acceptLabel}
              </Button>
            )}
          </div>
        )}
      </div>
    </Card>
  );
}; 