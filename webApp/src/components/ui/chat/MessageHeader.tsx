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
  const statusDotColorClasses = {
    green: 'bg-green-500',
    yellow: 'bg-yellow-500',
    gray: 'bg-gray-400',
  };

  return (
    <div className="p-3 px-4 flex items-center justify-between bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 shadow-sm">
      <div className="flex items-center">
        {/* Avatar/Icon could go here if desired */}
        {/* <div className="w-8 h-8 rounded-full bg-gray-300 dark:bg-gray-600 mr-3 flex-shrink-0"></div> */}
        <div>
          <h2 className="text-base font-semibold text-gray-900 dark:text-white">{chatTitle}</h2>
          {status && (
            <div className="flex items-center mt-0.5">
              <span className={clsx("w-2 h-2 rounded-full mr-1.5", statusDotColorClasses[statusColor])}></span>
              <p className="text-xs text-gray-500 dark:text-gray-400">{status}</p>
            </div>
          )}
        </div>
      </div>
      {/* <div className="flex items-center space-x-2">
        {onClearChat && (
          <button 
            onClick={onClearChat} 
            className="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 p-1 rounded-md"
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