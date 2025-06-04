// Auto-generated database types for Clarity v2
// Generated from Supabase schema on 2025-01-30

export type Json =
  | string
  | number
  | boolean
  | null
  | { [key: string]: Json | undefined }
  | Json[]

export interface Database {
  public: {
    Tables: {
      tasks: {
        Row: {
          id: string;
          user_id: string;
          title: string;
          notes: string | null;
          category: string | null;
          completed: boolean;
          due_date: string | null;
          time_period: string | null;
          created_at: string;
          updated_at: string | null;
          position: number | null;
          priority: number | null;
          status: string | null;
          motivation: string | null;
          description: string | null;
          completion_note: string | null;
          parent_task_id: string | null;
          subtask_position: number | null;
          deleted: boolean | null;
        };
        Insert: {
          id?: string;
          user_id: string;
          title: string;
          notes?: string | null;
          category?: string | null;
          completed?: boolean;
          due_date?: string | null;
          time_period?: string | null;
          created_at?: string;
          updated_at?: string | null;
          position?: number | null;
          priority?: number | null;
          status?: string | null;
          motivation?: string | null;
          description?: string | null;
          completion_note?: string | null;
          parent_task_id?: string | null;
          subtask_position?: number | null;
          deleted?: boolean | null;
        };
        Update: {
          id?: string;
          user_id?: string;
          title?: string;
          notes?: string | null;
          category?: string | null;
          completed?: boolean;
          due_date?: string | null;
          time_period?: string | null;
          created_at?: string;
          updated_at?: string | null;
          position?: number | null;
          priority?: number | null;
          status?: string | null;
          motivation?: string | null;
          description?: string | null;
          completion_note?: string | null;
          parent_task_id?: string | null;
          subtask_position?: number | null;
          deleted?: boolean | null;
        };
      };
      notes: {
        Row: {
          id: string;
          user_id: string;
          title: string | null;
          content: string;
          created_at: string;
          updated_at: string;
          deleted: boolean;
        };
        Insert: {
          id?: string;
          user_id: string;
          title?: string | null;
          content: string;
          created_at?: string;
          updated_at?: string;
          deleted?: boolean;
        };
        Update: {
          id?: string;
          user_id?: string;
          title?: string | null;
          content?: string;
          created_at?: string;
          updated_at?: string;
          deleted?: boolean;
        };
      };
      chat_sessions: {
        Row: {
          id: string;
          user_id: string;
          title: string | null;
          created_at: string;
          updated_at: string;
        };
        Insert: {
          id?: string;
          user_id: string;
          title?: string | null;
          created_at?: string;
          updated_at?: string;
        };
        Update: {
          id?: string;
          user_id?: string;
          title?: string | null;
          created_at?: string;
          updated_at?: string;
        };
      };
      chat_message_history: {
        Row: {
          id: string;
          session_id: string;
          user_id: string;
          role: string;
          content: string;
          created_at: string;
        };
        Insert: {
          id?: string;
          session_id: string;
          user_id: string;
          role: string;
          content: string;
          created_at?: string;
        };
        Update: {
          id?: string;
          session_id?: string;
          user_id?: string;
          role?: string;
          content?: string;
          created_at?: string;
        };
      };
    };
    Views: {
      [_ in never]: never;
    };
    Functions: {
      [_ in never]: never;
    };
    Enums: {
      [_ in never]: never;
    };
    CompositeTypes: {
      [_ in never]: never;
    };
  };
}

// Convenience type exports
export type Task = Database['public']['Tables']['tasks']['Row'];
export type CreateTaskRequest = Database['public']['Tables']['tasks']['Insert'];
export type UpdateTaskRequest = Database['public']['Tables']['tasks']['Update'];

export type Note = Database['public']['Tables']['notes']['Row'];
export type CreateNoteRequest = Database['public']['Tables']['notes']['Insert'];
export type UpdateNoteRequest = Database['public']['Tables']['notes']['Update'];

export type ChatSession = Database['public']['Tables']['chat_sessions']['Row'];
export type CreateChatSessionRequest = Database['public']['Tables']['chat_sessions']['Insert'];

export type ChatMessage = Database['public']['Tables']['chat_message_history']['Row'];
export type CreateChatMessageRequest = Database['public']['Tables']['chat_message_history']['Insert'];
