export type Json =
  | string
  | number
  | boolean
  | null
  | { [key: string]: Json | undefined }
  | Json[]

export type Database = {
  public: {
    Tables: {
      agent_configurations: {
        Row: {
          agent_name: string
          created_at: string | null
          id: string
          llm_config: Json
          system_prompt: string
          updated_at: string | null
        }
        Insert: {
          agent_name: string
          created_at?: string | null
          id?: string
          llm_config: Json
          system_prompt: string
          updated_at?: string | null
        }
        Update: {
          agent_name?: string
          created_at?: string | null
          id?: string
          llm_config?: Json
          system_prompt?: string
          updated_at?: string | null
        }
        Relationships: []
      }
      agent_logs: {
        Row: {
          action: string
          agent_name: string
          created_at: string | null
          id: string
          result: Json | null
          user_id: string
        }
        Insert: {
          action: string
          agent_name: string
          created_at?: string | null
          id?: string
          result?: Json | null
          user_id: string
        }
        Update: {
          action?: string
          agent_name?: string
          created_at?: string | null
          id?: string
          result?: Json | null
          user_id?: string
        }
        Relationships: []
      }
      agent_long_term_memory: {
        Row: {
          agent_name: string
          created_at: string
          id: string
          notes: string | null
          updated_at: string
          user_id: string
        }
        Insert: {
          agent_name: string
          created_at?: string
          id?: string
          notes?: string | null
          updated_at?: string
          user_id: string
        }
        Update: {
          agent_name?: string
          created_at?: string
          id?: string
          notes?: string | null
          updated_at?: string
          user_id?: string
        }
        Relationships: []
      }
      agent_schedules: {
        Row: {
          active: boolean | null
          agent_name: string
          config: Json | null
          created_at: string | null
          id: string
          prompt: string
          schedule_cron: string
          updated_at: string | null
          user_id: string
        }
        Insert: {
          active?: boolean | null
          agent_name: string
          config?: Json | null
          created_at?: string | null
          id?: string
          prompt: string
          schedule_cron: string
          updated_at?: string | null
          user_id: string
        }
        Update: {
          active?: boolean | null
          agent_name?: string
          config?: Json | null
          created_at?: string | null
          id?: string
          prompt?: string
          schedule_cron?: string
          updated_at?: string | null
          user_id?: string
        }
        Relationships: []
      }
      agent_sessions: {
        Row: {
          agent_id: string
          agent_name: string
          created_at: string
          session_id: string
          summary: string | null
          updated_at: string
          user_id: string
        }
        Insert: {
          agent_id?: string
          agent_name: string
          created_at?: string
          session_id?: string
          summary?: string | null
          updated_at?: string
          user_id: string
        }
        Update: {
          agent_id?: string
          agent_name?: string
          created_at?: string
          session_id?: string
          summary?: string | null
          updated_at?: string
          user_id?: string
        }
        Relationships: []
      }
      agent_tools: {
        Row: {
          agent_id: string
          config_override: Json | null
          created_at: string | null
          id: string
          is_active: boolean | null
          is_deleted: boolean | null
          tool_id: string
          updated_at: string | null
        }
        Insert: {
          agent_id: string
          config_override?: Json | null
          created_at?: string | null
          id?: string
          is_active?: boolean | null
          is_deleted?: boolean | null
          tool_id: string
          updated_at?: string | null
        }
        Update: {
          agent_id?: string
          config_override?: Json | null
          created_at?: string | null
          id?: string
          is_active?: boolean | null
          is_deleted?: boolean | null
          tool_id?: string
          updated_at?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "agent_tools_agent_id_fkey1"
            columns: ["agent_id"]
            isOneToOne: false
            referencedRelation: "agent_configurations"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "agent_tools_tool_id_fkey"
            columns: ["tool_id"]
            isOneToOne: false
            referencedRelation: "tools"
            referencedColumns: ["id"]
          },
        ]
      }
      agent_tools_backup: {
        Row: {
          agent_id: string | null
          config: Json
          created_at: string | null
          description: string | null
          id: string
          is_active: boolean | null
          is_deleted: boolean
          name: string
          order: number | null
          type: Database["public"]["Enums"]["agent_tool_type"]
          updated_at: string | null
        }
        Insert: {
          agent_id?: string | null
          config: Json
          created_at?: string | null
          description?: string | null
          id?: string
          is_active?: boolean | null
          is_deleted?: boolean
          name: string
          order?: number | null
          type: Database["public"]["Enums"]["agent_tool_type"]
          updated_at?: string | null
        }
        Update: {
          agent_id?: string | null
          config?: Json
          created_at?: string | null
          description?: string | null
          id?: string
          is_active?: boolean | null
          is_deleted?: boolean
          name?: string
          order?: number | null
          type?: Database["public"]["Enums"]["agent_tool_type"]
          updated_at?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "agent_tools_agent_id_fkey"
            columns: ["agent_id"]
            isOneToOne: false
            referencedRelation: "agent_configurations"
            referencedColumns: ["id"]
          },
        ]
      }
      chat_message_history: {
        Row: {
          created_at: string | null
          id: number
          message: Json
          session_id: string
        }
        Insert: {
          created_at?: string | null
          id?: number
          message: Json
          session_id: string
        }
        Update: {
          created_at?: string | null
          id?: number
          message?: Json
          session_id?: string
        }
        Relationships: []
      }
      chat_sessions: {
        Row: {
          agent_name: string
          chat_id: string | null
          created_at: string
          id: string
          is_active: boolean
          metadata: Json | null
          updated_at: string
          user_id: string
        }
        Insert: {
          agent_name: string
          chat_id?: string | null
          created_at?: string
          id?: string
          is_active?: boolean
          metadata?: Json | null
          updated_at?: string
          user_id: string
        }
        Update: {
          agent_name?: string
          chat_id?: string | null
          created_at?: string
          id?: string
          is_active?: boolean
          metadata?: Json | null
          updated_at?: string
          user_id?: string
        }
        Relationships: []
      }
      email_digest_batches: {
        Row: {
          created_at: string | null
          duration_seconds: number
          end_time: string
          failed: number
          id: string
          start_time: string
          successful: number
          summary: Json | null
          total_users: number
        }
        Insert: {
          created_at?: string | null
          duration_seconds: number
          end_time: string
          failed?: number
          id?: string
          start_time: string
          successful?: number
          summary?: Json | null
          total_users?: number
        }
        Update: {
          created_at?: string | null
          duration_seconds?: number
          end_time?: string
          failed?: number
          id?: string
          start_time?: string
          successful?: number
          summary?: Json | null
          total_users?: number
        }
        Relationships: []
      }
      email_digests: {
        Row: {
          context: string | null
          created_at: string | null
          digest_content: string
          email_count: number | null
          generated_at: string
          hours_back: number
          id: string
          include_read: boolean
          status: string
          updated_at: string | null
          user_id: string
        }
        Insert: {
          context?: string | null
          created_at?: string | null
          digest_content: string
          email_count?: number | null
          generated_at: string
          hours_back?: number
          id?: string
          include_read?: boolean
          status?: string
          updated_at?: string | null
          user_id: string
        }
        Update: {
          context?: string | null
          created_at?: string | null
          digest_content?: string
          email_count?: number | null
          generated_at?: string
          hours_back?: number
          id?: string
          include_read?: boolean
          status?: string
          updated_at?: string | null
          user_id?: string
        }
        Relationships: []
      }
      external_api_connections: {
        Row: {
          access_token_secret_id: string | null
          created_at: string
          id: string
          is_active: boolean
          refresh_token_secret_id: string | null
          scopes: string[]
          service_name: string
          service_user_email: string | null
          service_user_id: string | null
          token_expires_at: string | null
          updated_at: string
          user_id: string
        }
        Insert: {
          access_token_secret_id?: string | null
          created_at?: string
          id?: string
          is_active?: boolean
          refresh_token_secret_id?: string | null
          scopes?: string[]
          service_name: string
          service_user_email?: string | null
          service_user_id?: string | null
          token_expires_at?: string | null
          updated_at?: string
          user_id: string
        }
        Update: {
          access_token_secret_id?: string | null
          created_at?: string
          id?: string
          is_active?: boolean
          refresh_token_secret_id?: string | null
          scopes?: string[]
          service_name?: string
          service_user_email?: string | null
          service_user_id?: string | null
          token_expires_at?: string | null
          updated_at?: string
          user_id?: string
        }
        Relationships: []
      }
      focus_sessions: {
        Row: {
          created_at: string
          duration_seconds: number | null
          ended_at: string | null
          id: string
          mood: string | null
          notes: string | null
          outcome: string | null
          started_at: string
          task_id: string
          user_id: string
        }
        Insert: {
          created_at?: string
          duration_seconds?: number | null
          ended_at?: string | null
          id?: string
          mood?: string | null
          notes?: string | null
          outcome?: string | null
          started_at?: string
          task_id: string
          user_id: string
        }
        Update: {
          created_at?: string
          duration_seconds?: number | null
          ended_at?: string | null
          id?: string
          mood?: string | null
          notes?: string | null
          outcome?: string | null
          started_at?: string
          task_id?: string
          user_id?: string
        }
        Relationships: [
          {
            foreignKeyName: "focus_sessions_task_id_fkey"
            columns: ["task_id"]
            isOneToOne: false
            referencedRelation: "tasks"
            referencedColumns: ["id"]
          },
        ]
      }
      notes: {
        Row: {
          content: string
          created_at: string
          deleted: boolean
          id: string
          title: string | null
          updated_at: string
          user_id: string
        }
        Insert: {
          content?: string
          created_at?: string
          deleted?: boolean
          id?: string
          title?: string | null
          updated_at?: string
          user_id: string
        }
        Update: {
          content?: string
          created_at?: string
          deleted?: boolean
          id?: string
          title?: string | null
          updated_at?: string
          user_id?: string
        }
        Relationships: []
      }
      tasks: {
        Row: {
          category: string | null
          completed: boolean
          completion_note: string | null
          created_at: string
          deleted: boolean | null
          description: string | null
          due_date: string | null
          id: string
          motivation: string | null
          notes: string | null
          parent_task_id: string | null
          position: number | null
          priority: number | null
          status: Database["public"]["Enums"]["task_status"] | null
          subtask_position: number | null
          time_period: string | null
          title: string
          updated_at: string | null
          user_id: string
        }
        Insert: {
          category?: string | null
          completed?: boolean
          completion_note?: string | null
          created_at?: string
          deleted?: boolean | null
          description?: string | null
          due_date?: string | null
          id?: string
          motivation?: string | null
          notes?: string | null
          parent_task_id?: string | null
          position?: number | null
          priority?: number | null
          status?: Database["public"]["Enums"]["task_status"] | null
          subtask_position?: number | null
          time_period?: string | null
          title: string
          updated_at?: string | null
          user_id: string
        }
        Update: {
          category?: string | null
          completed?: boolean
          completion_note?: string | null
          created_at?: string
          deleted?: boolean | null
          description?: string | null
          due_date?: string | null
          id?: string
          motivation?: string | null
          notes?: string | null
          parent_task_id?: string | null
          position?: number | null
          priority?: number | null
          status?: Database["public"]["Enums"]["task_status"] | null
          subtask_position?: number | null
          time_period?: string | null
          title?: string
          updated_at?: string | null
          user_id?: string
        }
        Relationships: [
          {
            foreignKeyName: "tasks_parent_task_id_fkey"
            columns: ["parent_task_id"]
            isOneToOne: false
            referencedRelation: "tasks"
            referencedColumns: ["id"]
          },
        ]
      }
      tools: {
        Row: {
          config: Json
          created_at: string | null
          description: string | null
          id: string
          is_active: boolean | null
          is_deleted: boolean | null
          name: string
          type: Database["public"]["Enums"]["agent_tool_type"]
          updated_at: string | null
        }
        Insert: {
          config?: Json
          created_at?: string | null
          description?: string | null
          id?: string
          is_active?: boolean | null
          is_deleted?: boolean | null
          name: string
          type: Database["public"]["Enums"]["agent_tool_type"]
          updated_at?: string | null
        }
        Update: {
          config?: Json
          created_at?: string | null
          description?: string | null
          id?: string
          is_active?: boolean | null
          is_deleted?: boolean | null
          name?: string
          type?: Database["public"]["Enums"]["agent_tool_type"]
          updated_at?: string | null
        }
        Relationships: []
      }
      user_agent_prompt_customizations: {
        Row: {
          agent_name: string
          content: Json
          created_at: string
          customization_type: string
          id: string
          is_active: boolean
          priority: number
          updated_at: string
          user_id: string
        }
        Insert: {
          agent_name: string
          content: Json
          created_at?: string
          customization_type?: string
          id?: string
          is_active?: boolean
          priority?: number
          updated_at?: string
          user_id: string
        }
        Update: {
          agent_name?: string
          content?: Json
          created_at?: string
          customization_type?: string
          id?: string
          is_active?: boolean
          priority?: number
          updated_at?: string
          user_id?: string
        }
        Relationships: []
      }
    }
    Views: {
      user_api_tokens: {
        Row: {
          access_token: string | null
          created_at: string | null
          id: string | null
          is_active: boolean | null
          refresh_token: string | null
          scopes: string[] | null
          service_name: string | null
          service_user_email: string | null
          service_user_id: string | null
          token_expires_at: string | null
          updated_at: string | null
          user_id: string | null
        }
        Relationships: []
      }
    }
    Functions: {
      check_connection_status: {
        Args: { p_user_id: string; p_service_name: string }
        Returns: Json
      }
      get_connection_info: {
        Args: { p_user_id: string; p_service_name: string }
        Returns: Json
      }
      get_oauth_tokens: {
        Args: { p_user_id: string; p_service_name: string }
        Returns: Json
      }
      get_oauth_tokens_for_scheduler: {
        Args: { p_user_id: string; p_service_name: string }
        Returns: Json
      }
      is_record_owner: {
        Args: { record_user_id: string }
        Returns: boolean
      }
      list_user_connections: {
        Args: { p_user_id: string }
        Returns: Json
      }
      revoke_oauth_tokens: {
        Args: { p_user_id: string; p_service_name: string }
        Returns: Json
      }
      store_oauth_tokens: {
        Args: {
          p_user_id: string
          p_service_name: string
          p_access_token: string
          p_refresh_token?: string
          p_expires_at?: string
          p_scopes?: string[]
          p_service_user_id?: string
          p_service_user_email?: string
        }
        Returns: Json
      }
      store_secret: {
        Args: { p_secret: string; p_name: string; p_description?: string }
        Returns: string
      }
    }
    Enums: {
      agent_tool_type:
        | "FileManagementToolkit"
        | "CRUDTool"
        | "GmailTool"
        | "EmailDigestTool"
      task_status:
        | "pending"
        | "planning"
        | "in_progress"
        | "completed"
        | "skipped"
        | "deferred"
    }
    CompositeTypes: {
      [_ in never]: never
    }
  }
}

