"""ConfigChangeExecutor — apply proposed content to a vault file.

The ``diff`` field in the payload contains the complete new file content
(not a unified diff). The executor reads the current file for size tracking,
then writes the proposed content via ``VaultService.update_body``.
"""

from __future__ import annotations

import logging

from . import ExecutionResult
from .registry import register_executor

logger = logging.getLogger(__name__)


@register_executor("config_change")
class ConfigChangeExecutor:
    """Apply proposed file content to a vault file."""

    async def execute(self, card: dict, user_id: str) -> ExecutionResult:
        payload = card.get("payload") or {}
        file_path = payload.get("file_path")
        diff = payload.get("diff")  # actually complete new content

        if not file_path or diff is None:
            missing = [k for k in ("file_path", "diff") if not payload.get(k)]
            return ExecutionResult(
                success=False,
                error=f"Missing required payload fields: {', '.join(missing)}",
            )

        try:
            vault = self._get_vault_service()

            # Read current file for size tracking
            try:
                current_content = await vault.read_file(user_id, file_path)
                previous_size = len(current_content.encode("utf-8"))
            except Exception:
                # File may have been deleted since the card was created
                return ExecutionResult(
                    success=False,
                    error=(
                        f"File not found: {file_path}. "
                        "It may have been deleted since this change was proposed."
                    ),
                )

            # Write the proposed new content
            await vault.update_body(user_id, file_path, diff)
            new_size = len(diff.encode("utf-8"))

            return ExecutionResult(
                success=True,
                result={
                    "path": file_path,
                    "previous_size": previous_size,
                    "new_size": new_size,
                },
                activity_action=f"Applied config change to {file_path}",
            )
        except Exception as exc:
            logger.error("ConfigChangeExecutor failed for user %s: %s", user_id, exc)
            return ExecutionResult(
                success=False,
                error=f"Failed to apply config change: {exc}",
            )

    def _get_vault_service(self):
        """Create a VaultService instance. Factored out for testability."""
        import os
        from pathlib import Path

        from chatServer.services.vault_service import VaultService

        data_dir = Path(os.getenv("SANDBOX_DATA_DIR", "/data"))
        return VaultService(storage_sync=None, data_dir=data_dir)
