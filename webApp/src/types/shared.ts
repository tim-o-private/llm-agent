// Shared types for Clarity v2
// Common types used across multiple components and modules

export interface ApiResponse<T = any> {
  data?: T;
  error?: string;
  message?: string;
  status: 'success' | 'error';
}

export interface PaginatedResponse<T> {
  data: T[];
  count: number;
  page: number;
  limit: number;
  total_pages: number;
}

export interface User {
  id: string;
  email: string;
  name?: string;
  avatar_url?: string;
  created_at: string;
  updated_at: string;
}

export interface AuthState {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  error: string | null;
  
  // Actions
  signIn: (email: string, password: string) => Promise<void>;
  signOut: () => Promise<void>;
  refreshUser: () => Promise<void>;
  clearError: () => void;
}

// Common filter and sort types
export interface FilterOptions {
  search?: string;
  category?: string;
  status?: string;
  date_from?: string;
  date_to?: string;
  limit?: number;
  offset?: number;
}

export interface SortOptions {
  field: string;
  direction: 'asc' | 'desc';
}

// Task-specific types
export interface TaskState {
  tasks: Task[];
  isLoading: boolean;
  error: string | null;
  lastFetch: Date | null;
  
  // Actions
  createTask: (task: CreateTaskRequest) => Promise<Task>;
  getTasks: (forceRefresh?: boolean) => Promise<Task[]>;
  updateTask: (id: string, updates: UpdateTaskRequest) => Promise<Task>;
  deleteTask: (id: string) => Promise<void>;
  
  // Cache management
  clearCache: () => void;
  isStale: () => boolean;
  startPolling: () => void;
  stopPolling: () => void;
}

// Memory/Notes types
export interface MemoryState {
  notes: Note[];
  isLoading: boolean;
  error: string | null;
  lastFetch: Date | null;
  
  // Actions
  createNote: (note: CreateNoteRequest) => Promise<Note>;
  getNotes: (forceRefresh?: boolean) => Promise<Note[]>;
  updateNote: (id: string, updates: UpdateNoteRequest) => Promise<Note>;
  deleteNote: (id: string) => Promise<void>;
  
  // Cache management
  clearCache: () => void;
  isStale: () => boolean;
}

// Import database types
import type { Task, CreateTaskRequest, UpdateTaskRequest, Note, CreateNoteRequest, UpdateNoteRequest } from './database';

export type { Task, CreateTaskRequest, UpdateTaskRequest, Note, CreateNoteRequest, UpdateNoteRequest }; 