type DefaultSchema = Database[Extract<keyof Database, "public">]

export type Tables<
  DefaultSchemaTableNameOrOptions extends
    | keyof (DefaultSchema["Tables"] & DefaultSchema["Views"])
    | { schema: keyof Database },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof Database
  }
    ? keyof (Database[DefaultSchemaTableNameOrOptions["schema"]]["Tables"] &
        Database[DefaultSchemaTableNameOrOptions["schema"]]["Views"])
    : never = never,
> = DefaultSchemaTableNameOrOptions extends { schema: keyof Database }
  ? (Database[DefaultSchemaTableNameOrOptions["schema"]]["Tables"] &
      Database[DefaultSchemaTableNameOrOptions["schema"]]["Views"])[TableName] extends {
      Row: infer R
    }
    ? R
    : never
  : DefaultSchemaTableNameOrOptions extends keyof (DefaultSchema["Tables"] &
        DefaultSchema["Views"])
    ? (DefaultSchema["Tables"] &
        DefaultSchema["Views"])[DefaultSchemaTableNameOrOptions] extends {
        Row: infer R
      }
      ? R
      : never
    : never

export type TablesInsert<
  DefaultSchemaTableNameOrOptions extends
    | keyof DefaultSchema["Tables"]
    | { schema: keyof Database },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof Database
  }
    ? keyof Database[DefaultSchemaTableNameOrOptions["schema"]]["Tables"]
    : never = never,
