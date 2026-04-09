"""Tests for introspection job handler and scheduling (SPEC-040)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Patch targets: create_system_client is module-level import, rest are lazy
_P_CREATE_CLIENT = "chatServer.services.job_handlers.create_system_client"
_P_DISPATCH = "chatServer.workflows.dispatch.dispatch_workflow"
_P_ANTHROPIC = "chatServer.services.job_handlers._get_anthropic_client_for_workflow"
_P_DB_MGR = "chatServer.database.connection.get_database_manager"
_P_JOB_SVC = "chatServer.services.job_service.JobService"


def _make_db_mock(pref_data):
    """Build a mock Supabase client with chainable query returning pref_data."""
    mock_db = MagicMock()
    chain = MagicMock()
    chain.select.return_value = chain
    chain.eq.return_value = chain
    chain.maybe_single.return_value = chain
    pref_result = MagicMock()
    pref_result.data = pref_data
    chain.execute = AsyncMock(return_value=pref_result)
    mock_db.table.return_value = chain
    return mock_db


class TestHandleIntrospection:
    @pytest.mark.asyncio
    async def test_dispatches_workflow(self):
        from chatServer.services.job_handlers import handle_introspection

        mock_db = _make_db_mock({
            "introspection_enabled": True,
            "introspection_interval_days": 7,
            "introspection_focus_areas": ["briefing"],
        })
        job = {"input": {"user_id": "user-123"}}

        p1 = patch(_P_CREATE_CLIENT, new_callable=AsyncMock, return_value=mock_db)
        p2 = patch(_P_DISPATCH, new_callable=AsyncMock, return_value="Started workflow 'introspection-loop'")
        p3 = patch(_P_ANTHROPIC)
        p4 = patch(_P_DB_MGR)
        p5 = patch(_P_JOB_SVC)

        with p1, p2 as mock_dispatch, p3, p4 as mock_db_mgr, p5 as mock_job_svc_cls:
            mock_job_svc = AsyncMock()
            mock_job_svc_cls.return_value = mock_job_svc
            mock_db_mgr.return_value.pool = MagicMock()

            result = await handle_introspection(job)

            assert result["status"] == "workflow_dispatched"
            mock_dispatch.assert_called_once()
            call_args = mock_dispatch.call_args
            assert call_args.kwargs["args"]["workflow_name"] == "introspection-loop"
            assert call_args.kwargs["args"]["parameters"]["period_days"] == 7
            assert call_args.kwargs["args"]["parameters"]["focus_areas"] == ["briefing"]

    @pytest.mark.asyncio
    async def test_self_schedules_when_enabled(self):
        from chatServer.services.job_handlers import handle_introspection

        mock_db = _make_db_mock({
            "introspection_enabled": True,
            "introspection_interval_days": 14,
            "introspection_focus_areas": [],
        })
        job = {"input": {"user_id": "user-123"}}

        p1 = patch(_P_CREATE_CLIENT, new_callable=AsyncMock, return_value=mock_db)
        p2 = patch(_P_DISPATCH, new_callable=AsyncMock, return_value="Started workflow")
        p3 = patch(_P_ANTHROPIC)
        p4 = patch(_P_DB_MGR)
        p5 = patch(_P_JOB_SVC)

        with p1, p2, p3, p4 as mock_db_mgr, p5 as mock_job_svc_cls:
            mock_job_svc = AsyncMock()
            mock_job_svc_cls.return_value = mock_job_svc
            mock_db_mgr.return_value.pool = MagicMock()

            await handle_introspection(job)

            mock_job_svc.create.assert_called_once()
            create_kwargs = mock_job_svc.create.call_args.kwargs
            assert create_kwargs["job_type"] == "introspection"
            assert create_kwargs["user_id"] == "user-123"

    @pytest.mark.asyncio
    async def test_no_reschedule_when_disabled(self):
        from chatServer.services.job_handlers import handle_introspection

        mock_db = _make_db_mock({
            "introspection_enabled": False,
            "introspection_interval_days": 7,
            "introspection_focus_areas": [],
        })
        job = {"input": {"user_id": "user-123"}}

        p1 = patch(_P_CREATE_CLIENT, new_callable=AsyncMock, return_value=mock_db)
        p2 = patch(_P_DISPATCH, new_callable=AsyncMock, return_value="Started workflow")
        p3 = patch(_P_ANTHROPIC)
        p4 = patch(_P_DB_MGR)
        p5 = patch(_P_JOB_SVC)

        with p1, p2, p3, p4 as mock_db_mgr, p5 as mock_job_svc_cls:
            mock_job_svc = AsyncMock()
            mock_job_svc_cls.return_value = mock_job_svc
            mock_db_mgr.return_value.pool = MagicMock()

            await handle_introspection(job)

            mock_job_svc.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_defaults_when_no_preferences(self):
        from chatServer.services.job_handlers import handle_introspection

        mock_db = _make_db_mock(None)  # No preferences row
        job = {"input": {"user_id": "user-123"}}

        p1 = patch(_P_CREATE_CLIENT, new_callable=AsyncMock, return_value=mock_db)
        p2 = patch(_P_DISPATCH, new_callable=AsyncMock, return_value="Started workflow")
        p3 = patch(_P_ANTHROPIC)

        with p1, p2 as mock_dispatch, p3:
            await handle_introspection(job)

            call_args = mock_dispatch.call_args
            assert call_args.kwargs["args"]["parameters"]["period_days"] == 7
            assert call_args.kwargs["args"]["parameters"]["focus_areas"] == []

    @pytest.mark.asyncio
    async def test_raises_on_workflow_failure(self):
        from chatServer.services.job_handlers import handle_introspection

        mock_db = _make_db_mock({})
        job = {"input": {"user_id": "user-123"}}

        p1 = patch(_P_CREATE_CLIENT, new_callable=AsyncMock, return_value=mock_db)
        p2 = patch(_P_DISPATCH, new_callable=AsyncMock, return_value="Failed to start workflow")
        p3 = patch(_P_ANTHROPIC)

        with p1, p2, p3:
            with pytest.raises(RuntimeError, match="Failed"):
                await handle_introspection(job)


class TestIntrospectionHandlerRegistered:
    def test_handler_imported_in_background_tasks(self):
        """Verify handle_introspection is imported and available."""
        from chatServer.services.job_handlers import handle_introspection
        assert callable(handle_introspection)

    def test_handler_registered_with_runner(self):
        """Verify the import line exists in background_tasks."""
        from chatServer.services.background_tasks import handle_introspection
        assert callable(handle_introspection)
