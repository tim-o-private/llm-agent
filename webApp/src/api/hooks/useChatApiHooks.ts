// This file is now empty as its primary purpose (client-side batch archival) is removed.
// It can be deleted if no other chat-related API hooks are planned for this file.
// For now, leaving it empty. 

import { useMutation, UseMutationOptions } from '@tanstack/react-query';
import { supabase } from '@/lib/supabaseClient';

interface SendMessagePayload {
  message: string;
  userId: string | null; // Included for consistency, though not directly in VITE_DEFAULT_CHAT_AGENT_ID body for this specific API
  activeChatId: string | null;
}

// This function contains the actual API call logic, similar to the original fetchAiResponse
async function sendMessageApi(payload: SendMessagePayload): Promise<string> {
  const { message, userId, activeChatId } = payload;
  console.log('sendMessageApi: Sending message to backend API (/api/chat):', message, 'UserId:', userId, 'activeChatId (for history):', activeChatId);

  if (!activeChatId) {
    throw new Error("Active Chat ID (for history) is missing. Cannot send message.");
  }

  const apiUrl = `${import.meta.env.VITE_API_BASE_URL || ''}/api/chat`;
  const { data: { session } } = await supabase.auth.getSession();
  const accessToken = session?.access_token;

  if (!accessToken) {
    throw new Error("User not authenticated. Cannot send message.");
  }

  const agentIdToUse = import.meta.env.VITE_DEFAULT_CHAT_AGENT_ID || "assistant";

  const requestBody = {
    agent_id: agentIdToUse,
    message: message,
    session_id: activeChatId,
  };

  const response = await fetch(apiUrl, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${accessToken}`,
    },
    body: JSON.stringify(requestBody),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ detail: 'Unknown error from API' }));
    const detail = errorData.detail || errorData.reply || 'No detail';
    console.error('sendMessageApi: API Error response data:', errorData);
    throw new Error(`API Error: ${response.status} ${response.statusText} - ${detail}`);
  }

  const data = await response.json();
  if (!data || typeof data.response !== 'string') {
    console.error('sendMessageApi: Invalid response structure from API:', data);
    throw new Error('Invalid response structure from API. Missing "response" string.');
  }
  return data.response;
}

export const useSendMessageMutation = () => {
  return useMutation<string, Error, SendMessagePayload, unknown>({
    mutationFn: sendMessageApi,
    onError: (error: Error) => {
      console.error('useSendMessageMutation encountered an error:', error.message);
      // Toast notifications could be triggered here if a global toast system is in place
      // e.g., toast.error(`Failed to send message: ${error.message}`);
    },
  } as UseMutationOptions<string, Error, SendMessagePayload, unknown>);
};

// If there was other content in this file, like useArchiveChatMutation, it would remain.
// For now, assuming this is a new file or only contains this mutation. 