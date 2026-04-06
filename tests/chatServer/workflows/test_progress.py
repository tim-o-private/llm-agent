"""Tests for workflow progress tracking and human gates."""

from unittest.mock import AsyncMock

import pytest

from chatServer.workflows.progress import HumanGate, ProgressWriter


class MockCursor:
    """Mock psycopg async cursor."""

    def __init__(self):
        self.execute = AsyncMock()
        self.executed_queries = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass


class MockPgConnection:
    """Mock psycopg async connection with cursor context manager."""

    def __init__(self):
        self._cursor = MockCursor()

    def cursor(self):
        return self._cursor


@pytest.fixture
def pg_conn():
    return MockPgConnection()


@pytest.fixture
def writer(pg_conn):
    return ProgressWriter(
        pg_connection=pg_conn,
        session_id="session-1",
        run_id="run-1",
        template_name="email-triage",
    )


class TestProgressWriter:
    @pytest.mark.asyncio
    async def test_step_started(self, writer, pg_conn):
        await writer.step_started("fetch-emails")
        pg_conn._cursor.execute.assert_called_once()
        args = pg_conn._cursor.execute.call_args[0]
        assert "INSERT INTO chat_message_history" in args[0]
        msg_data = args[1][1]  # second parameter (message JSON)
        assert msg_data["data"]["additional_kwargs"]["event_type"] == "step_started"
        assert "fetch-emails" in msg_data["data"]["content"]

    @pytest.mark.asyncio
    async def test_step_completed(self, writer, pg_conn):
        await writer.step_completed("fetch-emails", output_preview="Found 5 emails")
        args = pg_conn._cursor.execute.call_args[0]
        msg_data = args[1][1]
        assert msg_data["data"]["additional_kwargs"]["event_type"] == "step_completed"
        assert "Found 5 emails" in msg_data["data"]["content"]

    @pytest.mark.asyncio
    async def test_step_completed_truncates_long_output(self, writer, pg_conn):
        long_output = "x" * 1000
        await writer.step_completed("step-1", output_preview=long_output)
        args = pg_conn._cursor.execute.call_args[0]
        msg_data = args[1][1]
        content = msg_data["data"]["content"]
        assert "..." in content
        # Content should be truncated (500 chars of output + prefix + ellipsis)
        assert len(content) < 1000

    @pytest.mark.asyncio
    async def test_approval_required(self, writer, pg_conn):
        await writer.approval_required("draft-step", "Review the draft before sending")
        args = pg_conn._cursor.execute.call_args[0]
        msg_data = args[1][1]
        assert msg_data["data"]["additional_kwargs"]["event_type"] == "approval_required"
        assert "draft-step" in msg_data["data"]["content"]

    @pytest.mark.asyncio
    async def test_workflow_completed(self, writer, pg_conn):
        await writer.workflow_completed(summary="Processed 5 emails")
        args = pg_conn._cursor.execute.call_args[0]
        msg_data = args[1][1]
        assert msg_data["data"]["additional_kwargs"]["event_type"] == "workflow_completed"
        assert "Processed 5 emails" in msg_data["data"]["content"]

    @pytest.mark.asyncio
    async def test_workflow_failed(self, writer, pg_conn):
        await writer.workflow_failed("API timeout")
        args = pg_conn._cursor.execute.call_args[0]
        msg_data = args[1][1]
        assert msg_data["data"]["additional_kwargs"]["event_type"] == "workflow_failed"
        assert "API timeout" in msg_data["data"]["content"]

    @pytest.mark.asyncio
    async def test_write_error_logged_not_raised(self, pg_conn):
        pg_conn._cursor.execute = AsyncMock(side_effect=Exception("DB down"))
        writer = ProgressWriter(
            pg_connection=pg_conn,
            session_id="s1",
            run_id="r1",
            template_name="test",
        )
        # Should not raise
        await writer.step_started("step-1")

    @pytest.mark.asyncio
    async def test_session_id_in_query(self, writer, pg_conn):
        await writer.step_started("step-1")
        args = pg_conn._cursor.execute.call_args[0]
        assert args[1][0] == "session-1"

    @pytest.mark.asyncio
    async def test_metadata_contains_run_id(self, writer, pg_conn):
        await writer.step_started("step-1")
        args = pg_conn._cursor.execute.call_args[0]
        msg_data = args[1][1]
        assert msg_data["data"]["additional_kwargs"]["run_id"] == "run-1"
        assert msg_data["data"]["additional_kwargs"]["template_name"] == "email-triage"


class TestHumanGate:
    @pytest.mark.asyncio
    async def test_request_approval_creates_pending_action(self):
        mock_pending = AsyncMock()
        mock_pending.queue_action = AsyncMock(return_value="action-1")
        mock_notifications = AsyncMock()
        mock_notifications.notify_user = AsyncMock()

        gate = HumanGate(mock_pending, mock_notifications)
        action_id = await gate.request_approval(
            user_id="user-1",
            run_id="run-1",
            step_name="draft-step",
            output_preview="Here is a draft...",
            template_name="draft-reply",
            session_id="session-1",
        )

        assert action_id == "action-1"
        mock_pending.queue_action.assert_called_once()
        call_kwargs = mock_pending.queue_action.call_args.kwargs
        assert call_kwargs["tool_name"] == "workflow_gate"
        assert call_kwargs["tool_args"]["run_id"] == "run-1"
        assert call_kwargs["tool_args"]["step_name"] == "draft-step"

    @pytest.mark.asyncio
    async def test_request_approval_notifies_user(self):
        mock_pending = AsyncMock()
        mock_pending.queue_action = AsyncMock(return_value="action-1")
        mock_notifications = AsyncMock()
        mock_notifications.notify_user = AsyncMock()

        gate = HumanGate(mock_pending, mock_notifications)
        await gate.request_approval(
            user_id="user-1",
            run_id="run-1",
            step_name="review",
            output_preview="Draft content",
            template_name="draft-reply",
        )

        mock_notifications.notify_user.assert_called_once()
        call_kwargs = mock_notifications.notify_user.call_args.kwargs
        assert call_kwargs["user_id"] == "user-1"
        assert call_kwargs["category"] == "workflow_gate"
        assert "review" in call_kwargs["title"]

    @pytest.mark.asyncio
    async def test_truncates_long_output_preview(self):
        mock_pending = AsyncMock()
        mock_pending.queue_action = AsyncMock(return_value="action-1")
        mock_notifications = AsyncMock()
        mock_notifications.notify_user = AsyncMock()

        gate = HumanGate(mock_pending, mock_notifications)
        long_output = "x" * 2000
        await gate.request_approval(
            user_id="user-1",
            run_id="run-1",
            step_name="step",
            output_preview=long_output,
            template_name="test",
        )

        call_kwargs = mock_pending.queue_action.call_args.kwargs
        assert len(call_kwargs["tool_args"]["output_preview"]) <= 1000
