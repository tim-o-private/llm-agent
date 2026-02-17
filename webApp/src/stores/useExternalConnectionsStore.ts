import { create } from 'zustand';

export interface ExternalConnection {
  id: string;
  user_id: string;
  service_name: 'gmail' | 'google_calendar' | 'slack';
  service_user_email?: string;
  service_user_id?: string;
  scopes: string[];
  token_expires_at?: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

interface ExternalConnectionsState {
  connections: ExternalConnection[];

  // Actions
  setConnections: (connections: ExternalConnection[]) => void;
  addConnection: (connection: ExternalConnection) => void;
  updateConnection: (id: string, updates: Partial<ExternalConnection>) => void;
  removeConnection: (id: string) => void;

  // Getters
  getConnectionByService: (serviceName: string) => ExternalConnection | undefined;
  isServiceConnected: (serviceName: string) => boolean;
}

export const useExternalConnectionsStore = create<ExternalConnectionsState>((set, get) => ({
  connections: [],

  setConnections: (connections) => set({ connections }),

  addConnection: (connection) =>
    set((state) => ({
      connections: [...state.connections.filter((c) => c.service_name !== connection.service_name), connection],
    })),

  updateConnection: (id, updates) =>
    set((state) => ({
      connections: state.connections.map((conn) => (conn.id === id ? { ...conn, ...updates } : conn)),
    })),

  removeConnection: (id) =>
    set((state) => ({
      connections: state.connections.filter((conn) => conn.id !== id),
    })),

  getConnectionByService: (serviceName) => {
    const { connections } = get();
    return connections.find((conn) => conn.service_name === serviceName && conn.is_active);
  },

  isServiceConnected: (serviceName) => {
    const connection = get().getConnectionByService(serviceName);
    return !!connection;
  },
}));
