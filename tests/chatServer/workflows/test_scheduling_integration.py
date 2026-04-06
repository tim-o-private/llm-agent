"""Tests for SPEC-037 job handler → workflow dispatch integration."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def _reset_config_service_global():
    """Reset the config_service module-level global to avoid test pollution.

    The lifespan in test_main_chat_logic.py can set _config_service to a
    mock, which then leaks into scheduling tests that import job_handlers.
    """
    import chatServer.services.config_service as cs
    original = cs._config_service
    yield
    cs._config_service = original


from chatServer.services.job_handlers import (
    handle_email_triage,
    handle_evening_briefing,
    handle_morning_briefing,
)

# Patch targets
# create_system_client is module-level import in job_handlers → patch at consumption site
_DISPATCH = "chatServer.workflows.dispatch.dispatch_workflow"
_SYSTEM_CLIENT = "chatServer.services.job_handlers.create_system_client"
_ANTHROPIC = "chatServer.services.job_handlers._get_anthropic_client_for_workflow"
_DB_MANAGER = "chatServer.database.connection.get_database_manager"
_BRIEFING_SERVICE = "chatServer.services.briefing_service.BriefingService"
_JOB_SERVICE = "chatServer.services.job_service.JobService"


def _mock_briefing_service(prefs=None):
    """Create a mock BriefingService that returns given preferences."""
    default_prefs = {
        "timezone": "America/New_York",
        "morning_briefing_time": "07:00",
        "evening_briefing_time": "19:00",
        "morning_briefing_enabled": True,
        "evening_briefing_enabled": True,
        "email_triage_enabled": True,
        "email_triage_interval_hours": 6,
        "briefing_sections": {},
    }
    if prefs:
        default_prefs.update(prefs)

    mock_svc = MagicMock()
    mock_svc.get_user_preferences = AsyncMock(return_value=default_prefs)
    return mock_svc


class TestHandleMorningBriefingWorkflow:
    @pytest.mark.asyncio
    @patch(_ANTHROPIC)
    @patch(_JOB_SERVICE)
    @patch(_DB_MANAGER)
    @patch(_BRIEFING_SERVICE)
    @patch(_SYSTEM_CLIENT, new_callable=AsyncMock)
    @patch(_DISPATCH, new_callable=AsyncMock)
    async def test_dispatches_morning_briefing_workflow(
        self, mock_dispatch, mock_sys_client, mock_bsvc_cls,
        mock_db_mgr, mock_job_cls, mock_anthropic
    ):
        mock_dispatch.return_value = "Started workflow 'morning-briefing' (run_id: r1)."
        mock_sys_client.return_value = MagicMock()
        mock_bsvc_cls.return_value = _mock_briefing_service()
        mock_db_mgr.return_value = MagicMock(pool=MagicMock())
        mock_job_cls.return_value = MagicMock(create=AsyncMock())
        mock_anthropic.return_value = MagicMock()

        result = await handle_morning_briefing({
            "input": {"user_id": "user-1"},
        })

        assert result["status"] == "workflow_dispatched"
        mock_dispatch.assert_called_once()
        call_args = mock_dispatch.call_args.kwargs
        assert call_args["args"]["workflow_name"] == "morning-briefing"

    @pytest.mark.asyncio
    @patch(_ANTHROPIC)
    @patch(_JOB_SERVICE)
    @patch(_DB_MANAGER)
    @patch(_BRIEFING_SERVICE)
    @patch(_SYSTEM_CLIENT, new_callable=AsyncMock)
    @patch(_DISPATCH, new_callable=AsyncMock)
    async def test_self_schedules_next_occurrence(
        self, mock_dispatch, mock_sys_client, mock_bsvc_cls,
        mock_db_mgr, mock_job_cls, mock_anthropic
    ):
        mock_dispatch.return_value = "Started workflow 'morning-briefing' (run_id: r1)."
        mock_sys_client.return_value = MagicMock()
        mock_bsvc_cls.return_value = _mock_briefing_service()
        mock_db_mgr.return_value = MagicMock(pool=MagicMock())
        mock_job_svc = MagicMock(create=AsyncMock())
        mock_job_cls.return_value = mock_job_svc
        mock_anthropic.return_value = MagicMock()

        await handle_morning_briefing({"input": {"user_id": "user-1"}})

        mock_job_svc.create.assert_called_once()
        call_kwargs = mock_job_svc.create.call_args.kwargs
        assert call_kwargs["job_type"] == "morning_briefing"


class TestHandleEveningBriefingWorkflow:
    @pytest.mark.asyncio
    @patch(_ANTHROPIC)
    @patch(_JOB_SERVICE)
    @patch(_DB_MANAGER)
    @patch(_BRIEFING_SERVICE)
    @patch(_SYSTEM_CLIENT, new_callable=AsyncMock)
    @patch(_DISPATCH, new_callable=AsyncMock)
    async def test_dispatches_evening_briefing_workflow(
        self, mock_dispatch, mock_sys_client, mock_bsvc_cls,
        mock_db_mgr, mock_job_cls, mock_anthropic
    ):
        mock_dispatch.return_value = "Started workflow 'evening-briefing' (run_id: r2)."
        mock_sys_client.return_value = MagicMock()
        mock_bsvc_cls.return_value = _mock_briefing_service()
        mock_db_mgr.return_value = MagicMock(pool=MagicMock())
        mock_job_cls.return_value = MagicMock(create=AsyncMock())
        mock_anthropic.return_value = MagicMock()

        result = await handle_evening_briefing({
            "input": {"user_id": "user-1"},
        })

        assert result["status"] == "workflow_dispatched"
        call_args = mock_dispatch.call_args.kwargs
        assert call_args["args"]["workflow_name"] == "evening-briefing"


class TestHandleEmailTriage:
    @pytest.mark.asyncio
    @patch(_ANTHROPIC)
    @patch(_JOB_SERVICE)
    @patch(_DB_MANAGER)
    @patch(_BRIEFING_SERVICE)
    @patch(_SYSTEM_CLIENT, new_callable=AsyncMock)
    @patch(_DISPATCH, new_callable=AsyncMock)
    async def test_dispatches_email_triage_workflow(
        self, mock_dispatch, mock_sys_client, mock_bsvc_cls,
        mock_db_mgr, mock_job_cls, mock_anthropic
    ):
        mock_dispatch.return_value = "Started workflow 'email-triage' (run_id: r3)."
        mock_sys_client.return_value = MagicMock()
        mock_bsvc_cls.return_value = _mock_briefing_service()
        mock_db_mgr.return_value = MagicMock(pool=MagicMock())
        mock_job_cls.return_value = MagicMock(create=AsyncMock())
        mock_anthropic.return_value = MagicMock()

        result = await handle_email_triage({
            "input": {"user_id": "user-1"},
        })

        assert result["status"] == "workflow_dispatched"
        call_args = mock_dispatch.call_args.kwargs
        assert call_args["args"]["workflow_name"] == "email-triage"
        assert call_args["args"]["parameters"]["hours_back"] == 12
        assert call_args["args"]["parameters"]["max_emails"] == 20

    @pytest.mark.asyncio
    @patch(_ANTHROPIC)
    @patch(_JOB_SERVICE)
    @patch(_DB_MANAGER)
    @patch(_BRIEFING_SERVICE)
    @patch(_SYSTEM_CLIENT, new_callable=AsyncMock)
    @patch(_DISPATCH, new_callable=AsyncMock)
    async def test_self_schedules_when_enabled(
        self, mock_dispatch, mock_sys_client, mock_bsvc_cls,
        mock_db_mgr, mock_job_cls, mock_anthropic
    ):
        mock_dispatch.return_value = "Started workflow 'email-triage' (run_id: r3)."
        mock_sys_client.return_value = MagicMock()
        mock_bsvc_cls.return_value = _mock_briefing_service()
        mock_db_mgr.return_value = MagicMock(pool=MagicMock())
        mock_job_svc = MagicMock(create=AsyncMock())
        mock_job_cls.return_value = mock_job_svc
        mock_anthropic.return_value = MagicMock()

        await handle_email_triage({"input": {"user_id": "user-1"}})

        mock_job_svc.create.assert_called_once()
        call_kwargs = mock_job_svc.create.call_args.kwargs
        assert call_kwargs["job_type"] == "email_triage"

    @pytest.mark.asyncio
    @patch(_ANTHROPIC)
    @patch(_JOB_SERVICE)
    @patch(_DB_MANAGER)
    @patch(_BRIEFING_SERVICE)
    @patch(_SYSTEM_CLIENT, new_callable=AsyncMock)
    @patch(_DISPATCH, new_callable=AsyncMock)
    async def test_skips_scheduling_when_disabled(
        self, mock_dispatch, mock_sys_client, mock_bsvc_cls,
        mock_db_mgr, mock_job_cls, mock_anthropic
    ):
        mock_dispatch.return_value = "Started workflow 'email-triage' (run_id: r3)."
        mock_sys_client.return_value = MagicMock()
        mock_bsvc_cls.return_value = _mock_briefing_service(
            {"email_triage_enabled": False}
        )
        mock_db_mgr.return_value = MagicMock(pool=MagicMock())
        mock_job_svc = MagicMock(create=AsyncMock())
        mock_job_cls.return_value = mock_job_svc
        mock_anthropic.return_value = MagicMock()

        await handle_email_triage({"input": {"user_id": "user-1"}})

        mock_job_svc.create.assert_not_called()

    @pytest.mark.asyncio
    @patch(_ANTHROPIC)
    @patch(_JOB_SERVICE)
    @patch(_DB_MANAGER)
    @patch(_BRIEFING_SERVICE)
    @patch(_SYSTEM_CLIENT, new_callable=AsyncMock)
    @patch(_DISPATCH, new_callable=AsyncMock)
    async def test_raises_on_dispatch_failure(
        self, mock_dispatch, mock_sys_client, mock_bsvc_cls,
        mock_db_mgr, mock_job_cls, mock_anthropic
    ):
        mock_dispatch.return_value = "Failed to start workflow: no template"
        mock_sys_client.return_value = MagicMock()
        mock_bsvc_cls.return_value = _mock_briefing_service(
            {"email_triage_enabled": False}
        )
        mock_anthropic.return_value = MagicMock()

        with pytest.raises(RuntimeError, match="Failed"):
            await handle_email_triage({"input": {"user_id": "user-1"}})
