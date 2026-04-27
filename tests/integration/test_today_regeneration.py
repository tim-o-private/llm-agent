"""Integration tests for today-regeneration coupling.

Covers:
- POST /api/today/regenerate returns the run_id from WorkflowRunManager.
- Toggling today_regeneration_enabled creates a `regenerate_today` job.
- Toggling it off cancels pending `regenerate_today` jobs.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from chatServer.database.supabase_client import get_user_scoped_client
from chatServer.dependencies.auth import get_current_user
from chatServer.routers.today_router import (
    get_llm_client,
    get_today_service,
    router,
)

USER_A = "user-a"


def _build_app(user_id: str = USER_A):
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_current_user] = lambda: user_id
    app.dependency_overrides[get_user_scoped_client] = lambda: MagicMock(user_id=user_id)
    return app


@pytest.mark.asyncio
async def test_regenerate_endpoint_returns_run_id_from_dispatch():
    app = _build_app()

    service = MagicMock()
    service.regenerate = AsyncMock(return_value="run-abc")
    llm_client = MagicMock()

    app.dependency_overrides[get_today_service] = lambda: service
    app.dependency_overrides[get_llm_client] = lambda: llm_client

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.post("/api/today/regenerate")

    assert r.status_code == 202
    assert r.json() == {"run_id": "run-abc"}
    service.regenerate.assert_awaited_once()
    call_args = service.regenerate.await_args.args
    assert call_args[0] == USER_A
    # db_client and llm_client are forwarded to the service.
    assert call_args[2] is llm_client


# ---------------------------------------------------------------------------
# Preferences toggle → jobs row (SPEC-045 AC "Scheduled-regenerate toggle")
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_enabling_today_regeneration_creates_job():
    """When today_regeneration_enabled flips false→true, the side-effect path
    creates a `regenerate_today` job."""
    from chatServer.tools.briefing_tools import ManageBriefingPreferencesTool

    tool = ManageBriefingPreferencesTool(user_id=USER_A)

    job_service = MagicMock()
    job_service.create = AsyncMock()
    job_service.fail_by_type = AsyncMock(return_value=0)

    with patch(
        "chatServer.services.job_service.JobService",
        return_value=job_service,
    ), patch(
        "chatServer.database.connection.get_database_manager",
        return_value=MagicMock(pool=MagicMock()),
    ):
        messages: list[str] = []
        await tool._handle_job_side_effects(
            old_prefs={
                "today_regeneration_enabled": False,
                "timezone": "America/New_York",
            },
            new_prefs={
                "today_regeneration_enabled": True,
                "today_regeneration_time": "06:30",
                "timezone": "America/New_York",
            },
            updates={"today_regeneration_enabled": True},
            messages=messages,
        )

    # Exactly one job created — with the expected job_type and input shape.
    assert job_service.create.await_count == 1
    call_kwargs = job_service.create.await_args.kwargs
    assert call_kwargs["job_type"] == "regenerate_today"
    assert call_kwargs["user_id"] == USER_A
    assert call_kwargs["input"]["template_name"] == "regenerate-today"
    assert call_kwargs["input"]["user_id"] == USER_A
    assert any("Today regeneration" in m for m in messages)


@pytest.mark.asyncio
async def test_disabling_today_regeneration_cancels_jobs():
    from chatServer.tools.briefing_tools import ManageBriefingPreferencesTool

    tool = ManageBriefingPreferencesTool(user_id=USER_A)

    job_service = MagicMock()
    job_service.create = AsyncMock()
    job_service.fail_by_type = AsyncMock(return_value=2)

    with patch(
        "chatServer.services.job_service.JobService",
        return_value=job_service,
    ), patch(
        "chatServer.database.connection.get_database_manager",
        return_value=MagicMock(pool=MagicMock()),
    ):
        messages: list[str] = []
        await tool._handle_job_side_effects(
            old_prefs={
                "today_regeneration_enabled": True,
                "timezone": "America/New_York",
            },
            new_prefs={
                "today_regeneration_enabled": False,
                "timezone": "America/New_York",
            },
            updates={"today_regeneration_enabled": False},
            messages=messages,
        )

    # fail_by_type called for regenerate_today job_type (plus defaults for
    # morning/evening, which pass through unchanged). Grab the regen one.
    calls = [c for c in job_service.fail_by_type.await_args_list
             if c.args[1] == "regenerate_today"]
    assert len(calls) == 1
    assert any("cancelled" in m.lower() for m in messages)
    # No new regenerate_today job was created during disable.
    for call in job_service.create.await_args_list:
        assert call.kwargs.get("job_type") != "regenerate_today"


@pytest.mark.asyncio
async def test_today_regeneration_time_validation():
    """update_user_preferences must reject bad HH:MM values."""
    from chatServer.services.briefing_service import BriefingService

    db = MagicMock()
    chain = db.table.return_value.select.return_value.eq.return_value
    chain.execute = AsyncMock(return_value=MagicMock(data=[{"user_id": USER_A}]))

    svc = BriefingService(db)
    with pytest.raises(ValueError):
        await svc.update_user_preferences(USER_A, {"today_regeneration_time": "25:99"})
    with pytest.raises(ValueError):
        await svc.update_user_preferences(USER_A, {"today_regeneration_time": "0630"})
    with pytest.raises(ValueError):
        await svc.update_user_preferences(USER_A, {"today_regeneration_enabled": "yes"})
