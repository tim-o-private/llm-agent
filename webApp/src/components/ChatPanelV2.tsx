import React, { useEffect, useMemo } from 'react';
import { AssistantRuntimeProvider, useLocalRuntime } from '@assistant-ui/react';
import { createCustomChatModelAdapter } from '@/lib/assistantui/CustomRuntime';
import { Thread } from '@assistant-ui/react-ui';
import { useChatStore, useInitializeChatStore } from '@/stores/useChatStore';
import { useAuthStore } from '@/features/auth/useAuthStore';
import { useTaskViewStore } from '@/stores/useTaskViewStore';
import { MessageHeader } from '@/components/ui/chat/MessageHeader';
import { useSendMessageMutation } from '@/api/hooks/useChatApiHooks';

interface ChatPanelV2Props {
  agentId?: string;
}

export const ChatPanelV2: React.FC<ChatPanelV2Props> = ({ agentId: agentIdProp }) => {
  const agentId = agentIdProp || import.meta.env.VITE_DEFAULT_CHAT_AGENT_ID || "assistant";
  
  // Initialize the chat store for this agent
  useInitializeChatStore(agentId);
  
  // Get current state from stores
  const { activeChatId, currentSessionInstanceId, sendHeartbeatAsync, clearCurrentSessionAsync } = useChatStore();
  const { user } = useAuthStore();
  const { setInputFocusState } = useTaskViewStore();

  // Get mutation state for header status
  const sendMessageMutation = useSendMessageMutation();

  // Create chat model adapter with provider functions that get current values
  const chatModelAdapter = useMemo(() => {
    const userIdProvider = () => user?.id || null;
    const activeChatIdProvider = () => activeChatId;
    
    return createCustomChatModelAdapter(agentId, userIdProvider, activeChatIdProvider);
  }, [agentId, user?.id, activeChatId]);

  // Create runtime using useLocalRuntime hook
  const runtime = useLocalRuntime(chatModelAdapter);

  // Periodic Heartbeat - same as original ChatPanel
  useEffect(() => {
    if (currentSessionInstanceId) {
      const intervalId = setInterval(() => {
        sendHeartbeatAsync();
      }, 60000); 

      return () => {
        clearInterval(intervalId);
      };
    }
  }, [currentSessionInstanceId, sendHeartbeatAsync]);

  // beforeunload listener to deactivate session instance - same as original ChatPanel
  useEffect(() => {
    const handleBeforeUnload = (_event: BeforeUnloadEvent) => {
      if (useChatStore.getState().currentSessionInstanceId) { 
        clearCurrentSessionAsync();
      }
    };
    window.addEventListener('beforeunload', handleBeforeUnload);
    return () => {
      window.removeEventListener('beforeunload', handleBeforeUnload);
    };
  }, [clearCurrentSessionAsync]);

  // Track focus state for assistant-ui inputs to prevent keyboard shortcut conflicts
  useEffect(() => {
    const handleFocusIn = (event: FocusEvent) => {
      const target = event.target as HTMLElement;
      // Check if the focused element is within the assistant-ui thread
      if (target && (
        target.matches('textarea[data-testid="composer-input"]') ||
        target.matches('input[data-testid="composer-input"]') ||
        target.closest('[data-testid="composer"]') ||
        target.matches('textarea') ||
        target.matches('input[type="text"]')
      )) {
        setInputFocusState(true);
      }
    };

    const handleFocusOut = (event: FocusEvent) => {
      const target = event.target as HTMLElement;
      // Check if the focused element is within the assistant-ui thread
      if (target && (
        target.matches('textarea[data-testid="composer-input"]') ||
        target.matches('input[data-testid="composer-input"]') ||
        target.closest('[data-testid="composer"]') ||
        target.matches('textarea') ||
        target.matches('input[type="text"]')
      )) {
        setInputFocusState(false);
      }
    };

    document.addEventListener('focusin', handleFocusIn);
    document.addEventListener('focusout', handleFocusOut);

    return () => {
      document.removeEventListener('focusin', handleFocusIn);
      document.removeEventListener('focusout', handleFocusOut);
    };
  }, [setInputFocusState]);

  return (
    <div className="flex flex-col h-full bg-ui-bg shadow-lg border-l border-ui-border">
      {/* Header matching the existing design */}
      <MessageHeader 
        chatTitle="AI Coach" 
        status={sendMessageMutation.isPending ? "Typing..." : "Online"}
        statusColor={sendMessageMutation.isPending ? 'yellow' : 'green'}
      />
      
      {/* Assistant-UI Thread with comprehensive theming from assistant-ui-theme.css */}
      <div className="flex-1 relative">
        <AssistantRuntimeProvider runtime={runtime}>
          <div className="h-full">
            <Thread />
          </div>
        </AssistantRuntimeProvider>
      </div>
    </div>
  );
}; 