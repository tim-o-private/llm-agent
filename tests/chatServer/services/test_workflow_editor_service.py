"""Unit tests for WorkflowEditorService.

Covers: list (parses frontmatter, handles empty dir, malformed YAML),
create (seed template, duplicate 409, invalid name), dry-run
(valid/invalid templates), run (delegates to dispatch_workflow).
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from chatServer.services.vault_service import VaultService
from chatServer.services.workflow_editor_service import (
    WorkflowEditorService,
    _seed_template,
)

TEST_USER = "user-test"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_vault(tmp_path: Path) -> VaultService:
    """Build a VaultService backed by a real tmp_path filesystem."""
    (tmp_path / "config" / "system").mkdir(parents=True, exist_ok=True)
    (tmp_path / "sandboxes").mkdir(parents=True, exist_ok=True)
    return VaultService(storage_sync=None, data_dir=tmp_path)


def _prep_user(tmp_path: Path, user_id: str = TEST_USER) -> Path:
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

MALFORMED_YAML_TEMPLATE = """\
---
name: broken
description: [invalid yaml
  : this is not valid
---

# Broken
"""

MISSING_NAME_TEMPLATE = """\
---
description: No name here
version: 1
---

# No Name
"""


# ---------------------------------------------------------------------------
# list_workflows
# ---------------------------------------------------------------------------


class TestListWorkflows:
    @pytest.mark.asyncio
    async def test_parses_frontmatter(self, tmp_path):
        vault = _make_vault(tmp_path)
        user_root = _prep_user(tmp_path)
        _write_workflow(user_root, "morning-briefing", VALID_TEMPLATE)

        service = WorkflowEditorService(vault=vault)
        result = await service.list_workflows(TEST_USER)

        assert len(result) == 1
        wf = result[0]
        assert wf["name"] == "morning-briefing"
        assert wf["filename"] == "morning-briefing.flow.md"
        assert wf["description"] == "A morning briefing workflow"
        assert wf["trigger_summary"] == "Manual"
        assert wf["next_run_at"] is None

    @pytest.mark.asyncio
    async def test_handles_empty_dir(self, tmp_path):
        vault = _make_vault(tmp_path)
        user_root = _prep_user(tmp_path)
        (user_root / "_workflows").mkdir(parents=True, exist_ok=True)

        service = WorkflowEditorService(vault=vault)
        result = await service.list_workflows(TEST_USER)

        assert result == []

    @pytest.mark.asyncio
    async def test_handles_missing_workflows_dir(self, tmp_path):
        vault = _make_vault(tmp_path)
        _prep_user(tmp_path)

        service = WorkflowEditorService(vault=vault)
        result = await service.list_workflows(TEST_USER)

        assert result == []

    @pytest.mark.asyncio
    async def test_handles_malformed_yaml(self, tmp_path):
        vault = _make_vault(tmp_path)
        user_root = _prep_user(tmp_path)
        _write_workflow(user_root, "broken", MALFORMED_YAML_TEMPLATE)

        service = WorkflowEditorService(vault=vault)
        result = await service.list_workflows(TEST_USER)

        assert len(result) == 1
        wf = result[0]
        # Falls back to template_name when parse fails
        assert wf["name"] == "broken"
        assert wf["description"] == ""

    @pytest.mark.asyncio
    async def test_skips_non_flow_files(self, tmp_path):
        vault = _make_vault(tmp_path)
        user_root = _prep_user(tmp_path)
        _write_workflow(user_root, "morning-briefing", VALID_TEMPLATE)
        # Add a non-.flow.md file
        (user_root / "_workflows" / "readme.md").write_text("# Readme")

        service = WorkflowEditorService(vault=vault)
        result = await service.list_workflows(TEST_USER)

        assert len(result) == 1
        assert result[0]["filename"] == "morning-briefing.flow.md"

    @pytest.mark.asyncio
    async def test_multiple_workflows(self, tmp_path):
        vault = _make_vault(tmp_path)
        user_root = _prep_user(tmp_path)
        _write_workflow(user_root, "morning-briefing", VALID_TEMPLATE)
        _write_workflow(
            user_root,
            "evening-briefing",
            VALID_TEMPLATE.replace("morning-briefing", "evening-briefing"),
        )

        service = WorkflowEditorService(vault=vault)
        result = await service.list_workflows(TEST_USER)

        assert len(result) == 2
        names = {wf["filename"] for wf in result}
        assert "morning-briefing.flow.md" in names
        assert "evening-briefing.flow.md" in names


# ---------------------------------------------------------------------------
# create_workflow
# ---------------------------------------------------------------------------


class TestCreateWorkflow:
    @pytest.mark.asyncio
    async def test_creates_seed_template(self, tmp_path):
        vault = _make_vault(tmp_path)
        _prep_user(tmp_path)

        service = WorkflowEditorService(vault=vault)
        path = await service.create_workflow(TEST_USER, "my-workflow")

        assert path == "_workflows/my-workflow.flow.md"
        # Verify file exists
        full_path = tmp_path / "sandboxes" / TEST_USER / "_workflows" / "my-workflow.flow.md"
        assert full_path.exists()
        content = full_path.read_text()
        assert "name: my-workflow" in content
        assert "# My Workflow" in content

    @pytest.mark.asyncio
    async def test_duplicate_409(self, tmp_path):
        vault = _make_vault(tmp_path)
        user_root = _prep_user(tmp_path)
        _write_workflow(user_root, "existing", VALID_TEMPLATE)

        service = WorkflowEditorService(vault=vault)
        with pytest.raises(HTTPException) as exc_info:
            await service.create_workflow(TEST_USER, "existing")
        assert exc_info.value.status_code == 409

    @pytest.mark.asyncio
    async def test_invalid_name_uppercase(self, tmp_path):
        vault = _make_vault(tmp_path)
        _prep_user(tmp_path)

        service = WorkflowEditorService(vault=vault)
        with pytest.raises(HTTPException) as exc_info:
            await service.create_workflow(TEST_USER, "MyWorkflow")
        assert exc_info.value.status_code == 422

    @pytest.mark.asyncio
    async def test_invalid_name_special_chars(self, tmp_path):
        vault = _make_vault(tmp_path)
        _prep_user(tmp_path)

        service = WorkflowEditorService(vault=vault)
        with pytest.raises(HTTPException) as exc_info:
            await service.create_workflow(TEST_USER, "my_workflow!")
        assert exc_info.value.status_code == 422

    @pytest.mark.asyncio
    async def test_invalid_name_empty(self, tmp_path):
        vault = _make_vault(tmp_path)
        _prep_user(tmp_path)

        service = WorkflowEditorService(vault=vault)
        with pytest.raises(HTTPException) as exc_info:
            await service.create_workflow(TEST_USER, "")
        assert exc_info.value.status_code == 422

    @pytest.mark.asyncio
    async def test_invalid_name_too_long(self, tmp_path):
        vault = _make_vault(tmp_path)
        _prep_user(tmp_path)

        service = WorkflowEditorService(vault=vault)
        with pytest.raises(HTTPException) as exc_info:
            await service.create_workflow(TEST_USER, "a" * 61)
        assert exc_info.value.status_code == 422

    @pytest.mark.asyncio
    async def test_valid_name_with_numbers(self, tmp_path):
        vault = _make_vault(tmp_path)
        _prep_user(tmp_path)

        service = WorkflowEditorService(vault=vault)
        path = await service.create_workflow(TEST_USER, "v2-workflow-3")
        assert path == "_workflows/v2-workflow-3.flow.md"


# ---------------------------------------------------------------------------
# dry_run
# ---------------------------------------------------------------------------


class TestDryRun:
    @pytest.mark.asyncio
    async def test_valid_template(self, tmp_path):
        vault = _make_vault(tmp_path)
        user_root = _prep_user(tmp_path)
        _write_workflow(user_root, "morning-briefing", VALID_TEMPLATE)

        service = WorkflowEditorService(vault=vault)
        result = await service.dry_run(TEST_USER, "morning-briefing")

        assert result["valid"] is True
        assert result["errors"] == []
        assert len(result["steps"]) == 1
        step = result["steps"][0]
        assert step["name"] == "fetch-data"
        assert step["agent"] == "briefing-agent"
        assert step["tools"] == ["web_search"]
        assert result["parameters"] == []

    @pytest.mark.asyncio
    async def test_invalid_template_returns_errors(self, tmp_path):
        vault = _make_vault(tmp_path)
        user_root = _prep_user(tmp_path)
        _write_workflow(user_root, "broken", MISSING_NAME_TEMPLATE)

        service = WorkflowEditorService(vault=vault)
        result = await service.dry_run(TEST_USER, "broken")

        assert result["valid"] is False
        assert len(result["errors"]) > 0
        assert any("name" in e.lower() for e in result["errors"])
        assert result["steps"] == []

    @pytest.mark.asyncio
    async def test_not_found_404(self, tmp_path):
        vault = _make_vault(tmp_path)
        _prep_user(tmp_path)

        service = WorkflowEditorService(vault=vault)
        with pytest.raises(HTTPException) as exc_info:
            await service.dry_run(TEST_USER, "nonexistent")
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_template_with_parameters(self, tmp_path):
        vault = _make_vault(tmp_path)
        user_root = _prep_user(tmp_path)
        template_with_params = """\
---
name: param-workflow
description: Test params
version: 1
default_gate_policy: none
---

# Param Workflow

## Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| topic | yes | The topic to research |
| depth | no | How deep to go |

## Steps

### step-1: Research
- **agent:** researcher
- **depends_on:** []
- **tools:** []
- **description:** Research the topic.
- **gate:** none
"""
        _write_workflow(user_root, "param-workflow", template_with_params)

        service = WorkflowEditorService(vault=vault)
        result = await service.dry_run(TEST_USER, "param-workflow")

        assert result["valid"] is True
        assert len(result["parameters"]) == 2
        topic = next(p for p in result["parameters"] if p["name"] == "topic")
        assert topic["required"] is True
        depth = next(p for p in result["parameters"] if p["name"] == "depth")
        assert depth["required"] is False


# ---------------------------------------------------------------------------
# run_workflow
# ---------------------------------------------------------------------------


class TestRunWorkflow:
    @pytest.mark.asyncio
    async def test_delegates_to_dispatch(self, tmp_path):
        vault = _make_vault(tmp_path)
        user_root = _prep_user(tmp_path)
        _write_workflow(user_root, "morning-briefing", VALID_TEMPLATE)

        service = WorkflowEditorService(vault=vault)

        with patch(
            "chatServer.workflows.dispatch.dispatch_workflow",
            new_callable=AsyncMock,
            return_value="Started workflow 'morning-briefing' (run_id: abc-123). I'll keep you updated.",
        ) as mock_dispatch:
            run_id = await service.run_workflow(
                user_id=TEST_USER,
                template_name="morning-briefing",
                db_client=MagicMock(),
                llm_client=MagicMock(),
            )

        assert run_id == "abc-123"
        mock_dispatch.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_not_found_404(self, tmp_path):
        vault = _make_vault(tmp_path)
        _prep_user(tmp_path)

        service = WorkflowEditorService(vault=vault)
        with pytest.raises(HTTPException) as exc_info:
            await service.run_workflow(
                user_id=TEST_USER,
                template_name="nonexistent",
                db_client=MagicMock(),
                llm_client=MagicMock(),
            )
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_engine_unavailable_503(self, tmp_path):
        vault = _make_vault(tmp_path)
        user_root = _prep_user(tmp_path)
        _write_workflow(user_root, "morning-briefing", VALID_TEMPLATE)

        service = WorkflowEditorService(vault=vault)
        # No db_client or llm_client → 503
        with pytest.raises(HTTPException) as exc_info:
            await service.run_workflow(
                user_id=TEST_USER,
                template_name="morning-briefing",
            )
        assert exc_info.value.status_code == 503

    @pytest.mark.asyncio
    async def test_missing_params_from_dispatch(self, tmp_path):
        vault = _make_vault(tmp_path)
        user_root = _prep_user(tmp_path)
        _write_workflow(user_root, "morning-briefing", VALID_TEMPLATE)

        service = WorkflowEditorService(vault=vault)

        with patch(
            "chatServer.workflows.dispatch.dispatch_workflow",
            new_callable=AsyncMock,
            return_value="Missing required parameters for 'morning-briefing': topic, depth",
        ):
            with pytest.raises(HTTPException) as exc_info:
                await service.run_workflow(
                    user_id=TEST_USER,
                    template_name="morning-briefing",
                    db_client=MagicMock(),
                    llm_client=MagicMock(),
                )
            assert exc_info.value.status_code == 422


# ---------------------------------------------------------------------------
# _seed_template
# ---------------------------------------------------------------------------


class TestSeedTemplate:
    def test_contains_name(self):
        content = _seed_template("morning-briefing")
        assert "name: morning-briefing" in content

    def test_contains_display_title(self):
        content = _seed_template("morning-briefing")
        assert "# Morning Briefing" in content

    def test_contains_frontmatter(self):
        content = _seed_template("test")
        assert content.startswith("---")
        assert "version: 1" in content

    def test_contains_step_section(self):
        content = _seed_template("test")
        assert "## Steps" in content
        assert "### step-1:" in content