> = DefaultSchemaTableNameOrOptions extends { schema: keyof Database }
  ? Database[DefaultSchemaTableNameOrOptions["schema"]]["Tables"][TableName] extends {
      Insert: infer I
    }
    ? I
    : never
  : DefaultSchemaTableNameOrOptions extends keyof DefaultSchema["Tables"]
    ? DefaultSchema["Tables"][DefaultSchemaTableNameOrOptions] extends {
        Insert: infer I
      }
      ? I
      : never
    : never

export type TablesUpdate<
  DefaultSchemaTableNameOrOptions extends
    | keyof DefaultSchema["Tables"]
    | { schema: keyof Database },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof Database
  }
    ? keyof Database[DefaultSchemaTableNameOrOptions["schema"]]["Tables"]
    : never = never,
> = DefaultSchemaTableNameOrOptions extends { schema: keyof Database }
  ? Database[DefaultSchemaTableNameOrOptions["schema"]]["Tables"][TableName] extends {
      Update: infer U
    }
    ? U
    : never
  : DefaultSchemaTableNameOrOptions extends keyof DefaultSchema["Tables"]
    ? DefaultSchema["Tables"][DefaultSchemaTableNameOrOptions] extends {
        Update: infer U
      }
      ? U
      : never
    : never

export type Enums<
  DefaultSchemaEnumNameOrOptions extends
    | keyof DefaultSchema["Enums"]
    | { schema: keyof Database },
  EnumName extends DefaultSchemaEnumNameOrOptions extends {
    schema: keyof Database
  }
    ? keyof Database[DefaultSchemaEnumNameOrOptions["schema"]]["Enums"]
    : never = never,
