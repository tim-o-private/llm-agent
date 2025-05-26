"""Unit tests for constants module."""

import unittest
import logging

from chatServer.config.constants import (
    SESSION_INSTANCE_TTL_SECONDS,
    SCHEDULED_TASK_INTERVAL_SECONDS,
    PROMPT_CUSTOMIZATIONS_TAG,
    CHAT_MESSAGE_HISTORY_TABLE_NAME,
    DEFAULT_LOG_LEVEL,
)


class TestConstants(unittest.TestCase):
    """Test cases for constants module."""

    def test_session_instance_ttl_seconds(self):
        """Test SESSION_INSTANCE_TTL_SECONDS constant."""
        self.assertEqual(SESSION_INSTANCE_TTL_SECONDS, 30 * 60)  # 30 minutes
        self.assertIsInstance(SESSION_INSTANCE_TTL_SECONDS, int)

    def test_scheduled_task_interval_seconds(self):
        """Test SCHEDULED_TASK_INTERVAL_SECONDS constant."""
        self.assertEqual(SCHEDULED_TASK_INTERVAL_SECONDS, 5 * 60)  # 5 minutes
        self.assertIsInstance(SCHEDULED_TASK_INTERVAL_SECONDS, int)

    def test_prompt_customizations_tag(self):
        """Test PROMPT_CUSTOMIZATIONS_TAG constant."""
        self.assertEqual(PROMPT_CUSTOMIZATIONS_TAG, "Prompt Customizations")
        self.assertIsInstance(PROMPT_CUSTOMIZATIONS_TAG, str)

    def test_chat_message_history_table_name(self):
        """Test CHAT_MESSAGE_HISTORY_TABLE_NAME constant."""
        self.assertEqual(CHAT_MESSAGE_HISTORY_TABLE_NAME, "chat_message_history")
        self.assertIsInstance(CHAT_MESSAGE_HISTORY_TABLE_NAME, str)

    def test_default_log_level(self):
        """Test DEFAULT_LOG_LEVEL constant."""
        self.assertEqual(DEFAULT_LOG_LEVEL, logging.INFO)
        self.assertIsInstance(DEFAULT_LOG_LEVEL, int)

    def test_constants_are_immutable_types(self):
        """Test that constants are immutable types (int, str, etc.)."""
        # These should be immutable types to prevent accidental modification
        self.assertIsInstance(SESSION_INSTANCE_TTL_SECONDS, (int, float, str, bool))
        self.assertIsInstance(SCHEDULED_TASK_INTERVAL_SECONDS, (int, float, str, bool))
        self.assertIsInstance(PROMPT_CUSTOMIZATIONS_TAG, (int, float, str, bool))
        self.assertIsInstance(CHAT_MESSAGE_HISTORY_TABLE_NAME, (int, float, str, bool))
        self.assertIsInstance(DEFAULT_LOG_LEVEL, (int, float, str, bool))

    def test_time_constants_are_positive(self):
        """Test that time-related constants are positive values."""
        self.assertGreater(SESSION_INSTANCE_TTL_SECONDS, 0)
        self.assertGreater(SCHEDULED_TASK_INTERVAL_SECONDS, 0)

    def test_string_constants_are_non_empty(self):
        """Test that string constants are non-empty."""
        self.assertTrue(PROMPT_CUSTOMIZATIONS_TAG.strip())
        self.assertTrue(CHAT_MESSAGE_HISTORY_TABLE_NAME.strip())

    def test_log_level_is_valid(self):
        """Test that DEFAULT_LOG_LEVEL is a valid logging level."""
        valid_levels = [
            logging.NOTSET,
            logging.DEBUG,
            logging.INFO,
            logging.WARNING,
            logging.ERROR,
            logging.CRITICAL
        ]
        self.assertIn(DEFAULT_LOG_LEVEL, valid_levels)


if __name__ == '__main__':
    unittest.main() 