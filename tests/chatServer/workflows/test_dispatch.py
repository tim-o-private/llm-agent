"""Tests for dispatch_workflow tool executor."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from chatServer.workflows.dispatch import dispatch_workflow
from chatServer.workflows.models import MissingParameterError, TemplateNotFoundError

_RUN_MANAGER_PATH = "chatServer.workflows.dispatch.WorkflowRunManager"
_REGISTRY_PATH = "chatServer.workflows.dispatch.get_template_registry"


@pytest.fixture
def mock_deps():
    return {
        "user_id": "user-1",
        "db_client": MagicMock(),
        "llm_client": MagicMock(),
        "tool_schemas": [],
        "tool_executors": {},
    }


class TestDispatchWorkflow:
    @pytest.mark.asyncio
    @patch(_RUN_MANAGER_PATH)
    async def test_starts_workflow(self, mock_manager_cls, mock_deps):
        mock_manager = MagicMock()
        mock_manager.start_run = AsyncMock(return_value="run-123")
        mock_manager_cls.return_value = mock_manager

        result = await dispatch_workflow(
            args={"workflow_name": "email-triage", "parameters": {"hours_back": 12}},
            **mock_deps,
        )

        assert "run-123" in result
        assert "email-triage" in result
        mock_manager.start_run.assert_called_once_with(
            user_id="user-1",
            template_name="email-triage",
            parameters={"hours_back": 12},
        )

    @pytest.mark.asyncio
    async def test_missing_workflow_name(self, mock_deps):
        result = await dispatch_workflow(
            args={"workflow_name": ""},
            **mock_deps,
        )
        assert "required" in result.lower()

    @pytest.mark.asyncio
    @patch(_REGISTRY_PATH)
    @patch(_RUN_MANAGER_PATH)
    async def test_template_not_found(
        self, mock_manager_cls, mock_registry_fn, mock_deps
    ):
        mock_manager = MagicMock()
        mock_manager.start_run = AsyncMock(
            side_effect=TemplateNotFoundError("nope")
        )
        mock_manager_cls.return_value = mock_manager

        mock_registry = AsyncMock()
        mock_registry.list_templates = AsyncMock(
            return_value=["morning-briefing", "draft-reply"]
        )
        mock_registry_fn.return_value = mock_registry

        result = await dispatch_workflow(
            args={"workflow_name": "nonexistent"},
            **mock_deps,
        )

        assert "Unknown workflow" in result
        assert "morning-briefing" in result

    @pytest.mark.asyncio
    @patch(_RUN_MANAGER_PATH)
    async def test_missing_parameters(self, mock_manager_cls, mock_deps):
        mock_manager = MagicMock()
        mock_manager.start_run = AsyncMock(
            side_effect=MissingParameterError(["account_id", "hours_back"])
        )
        mock_manager_cls.return_value = mock_manager

        result = await dispatch_workflow(
            args={"workflow_name": "email-triage"},
            **mock_deps,
        )

        assert "Missing required parameters" in result
        assert "account_id" in result

    @pytest.mark.asyncio
    @patch(_RUN_MANAGER_PATH)
    async def test_general_error(self, mock_manager_cls, mock_deps):
        mock_manager = MagicMock()
        mock_manager.start_run = AsyncMock(
            side_effect=RuntimeError("connection failed")
        )
        mock_manager_cls.return_value = mock_manager

        result = await dispatch_workflow(
            args={"workflow_name": "email-triage"},
            **mock_deps,
        )

        assert "Failed to start workflow" in result

    @pytest.mark.asyncio
    @patch(_RUN_MANAGER_PATH)
    async def test_default_empty_parameters(self, mock_manager_cls, mock_deps):
        mock_manager = MagicMock()
        mock_manager.start_run = AsyncMock(return_value="run-456")
        mock_manager_cls.return_value = mock_manager

        result = await dispatch_workflow(
            args={"workflow_name": "test"},
            **mock_deps,
        )

        mock_manager.start_run.assert_called_once_with(
            user_id="user-1",
            template_name="test",
            parameters={},
        )
        assert "run-456" in result
