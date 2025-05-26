import React from 'react';
import { useFeatureFlag } from '@/lib/featureFlags';
import { ChatPanelV2 } from './ChatPanelV2';

// Import the original ChatPanel implementation
// Note: We'll need to rename the current ChatPanel to ChatPanelV1 first
import { ChatPanelV1 } from './ChatPanelV1';

interface ChatPanelProps {
  agentId?: string;
}

/**
 * Unified ChatPanel component that routes between old and new implementations
 * based on the useAssistantUI feature flag.
 * 
 * This allows for:
 * - Gradual rollout of assistant-ui migration
 * - Easy rollback if issues are discovered
 * - A/B testing between implementations
 * - Seamless user experience during transition
 */
export const ChatPanel: React.FC<ChatPanelProps> = ({ agentId }) => {
  const useAssistantUI = useFeatureFlag('useAssistantUI');

  // Log which implementation is being used (development only)
  if (import.meta.env.DEV) {
    console.log(`ChatPanel: Using ${useAssistantUI ? 'assistant-ui (V2)' : 'legacy (V1)'} implementation`);
  }

  // Route to the appropriate implementation
  if (useAssistantUI) {
    return <ChatPanelV2 agentId={agentId} />;
  } else {
    return <ChatPanelV1 agentId={agentId} />;
  }
};

// Re-export for backward compatibility
export default ChatPanel; 