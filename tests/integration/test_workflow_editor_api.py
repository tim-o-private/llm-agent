"""Integration tests for /api/vault/workflows/* — auth, cross-user isolation,
list/create/dry-run/run round-trips.

Also covers GET /api/workflows/runs/detailed.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from chatServer.database.supabase_client import get_user_scoped_client
from chatServer.dependencies.auth import get_current_user
from chatServer.routers.workflow_editor_router import (
    get_anthropic_client,
    get_workflow_editor_service,
)
from chatServer.routers.workflow_editor_router import (
    router as editor_router,
)
from chatServer.routers.workflows_router import router as runs_router
from chatServer.services.vault_service import VaultService
from chatServer.services.workflow_editor_service import WorkflowEditorService

TEST_USER_A = "user-a"
TEST_USER_B = "user-b"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_vault(tmp_path: Path) -> VaultService:
    (tmp_path / "config" / "system").mkdir(parents=True, exist_ok=True)
    (tmp_path / "sandboxes").mkdir(parents=True, exist_ok=True)
    return VaultService(storage_sync=None, data_dir=tmp_path)


def _prep_user(tmp_path: Path, user_id: str) -> Path:
    user_root = tmp_path / "sandboxes" / user_id
    user_root.mkdir(parents=True, exist_ok=True)
    return user_root


def _write_workflow(user_root: Path, name: str, content: str) -> None:
    wf_dir = user_root / "_workflows"
    wf_dir.mkdir(parents=True, exist_ok=True)
    (wf_dir / f"{name}.flow.md").write_text(content)


VALID_TEMPLATE = """\
---
name: morning-briefing
description: A morning briefing workflow
version: 1
default_gate_policy: none
---

# Morning Briefing

## Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|

## Steps

### step-1: Fetch data
- **agent:** briefing-agent
- **depends_on:** []
- **tools:** [web_search]
- **description:** Fetches latest data.
- **gate:** none
"""


def _build_app(user_id: str, vault: VaultService) -> FastAPI:
    app = FastAPI()
    app.include_router(editor_router)
    app.include_router(runs_router)
    service = WorkflowEditorService(vault=vault)
    app.dependency_overrides[get_current_user] = lambda: user_id
    app.dependency_overrides[get_workflow_editor_service] = lambda: service
    app.dependency_overrides[get_anthropic_client] = lambda: MagicMock()
    scoped_client = MagicMock(user_id=user_id)
    app.dependency_overrides[get_user_scoped_client] = lambda: scoped_client
    return app


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------


class TestAuth:
    @pytest.mark.asyncio
    async def test_list_requires_auth(self, tmp_path):
        vault = _make_vault(tmp_path)
        app = FastAPI()
        app.include_router(editor_router)
        app.dependency_overrides[get_workflow_editor_service] = lambda: WorkflowEditorService(vault=vault)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            r = await c.get("/api/vault/workflows/list")
        assert r.status_code in (401, 403)

    @pytest.mark.asyncio
    async def test_create_requires_auth(self, tmp_path):
        vault = _make_vault(tmp_path)
        app = FastAPI()
        app.include_router(editor_router)
        app.dependency_overrides[get_workflow_editor_service] = lambda: WorkflowEditorService(vault=vault)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            r = await c.post("/api/vault/workflows/new", json={"name": "test"})
        assert r.status_code in (401, 403)

    @pytest.mark.asyncio
    async def test_dry_run_requires_auth(self, tmp_path):
        vault = _make_vault(tmp_path)
        app = FastAPI()
        app.include_router(editor_router)
        app.dependency_overrides[get_workflow_editor_service] = lambda: WorkflowEditorService(vault=vault)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            r = await c.post("/api/vault/workflows/dry-run", json={"template_name": "test"})
        assert r.status_code in (401, 403)

    @pytest.mark.asyncio
    async def test_run_requires_auth(self, tmp_path):
        vault = _make_vault(tmp_path)
        app = FastAPI()
        app.include_router(editor_router)
        app.dependency_overrides[get_workflow_editor_service] = lambda: WorkflowEditorService(vault=vault)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            r = await c.post("/api/vault/workflows/run", json={"template_name": "test"})
        assert r.status_code in (401, 403)


# ---------------------------------------------------------------------------
# GET /api/vault/workflows/list
# ---------------------------------------------------------------------------


class TestListWorkflows:
    @pytest.mark.asyncio
    async def test_returns_workflow_entries(self, tmp_path):
        vault = _make_vault(tmp_path)
        user_root = _prep_user(tmp_path, TEST_USER_A)
        _write_workflow(user_root, "morning-briefing", VALID_TEMPLATE)

        app = _build_app(TEST_USER_A, vault)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            r = await c.get("/api/vault/workflows/list")

        assert r.status_code == 200
        body = r.json()
        assert len(body["workflows"]) == 1
        wf = body["workflows"][0]
        assert wf["name"] == "morning-briefing"
        assert wf["filename"] == "morning-briefing.flow.md"
        assert wf["description"] == "A morning briefing workflow"
        assert wf["trigger_summary"] == "Manual"

    @pytest.mark.asyncio
    async def test_empty_for_user_with_no_workflows(self, tmp_path):
        vault = _make_vault(tmp_path)
        _prep_user(tmp_path, TEST_USER_A)

        app = _build_app(TEST_USER_A, vault)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            r = await c.get("/api/vault/workflows/list")

        assert r.status_code == 200
        assert r.json()["workflows"] == []


# ---------------------------------------------------------------------------
# POST /api/vault/workflows/new
# ---------------------------------------------------------------------------


class TestCreateWorkflow:
    @pytest.mark.asyncio
    async def test_creates_file_returns_path(self, tmp_path):
        vault = _make_vault(tmp_path)
        _prep_user(tmp_path, TEST_USER_A)

        app = _build_app(TEST_USER_A, vault)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            r = await c.post("/api/vault/workflows/new", json={"name": "test-wf"})

        assert r.status_code == 200
        body = r.json()
        assert body["path"] == "_workflows/test-wf.flow.md"

        # Verify file on disk
        full = tmp_path / "sandboxes" / TEST_USER_A / "_workflows" / "test-wf.flow.md"
        assert full.exists()

    @pytest.mark.asyncio
    async def test_409_on_duplicate(self, tmp_path):
        vault = _make_vault(tmp_path)
        user_root = _prep_user(tmp_path, TEST_USER_A)
        _write_workflow(user_root, "existing", VALID_TEMPLATE)

        app = _build_app(TEST_USER_A, vault)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            r = await c.post("/api/vault/workflows/new", json={"name": "existing"})

        assert r.status_code == 409

    @pytest.mark.asyncio
    async def test_422_on_invalid_name(self, tmp_path):
        vault = _make_vault(tmp_path)
        _prep_user(tmp_path, TEST_USER_A)

        app = _build_app(TEST_USER_A, vault)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            r = await c.post("/api/vault/workflows/new", json={"name": "INVALID!"})

        assert r.status_code == 422


# ---------------------------------------------------------------------------
# POST /api/vault/workflows/dry-run
# ---------------------------------------------------------------------------


class TestDryRun:
    @pytest.mark.asyncio
    async def test_valid_template(self, tmp_path):
        vault = _make_vault(tmp_path)
        user_root = _prep_user(tmp_path, TEST_USER_A)
        _write_workflow(user_root, "morning-briefing", VALID_TEMPLATE)

        app = _build_app(TEST_USER_A, vault)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            r = await c.post(
                "/api/vault/workflows/dry-run",
                json={"template_name": "morning-briefing"},
            )

        assert r.status_code == 200
        body = r.json()
        assert body["valid"] is True
        assert body["errors"] == []
        assert len(body["steps"]) == 1

    @pytest.mark.asyncio
    async def test_invalid_template_422(self, tmp_path):
        vault = _make_vault(tmp_path)
        user_root = _prep_user(tmp_path, TEST_USER_A)
        no_name = """\
