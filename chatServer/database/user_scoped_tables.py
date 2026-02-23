"""Canonical set of tables that have a user_id column."""

USER_SCOPED_TABLES: set[str] = {
    "tasks",
    "notes",
    "focus_sessions",
    "reminders",
    "agent_logs",
    "agent_long_term_memory",
    "agent_sessions",
    "agent_schedules",
    "audit_logs",
    "channel_linking_tokens",
    "email_digests",
    "external_api_connections",
    "notifications",
    "pending_actions",
    "user_agent_prompt_customizations",
    "user_channels",
    "user_tool_preferences",
    "chat_sessions",
    "agent_execution_results",
}
