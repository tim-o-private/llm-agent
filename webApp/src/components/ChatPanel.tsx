import React, { useEffect, useCallback, useRef, useState, Component, type ErrorInfo, type ReactNode } from 'react';
import { AssistantRuntimeProvider, useMessage, makeAssistantToolUI } from '@assistant-ui/react';
import { useExternalStoreRuntime } from '@assistant-ui/react';
import type { ThreadMessageLike, AppendMessage } from '@assistant-ui/react';
import { Thread, Composer } from '@assistant-ui/react-ui';
import { useChatStore, useInitializeChatStore, type ChatMessage } from '@/stores/useChatStore';
import { useChatTimeline } from '@/api/hooks/useChatTimeline';
import { useTaskViewStore } from '@/stores/useTaskViewStore';
import { MessageHeader } from '@/components/ui/chat/MessageHeader';
import type { ChatScope } from '@/api/types/chat';
import { NotificationInlineMessage } from '@/components/ui/chat/NotificationInlineMessage';
import { ApprovalInlineMessage } from '@/components/ui/chat/ApprovalInlineMessage';
import { ConversationList } from '@/components/features/Conversations';
import { authHeaders } from '@/lib/apiClient';
import { ToolFallback } from '@/components/assistantui/ToolCallIndicator';

const GenericToolUI = makeAssistantToolUI({
  toolName: '*',
  render: (props) => <ToolFallback toolName={props.toolName} status={props.status} />,
});

// Error boundary to catch assistant-ui rendering errors (e.g., "can't access property 'role'")
// and prevent black screen. Shows error in console and allows retry without hard refresh.
class ThreadErrorBoundary extends Component<
  { children: ReactNode },
  { hasError: boolean; error: Error | null }
> {
  constructor(props: { children: ReactNode }) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('ThreadErrorBoundary caught error:', error, errorInfo.componentStack);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex flex-col items-center justify-center h-full gap-4 p-4 text-text-secondary">
          <p>Something went wrong displaying the chat.</p>
          <button
            className="px-4 py-2 rounded bg-brand-primary text-white"
            onClick={() => this.setState({ hasError: false, error: null })}
          >
            Retry
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}

interface ChatPanelProps {
  agentId?: string;
  scope?: ChatScope;
}

