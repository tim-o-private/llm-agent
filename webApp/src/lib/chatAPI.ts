import { ChatRequest, ChatResponse } from '../types/chat';

const ROUTER_BASE_URL = import.meta.env.VITE_API_URL || '';

export class ChatAPIClient {
  private baseURL: string;

  constructor(baseURL: string = ROUTER_BASE_URL) {
    this.baseURL = baseURL;
  }

  async sendMessage(request: ChatRequest): Promise<ChatResponse> {
    const response = await fetch(`${this.baseURL}/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-client-info': 'clarity-v2-frontend',
      },
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      throw new Error(`Chat request failed: ${response.statusText}`);
    }

    return response.json();
  }

  async healthCheck(): Promise<boolean> {
    try {
      const response = await fetch(`${this.baseURL}/health`);
      return response.ok;
    } catch {
      return false;
    }
  }
}

export const chatAPI = new ChatAPIClient();
