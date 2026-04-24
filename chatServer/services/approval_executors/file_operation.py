"""FileOperationExecutor — move, rename, or delete vault files.

All paths go through ``VaultService._resolve`` for containment safety.
Protected paths (``today.md``, ``_workflows/``) are rejected.
"""

from __future__ import annotations

import logging
from pathlib import PurePosixPath

from . import ExecutionResult
from ._vault_factory import create_vault_service
from .registry import register_executor

logger = logging.getLogger(__name__)

# Protected paths — use ``workflow_proposal`` for _workflows/ changes.
_PROTECTED_PATHS = {"today.md"}
_PROTECTED_PREFIXES = ("_workflows/",)


def _is_protected(rel_path: str) -> bool:
    """Check if a relative path is protected from file operations."""
    normalized = PurePosixPath(rel_path).as_posix()
    if normalized in _PROTECTED_PATHS:
        return True
    for prefix in _PROTECTED_PREFIXES:
        if normalized.startswith(prefix):
            return True
    return False


@register_executor("file_operation")
class FileOperationExecutor:
    """Move, rename, or delete files within the user's vault."""

    async def execute(self, card: dict, user_id: str) -> ExecutionResult:
        payload = card.get("payload") or {}
        operation = payload.get("operation")
        source = payload.get("source")
        target = payload.get("target")

        if not operation or not source:
            missing = [k for k in ("operation", "source") if not payload.get(k)]
            return ExecutionResult(
                success=False,
                error=f"Missing required payload fields: {', '.join(missing)}",
            )

        if operation not in ("move", "rename", "delete"):
            return ExecutionResult(
                success=False,
                error=f"Unknown operation: {operation}. Must be move, rename, or delete.",
            )

        if operation in ("move", "rename") and not target:
            return ExecutionResult(
                success=False,
                error=f"Operation '{operation}' requires a target path.",
            )

        # Check protected paths
        if _is_protected(source):
            return ExecutionResult(
                success=False,
                error=f"Cannot {operation} protected path: {source}",
            )
        if target and _is_protected(target):
            return ExecutionResult(
                success=False,
                error=f"Cannot {operation} to protected path: {target}",
            )

        try:
            vault = create_vault_service()

            if operation == "delete":
                await vault.delete_file(user_id, source)
                return ExecutionResult(
                    success=True,
                    result={"operation": "delete", "source": source},
                    activity_action=f"Deleted file: {source}",
                )
            else:
                # move or rename
                await vault.move_file(user_id, source, target)
                return ExecutionResult(
                    success=True,
                    result={"operation": operation, "source": source, "target": target},
                    activity_action=f"{'Moved' if operation == 'move' else 'Renamed'} {source} to {target}",
                )
        except Exception as exc:
            logger.error("FileOperationExecutor failed for user %s: %s", user_id, exc)
            error_str = str(exc)
            # Surface HTTP exception details
            if hasattr(exc, "status_code"):
                if exc.status_code == 404:
                    return ExecutionResult(
                        success=False,
                        error=f"Source file not found: {source}",
                    )
                if exc.status_code == 409:
                    return ExecutionResult(
                        success=False,
                        error=f"Target file already exists: {target}",
                    )
            return ExecutionResult(
                success=False,
                error=f"File operation failed: {error_str}",
            )

