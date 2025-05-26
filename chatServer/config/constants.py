"""Constants used throughout the chat server."""

import logging

# Session and task management constants
SESSION_INSTANCE_TTL_SECONDS = 30 * 60  # 30 minutes
SCHEDULED_TASK_INTERVAL_SECONDS = 5 * 60  # Run checks every 5 minutes

# API tags
PROMPT_CUSTOMIZATIONS_TAG = "Prompt Customizations"

# Database table names
CHAT_MESSAGE_HISTORY_TABLE_NAME = "chat_message_history"

# Logging
DEFAULT_LOG_LEVEL = logging.INFO 