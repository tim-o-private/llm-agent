"""Tests for draft-reply revision loop in WorkflowRunManager."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from chatServer.workflows.models import WorkflowRunRecord, WorkflowRunStatus
from chatServer.workflows.run_manager import WorkflowRunManager


def _make_manager(run_record=None):
    """Create a WorkflowRunManager with mocked dependencies."""
    db_client = MagicMock()

    # Mock the query chain for update
    update_chain = MagicMock()
    update_chain.eq = MagicMock(return_value=update_chain)
    update_chain.in_ = MagicMock(return_value=update_chain)
    update_chain.execute = AsyncMock(return_value=MagicMock(data=[{"id": "run-1"}]))
    db_client.table = MagicMock(return_value=MagicMock(
        update=MagicMock(return_value=update_chain),
        select=MagicMock(return_value=update_chain),
    ))

    manager = WorkflowRunManager(
        db_client=db_client,
        anthropic_client=MagicMock(),
        tool_schemas=[],
        tool_executors={},
    )

    # Patch get_run_status to return the provided record
    if run_record:
        manager.get_run_status = AsyncMock(return_value=run_record)

    return manager, db_client


def _waiting_record(**overrides):
    """Create a WorkflowRunRecord in waiting_for_approval status."""
    defaults = {
        "id": "run-1",
        "user_id": "user-1",
        "template_name": "draft-reply",
        "thread_id": "thread-1",
        "status": WorkflowRunStatus.waiting_for_approval,
        "parameters": {"message_id": "msg-1", "account": "test@example.com"},
        "step_outputs": {"compose-draft": "Draft text here"},
        "current_step": "present-for-approval_gate",
    }
    defaults.update(overrides)
    return WorkflowRunRecord(**defaults)


class TestResumeRunApprove:
    @pytest.mark.asyncio
    async def test_approve_sets_running(self):
        record = _waiting_record()
        manager, db = _make_manager(record)

        result = await manager.resume_run("run-1", action="approve")
        assert result is True

    @pytest.mark.asyncio
    async def test_approve_not_found(self):
        manager, _ = _make_manager()
        manager.get_run_status = AsyncMock(return_value=None)

        result = await manager.resume_run("nonexistent", action="approve")
        assert result is False

    @pytest.mark.asyncio
    async def test_approve_wrong_status(self):
        record = _waiting_record(status=WorkflowRunStatus.completed)
        manager, _ = _make_manager(record)

        result = await manager.resume_run("run-1", action="approve")
        assert result is False


class TestResumeRunReject:
    @pytest.mark.asyncio
    async def test_reject_cancels_run(self):
        record = _waiting_record()
        manager, db = _make_manager(record)

        result = await manager.resume_run("run-1", action="reject")
        assert result is True


class TestResumeRunRevise:
    @pytest.mark.asyncio
    async def test_revise_appends_instructions(self):
        record = _waiting_record(
            parameters={"message_id": "msg-1", "account": "a@b.com", "instructions": "Be brief"}
        )
        manager, db = _make_manager(record)

        result = await manager.resume_run(
            "run-1",
            action="revise",
            data={"instructions": "Make it shorter"},
        )
        assert result is True

        # Verify the update call included updated parameters
        update_call = db.table.return_value.update
        assert update_call.called
        call_args = update_call.call_args[0][0]
        assert call_args["status"] == "running"
        assert "Make it shorter" in call_args["parameters"]["instructions"]
        assert call_args["parameters"]["_revision_count"] == 1

    @pytest.mark.asyncio
    async def test_revise_increments_count(self):
        record = _waiting_record(
            parameters={"message_id": "msg-1", "account": "a@b.com", "_revision_count": 1}
        )
        manager, db = _make_manager(record)

        await manager.resume_run("run-1", action="revise", data={"instructions": "Try again"})
        call_args = db.table.return_value.update.call_args[0][0]
        assert call_args["parameters"]["_revision_count"] == 2

    @pytest.mark.asyncio
    async def test_revise_max_reached_cancels(self):
        record = _waiting_record(
            parameters={"message_id": "msg-1", "account": "a@b.com", "_revision_count": 3}
        )
        manager, db = _make_manager(record)

        result = await manager.resume_run("run-1", action="revise", data={"instructions": "Again"})
        assert result is True

        # Should cancel, not update to running
        call_args = db.table.return_value.update.call_args[0][0]
        assert call_args["status"] == "cancelled"
        assert "Max revisions" in call_args.get("error", "")

    @pytest.mark.asyncio
    async def test_revise_first_time_no_existing_instructions(self):
        record = _waiting_record(
            parameters={"message_id": "msg-1", "account": "a@b.com"}
        )
        manager, db = _make_manager(record)

        await manager.resume_run("run-1", action="revise", data={"instructions": "Be formal"})
        call_args = db.table.return_value.update.call_args[0][0]
        assert "Be formal" in call_args["parameters"]["instructions"]
        assert call_args["parameters"]["_revision_count"] == 1
