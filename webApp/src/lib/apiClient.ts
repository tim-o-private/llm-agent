// Router API client for Clarity v2
// This client handles all communication with our FastAPI router
// which proxies PostgREST calls and provides the chat gateway

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '';

interface RequestOptions extends RequestInit {
  headers?: Record<string, string>;
}

class APIClient {
  private baseURL: string;

  constructor(baseURL: string = API_BASE_URL) {
    this.baseURL = baseURL;
  }

  private async getAuthHeaders(): Promise<Record<string, string>> {
    // Get the current session token for authentication
    const { getCurrentSession } = await import('./supabase');
    const session = await getCurrentSession();

    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      'x-client-info': 'clarity-v2-frontend',
    };

    if (session?.access_token) {
      headers['Authorization'] = `Bearer ${session.access_token}`;
    }

    return headers;
  }

  async request<T>(endpoint: string, options: RequestOptions = {}): Promise<T> {
    const url = `${this.baseURL}${endpoint}`;
    console.log(`[APIClient] Making request to: ${url}`);
    const authHeaders = await this.getAuthHeaders();

    const response = await fetch(url, {
      headers: {
        ...authHeaders,
        ...options.headers,
      },
      ...options,
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`API request failed: ${response.status} ${response.statusText} - ${errorText}`);
    }

    const contentType = response.headers.get('content-type');
    if (contentType && contentType.includes('application/json')) {
      return response.json();
    }

    return response.text() as T;
  }

  // PostgREST-style query methods (proxied through router)
  async select<T>(table: string, query: string = ''): Promise<T[]> {
    const queryString = query ? `?${query}` : '';
    return this.request<T[]>(`/api/${table}${queryString}`);
  }

  async insert<T>(table: string, data: any): Promise<T> {
    return this.request<T>(`/api/${table}`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async update<T>(table: string, id: string, data: any): Promise<T> {
    return this.request<T>(`/api/${table}?id=eq.${id}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  }

  async delete(table: string, id: string): Promise<void> {
    await this.request(`/api/${table}?id=eq.${id}`, {
      method: 'DELETE',
    });
  }

  // Chat gateway methods
  async sendChatMessage(message: string, sessionId?: string, agentName?: string): Promise<any> {
    return this.request('/chat', {
      method: 'POST',
      body: JSON.stringify({
        message,
        session_id: sessionId,
        agent_name: agentName,
      }),
    });
  }

  // Health check
  async health(): Promise<any> {
    return this.request('/health');
  }
}

export const apiClient = new APIClient();

// Export for testing and custom instances
export { APIClient };
