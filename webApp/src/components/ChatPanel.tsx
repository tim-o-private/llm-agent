import React from 'react';
import { ChatPanelV2 } from './ChatPanelV2';

interface ChatPanelProps {
  agentId?: string;
}

/**
 * ChatPanel component using assistant-ui implementation.
 * This provides enhanced functionality, better accessibility, and improved maintainability.
 */
export const ChatPanel: React.FC<ChatPanelProps> = ({ agentId }) => {
  return <ChatPanelV2 agentId={agentId} />;
};

// Re-export for backward compatibility
export default ChatPanel; 