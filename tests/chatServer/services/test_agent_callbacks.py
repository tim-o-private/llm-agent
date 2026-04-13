"""Tests for chatServer.services.agent_callbacks — ToolCallLogger."""

import uuid

from chatServer.services.agent_callbacks import ToolCallLogger, tool_call_logger


class TestToolCallLogger:
    def test_on_tool_start_logs_tool_name(self, caplog):
        logger = ToolCallLogger()
        with caplog.at_level("INFO", logger="chatServer.services.agent_callbacks"):
            logger.on_tool_start(
                serialized={"name": "edit_file"},
                input_str='{"path": "/user/memory/AGENTS.md"}',
                run_id=uuid.uuid4(),
            )
        assert "edit_file" in caplog.text

    def test_on_tool_start_truncates_long_input(self, caplog):
        logger = ToolCallLogger()
        long_input = "x" * 500
        with caplog.at_level("INFO", logger="chatServer.services.agent_callbacks"):
            logger.on_tool_start(
                serialized={"name": "write_file"},
                input_str=long_input,
                run_id=uuid.uuid4(),
            )
        # Should truncate to 200 chars, not include full 500
        assert "x" * 200 in caplog.text
        assert "x" * 201 not in caplog.text

    def test_on_tool_start_short_input_not_truncated(self, caplog):
        logger = ToolCallLogger()
        short_input = "short input"
        with caplog.at_level("INFO", logger="chatServer.services.agent_callbacks"):
            logger.on_tool_start(
                serialized={"name": "ls"},
                input_str=short_input,
                run_id=uuid.uuid4(),
            )
        assert "short input" in caplog.text

    def test_on_tool_start_missing_name(self, caplog):
        logger = ToolCallLogger()
        with caplog.at_level("INFO", logger="chatServer.services.agent_callbacks"):
            logger.on_tool_start(
                serialized={},
                input_str="test",
                run_id=uuid.uuid4(),
            )
        assert "unknown" in caplog.text

    def test_on_tool_end_logs_output_length(self, caplog):
        logger = ToolCallLogger()
        with caplog.at_level("DEBUG", logger="chatServer.services.agent_callbacks"):
            logger.on_tool_end(
                output="result content here",
                run_id=uuid.uuid4(),
            )
        assert "19 chars" in caplog.text

    def test_singleton_is_tool_call_logger_instance(self):
        assert isinstance(tool_call_logger, ToolCallLogger)

    def test_singleton_reusable(self):
        """Singleton can be called multiple times without error."""
        tool_call_logger.on_tool_start(
            serialized={"name": "test"},
            input_str="test",
            run_id=uuid.uuid4(),
        )
        tool_call_logger.on_tool_end(
            output="result",
            run_id=uuid.uuid4(),
        )
