import React from 'react';
import { ChatPanelV1 } from './ChatPanelV1';

interface ChatPanelProps {
  agentId?: string;
}

/**
 * ChatPanel component using assistant-ui implementation.
 * This provides enhanced functionality, better accessibility, and improved maintainability.
 */
export const ChatPanel: React.FC<ChatPanelProps> = ({ agentId }) => {
  return <ChatPanelV1 agentId={agentId} />;
};

// Re-export for backward compatibility
export default ChatPanel; 