export const ChatPanel: React.FC<ChatPanelProps> = ({ agentId: agentIdProp, scope }) => {
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
    updateLastAiMessage,
    refreshMessages,
  } = useChatStore();
  const { setInputFocusState } = useTaskViewStore();

  // Get merged timeline for notification/approval items
  const timeline = useChatTimeline();

  // Track running state for the external store
  const [isRunning, setIsRunning] = useState(false);

  // Convert ChatMessage to ThreadMessageLike.
  // Notification/approval items use role 'system' with metadata.custom carrying the
  // full ChatMessage payload — picked up by TimelineSystemMessage below.
  const convertMessage = useCallback(
    (msg: ChatMessage): ThreadMessageLike => {
      if (msg.sender === 'notification' || msg.sender === 'approval') {
        return {
          role: 'system' as const,
          content: [{ type: 'text', text: msg.text || '' }],
          id: msg.id,
          createdAt: msg.timestamp instanceof Date ? msg.timestamp : new Date(msg.timestamp),
          metadata: { custom: { ...msg } },
        };
      }
      if (!msg.tool_calls?.length) {
        return {
          role: msg.sender === 'user' ? 'user' : 'assistant',
          content: msg.text || '',
          id: msg.id,
          createdAt: msg.timestamp instanceof Date ? msg.timestamp : new Date(msg.timestamp),
          metadata: { custom: { ...msg } },
        };
      }
      const parts: ThreadMessageLike['content'] & unknown[] = [];
      if (msg.text) {
        parts.push({ type: 'text' as const, text: msg.text });
      }
      for (const tc of msg.tool_calls) {
        parts.push({ type: 'tool-call' as const, toolCallId: tc.id, toolName: tc.name });
      }
      return {
        role: 'assistant' as const,
        content: parts,
        id: msg.id,
        createdAt: msg.timestamp instanceof Date ? msg.timestamp : new Date(msg.timestamp),
        metadata: { custom: { ...msg } },
      };
    },
    [],
  );

  // onNew handler - sends message via /api/chat with SSE streaming
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

        // Add empty AI placeholder for streaming updates
        await addMessage({ text: '', sender: 'ai' });

        const headers = await authHeaders();
        const apiUrl = `${import.meta.env.VITE_API_BASE_URL || ''}/api/chat`;
        const response = await fetch(apiUrl, {
          method: 'POST',
          headers: { ...headers, Accept: 'text/event-stream' },
          body: JSON.stringify({
            agent_name: agentId,
            message: userText,
            session_id: activeChatId,
            ...(() => {
              const currentScope = useChatStore.getState().scope;
              return currentScope.type !== 'global' ? { scope: currentScope } : {};
            })(),
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
          updateLastAiMessage({ text: errorDetail });
          throw new Error(errorDetail);
        }

        const reader = response.body?.getReader();
        if (!reader) throw new Error('No response body');

        const decoder = new TextDecoder();
        let buffer = '';
        let accumulated = '';
        const toolCalls: Array<{ id: string; name: string }> = [];
        let textDirty = false;
        let rafId = 0;

        const flushText = () => {
          if (textDirty) {
            updateLastAiMessage({ text: accumulated });
            textDirty = false;
          }
        };

        try {
          while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop() ?? '';

            for (const line of lines) {
              if (!line.startsWith('data: ')) continue;
              try {
                const payload = JSON.parse(line.slice(6));
                if (payload.type === 'text_delta' && payload.text) {
                  accumulated += payload.text;
                  textDirty = true;
                  if (!rafId) {
                    rafId = requestAnimationFrame(() => { rafId = 0; flushText(); });
                  }
                } else if (payload.type === 'tool_start' && payload.tool_name) {
                  flushText();
                  toolCalls.push({ id: payload.tool_call_id || `tc_${toolCalls.length}`, name: payload.tool_name });
                  updateLastAiMessage({ tool_calls: [...toolCalls] });
                } else if (payload.type === 'error') {
                  accumulated += `\n\n*Error: ${payload.message}*`;
                  textDirty = true;
                  flushText();
                  if (payload.error_type === 'reauth_required') {
                    useChatStore.getState().handleReauthError(
                      new Error(`[REAUTH_REQUIRED:${payload.service}] ${payload.message}`),
                    );
                  }
                }
              } catch { /* malformed SSE line */ }
            }
          }
        } finally {
          cancelAnimationFrame(rafId);
          reader.releaseLock();
        }
        flushText();
        await sendHeartbeatAsync();
      } catch (error) {
        console.error('ChatPanel: Error sending message:', error);
        throw error;
      } finally {
        setIsRunning(false);
      }
    },
    [agentId, activeChatId, addMessage, updateLastAiMessage, sendHeartbeatAsync],
  );

  // Create runtime using useExternalStoreRuntime.
  // Feed the full timeline (chat messages + notification/approval items) so that
  // assistant-ui interleaves them chronologically by timestamp.
  const runtime = useExternalStoreRuntime({
    messages: timeline,
    convertMessage,
    onNew,
    isRunning,
  });

  // Periodic Heartbeat
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

  // Poll for cross-channel messages (e.g., Telegram → web sync).
  // Skip polling while isRunning — the optimistic user message is only in the
  // local store; the server won't have it until the agent finishes, so a poll
  // would overwrite the store and make the user message disappear.
  useEffect(() => {
    if (!activeChatId || !currentSessionInstanceId || isRunning) return;
    const intervalId = setInterval(() => {
      refreshMessages();
    }, 5000);
    return () => clearInterval(intervalId);
  }, [activeChatId, currentSessionInstanceId, refreshMessages, isRunning]);

  // Trigger session_open wakeup when tab becomes visible again
  useEffect(() => {
    const handleVisibilityChange = () => {
      if (!document.hidden) {
        useChatStore.getState().triggerWakeup();
      }
    };
    document.addEventListener('visibilitychange', handleVisibilityChange);
    return () => document.removeEventListener('visibilitychange', handleVisibilityChange);
  }, []);

  // beforeunload listener to deactivate session instance
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

  // SPEC-049: consume pendingPrompt from store (set by AskChip or Cmd+K).
  // Programmatically submit through the runtime's composer, then clear the store field.
  const pendingPrompt = useChatStore((s) => s.pendingPrompt);
  useEffect(() => {
    if (!pendingPrompt || !activeChatId || isRunning) return;
    useChatStore.getState().setPendingPrompt(null);
    // Use the runtime's thread composer to send — this goes through the same
    // onNew callback that the <Composer /> UI uses, keeping the message flow consistent.
    const composer = runtime.thread.composer;
    composer.setText(pendingPrompt);
    composer.send();
  }, [pendingPrompt, activeChatId, isRunning, runtime]);

  // Scroll to bottom when messages first load for a session (initial hydration or session switch).
  // Uses MutationObserver instead of fixed timeouts because assistant-ui Thread renders
  // messages asynchronously — fixed delays are a race condition.
  const hasScrolledRef = useRef(false);
  const lastChatIdRef = useRef<string | null>(null);

  useEffect(() => {
    if (activeChatId !== lastChatIdRef.current) {
      hasScrolledRef.current = false;
      lastChatIdRef.current = activeChatId ?? null;
    }

    if (messages.length > 0 && !hasScrolledRef.current) {
      const viewport = document.querySelector('.aui-thread-viewport');
      if (!viewport) return;

      const scrollToEnd = () => {
        viewport.scrollTop = viewport.scrollHeight;
      };

      const observer = new window.MutationObserver(() => {
        scrollToEnd();
      });
      observer.observe(viewport, { childList: true, subtree: true });

      const settleTimer = setTimeout(() => {
        hasScrolledRef.current = true;
        observer.disconnect();
      }, 1500);

      scrollToEnd();

      return () => {
        observer.disconnect();
        clearTimeout(settleTimer);
      };
    }
  }, [activeChatId, messages.length]);

  return (
    <div className="flex flex-col h-full bg-ui-bg">
      <MessageHeader
        chatTitle="AI Coach"
        status={isRunning ? 'Typing...' : 'Online'}
        statusColor={isRunning ? 'yellow' : 'green'}
        scope={scope}
      />

      <ConversationList agentName={agentId} />

      <div className="flex-1 min-h-0 relative">
        <AssistantRuntimeProvider runtime={runtime}>
          <GenericToolUI />
          <ThreadErrorBoundary>
            <div className="h-full">
              <Thread.Root>
                <Thread.Viewport>
                  <Thread.Messages components={{ SystemMessage: TimelineSystemMessage }} />
                  <Thread.ViewportFooter>
                    <Thread.ScrollToBottom />
                    <Composer />
                  </Thread.ViewportFooter>
                </Thread.Viewport>
              </Thread.Root>
            </div>
          </ThreadErrorBoundary>
        </AssistantRuntimeProvider>
      </div>
    </div>
  );
};

// Renders notification/approval timeline items that arrive as role:'system' messages.
// useMessage() is only valid inside a MessageRuntimeProvider, which Thread.Messages
// wraps each item in automatically.
const TimelineSystemMessage: React.FC = () => {
  const message = useMessage((m) => m);
  const custom = message.metadata?.custom as unknown as ChatMessage | undefined;
  if (!custom) return null;
  if (custom.sender === 'approval') return <ApprovalInlineMessage message={custom} />;
  if (custom.sender === 'notification') return <NotificationInlineMessage message={custom} />;
  return null;
};

export default ChatPanel;
