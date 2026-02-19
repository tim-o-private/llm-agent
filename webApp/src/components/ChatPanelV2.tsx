import React, { useEffect, useCallback, useRef, useState } from 'react';
import { AssistantRuntimeProvider } from '@assistant-ui/react';
import { useExternalStoreRuntime } from '@assistant-ui/react';
import type { ThreadMessageLike, AppendMessage } from '@assistant-ui/react';
import { Thread } from '@assistant-ui/react-ui';
import { useChatStore, useInitializeChatStore, type ChatMessage } from '@/stores/useChatStore';
import { useTaskViewStore } from '@/stores/useTaskViewStore';
import { MessageHeader } from '@/components/ui/chat/MessageHeader';
import { ConversationList } from '@/components/features/Conversations';
import { supabase } from '@/lib/supabaseClient';

interface ChatPanelV2Props {
  agentId?: string;
}

export const ChatPanelV2: React.FC<ChatPanelV2Props> = ({ agentId: agentIdProp }) => {
  const agentId = agentIdProp || import.meta.env.VITE_DEFAULT_CHAT_AGENT_ID || 'assistant';

  // Initialize the chat store for this agent
  useInitializeChatStore(agentId);

  // Get current state from stores
  const {
    messages,
    activeChatId,
    currentSessionInstanceId,
    sendHeartbeatAsync,
    clearCurrentSessionAsync,
    addMessage,
  } = useChatStore();
  const { setInputFocusState } = useTaskViewStore();

  // Track running state for the external store
  const [isRunning, setIsRunning] = useState(false);

  // Convert ChatMessage to ThreadMessageLike
  const convertMessage = useCallback(
    (msg: ChatMessage): ThreadMessageLike => ({
      role: msg.sender === 'user' ? 'user' : 'assistant',
      content: msg.text,
      id: msg.id,
      createdAt: msg.timestamp instanceof Date ? msg.timestamp : new Date(msg.timestamp),
    }),
    [],
  );

  // onNew handler - sends message via /api/chat
  const onNew = useCallback(
    async (message: AppendMessage) => {
      // Extract text from content parts
      const userText = message.content
        .filter((c): c is { type: 'text'; text: string } => c.type === 'text')
        .map((c) => c.text)
        .join(' ');
      if (!userText) return;

      setIsRunning(true);
      try {
        // Add user message to store
        await addMessage({ text: userText, sender: 'user' });

        // Call /api/chat
        const {
          data: { session },
        } = await supabase.auth.getSession();
        const accessToken = session?.access_token;
        if (!accessToken) throw new Error('Not authenticated');

        const apiUrl = `${import.meta.env.VITE_API_BASE_URL || ''}/api/chat`;
        const response = await fetch(apiUrl, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${accessToken}`,
          },
          body: JSON.stringify({
            agent_name: agentId,
            message: userText,
            session_id: activeChatId,
          }),
        });

        if (!response.ok) {
          let errorDetail = `API Error: ${response.status} ${response.statusText}`;
          try {
            const errorData = await response.json();
            errorDetail = errorData.detail || errorDetail;
          } catch {
            // Ignore if error response is not JSON
          }
          throw new Error(errorDetail);
        }

        const data = await response.json();

        if (data.error) {
          throw new Error(data.error);
        }

        // Add AI response to store
        await addMessage({
          text: data.response,
          sender: 'ai',
          tool_name: data.tool_name || undefined,
          tool_input: data.tool_input || undefined,
        });
        await sendHeartbeatAsync();
      } catch (error) {
        console.error('ChatPanelV2: Error sending message:', error);
        throw error;
      } finally {
        setIsRunning(false);
      }
    },
    [agentId, activeChatId, addMessage, sendHeartbeatAsync],
  );

  // Create runtime using useExternalStoreRuntime
  const runtime = useExternalStoreRuntime({
    messages,
    convertMessage,
    onNew,
    isRunning,
  });

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
    const handleBeforeUnload = () => {
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
      if (
        target &&
        (target.matches('textarea[data-testid="composer-input"]') ||
          target.matches('input[data-testid="composer-input"]') ||
          target.closest('[data-testid="composer"]') ||
          target.matches('textarea') ||
          target.matches('input[type="text"]'))
      ) {
        setInputFocusState(true);
      }
    };

    const handleFocusOut = (event: FocusEvent) => {
      const target = event.target as HTMLElement;
      // Check if the focused element is within the assistant-ui thread
      if (
        target &&
        (target.matches('textarea[data-testid="composer-input"]') ||
          target.matches('input[data-testid="composer-input"]') ||
          target.closest('[data-testid="composer"]') ||
          target.matches('textarea') ||
          target.matches('input[type="text"]'))
      ) {
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

  // Scroll to bottom when messages first load for a session (initial hydration or session switch)
  const hasScrolledRef = useRef(false);
  const lastChatIdRef = useRef<string | null>(null);

  useEffect(() => {
    if (activeChatId !== lastChatIdRef.current) {
      hasScrolledRef.current = false;
      lastChatIdRef.current = activeChatId ?? null;
    }

    if (messages.length > 0 && !hasScrolledRef.current) {
      hasScrolledRef.current = true;
      requestAnimationFrame(() => {
        const viewport = document.querySelector('.aui-thread-viewport');
        if (viewport) {
          viewport.scrollTop = viewport.scrollHeight;
        }
      });
    }
  }, [activeChatId, messages.length]);

  return (
    <div className="flex flex-col h-full bg-ui-bg shadow-lg border-l border-ui-border">
      {/* Header matching the existing design */}
      <MessageHeader
        chatTitle="AI Coach"
        status={isRunning ? 'Typing...' : 'Online'}
        statusColor={isRunning ? 'yellow' : 'green'}
      />

      {/* Conversation history list */}
      <ConversationList agentName={agentId} />

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
