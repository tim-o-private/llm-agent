"""
Pending Actions Service.

Manages the queue of actions awaiting user approval before execution.

Workflow:
1. Tool wrapper calls queue_action() when tier is REQUIRES_APPROVAL
2. User sees pending actions in UI
3. User approves/rejects via API
4. On approval, action is executed and logged
5. Stale actions are expired via expire_stale_actions()
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class PendingAction(BaseModel):
    """Data model for a pending action."""
    id: UUID
    user_id: UUID
    tool_name: str
    tool_args: dict
    status: str
    created_at: datetime
    updated_at: datetime
    expires_at: datetime
    resolved_at: Optional[datetime] = None
    execution_result: Optional[dict] = None
    context: dict = {}


class ActionResult(BaseModel):
    """Result of executing an approved action."""
    success: bool
    result: Optional[Any] = None
    error: Optional[str] = None


class PendingActionsService:
    """
    Service for managing the pending actions queue.

    This service is the bridge between tool execution and user approval.
    """

    def __init__(
        self,
        db_client,
        tool_executor=None,
        audit_service=None,
        default_expiry_hours: int = 24,
    ):
        self.db = db_client
        self.tool_executor = tool_executor
        self.audit_service = audit_service
        self.default_expiry_hours = default_expiry_hours

    async def queue_action(
        self,
        user_id: str,
        tool_name: str,
        tool_args: dict,
        context: Optional[dict] = None,
        expiry_hours: Optional[int] = None,
    ) -> str:
        """Queue an action for user approval. Returns action ID."""
        expiry = expiry_hours or self.default_expiry_hours
        expires_at = datetime.utcnow() + timedelta(hours=expiry)

        entry = {
            "user_id": user_id,
            "tool_name": tool_name,
            "tool_args": tool_args,
            "status": "pending",
            "expires_at": expires_at.isoformat(),
            "context": context or {},
        }

        result = await self.db.table("pending_actions") \
            .insert(entry) \
            .execute()

        if not result.data or len(result.data) == 0:
            raise Exception("Failed to queue action")

        action_id = result.data[0]["id"]
        logger.info(f"Queued action {action_id}: {tool_name} for user {user_id}")
        return action_id

    async def get_pending_actions(
        self,
        user_id: str,
        limit: int = 50,
        include_expired: bool = False,
    ) -> list[PendingAction]:
        """Get pending actions for a user."""
        try:
            query = self.db.table("pending_actions") \
                .select("*") \
                .eq("user_id", user_id) \
                .order("created_at", desc=True) \
                .limit(limit)

            if not include_expired:
                query = query.eq("status", "pending")

            result = await query.execute()

            actions = []
            for row in result.data or []:
                actions.append(PendingAction(**row))
            return actions

        except Exception as e:
            logger.error(f"Failed to get pending actions: {e}")
            return []

    async def get_action(self, action_id: str, user_id: str) -> Optional[PendingAction]:
        """Get a specific pending action."""
        try:
            result = await self.db.table("pending_actions") \
                .select("*") \
                .eq("id", action_id) \
                .eq("user_id", user_id) \
                .single() \
                .execute()

            if result.data:
                return PendingAction(**result.data)
            return None

        except Exception as e:
            logger.error(f"Failed to get action {action_id}: {e}")
            return None

    async def approve_action(
        self,
        action_id: str,
        user_id: str,
    ) -> ActionResult:
        """Approve and execute a pending action."""
        action = await self.get_action(action_id, user_id)

        if action is None:
            return ActionResult(success=False, error="Action not found or not authorized")

        if action.status != "pending":
            return ActionResult(success=False, error=f"Action is not pending (status: {action.status})")

        if datetime.utcnow() > action.expires_at.replace(tzinfo=None):
            await self._update_status(action_id, "expired")
            return ActionResult(success=False, error="Action has expired")

        await self._update_status(action_id, "approved")

        execution_result = None
        execution_error = None

        if self.tool_executor:
            try:
                execution_result = await self.tool_executor(
                    tool_name=action.tool_name,
                    tool_args=action.tool_args,
                    user_id=user_id,
                )

                await self.db.table("pending_actions") \
                    .update({
                        "status": "executed",
                        "resolved_at": datetime.utcnow().isoformat(),
                        "execution_result": {"result": str(execution_result)[:10000]},
                    }) \
                    .eq("id", action_id) \
                    .execute()

            except Exception as e:
                execution_error = str(e)
                logger.error(f"Failed to execute approved action {action_id}: {e}")

                await self.db.table("pending_actions") \
                    .update({
                        "status": "executed",
                        "resolved_at": datetime.utcnow().isoformat(),
                        "execution_result": {"error": execution_error},
                    }) \
                    .eq("id", action_id) \
                    .execute()
        else:
            logger.warning(f"No tool executor configured, action {action_id} marked approved but not executed")
            await self._update_status(action_id, "approved", resolved=True)

        if self.audit_service:
            await self.audit_service.log_action(
                user_id=user_id,
                tool_name=action.tool_name,
                tool_args=action.tool_args,
                approval_tier="requires_approval",
                approval_status="user_approved",
                execution_status="success" if execution_error is None else "error",
                execution_result={"result": str(execution_result)[:1000]} if execution_result else None,
                error_message=execution_error,
                pending_action_id=action_id,
                session_id=action.context.get("session_id"),
                agent_name=action.context.get("agent_name"),
            )

        if execution_error:
            return ActionResult(success=False, error=execution_error)
        return ActionResult(success=True, result=execution_result)

    async def reject_action(
        self,
        action_id: str,
        user_id: str,
        reason: Optional[str] = None,
    ) -> bool:
        """Reject a pending action."""
        action = await self.get_action(action_id, user_id)

        if action is None:
            logger.warning(f"Reject failed: action {action_id} not found")
            return False

        if action.status != "pending":
            logger.warning(f"Reject failed: action {action_id} is not pending")
            return False

        await self._update_status(action_id, "rejected", resolved=True)

        if self.audit_service:
            await self.audit_service.log_action(
                user_id=user_id,
                tool_name=action.tool_name,
                tool_args=action.tool_args,
                approval_tier="requires_approval",
                approval_status="user_rejected",
                execution_status="skipped",
                session_id=action.context.get("session_id"),
                agent_name=action.context.get("agent_name"),
            )

        logger.info(f"Action {action_id} rejected by user {user_id}")
        return True

    async def _update_status(
        self,
        action_id: str,
        status: str,
        resolved: bool = False,
    ) -> None:
        """Update action status in database."""
        update = {
            "status": status,
            "updated_at": datetime.utcnow().isoformat(),
        }
        if resolved:
            update["resolved_at"] = datetime.utcnow().isoformat()

        await self.db.table("pending_actions") \
            .update(update) \
            .eq("id", action_id) \
            .execute()

    async def expire_stale_actions(self) -> int:
        """Expire all pending actions past their expiry time."""
        try:
            result = await self.db.rpc("expire_pending_actions").execute()
            expired_count = result.data or 0

            if expired_count > 0:
                logger.info(f"Expired {expired_count} stale pending actions")
            return expired_count

        except Exception as e:
            logger.error(f"Failed to expire stale actions: {e}")
            return 0

    async def get_pending_count(self, user_id: str) -> int:
        """Get count of pending actions for a user."""
        try:
            result = await self.db.table("pending_actions") \
                .select("id", count="exact") \
                .eq("user_id", user_id) \
                .eq("status", "pending") \
                .execute()

            return result.count or 0

        except Exception as e:
            logger.error(f"Failed to get pending count: {e}")
            return 0
