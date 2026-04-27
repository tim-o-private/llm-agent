"""Workflow editor service — list, create, dry-run, run workflows.

Composes VaultService (filesystem), template_parser (validation), and
WorkflowRunManager (execution). Routers delegate here per A1.
"""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Any, Optional

from fastapi import HTTPException, status

from ..lib.frontmatter import parse_frontmatter
from ..services.tool_resolver_service import resolve_tools_for_agent
from ..services.vault_service import VaultService
from ..workflows.models import TemplateParseError
from ..workflows.services import DEFAULT_SERVICE_REGISTRY
from ..workflows.template_parser import parse_template

logger = logging.getLogger(__name__)

_WORKFLOWS_DIR = "_workflows"
_FLOW_EXT = ".flow.md"
_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
_NAME_MAX_LEN = 60


def _seed_template(name: str) -> str:
    """Return the seed content for a new workflow file."""
    display = name.replace("-", " ").title()
    return f"""---
name: {name}
description: ""
version: 1
default_gate_policy: none
---

# {display}

## Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|

## Steps

### step-1: First step
- **agent:** (specify agent)
- **depends_on:** []
- **tools:** []
- **description:** Describe what this step does.
- **gate:** none
"""


class WorkflowEditorService:
    """Backend for the workflow editor surface (SPEC-048)."""

    def __init__(
        self,
        vault: VaultService,
        db: Any = None,
    ):
        self._vault = vault
        self._db = db  # UserScopedClient — used for jobs table lookup

    # ------------------------------------------------------------------
    # List workflows
    # ------------------------------------------------------------------

    async def list_workflows(self, user_id: str) -> list[dict[str, Any]]:
        """Read ``_workflows/`` via VaultService, parse frontmatter of each
        ``.flow.md`` file, check jobs table for next scheduled run.

        Returns ``[{name, filename, description, trigger_summary, next_run_at}]``.
        """
        try:
            entries = await self._vault.list_folder(user_id, _WORKFLOWS_DIR)
        except HTTPException:
            # _workflows/ doesn't exist — return empty list
            return []

        flow_entries = [
            e for e in entries
            if e.type == "file" and e.name.endswith(_FLOW_EXT)
        ]
        if not flow_entries:
            return []

        # Read all workflow files in parallel
        async def _read_fm(entry):
            try:
                content = await self._vault.read_file(user_id, entry.path)
                return self._parse_frontmatter_only(content)
            except Exception:
                return {}

        template_names = [e.name[: -len(_FLOW_EXT)] for e in flow_entries]
        frontmatters, next_runs = await asyncio.gather(
            asyncio.gather(*[_read_fm(e) for e in flow_entries]),
            asyncio.gather(*[self._get_next_scheduled_run(tn) for tn in template_names]),
        )

        return [
            {
                "name": fm.get("name", tn),
                "filename": entry.name,
                "description": fm.get("description", ""),
                "trigger_summary": self._format_triggers(fm),
                "next_run_at": nr,
            }
            for entry, tn, fm, nr in zip(flow_entries, template_names, frontmatters, next_runs)
        ]

    # ------------------------------------------------------------------
    # Create workflow
    # ------------------------------------------------------------------

    async def create_workflow(self, user_id: str, name: str) -> str:
        """Validate name, create ``_workflows/<name>.flow.md`` with seed
        template. Return vault-relative path. 409 if exists.
        """
        # Validate name
        if (
            not name
            or len(name) > _NAME_MAX_LEN
            or not _NAME_RE.match(name)
        ):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    "Invalid workflow name: must be 1-60 chars, "
                    "lowercase alphanumeric and hyphens, starting with a letter or digit."
                ),
            )

        rel_path = f"{_WORKFLOWS_DIR}/{name}{_FLOW_EXT}"

        # Check if file already exists
        stat = await self._vault.stat_file(user_id, rel_path)
        if stat is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Workflow '{name}' already exists",
            )

        # Write seed template
        content = _seed_template(name)
        await self._vault.update_body(user_id, rel_path, content)
        return rel_path

    # ------------------------------------------------------------------
    # Dry run
    # ------------------------------------------------------------------

    async def dry_run(self, user_id: str, template_name: str) -> dict[str, Any]:
        """Parse template via ``template_parser.parse_template()``. Return
        structured validation result. No execution.
        """
        rel_path = f"{_WORKFLOWS_DIR}/{template_name}{_FLOW_EXT}"

        # Try to read the user's workflow file
        try:
            content = await self._vault.read_file(user_id, rel_path)
        except HTTPException as exc:
            if exc.status_code == 404:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Template '{template_name}' not found",
                )
            raise

        # Parse the template
        try:
            template = parse_template(content, source_name=template_name)
        except TemplateParseError as e:
            return {
                "valid": False,
                "errors": [str(e)],
                "steps": [],
                "parameters": [],
            }

        return {
            "valid": True,
            "errors": [],
            "steps": [
                {
                    "name": s.name,
                    "agent": s.agent,
                    "depends_on": s.depends_on,
                    "tools": s.tools,
                }
                for s in template.steps
            ],
            "parameters": [
                {
                    "name": p.name,
                    "required": p.required,
                    "description": p.description,
                }
                for p in template.parameters
            ],
        }

    # ------------------------------------------------------------------
    # Run workflow
    # ------------------------------------------------------------------

    async def run_workflow(
        self,
        user_id: str,
        template_name: str,
        parameters: Optional[dict] = None,
        db_client: Any = None,
        llm_client: Any = None,
    ) -> str:
        """Delegate to ``dispatch_workflow`` (same path as today regenerate).

        Returns the run_id extracted from the dispatch result message.
        """
        from ..workflows.dispatch import dispatch_workflow

        # Verify template exists in user vault first
        rel_path = f"{_WORKFLOWS_DIR}/{template_name}{_FLOW_EXT}"
        try:
            await self._vault.read_file(user_id, rel_path)
        except HTTPException as exc:
            if exc.status_code == 404:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Template '{template_name}' not found",
                )
            raise

        effective_db = db_client or self._db
        if effective_db is None or llm_client is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Workflow engine unavailable",
            )

        agent_name = "assistant"
        try:
            tool_schemas, tool_executors, _ = await resolve_tools_for_agent(
                user_id, agent_name
            )
        except Exception as exc:
            logger.error(
                "Failed to resolve tools for workflow '%s': %s",
                template_name,
                exc,
                exc_info=True,
            )
            tool_schemas, tool_executors = [], {}

        try:
            result_msg = await dispatch_workflow(
                args={
                    "workflow_name": template_name,
                    "parameters": parameters or {},
                },
                user_id=user_id,
                db_client=effective_db,
                llm_client=llm_client,
                tool_schemas=tool_schemas,
                tool_executors=tool_executors,
                service_registry=DEFAULT_SERVICE_REGISTRY,
            )
        except Exception as exc:
            logger.error("run_workflow dispatch failed: %s", exc, exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Workflow engine unavailable",
            )

        # dispatch_workflow returns a status message string. Extract run_id.
        if "run_id:" in result_msg:
            # Format: "Started workflow 'X' (run_id: <uuid>). ..."
            import re as _re

            match = _re.search(r"run_id:\s*([a-f0-9-]+)", result_msg)
            if match:
                return match.group(1)

        # If dispatch returned an error message, translate to HTTP errors
        if "Unknown workflow" in result_msg:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Template '{template_name}' not found",
            )
        if "Missing required parameters" in result_msg:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=result_msg,
            )

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Workflow engine unavailable",
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_frontmatter_only(content: str) -> dict[str, Any]:
        """Extract YAML frontmatter without parsing steps (fast for listing)."""
        fm, _ = parse_frontmatter(content)
        return fm

    @staticmethod
    def _format_triggers(fm: dict) -> str:
        """Format trigger summary from frontmatter. Returns 'Manual' if no triggers."""
        triggers = fm.get("triggers")
        if not triggers:
            return "Manual"
        if isinstance(triggers, list):
            return ", ".join(str(t) for t in triggers)
        return str(triggers)

    async def _get_next_scheduled_run(
        self, template_name: str
    ) -> Optional[str]:
        """Check the ``jobs`` table for the next scheduled run."""
        if self._db is None:
            return None
        try:
            result = await (
                self._db.table("jobs")
                .select("scheduled_for")
                .eq("status", "pending")
                .like("input->>template_name", template_name)
                .order("scheduled_for", desc=False)
                .limit(1)
                .execute()
            )
            if result.data:
                return result.data[0].get("scheduled_for")
        except Exception:
            logger.debug(
                "Failed to query jobs table for %s", template_name, exc_info=True
            )
        return None
