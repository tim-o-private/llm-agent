"""Unit tests for WorkflowRunsService."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from chatServer.services.workflow_runs_service import WorkflowRunsService


def _mock_db(data=None):
    """Return a mock UserScopedClient whose query chain echoes the recorded calls.

    The chain is: ``db.table(...).select(...).order(...).limit(...).eq(...).execute()``
    where ``.eq()`` is optional (only called when ``template_name`` is set).
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


@pytest.mark.asyncio
async def test_list_runs_returns_rows():
    rows = [{"id": "r1", "template_name": "regenerate-today", "status": "completed"}]
    db, _ = _mock_db(data=rows)

    result = await WorkflowRunsService(db).list_runs()

    assert result == rows


@pytest.mark.asyncio
async def test_list_runs_returns_empty_when_data_is_none():
    db, _ = _mock_db(data=None)

    result = await WorkflowRunsService(db).list_runs()

    assert result == []


@pytest.mark.asyncio
async def test_list_runs_hits_workflow_runs_table_with_expected_columns():
    db, chain = _mock_db(data=[])

    await WorkflowRunsService(db).list_runs()

    db.table.assert_called_once_with("workflow_runs")
    chain.select.assert_called_once()
    selected = chain.select.call_args.args[0]
    for col in (
        "id",
        "template_name",
        "status",
        "current_step",
        "error",
        "started_at",
        "completed_at",
        "created_at",
    ):
        assert col in selected


@pytest.mark.asyncio
async def test_list_runs_orders_by_created_at_desc():
    db, chain = _mock_db(data=[])

    await WorkflowRunsService(db).list_runs()

    chain.order.assert_called_once_with("created_at", desc=True)


@pytest.mark.asyncio
async def test_list_runs_applies_limit():
    db, chain = _mock_db(data=[])

    await WorkflowRunsService(db).list_runs(limit=42)

    chain.limit.assert_called_once_with(42)


@pytest.mark.asyncio
async def test_list_runs_defaults_limit_to_ten():
    db, chain = _mock_db(data=[])

    await WorkflowRunsService(db).list_runs()

    chain.limit.assert_called_once_with(10)


@pytest.mark.asyncio
async def test_list_runs_filters_by_template_name_when_provided():
    db, chain = _mock_db(data=[])

    await WorkflowRunsService(db).list_runs(template_name="regenerate-today")

    chain.eq.assert_called_once_with("template_name", "regenerate-today")


@pytest.mark.asyncio
async def test_list_runs_does_not_filter_when_template_name_is_none():
    db, chain = _mock_db(data=[])

    await WorkflowRunsService(db).list_runs(template_name=None)

    chain.eq.assert_not_called()
