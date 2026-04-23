"""Config-change executor — applies approved config_change proposals to the vault.

SPEC-052 AC-12 + SPEC-054 AC-13 (safety validator integration).

This is a stub executor that will be completed when SPEC-052 lands on this
branch. The safety validator hook is wired here as defense-in-depth — it
runs before the actual file write.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Optional

from ..config_change_validator import ConfigChangeSafetyValidator

logger = logging.getLogger(__name__)

_validator = ConfigChangeSafetyValidator()


@dataclass
class ExecutionResult:
    success: bool
    error: Optional[str] = None
    detail: Optional[dict] = None


async def execute_config_change(
    card: dict,
    vault: Any,
    user_id: str,
) -> ExecutionResult:
    """Execute an approved config_change card.

    1. Validate proposed content with ConfigChangeSafetyValidator.
    2. Write the file via VaultService.

    Returns ExecutionResult with success=False if validation fails.
    """
    payload = card.get("payload", {})
    file_path = payload.get("file_path", "")
    proposed_content = payload.get("diff", "")

    if not file_path or not proposed_content:
        return ExecutionResult(
            success=False,
            error="Missing file_path or diff in payload",
        )

    # Safety validator — defense-in-depth (AC-13)
    is_safe, reason = _validator.validate(file_path, proposed_content)
    if not is_safe:
        logger.warning(
            "Config change rejected by safety validator: %s (path=%s, user=%s)",
            reason,
            file_path,
            user_id,
        )
        return ExecutionResult(success=False, error=reason)

    # Write the file
    try:
        await vault.update_body(user_id, file_path, proposed_content)
    except Exception as exc:
        logger.error(
            "Config change write failed: %s (path=%s, user=%s)",
            exc,
            file_path,
            user_id,
            exc_info=True,
        )
        return ExecutionResult(success=False, error=str(exc))

    return ExecutionResult(
        success=True,
        detail={"file_path": file_path},
    )
