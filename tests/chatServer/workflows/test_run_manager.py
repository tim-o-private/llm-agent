"""Tests for WorkflowRunManager."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from chatServer.workflows.models import (
    MissingParameterError,
    TemplateNotFoundError,
    WorkflowRunStatus,
)
from chatServer.workflows.run_manager import WorkflowRunManager

SAMPLE_TEMPLATE_MD = """\
---
name: test-workflow
description: Test workflow
version: 1
default_gate_policy: none
---

# Test

## Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| account_id | yes | Account to use |
| limit | no | Max items |

## Steps

### step-1: Do Work
- **agent:** worker
- **depends_on:** []
- **tools:** []
- **description:** Do the work.
"""


def _mock_db_client():
    """Create a mock Supabase client with chained query builder."""
    db = MagicMock()
    table_mock = MagicMock()
    db.table.return_value = table_mock

    # Chain: insert().execute()
    insert_mock = MagicMock()
    insert_mock.execute = AsyncMock(return_value=MagicMock(data=[{"id": "run-1"}]))
    table_mock.insert.return_value = insert_mock

    # Chain: select().eq().execute()
    select_mock = MagicMock()
    eq_mock = MagicMock()
    eq_mock.execute = AsyncMock(return_value=MagicMock(data=[]))
    select_mock.eq.return_value = eq_mock
    table_mock.select.return_value = select_mock

    # Chain: update().eq().in_().execute()
    update_mock = MagicMock()
    update_eq_mock = MagicMock()
    update_in_mock = MagicMock()
    update_in_mock.execute = AsyncMock(return_value=MagicMock(data=[{"id": "run-1"}]))
    update_eq_mock.in_.return_value = update_in_mock
    update_mock.eq.return_value = update_eq_mock
    table_mock.update.return_value = update_mock

    return db


def _make_run_manager(db=None):
    if db is None:
        db = _mock_db_client()
    return WorkflowRunManager(
        db_client=db,
        llm_client=MagicMock(),
        tool_schemas=[],
        tool_executors={},
    )


class TestStartRun:
    @pytest.mark.asyncio
    @patch("chatServer.workflows.run_manager.get_template_registry")
    @patch("chatServer.workflows.run_manager.get_workflow_checkpointer")
    async def test_validates_missing_required_params(
        self, mock_checkpointer, mock_registry
    ):
        # Set up registry to return a template with a required param
        from chatServer.workflows.models import GraphTemplate, ParameterDef, StepDef

        template = GraphTemplate(
            name="test",
            parameters=[ParameterDef(name="account_id", required=True)],
            steps=[StepDef(name="step-1", description="Do it")],
        )
        registry = AsyncMock()
        registry.get_template = AsyncMock(return_value=template)
        mock_registry.return_value = registry

        manager = _make_run_manager()
        with pytest.raises(MissingParameterError, match="account_id"):
            await manager.start_run("user-1", "test", parameters={})

    @pytest.mark.asyncio
    @patch("chatServer.workflows.run_manager.get_template_registry")
    async def test_template_not_found(self, mock_registry):
        registry = AsyncMock()
        registry.get_template = AsyncMock(
            side_effect=TemplateNotFoundError("nope")
        )
        mock_registry.return_value = registry

        manager = _make_run_manager()
        with pytest.raises(TemplateNotFoundError):
            await manager.start_run("user-1", "nonexistent", parameters={})


class TestGetRunStatus:
    @pytest.mark.asyncio
    async def test_returns_none_for_missing(self):
        manager = _make_run_manager()
        result = await manager.get_run_status("nonexistent-id")
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_record(self):
        db = _mock_db_client()
        # Override select chain to return data
        select_mock = MagicMock()
        eq_mock = MagicMock()
        eq_mock.execute = AsyncMock(return_value=MagicMock(data=[{
            "id": "run-1",
            "user_id": "user-1",
            "template_name": "test",
            "thread_id": "thread-1",
            "status": "running",
            "parameters": {},
            "step_outputs": {},
            "current_step": "step-1",
            "error": None,
            "started_at": "2026-04-07T00:00:00Z",
            "completed_at": None,
            "created_at": "2026-04-07T00:00:00Z",
        }]))
        select_mock.eq.return_value = eq_mock
        db.table.return_value.select.return_value = select_mock

        manager = _make_run_manager(db)
        record = await manager.get_run_status("run-1")
        assert record is not None
        assert record.id == "run-1"
        assert record.status == WorkflowRunStatus.running


class TestCancelRun:
    @pytest.mark.asyncio
    async def test_cancels_active_run(self):
        db = _mock_db_client()
        manager = _make_run_manager(db)

        # Simulate an active task
        async def long_running():
            await asyncio.sleep(100)

        task = asyncio.create_task(long_running())
        manager._active_tasks["run-1"] = task

        result = await manager.cancel_run("run-1")
        assert result is True
        # Allow event loop to process the cancellation
        await asyncio.sleep(0)
        assert task.cancelled()
        assert "run-1" not in manager._active_tasks

    @pytest.mark.asyncio
    async def test_cancel_nonexistent_returns_false(self):
        db = _mock_db_client()
        # Override update chain to return empty (no rows matched)
        update_mock = MagicMock()
        update_eq_mock = MagicMock()
        update_in_mock = MagicMock()
        update_in_mock.execute = AsyncMock(return_value=MagicMock(data=[]))
        update_eq_mock.in_.return_value = update_in_mock
        update_mock.eq.return_value = update_eq_mock
        db.table.return_value.update.return_value = update_mock

        manager = _make_run_manager(db)
        result = await manager.cancel_run("nonexistent")
        assert result is False


class TestListRuns:
    @pytest.mark.asyncio
    async def test_lists_user_runs(self):
        db = _mock_db_client()
        # Override select chain for list
        select_mock = MagicMock()
        eq_mock = MagicMock()
        order_mock = MagicMock()
        order_mock.execute = AsyncMock(return_value=MagicMock(data=[
            {
                "id": "run-1",
                "user_id": "user-1",
                "template_name": "test",
                "thread_id": "t1",
                "status": "completed",
                "parameters": {},
                "step_outputs": {"step-1": "done"},
                "current_step": "step-1",
                "error": None,
                "started_at": "2026-04-07T00:00:00Z",
                "completed_at": "2026-04-07T00:01:00Z",
                "created_at": "2026-04-07T00:00:00Z",
            }
        ]))
        eq_mock.order.return_value = order_mock
        select_mock.eq.return_value = eq_mock
        db.table.return_value.select.return_value = select_mock

        manager = _make_run_manager(db)
        runs = await manager.list_runs("user-1")
        assert len(runs) == 1
        assert runs[0].template_name == "test"
        assert runs[0].status == WorkflowRunStatus.completed
