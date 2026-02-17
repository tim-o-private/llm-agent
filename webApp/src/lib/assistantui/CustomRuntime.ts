import type { ChatModelAdapter } from '@assistant-ui/react';
import { supabase } from '@/lib/supabaseClient';
import { useChatStore, type ChatMessage } from '@/stores/useChatStore';

// Helper function to check if content is text type
function isTextContent(content: unknown): content is { type: 'text'; text: string } {
  return (
    typeof content === 'object' &&
    content !== null &&
    'type' in content &&
    'text' in content &&
    (content as { type: unknown }).type === 'text' &&
    typeof (content as { text: unknown }).text === 'string'
  );
}

interface BackendChatResponse {
  session_id: string;
  response: string;
  tool_name?: string | null;
  tool_input?: Record<string, unknown> | null;
  error?: string | null;
}

export function createCustomChatModelAdapter(
  agentName: string,
  userIdProvider: () => string | null,
  activeChatIdProvider: () => string | null,
): ChatModelAdapter {
  return {
    async run({ messages, abortSignal }) {
      const userId = userIdProvider();
      const activeChatId = activeChatIdProvider();

      if (!activeChatId) {
        throw new Error('Chat session ID not available. Please ensure the session is initialized.');
      }

      if (!userId) {
        throw new Error('User not authenticated. Please log in and try again.');
      }

      // Get the last user message
      const lastMessage = messages[messages.length - 1];
      if (!lastMessage || lastMessage.role !== 'user') {
        throw new Error('No user message found');
      }

      // Extract text from the message content
      const userText = lastMessage.content
        .filter(isTextContent)
        .map((content) => content.text)
        .join(' ');

      if (!userText) {
        throw new Error('No text content found in user message');
      }

      // Add user message to Zustand store for state synchronization
      try {
        await useChatStore.getState().addMessage({
          text: userText,
          sender: 'user',
        });
      } catch (error) {
        console.warn('Failed to sync user message to Zustand store:', error);
        // Continue with API call even if store sync fails
      }

      try {
        const {
          data: { session },
        } = await supabase.auth.getSession();
        const accessToken = session?.access_token;
        if (!accessToken) {
          throw new Error('User authentication token not found.');
        }

        const requestBody = {
          agent_name: agentName,
          message: userText,
          session_id: activeChatId,
        };

        const apiUrl = `${import.meta.env.VITE_API_BASE_URL || ''}/api/chat`;
        const httpResponse = await fetch(apiUrl, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${accessToken}`,
          },
          body: JSON.stringify(requestBody),
          signal: abortSignal,
        });

        if (!httpResponse.ok) {
          let errorDetail = `API Error: ${httpResponse.status} ${httpResponse.statusText}`;
          try {
            const errorData = await httpResponse.json();
            errorDetail = errorData.detail || errorDetail;
          } catch {
            // Ignore if error response is not JSON
          }
          throw new Error(errorDetail);
        }

        const backendResponse: BackendChatResponse = await httpResponse.json();

        if (backendResponse.error) {
          throw new Error(backendResponse.error);
        }

        // Add AI response to Zustand store for state synchronization
        try {
          await useChatStore.getState().addMessage({
            text: backendResponse.response,
            sender: 'ai',
            tool_name: backendResponse.tool_name || undefined,
            tool_input: backendResponse.tool_input || undefined,
          });
        } catch (error) {
          console.warn('Failed to sync AI response to Zustand store:', error);
          // Continue with response even if store sync fails
        }

        // Send heartbeat to maintain session
        try {
          await useChatStore.getState().sendHeartbeatAsync();
        } catch (error) {
          console.warn('Failed to send heartbeat:', error);
          // Non-critical, continue with response
        }

        // Return the response in the format expected by assistant-ui
        return {
          content: [{ type: 'text', text: backendResponse.response }],
          // TODO: Handle tool calls when needed
          // toolCalls: backendResponse.tool_name ? [...] : undefined
        };
      } catch (error) {
        console.error('CustomChatModelAdapter: Error sending message:', error);
        throw error;
      }
    },
  };
}

// Enhanced runtime adapter with state synchronization hooks
export function createEnhancedCustomChatModelAdapter(
  agentName: string,
  userIdProvider: () => string | null,
  activeChatIdProvider: () => string | null,
  onMessageSent?: (message: ChatMessage) => void,
  onMessageReceived?: (message: ChatMessage) => void,
): ChatModelAdapter {
  return {
    async run({ messages, abortSignal }) {
      const userId = userIdProvider();
      const activeChatId = activeChatIdProvider();

      if (!activeChatId) {
        throw new Error('Chat session ID not available. Please ensure the session is initialized.');
      }

      if (!userId) {
        throw new Error('User not authenticated. Please log in and try again.');
      }

      // Get the last user message
      const lastMessage = messages[messages.length - 1];
      if (!lastMessage || lastMessage.role !== 'user') {
        throw new Error('No user message found');
      }

      // Extract text from the message content
      const userText = lastMessage.content
        .filter(isTextContent)
        .map((content) => content.text)
        .join(' ');

      if (!userText) {
        throw new Error('No text content found in user message');
      }

      // Create user message object
      const userMessage: Omit<ChatMessage, 'id' | 'timestamp'> = {
        text: userText,
        sender: 'user',
      };

      // Add user message to Zustand store and trigger callback
      try {
        await useChatStore.getState().addMessage(userMessage);
        if (onMessageSent) {
          const fullUserMessage: ChatMessage = {
            ...userMessage,
            id: `user-${Date.now()}`,
            timestamp: new Date(),
          };
          onMessageSent(fullUserMessage);
        }
      } catch (error) {
        console.warn('Failed to sync user message to Zustand store:', error);
      }

      try {
        const {
          data: { session },
        } = await supabase.auth.getSession();
        const accessToken = session?.access_token;
        if (!accessToken) {
          throw new Error('User authentication token not found.');
        }

        const requestBody = {
          agent_name: agentName,
          message: userText,
          session_id: activeChatId,
        };

        const apiUrl = `${import.meta.env.VITE_API_BASE_URL || ''}/api/chat`;
        const httpResponse = await fetch(apiUrl, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${accessToken}`,
          },
          body: JSON.stringify(requestBody),
          signal: abortSignal,
        });

        if (!httpResponse.ok) {
          let errorDetail = `API Error: ${httpResponse.status} ${httpResponse.statusText}`;
          try {
            const errorData = await httpResponse.json();
            errorDetail = errorData.detail || errorDetail;
          } catch {
            // Ignore if error response is not JSON
          }
          throw new Error(errorDetail);
        }

        const backendResponse: BackendChatResponse = await httpResponse.json();

        if (backendResponse.error) {
          throw new Error(backendResponse.error);
        }

        // Create AI response message object
        const aiMessage: Omit<ChatMessage, 'id' | 'timestamp'> = {
          text: backendResponse.response,
          sender: 'ai',
          tool_name: backendResponse.tool_name || undefined,
          tool_input: backendResponse.tool_input || undefined,
        };

        // Add AI response to Zustand store and trigger callback
        try {
          await useChatStore.getState().addMessage(aiMessage);
          if (onMessageReceived) {
            const fullAiMessage: ChatMessage = {
              ...aiMessage,
              id: `ai-${Date.now()}`,
              timestamp: new Date(),
            };
            onMessageReceived(fullAiMessage);
          }
        } catch (error) {
          console.warn('Failed to sync AI response to Zustand store:', error);
        }

        // Send heartbeat to maintain session
        try {
          await useChatStore.getState().sendHeartbeatAsync();
        } catch (error) {
          console.warn('Failed to send heartbeat:', error);
        }

        // Return the response in the format expected by assistant-ui
        return {
          content: [{ type: 'text', text: backendResponse.response }],
          // TODO: Handle tool calls when needed
          // toolCalls: backendResponse.tool_name ? [...] : undefined
        };
      } catch (error) {
        console.error('CustomChatModelAdapter: Error sending message:', error);
        throw error;
      }
    },
  };
}
