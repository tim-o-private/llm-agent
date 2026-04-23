"""Approval card executor pattern — SPEC-052.

Each card type maps to an executor class registered via ``@register_executor``.
The dispatch layer in ``ApprovalService`` looks up the executor and calls
``execute(card, user_id)`` after the status flip.

To add a new card type:
1. Add the value to the ``approval_card_type`` enum (migration).
2. Write a class implementing ``CardExecutor`` and decorate it with
   ``@register_executor("new_type")``.
3. Import the module here so registration fires at import time.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Protocol


@dataclass
class ExecutionResult:
    """Returned by every executor."""

    success: bool
    result: Optional[dict] = field(default=None)
    error: Optional[str] = field(default=None)
    activity_action: Optional[str] = field(default=None)


class CardExecutor(Protocol):
    """Protocol that every card-type executor implements."""

    async def execute(
        self,
        card: dict,
        user_id: str,
    ) -> ExecutionResult:
        """Execute the approved action.

        Must be idempotent if called with the same card — but the dispatcher
        already guards against double-execution via the ``executed_at`` check.
        """
        ...


# Import executor modules to trigger registration at import time.
from . import (  # noqa: E402, F401
    email_draft,
    calendar_hold,
    outreach,
    workflow_proposal,
    config_change,
    file_operation,
)
