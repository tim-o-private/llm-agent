import React from 'react';
import clsx from 'clsx';

export interface MessageBubbleProps {
  id: string; // For key prop in lists
  text: string;
  sender: 'user' | 'ai' | 'system';
  timestamp?: string;
  avatarUrl?: string; // URL for the sender's avatar
  senderName?: string; // Optional: if needed beyond 'user'/'ai' or for system messages
}

export const MessageBubble: React.FC<MessageBubbleProps> = ({
  text,
  sender,
  timestamp,
  avatarUrl,
  senderName,
}) => {
  const isUser = sender === 'user';
  const isSystem = sender === 'system';

  const bubbleClasses = clsx(
    'p-3 rounded-lg max-w-xs md:max-w-md lg:max-w-lg break-words shadow',
    {
      'bg-brand-primary text-brand-primary-text': isUser,
      'bg-ui-element-bg text-text-primary': !isUser && !isSystem,
      'bg-transparent text-text-muted text-center text-xs w-full italic': isSystem,
    }
  );

  const alignmentClasses = clsx(
    'flex mb-3',
    {
      'justify-end': isUser,
      'justify-start': !isUser && !isSystem,
      'justify-center': isSystem,
    }
  );

  const avatar = (
    <div className={clsx("w-8 h-8 rounded-full bg-neutral-subtle flex-shrink-0", isUser ? 'ml-2' : 'mr-2')}>
      {avatarUrl && <img src={avatarUrl} alt={`${senderName || sender}'s avatar`} className="w-full h-full rounded-full object-cover" />}
      {!avatarUrl && senderName && <span className="flex items-center justify-center w-full h-full text-xs text-neutral-strong font-semibold">{senderName.substring(0, 2).toUpperCase()}</span>}
      {!avatarUrl && !senderName && sender === 'ai' && <span className="flex items-center justify-center w-full h-full text-xs">🤖</span>}
      {!avatarUrl && !senderName && sender === 'user' && <span className="flex items-center justify-center w-full h-full text-xs">👤</span>}
    </div>
  );

  if (isSystem) {
    return (
      <div className={alignmentClasses}>
        <p className={bubbleClasses}>{text}</p>
      </div>
    );
  }

  return (
    <div className={alignmentClasses}>
      {!isUser && avatar}
      <div className={clsx("flex flex-col", isUser ? 'items-end' : 'items-start')}>
        {senderName && !isUser && (
          <span className="text-xs text-text-muted mb-0.5 ml-1">
            {senderName}
          </span>
        )}
        <div className={bubbleClasses}>
          <p className="text-sm">{text}</p>
        </div>
        {timestamp && (
          <span className={clsx("text-xs text-text-muted mt-1", isUser ? 'mr-1' : 'ml-1')}>
            {timestamp}
          </span>
        )}
      </div>
      {isUser && avatar}
    </div>
  );
}; 