> = DefaultSchemaEnumNameOrOptions extends { schema: keyof Database }
  ? Database[DefaultSchemaEnumNameOrOptions["schema"]]["Enums"][EnumName]
  : DefaultSchemaEnumNameOrOptions extends keyof DefaultSchema["Enums"]
    ? DefaultSchema["Enums"][DefaultSchemaEnumNameOrOptions]
    : never

export type CompositeTypes<
  PublicCompositeTypeNameOrOptions extends
    | keyof DefaultSchema["CompositeTypes"]
    | { schema: keyof Database },
  CompositeTypeName extends PublicCompositeTypeNameOrOptions extends {
    schema: keyof Database
  }
    ? keyof Database[PublicCompositeTypeNameOrOptions["schema"]]["CompositeTypes"]
    : never = never,
> = PublicCompositeTypeNameOrOptions extends { schema: keyof Database }
  ? Database[PublicCompositeTypeNameOrOptions["schema"]]["CompositeTypes"][CompositeTypeName]
  : PublicCompositeTypeNameOrOptions extends keyof DefaultSchema["CompositeTypes"]
    ? DefaultSchema["CompositeTypes"][PublicCompositeTypeNameOrOptions]
    : never

export const Constants = {
  public: {
    Enums: {
      agent_tool_type: [
        "FileManagementToolkit",
        "CRUDTool",
        "GmailTool",
        "EmailDigestTool",
      ],
      task_status: [
        "pending",
        "planning",
        "in_progress",
        "completed",
        "skipped",
        "deferred",
      ],
    },
  },
} as const
