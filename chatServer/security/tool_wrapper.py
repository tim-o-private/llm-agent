"""
Tool wrapper for approval-based execution.

This module provides a wrapper that intercepts LangChain tool execution
to enforce the approval tier system. Tools that require approval are
queued instead of executed immediately.
"""

import logging
from typing import Optional

from langchain_core.tools import BaseTool

try:
    from ..security.approval_tiers import (
        ApprovalTier,
        get_effective_tier,
    )
except ImportError:
    from chatServer.security.approval_tiers import (
        ApprovalTier,
        get_effective_tier,
    )

logger = logging.getLogger(__name__)


class ApprovalContext:
    """
    Context for tool execution with approval checking.

    Holds the user_id and services needed to check approval,
    queue actions, and log to the audit trail.
    """

    def __init__(
        self,
        user_id: str,
        session_id: Optional[str] = None,
        agent_name: Optional[str] = None,
        db_client=None,
        pending_actions_service=None,
        audit_service=None,
    ):
        self.user_id = user_id
        self.session_id = session_id
        self.agent_name = agent_name
        self.db_client = db_client
        self.pending_actions_service = pending_actions_service
        self.audit_service = audit_service


def with_approval(
    tool: BaseTool,
    context: ApprovalContext,
) -> BaseTool:
    """
    Wrap a LangChain tool to check approval tier before execution.

    Modifies the tool's _arun method to:
    1. Look up the effective approval tier
    2. If AUTO_APPROVE: execute immediately
    3. If REQUIRES_APPROVAL: queue action and return a message
    """
    original_arun = tool._arun

    async def wrapped_arun(*args, **kwargs) -> str:
        tool_name = tool.name

        tier = await get_effective_tier(
            user_id=context.user_id,
            tool_name=tool_name,
            db_client=context.db_client,
        )

        logger.info(f"Tool {tool_name} execution requested, tier: {tier.value}")

        if tier == ApprovalTier.AUTO_APPROVE:
            try:
                result = await original_arun(*args, **kwargs)

                if context.audit_service:
                    await context.audit_service.log_action(
                        user_id=context.user_id,
                        tool_name=tool_name,
                        tool_args=kwargs,
                        approval_tier="auto",
                        approval_status="auto_approved",
                        execution_status="success",
                        execution_result={"result": str(result)[:1000]},
                        session_id=context.session_id,
                        agent_name=context.agent_name,
                    )

                return result
            except Exception as e:
                if context.audit_service:
                    await context.audit_service.log_action(
                        user_id=context.user_id,
                        tool_name=tool_name,
                        tool_args=kwargs,
                        approval_tier="auto",
                        approval_status="auto_approved",
                        execution_status="error",
                        error_message=str(e),
                        session_id=context.session_id,
                        agent_name=context.agent_name,
                    )
                raise

        else:
            # Queue for approval
            if context.pending_actions_service is None:
                logger.error("No pending_actions_service provided, cannot queue action")
                return f"Error: Action '{tool_name}' requires approval but queue is unavailable."

            try:
                action_id = await context.pending_actions_service.queue_action(
                    user_id=context.user_id,
                    tool_name=tool_name,
                    tool_args=kwargs,
                    context={
                        "session_id": context.session_id,
                        "agent_name": context.agent_name,
                    }
                )

                logger.info(f"Action {tool_name} queued for approval: {action_id}")

                return (
                    f"Action '{tool_name}' has been queued for your approval. "
                    f"Action ID: {action_id}. "
                    f"Please review and approve this action in the confirmation panel."
                )
            except Exception as e:
                logger.error(f"Failed to queue action {tool_name}: {e}")
                return f"Error: Failed to queue action '{tool_name}' for approval: {str(e)}"

    tool._arun = wrapped_arun

    original_run = tool._run

    def wrapped_run(*args, **kwargs) -> str:
        logger.warning(f"Sync _run called for {tool.name}, skipping approval check")
        return original_run(*args, **kwargs)

    tool._run = wrapped_run

    return tool


def wrap_tools_with_approval(
    tools: list[BaseTool],
    context: ApprovalContext,
) -> list[BaseTool]:
    """Wrap multiple tools with approval checking."""
    for tool in tools:
        with_approval(tool, context)

    logger.info(f"Wrapped {len(tools)} tools with approval checking for user {context.user_id}")
    return tools


class ApprovalRequiredError(Exception):
    """Raised when an action requires approval but was attempted directly."""

    def __init__(self, tool_name: str, action_id: Optional[str] = None):
        self.tool_name = tool_name
        self.action_id = action_id
        message = f"Action '{tool_name}' requires approval."
        if action_id:
            message += f" Action ID: {action_id}"
        super().__init__(message)
