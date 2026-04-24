"""WorkflowProposalExecutor — write a ``.flow.md`` file to the vault.

Refuses to overwrite existing files. All paths go through
``VaultService._resolve`` for containment safety.
"""

from __future__ import annotations

import logging

from . import ExecutionResult
from .registry import register_executor

logger = logging.getLogger(__name__)


@register_executor("workflow_proposal")
class WorkflowProposalExecutor:
    """Write a proposed workflow file to ``_workflows/{filename}``."""

    async def execute(self, card: dict, user_id: str) -> ExecutionResult:
        payload = card.get("payload") or {}
        filename = payload.get("filename")
        body = payload.get("body")

        if not filename or not body:
            missing = [k for k in ("filename", "body") if not payload.get(k)]
            return ExecutionResult(
                success=False,
                error=f"Missing required payload fields: {', '.join(missing)}",
            )

        # Validate filename extension
        if not (filename.endswith(".flow.md") or filename.endswith(".md")):
            return ExecutionResult(
                success=False,
                error=f"Invalid filename extension: {filename}. Must end with .flow.md or .md.",
            )

        rel_path = f"_workflows/{filename}"

        try:
            from chatServer.services.vault_service import VaultService

            vault = self._get_vault_service()

            # Check if file already exists — refuse to overwrite
            stat = await vault.stat_file(user_id, rel_path)
            if stat is not None:
                return ExecutionResult(
                    success=False,
                    error=(
                        f"Workflow file already exists at {rel_path}. "
                        "Edit or delete the existing file first."
                    ),
                )

            # Write via VaultService
            await vault.update_body(user_id, rel_path, body)
            bytes_written = len(body.encode("utf-8"))

            return ExecutionResult(
                success=True,
                result={"path": rel_path, "bytes_written": bytes_written},
                activity_action=f"Created workflow file: {rel_path}",
            )
        except Exception as exc:
            logger.error("WorkflowProposalExecutor failed for user %s: %s", user_id, exc)
            return ExecutionResult(
                success=False,
                error=f"Failed to write workflow file: {exc}",
            )

    def _get_vault_service(self):
        """Create a VaultService instance. Factored out for testability."""
        import os
        from pathlib import Path

        from chatServer.services.vault_service import VaultService

        data_dir = Path(os.getenv("SANDBOX_DATA_DIR", "/data"))
        return VaultService(storage_sync=None, data_dir=data_dir)
