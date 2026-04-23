"""Unit tests for WorkflowRunsService.list_runs_detailed method (SPEC-048 FU-1).

Tests the extended query that selects all columns including step_outputs
and parameters for the run detail view (AC-19).  The existing list_runs
tests live in test_workflow_runs_service.py and are not duplicated here.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from chatServer.services.workflow_runs_service import WorkflowRunsService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_run(idx: int, **overrides) -> dict:
    """Build a fake workflow_runs row with all detailed columns."""
    base = {
        "id": f"run-{idx:03d}",
        "template_name": "morning-briefing",
        "status": "completed",
        "current_step": "",
        "error": None,
        "parameters": {"recipient": "tim@stlvr.coffee"},
        "step_outputs": {
            "step-1": f"Output from step-1 of run {idx}",
            "step-2": f"Output from step-2 of run {idx}",
        },
        "started_at": f"2026-04-{21 - idx}T06:00:00Z",
        "completed_at": f"2026-04-{21 - idx}T06:02:30Z",
        "created_at": f"2026-04-{21 - idx}T06:00:00Z",
    }
    base.update(overrides)
    return base


def _mock_db(data=None):
    """Return a mock UserScopedClient whose query chain echoes recorded calls.

    Chain: db.table(...).select(...).order(...).limit(...)[.eq(...)].execute()
    """
    db = MagicMock()
    chain = MagicMock()

    db.table.return_value = chain
    chain.select.return_value = chain
    chain.order.return_value = chain
    chain.limit.return_value = chain
    chain.eq.return_value = chain
    chain.execute = AsyncMock(return_value=MagicMock(data=data))
    return db, chain


# ---------------------------------------------------------------------------
# list_runs_detailed — returns all columns
# ---------------------------------------------------------------------------


class TestListRunsDetailed:
    @pytest.mark.asyncio
    async def test_returns_all_columns_including_step_outputs_and_parameters(self):
        rows = [_make_run(1), _make_run(2)]
        db, _ = _mock_db(data=rows)

        result = await WorkflowRunsService(db).list_runs_detailed()

        assert len(result) == 2
        # Verify the detailed columns are present.
        assert "step_outputs" in result[0]
        assert "parameters" in result[0]
        assert result[0]["step_outputs"]["step-1"] == "Output from step-1 of run 1"
        assert result[0]["parameters"]["recipient"] == "tim@stlvr.coffee"

    @pytest.mark.asyncio
    async def test_selects_detailed_columns(self):
        db, chain = _mock_db(data=[])

        await WorkflowRunsService(db).list_runs_detailed()

        chain.select.assert_called_once()
        selected = chain.select.call_args.args[0]
        for col in (
            "id",
            "template_name",
            "status",
            "current_step",
            "error",
            "parameters",
            "step_outputs",
            "started_at",
            "completed_at",
            "created_at",
        ):
            assert col in selected, f"Missing column {col!r} in select"

    @pytest.mark.asyncio
    async def test_template_name_filter_works(self):
        db, chain = _mock_db(data=[])

        await WorkflowRunsService(db).list_runs_detailed(
            template_name="regenerate-today",
        )

        chain.eq.assert_called_once_with("template_name", "regenerate-today")

    @pytest.mark.asyncio
    async def test_template_name_none_skips_filter(self):
        db, chain = _mock_db(data=[])

        await WorkflowRunsService(db).list_runs_detailed(template_name=None)

        chain.eq.assert_not_called()

    @pytest.mark.asyncio
    async def test_limit_applies(self):
        db, chain = _mock_db(data=[])

        await WorkflowRunsService(db).list_runs_detailed(limit=5)

        chain.limit.assert_called_once_with(5)

    @pytest.mark.asyncio
    async def test_default_limit_is_25(self):
        db, chain = _mock_db(data=[])

        await WorkflowRunsService(db).list_runs_detailed()

        chain.limit.assert_called_once_with(25)

    @pytest.mark.asyncio
    async def test_empty_result_returns_empty_list(self):
        db, _ = _mock_db(data=None)

        result = await WorkflowRunsService(db).list_runs_detailed()

        assert result == []

    @pytest.mark.asyncio
    async def test_orders_by_created_at_desc(self):
        db, chain = _mock_db(data=[])

        await WorkflowRunsService(db).list_runs_detailed()

        chain.order.assert_called_once_with("created_at", desc=True)
