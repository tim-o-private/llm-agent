import React from 'react';
import clsx from 'clsx';

export interface MessageHeaderProps {
  chatTitle: string;
  status?: string;
  statusColor?: 'green' | 'yellow' | 'gray'; // For status indicator dot
  // onClearChat?: () => void; // Example for a future action button
}

export const MessageHeader: React.FC<MessageHeaderProps> = ({
  chatTitle,
  status,
  statusColor = 'gray',
  // onClearChat
}) => {
  const statusDotColorClasses: Record<string, string> = {
    // Widened key type for safety
    green: 'bg-success-indicator',
    yellow: 'bg-warning-indicator',
    gray: 'bg-neutral-indicator',
  };

  return (
    <div className="p-3 px-4 flex items-center justify-between bg-ui-element-bg border-b border-ui-border shadow-sm">
      <div className="flex items-center">
        {/* Avatar/Icon could go here if desired */}
        {/* <div className="w-8 h-8 rounded-full bg-ui-interactive-bg mr-3 flex-shrink-0"></div> */}
        <div>
          <h2 className="text-base font-semibold text-text-primary">{chatTitle}</h2>
          {status && (
            <div className="flex items-center mt-0.5">
              <span
                className={clsx(
                  'w-2 h-2 rounded-full mr-1.5',
                  statusDotColorClasses[statusColor] || 'bg-neutral-indicator',
                )}
              ></span>
              <p className="text-xs text-text-muted">{status}</p>
            </div>
          )}
        </div>
      </div>
      {/* <div className="flex items-center space-x-2">
        {onClearChat && (
          <button 
            onClick={onClearChat} 
            className="text-text-muted hover:text-text-secondary p-1 rounded-md"
            title="Clear chat"
            aria-label="Clear chat"
          >
            Clear Icon SVG
          </button>
        )}
      </div> */}
    </div>
  );
};