---
description: missing name
version: 1
---

# No Name
"""
        _write_workflow(user_root, "broken", no_name)

        app = _build_app(TEST_USER_A, vault)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            r = await c.post(
                "/api/vault/workflows/dry-run",
                json={"template_name": "broken"},
            )

        assert r.status_code == 200
        body = r.json()
        assert body["valid"] is False
        assert len(body["errors"]) > 0

    @pytest.mark.asyncio
    async def test_not_found_404(self, tmp_path):
        vault = _make_vault(tmp_path)
        _prep_user(tmp_path, TEST_USER_A)

        app = _build_app(TEST_USER_A, vault)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            r = await c.post(
                "/api/vault/workflows/dry-run",
                json={"template_name": "nonexistent"},
            )

        assert r.status_code == 404


# ---------------------------------------------------------------------------
# POST /api/vault/workflows/run
# ---------------------------------------------------------------------------


class TestRunWorkflow:
    @pytest.mark.asyncio
    async def test_returns_202_with_run_id(self, tmp_path):
        vault = _make_vault(tmp_path)
        user_root = _prep_user(tmp_path, TEST_USER_A)
        _write_workflow(user_root, "morning-briefing", VALID_TEMPLATE)

        app = _build_app(TEST_USER_A, vault)
        transport = ASGITransport(app=app)
        with patch(
            "chatServer.workflows.dispatch.dispatch_workflow",
            new_callable=AsyncMock,
            return_value="Started workflow 'morning-briefing' (run_id: abc-123). I'll keep you updated.",
        ):
            async with AsyncClient(transport=transport, base_url="http://test") as c:
                r = await c.post(
                    "/api/vault/workflows/run",
                    json={"template_name": "morning-briefing"},
                )

        assert r.status_code == 202
        assert r.json()["run_id"] == "abc-123"

    @pytest.mark.asyncio
    async def test_not_found_404(self, tmp_path):
        vault = _make_vault(tmp_path)
        _prep_user(tmp_path, TEST_USER_A)

        app = _build_app(TEST_USER_A, vault)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            r = await c.post(
                "/api/vault/workflows/run",
                json={"template_name": "nonexistent"},
            )

        assert r.status_code == 404


# ---------------------------------------------------------------------------
# GET /api/workflows/runs/detailed
# ---------------------------------------------------------------------------


class TestDetailedRuns:
    @pytest.mark.asyncio
    async def test_returns_detailed_fields(self, tmp_path):
        vault = _make_vault(tmp_path)
        _prep_user(tmp_path, TEST_USER_A)

        app = _build_app(TEST_USER_A, vault)
        rows = [
            {
                "id": "run-1",
                "template_name": "morning-briefing",
                "status": "completed",
                "current_step": "finalize",
                "error": None,
                "parameters": {"topic": "news"},
                "step_outputs": {"fetch-data": "result text"},
                "started_at": "2026-04-21T10:00:00+00:00",
                "completed_at": "2026-04-21T10:00:30+00:00",
                "created_at": "2026-04-21T10:00:00+00:00",
            },
        ]
        service = MagicMock()
        service.list_runs_detailed = AsyncMock(return_value=rows)
        with patch(
            "chatServer.routers.workflows_router.WorkflowRunsService",
            return_value=service,
        ):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as c:
                r = await c.get(
                    "/api/workflows/runs/detailed",
                    params={"template_name": "morning-briefing"},
                )

        assert r.status_code == 200
        body = r.json()
        assert len(body) == 1
        assert body[0]["parameters"] == {"topic": "news"}
        assert body[0]["step_outputs"] == {"fetch-data": "result text"}

    @pytest.mark.asyncio
    async def test_requires_auth(self, tmp_path):
        app = FastAPI()
        app.include_router(runs_router)
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            r = await c.get("/api/workflows/runs/detailed")
        assert r.status_code in (401, 403)


# ---------------------------------------------------------------------------
# Cross-user isolation
# ---------------------------------------------------------------------------


class TestCrossUserIsolation:
    @pytest.mark.asyncio
    async def test_list_scoped_to_user(self, tmp_path):
        vault = _make_vault(tmp_path)
        root_a = _prep_user(tmp_path, TEST_USER_A)
        root_b = _prep_user(tmp_path, TEST_USER_B)
        _write_workflow(root_a, "a-workflow", VALID_TEMPLATE)
        _write_workflow(
            root_b,
            "b-workflow",
            VALID_TEMPLATE.replace("morning-briefing", "b-workflow"),
        )

        # User A sees only their workflow
        app_a = _build_app(TEST_USER_A, vault)
        transport = ASGITransport(app=app_a)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            r = await c.get("/api/vault/workflows/list")
        assert r.status_code == 200
        filenames = [w["filename"] for w in r.json()["workflows"]]
        assert "a-workflow.flow.md" in filenames
        assert "b-workflow.flow.md" not in filenames

        # User B sees only their workflow
        app_b = _build_app(TEST_USER_B, vault)
        transport = ASGITransport(app=app_b)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            r = await c.get("/api/vault/workflows/list")
        assert r.status_code == 200
        filenames = [w["filename"] for w in r.json()["workflows"]]
        assert "b-workflow.flow.md" in filenames
        assert "a-workflow.flow.md" not in filenames

    @pytest.mark.asyncio
    async def test_create_scoped_to_user(self, tmp_path):
        vault = _make_vault(tmp_path)
        _prep_user(tmp_path, TEST_USER_A)
        _prep_user(tmp_path, TEST_USER_B)

        app_a = _build_app(TEST_USER_A, vault)
        transport = ASGITransport(app=app_a)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            r = await c.post("/api/vault/workflows/new", json={"name": "private"})
        assert r.status_code == 200

        # B should not see A's workflow
        app_b = _build_app(TEST_USER_B, vault)
        transport = ASGITransport(app=app_b)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            r = await c.get("/api/vault/workflows/list")
        assert r.status_code == 200
        assert len(r.json()["workflows"]) == 0

    @pytest.mark.asyncio
    async def test_dry_run_scoped_to_user(self, tmp_path):
        vault = _make_vault(tmp_path)
        root_a = _prep_user(tmp_path, TEST_USER_A)
        _prep_user(tmp_path, TEST_USER_B)
        _write_workflow(root_a, "a-only", VALID_TEMPLATE)

        # B cannot dry-run A's workflow
        app_b = _build_app(TEST_USER_B, vault)
        transport = ASGITransport(app=app_b)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            r = await c.post(
                "/api/vault/workflows/dry-run",
                json={"template_name": "a-only"},
            )
        assert r.status_code == 404
