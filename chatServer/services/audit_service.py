"""
Audit logging service for tool executions.

Records all tool executions to the audit_logs table,
providing a complete trail of agent actions for security review.
"""

import hashlib
import json
import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


class AuditService:
    """
    Service for logging tool executions to the audit trail.

    All tool executions flow through this service, creating a complete
    record of what agents have done on behalf of users.
    """

    def __init__(self, db_client):
        self.db = db_client

    @staticmethod
    def _hash_args(args: dict) -> str:
        """Create a SHA-256 hash of tool arguments for privacy."""
        args_json = json.dumps(args, sort_keys=True, default=str)
        return hashlib.sha256(args_json.encode()).hexdigest()

    async def log_action(
        self,
        user_id: str,
        tool_name: str,
        tool_args: dict,
        approval_tier: str,
        approval_status: str,
        execution_status: Optional[str] = None,
        execution_result: Optional[dict] = None,
        error_message: Optional[str] = None,
        pending_action_id: Optional[str] = None,
        session_id: Optional[str] = None,
        agent_name: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Optional[str]:
        """Log a tool execution to the audit trail."""
        try:
            args_hash = self._hash_args(tool_args)

            entry = {
                "user_id": user_id,
                "tool_name": tool_name,
                "tool_args_hash": args_hash,
                "approval_tier": approval_tier,
                "approval_status": approval_status,
            }

            if execution_status:
                entry["execution_status"] = execution_status
            if execution_result:
                entry["execution_result"] = self._truncate_result(execution_result)
            if error_message:
                entry["error_message"] = error_message[:1000]
            if pending_action_id:
                entry["pending_action_id"] = pending_action_id
            if session_id:
                entry["session_id"] = session_id
            if agent_name:
                entry["agent_name"] = agent_name
            if ip_address:
                entry["ip_address"] = ip_address
            if user_agent:
                entry["user_agent"] = user_agent[:500]

            result = await self.db.table("audit_logs") \
                .insert(entry) \
                .execute()

            if result.data and len(result.data) > 0:
                audit_id = result.data[0].get("id")
                logger.debug(f"Audit log created: {audit_id} for {tool_name}")
                return audit_id
            return None

        except Exception as e:
            # Audit logging should never break the main flow
            logger.error(f"Failed to create audit log entry: {e}")
            return None

    @staticmethod
    def _truncate_result(result: dict, max_size: int = 10000) -> dict:
        """Truncate execution result to avoid huge payloads."""
        result_json = json.dumps(result, default=str)
        if len(result_json) <= max_size:
            return result

        return {
            "truncated": True,
            "preview": result_json[:max_size],
            "original_size": len(result_json),
        }

    async def get_audit_log(
        self,
        user_id: str,
        limit: int = 50,
        offset: int = 0,
        tool_name: Optional[str] = None,
        approval_status: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> list[dict]:
        """Get audit log entries for a user."""
        try:
            query = self.db.table("audit_logs") \
                .select("*") \
                .eq("user_id", user_id) \
                .order("created_at", desc=True) \
                .limit(limit) \
                .offset(offset)

            if tool_name:
                query = query.eq("tool_name", tool_name)
            if approval_status:
                query = query.eq("approval_status", approval_status)
            if start_date:
                query = query.gte("created_at", start_date.isoformat())
            if end_date:
                query = query.lte("created_at", end_date.isoformat())

            result = await query.execute()
            return result.data or []

        except Exception as e:
            logger.error(f"Failed to get audit log: {e}")
            return []

    async def get_action_count(
        self,
        user_id: str,
        tool_name: Optional[str] = None,
        since: Optional[datetime] = None,
    ) -> int:
        """Get count of actions for a user."""
        try:
            query = self.db.table("audit_logs") \
                .select("id", count="exact") \
                .eq("user_id", user_id)

            if tool_name:
                query = query.eq("tool_name", tool_name)
            if since:
                query = query.gte("created_at", since.isoformat())

            result = await query.execute()
            return result.count or 0

        except Exception as e:
            logger.error(f"Failed to get action count: {e}")
            return 0
