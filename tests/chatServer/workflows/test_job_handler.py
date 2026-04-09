"""Tests for handle_workflow job handler."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from chatServer.services.job_handlers import handle_workflow

# dispatch_workflow and create_system_client are lazily imported inside
# handle_workflow, so we patch at the source modules
_DISPATCH_PATH = "chatServer.workflows.dispatch.dispatch_workflow"
_SYSTEM_CLIENT_PATH = "chatServer.database.supabase_client.create_system_client"
_ANTHROPIC_PATH = "chatServer.services.job_handlers._get_anthropic_client_for_workflow"


class TestHandleWorkflow:
    @pytest.mark.asyncio
    @patch(_ANTHROPIC_PATH)
    @patch(_SYSTEM_CLIENT_PATH, new_callable=AsyncMock)
    @patch(_DISPATCH_PATH, new_callable=AsyncMock)
    async def test_dispatches_workflow(
        self, mock_dispatch, mock_system_client, mock_anthropic
    ):
        mock_dispatch.return_value = "Started workflow 'email-triage' (run_id: run-1)."
        mock_system_client.return_value = MagicMock()
        mock_anthropic.return_value = MagicMock()

        result = await handle_workflow({
            "id": "job-1",
            "input": {
                "user_id": "user-1",
                "template_name": "email-triage",
                "parameters": {"hours_back": 12},
            },
        })

        assert result["status"] == "started"
        mock_dispatch.assert_called_once()

    @pytest.mark.asyncio
    @patch(_ANTHROPIC_PATH)
    @patch(_SYSTEM_CLIENT_PATH, new_callable=AsyncMock)
    @patch(_DISPATCH_PATH, new_callable=AsyncMock)
    async def test_raises_on_failure(
        self, mock_dispatch, mock_system_client, mock_anthropic
    ):
        mock_dispatch.return_value = "Failed to start workflow: template not found"
        mock_system_client.return_value = MagicMock()
        mock_anthropic.return_value = MagicMock()

        with pytest.raises(RuntimeError, match="Failed"):
            await handle_workflow({
                "id": "job-1",
                "input": {
                    "user_id": "user-1",
                    "template_name": "nonexistent",
                    "parameters": {},
                },
            })

    @pytest.mark.asyncio
    @patch(_ANTHROPIC_PATH)
    @patch(_SYSTEM_CLIENT_PATH, new_callable=AsyncMock)
    @patch(_DISPATCH_PATH, new_callable=AsyncMock)
    async def test_default_empty_parameters(
        self, mock_dispatch, mock_system_client, mock_anthropic
    ):
        mock_dispatch.return_value = "Started workflow 'test' (run_id: run-2)."
        mock_system_client.return_value = MagicMock()
        mock_anthropic.return_value = MagicMock()

        await handle_workflow({
            "id": "job-2",
            "input": {
                "user_id": "user-1",
                "template_name": "test",
            },
        })

        call_kwargs = mock_dispatch.call_args.kwargs
        assert call_kwargs["args"]["parameters"] == {}

    @pytest.mark.asyncio
    @patch(_ANTHROPIC_PATH)
    @patch(_SYSTEM_CLIENT_PATH, new_callable=AsyncMock)
    @patch(_DISPATCH_PATH, new_callable=AsyncMock)
    async def test_raises_on_unknown_workflow(
        self, mock_dispatch, mock_system_client, mock_anthropic
    ):
        mock_dispatch.return_value = "Unknown workflow 'bad'. Available: email-triage."
        mock_system_client.return_value = MagicMock()
        mock_anthropic.return_value = MagicMock()

        with pytest.raises(RuntimeError, match="Unknown"):
            await handle_workflow({
                "id": "job-3",
                "input": {
                    "user_id": "user-1",
                    "template_name": "bad",
                    "parameters": {},
                },
            })
