import { useMutation, UseMutationOptions } from '@tanstack/react-query';
import { supabase } from '@/lib/supabaseClient';

interface SendMessagePayload {
  message: string;
  userId: string | null; // Included for consistency, though not directly in VITE_DEFAULT_CHAT_AGENT_ID body for this specific API
  activeChatId: string | null;
}

// Interface matching the server's ChatResponse Pydantic model
interface ChatApiResponse {
  session_id: string;
  response: string; // The AI's textual response or a generic error message if data.error is also set
  tool_name?: string | null;
  tool_input?: Record<string, unknown> | null;
  error?: string | null; // Null if successful, error message string if an error occurred server-side
}

// This function contains the actual API call logic, similar to the original fetchAiResponse
async function sendMessageApi(payload: SendMessagePayload): Promise<string> {
  const { message, userId, activeChatId } = payload;
  console.log('sendMessageApi: Sending message to backend API (/api/chat):', message, 'UserId:', userId, 'activeChatId (for history):', activeChatId);

  if (!activeChatId) {
    // This should ideally be caught before calling the mutation, but good to have a safeguard.
    throw new Error("Active Chat ID (for history) is missing. Cannot send message.");
  }

  const apiUrl = `/api/chat`;
  const { data: { session } } = await supabase.auth.getSession();
  const accessToken = session?.access_token;

  if (!accessToken) {
    throw new Error("User not authenticated. Cannot send message.");
  }

  const agentName = import.meta.env.VITE_DEFAULT_CHAT_AGENT_ID || "assistant";

  const requestBody = {
    agent_name: agentName,
    message: message,
    session_id: activeChatId,
  };
  console.log("sendMessageApi: Request body:", requestBody);

  const httpResponse = await fetch(apiUrl, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${accessToken}`,
    },
    body: JSON.stringify(requestBody),
  });
  console.log("sendMessageApi: Raw HTTP response:", httpResponse);

  if (!httpResponse.ok) {
    // Attempt to parse error JSON, but provide a fallback
    const errorData = await httpResponse.json().catch(() => ({ 
      detail: `HTTP error ${httpResponse.status} ${httpResponse.statusText}. No further details from API.` 
    }));
    // Prioritize 'detail' (FastAPI default), then 'error' (our ChatApiResponse field if it somehow leaks here), then generic message
    const errorMessage = errorData.detail || errorData.error || `API Error: ${httpResponse.status} ${httpResponse.statusText}`;
    console.error('sendMessageApi: API Error response data (from !httpResponse.ok block):', errorData);
    throw new Error(errorMessage);
  }

  // httpResponse.ok is true, so we expect a 2xx status.
  // Now, parse the JSON and check the business logic 'error' field.
  const apiData: ChatApiResponse = await httpResponse.json();
  console.log('sendMessageApi: Parsed API data (ChatApiResponse):', apiData);

  if (apiData.error) {
    // The server processed the request but indicates a business logic error (e.g., ToolException, validation error)
    console.error('sendMessageApi: Business logic error from API:', apiData.error);
    throw new Error(apiData.error); // This error message will be available in mutation.error.message
  }

  // No HTTP error and no business logic error in apiData.error, so it's a success.
  // The 'response' field should contain the agent's textual message.
  if (typeof apiData.response !== 'string') {
    // This case should be rare if the server adheres to ChatResponse model,
    // but it's a good safeguard.
    console.error('sendMessageApi: Invalid successful response structure from API:', apiData);
    throw new Error('Invalid successful response structure from API. Missing "response" string.');
  }
  
  return apiData.response; // Return the actual agent message string
}

export const useSendMessageMutation = () => {
  return useMutation<string, Error, SendMessagePayload, unknown>({
    mutationFn: sendMessageApi,
    onSuccess: (data, variables) => {
      // data is the string returned by sendMessageApi (apiData.response)
      console.log('useSendMessageMutation: Message sent successfully. Agent response:', data, 'Variables:', variables);
      // Here you might want to update local state or react-query cache
      // with the new message pair (user message + AI response).
    },
    onError: (error: Error, variables) => {
      console.error('useSendMessageMutation encountered an error:', error.message, 'Variables:', variables);
      // The 'error.message' will now be the specific error string from apiData.error
      // or the HTTP error message.
      // This is where you would trigger a toast notification to the user.
      // e.g., toast.error(`Error: ${error.message}`);
    },
  } as UseMutationOptions<string, Error, SendMessagePayload, unknown>);
};

// If there was other content in this file, like useArchiveChatMutation, it would remain.
// For now, assuming this is a new file or only contains this mutation. 