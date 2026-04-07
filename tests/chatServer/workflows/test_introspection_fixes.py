"""Tests for SPEC-043 FU-6 introspection loop fixes (ACs 23-28)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# AC-23: Template uses skill paths, not old agent paths
# ---------------------------------------------------------------------------


def test_template_references_skill_paths():
    """Service step descriptions reference /skills/ paths, not /agent/ paths."""
    from chatServer.workflows.templates.introspection import (
        PROMPT_APPLY_CHANGES,
        PROMPT_GATHER_SIGNALS,
        PROMPT_PROPOSE_CHANGES,
    )

    # Old paths must not appear in the prompts
    for prompt in (PROMPT_GATHER_SIGNALS, PROMPT_PROPOSE_CHANGES, PROMPT_APPLY_CHANGES):
        assert "/user/agent/" not in prompt, f"Old /user/agent/ path found in prompt"
        assert "/user/preferences/" not in prompt, f"Old /user/preferences/ path found"

    # New skill paths must appear
    assert "/user/skills/" in PROMPT_GATHER_SIGNALS
    assert "/system/skills/" in PROMPT_GATHER_SIGNALS
    assert "/user/skills/communication-preferences/SKILL.md" in PROMPT_PROPOSE_CHANGES


def test_template_service_nodes_have_no_tools():
    """Service nodes (gather-signals, apply-changes) must have empty tool lists."""
    from chatServer.workflows.template_parser import parse_template
    from chatServer.workflows.templates.introspection import TEMPLATE

    tpl = parse_template(TEMPLATE, "introspection-loop")
    service_steps = [s for s in tpl.steps if s.node_type == "service"]
    assert len(service_steps) == 2, "Expected 2 service steps"

    for step in service_steps:
        assert step.tools == [], (
            f"Service node '{step.name}' should have no tools — "
            "service nodes run Python, not LLM tool calls"
        )


# ---------------------------------------------------------------------------
# AC-25: gather_metrics reads skills from ConfigService
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_gather_metrics_reads_skills():
    """gather_metrics calls ConfigService.list_paths + read for current skill files."""
    from chatServer.workflows.nodes.gather_metrics import gather_metrics

    mock_config = MagicMock()
    mock_config.list_paths = AsyncMock(
        return_value=["skills/clarity-soul/SKILL.md", "skills/communication-preferences/SKILL.md"]
    )
    mock_config.read = AsyncMock(return_value="# Skill content\n\nBe helpful.")

    state = {
        "parameters": {
            "user_id": "user-1",
            "period_days": 7,
            "focus_areas": [],
        }
    }

    with (
        patch(
            "chatServer.workflows.nodes.gather_metrics._collect_feedback",
            new=AsyncMock(return_value={"total": 0}),
        ),
        patch(
            "chatServer.workflows.nodes.gather_metrics._collect_interaction_metrics",
            new=AsyncMock(return_value={"total_messages": 0}),
        ),
        patch(
            "chatServer.workflows.nodes.gather_metrics._collect_workflow_runs",
            new=AsyncMock(return_value={"total": 0}),
        ),
        patch(
            "chatServer.services.config_service.get_config_service",
            return_value=mock_config,
        ),
    ):
        import json

        output = await gather_metrics(state)
        data = json.loads(output)

    # ConfigService was consulted
    mock_config.list_paths.assert_awaited_once_with("skills/", "user-1")
    assert mock_config.read.await_count == 2  # one per skill path

    # Skills appear in output
    assert "current_skills" in data
    assert len(data["current_skills"]) == 2
    for content in data["current_skills"].values():
        assert "Be helpful" in content


@pytest.mark.asyncio
async def test_gather_metrics_graceful_when_config_service_unavailable():
    """gather_metrics returns empty skills dict if ConfigService raises."""
    from chatServer.workflows.nodes.gather_metrics import gather_metrics

    state = {
        "parameters": {
            "user_id": "user-1",
            "period_days": 7,
            "focus_areas": [],
        }
    }

    with (
        patch(
            "chatServer.workflows.nodes.gather_metrics._collect_feedback",
            new=AsyncMock(return_value={}),
        ),
        patch(
            "chatServer.workflows.nodes.gather_metrics._collect_interaction_metrics",
            new=AsyncMock(return_value={}),
        ),
        patch(
            "chatServer.workflows.nodes.gather_metrics._collect_workflow_runs",
            new=AsyncMock(return_value={}),
        ),
        patch(
            "chatServer.services.config_service.get_config_service",
            side_effect=RuntimeError("not initialized"),
        ),
    ):
        import json

        output = await gather_metrics(state)
        data = json.loads(output)

    # Graceful fallback — no crash, empty skills
    assert "current_skills" in data
    assert data["current_skills"] == {}


# ---------------------------------------------------------------------------
# AC-26: apply_improvements uses SelfImprovementService.propose_change
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_apply_improvements_uses_self_improvement(tmp_path):
    """apply_improvements calls SelfImprovementService.propose_change for mutable paths."""
    import json

    from chatServer.workflows.nodes.apply_improvements import apply_improvements

    proposals_json = json.dumps([{
        "file_path": "/user/skills/communication-preferences/SKILL.md",
        "change_type": "update",
        "content": "# Updated skill\n\nBe concise.",
        "rationale": "3 negative feedback signals on verbosity",
        "elevated": False,
    }])

    state = {
        "parameters": {"user_id": "user-1", "trust_tier": "inform"},
        "step_outputs": {"propose-changes": proposals_json},
    }

    mock_proposal = MagicMock()
    mock_proposal.id = "prop-1"
    mock_proposal.git_commit_hash = "abc123"

    mock_sis = MagicMock()
    mock_sis.propose_change = AsyncMock(return_value=mock_proposal)

    mock_git = MagicMock()
    mock_provisioner = MagicMock()
    mock_provisioner.get_or_create = AsyncMock()
    # Use real tmp_path so user_dir / rel_path and write_text work without extra mocking
    mock_provisioner.get_user_dir = MagicMock(return_value=tmp_path)

    with (
        patch("chatServer.sandbox.provisioner.get_provisioner", return_value=mock_provisioner),
        patch("chatServer.sandbox.git_tracker.GitTracker", return_value=mock_git),
        patch("chatServer.sandbox.self_improvement.SelfImprovementService", return_value=mock_sis),
    ):
        output = await apply_improvements(state)
        data = json.loads(output)

    # SelfImprovementService.propose_change was called with skill path
    mock_sis.propose_change.assert_awaited_once()
    call_kwargs = mock_sis.propose_change.call_args.kwargs
    assert call_kwargs["user_id"] == "user-1"
    assert "skills/communication-preferences/SKILL.md" in call_kwargs["file_path"]

    # Proposal appears in applied list
    assert len(data["applied"]) == 1
    assert data["applied"][0]["status"] == "committed"


# ---------------------------------------------------------------------------
# AC-23: Service node registration in WorkflowRunManager
# ---------------------------------------------------------------------------


def test_run_manager_registers_service_nodes():
    """WorkflowRunManager registers gather-signals and apply-changes as service handlers."""
    from chatServer.workflows.run_manager import WorkflowRunManager

    manager = WorkflowRunManager(
        db_client=MagicMock(),
        anthropic_client=MagicMock(),
        tool_schemas=[],
        tool_executors={},
    )

    assert "gather-signals" in manager._builder._service_registry
    assert "apply-changes" in manager._builder._service_registry


# ---------------------------------------------------------------------------
# AC-27: Debug introspection endpoint
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_introspection_trigger_endpoint():
    """POST /api/introspection/trigger is registered in non-prod and returns 200."""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from chatServer.dependencies.auth import get_current_user
    from chatServer.routers.introspection_router import router

    app = FastAPI()
    app.include_router(router)

    # The route is registered when ENVIRONMENT != "production" (default in tests)
    routes = [r.path for r in app.routes]
    assert "/api/introspection/trigger" in routes, (
        "Trigger route not registered — check ENVIRONMENT env var"
    )

    mock_result = {"status": "workflow_dispatched", "message": "Started"}

    with patch(
        "chatServer.services.job_handlers.handle_introspection",
        new=AsyncMock(return_value=mock_result),
    ):
        app.dependency_overrides[get_current_user] = lambda: "user-1"
        client = TestClient(app, raise_server_exceptions=True)
        response = client.post("/api/introspection/trigger")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "triggered"
    assert body["result"] == mock_result
