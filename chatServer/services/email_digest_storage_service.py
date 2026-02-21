"""Dedicated service for email digest persistence with comprehensive error handling."""

import logging
from datetime import datetime
from typing import Any, Dict, List

from ..database.connection import get_database_manager

logger = logging.getLogger(__name__)


class EmailDigestStorageService:
    """Dedicated service for email digest persistence with proper error handling."""

    def __init__(self):
        """Initialize the storage service."""
        pass

    async def store_digest(self, digest_data: Dict[str, Any]) -> bool:
        """
        Store email digest with comprehensive error handling and validation.

        Args:
            digest_data: Dictionary containing digest information

        Returns:
            bool: True if storage successful, False otherwise
        """
        try:
            # Validate required fields
            required_fields = ["user_id", "generated_at", "hours_back", "include_read", "digest_content", "status"]
            missing_fields = [field for field in required_fields if field not in digest_data]

            if missing_fields:
                logger.error(f"Missing required fields for digest storage: {missing_fields}")
                return False

            # Validate data types and values
            if not isinstance(digest_data["user_id"], str) or not digest_data["user_id"]:
                logger.error(f"Invalid user_id: {digest_data['user_id']}")
                return False

            if not isinstance(digest_data["hours_back"], (int, float)) or digest_data["hours_back"] <= 0:
                logger.error(f"Invalid hours_back: {digest_data['hours_back']}")
                return False

            if not isinstance(digest_data["include_read"], bool):
                logger.error(f"Invalid include_read: {digest_data['include_read']}")
                return False

            if digest_data["status"] not in ["success", "error"]:
                logger.error(f"Invalid status: {digest_data['status']}")
                return False

            # Ensure generated_at is a datetime object
            if isinstance(digest_data["generated_at"], str):
                try:
                    digest_data["generated_at"] = datetime.fromisoformat(digest_data["generated_at"].replace('Z', '+00:00'))  # noqa: E501
                except ValueError as e:
                    logger.error(f"Invalid generated_at format: {digest_data['generated_at']}: {e}")
                    return False
            elif not isinstance(digest_data["generated_at"], datetime):
                logger.error(f"Invalid generated_at type: {type(digest_data['generated_at'])}")
                return False

            # Add context and email_count if not present
            context = digest_data.get("context", "unknown")
            email_count = digest_data.get("email_count", None)

            logger.info(f"Storing email digest for user {digest_data['user_id']} (context: {context}, status: {digest_data['status']})")  # noqa: E501

            # Get database manager and store
            db_manager = get_database_manager()

            async for conn in db_manager.get_connection():
                async with conn.cursor() as cur:
                    # Insert with all available fields
                    await cur.execute("""
                        INSERT INTO email_digests
                        (user_id, generated_at, hours_back, include_read, digest_content, status, context, email_count)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        digest_data["user_id"],
                        digest_data["generated_at"],
                        digest_data["hours_back"],
                        digest_data["include_read"],
                        digest_data["digest_content"],
                        digest_data["status"],
                        context,
                        email_count
                    ))

                    # Commit the transaction explicitly
                    await conn.commit()

                    # Verify the insert
                    await cur.execute("""
                        SELECT id FROM email_digests
                        WHERE user_id = %s AND generated_at = %s
                        ORDER BY created_at DESC LIMIT 1
                    """, (digest_data["user_id"], digest_data["generated_at"]))

                    result = await cur.fetchone()
                    if result:
                        logger.info(f"Successfully stored digest with ID {result[0]} for user {digest_data['user_id']}")
                        return True
                    else:
                        logger.error(f"Failed to verify digest storage for user {digest_data['user_id']}")
                        return False

        except Exception as e:
            logger.error(f"Failed to store digest for user {digest_data.get('user_id', 'unknown')}: {e}", exc_info=True)
            return False

    async def get_recent_digests(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Retrieve recent email digests for a user.

        Args:
            user_id: User ID to fetch digests for
            limit: Maximum number of digests to return

        Returns:
            List of digest dictionaries
        """
        try:
            if not isinstance(user_id, str) or not user_id:
                logger.error(f"Invalid user_id for digest retrieval: {user_id}")
                return []

            if not isinstance(limit, int) or limit <= 0:
                logger.warning(f"Invalid limit for digest retrieval: {limit}, using default 10")
                limit = 10

            db_manager = get_database_manager()

            async for conn in db_manager.get_connection():
                async with conn.cursor() as cur:
                    await cur.execute("""
                        SELECT id, user_id, generated_at, hours_back, include_read,
                               digest_content, status, context, email_count, created_at
                        FROM email_digests
                        WHERE user_id = %s
                        ORDER BY generated_at DESC
                        LIMIT %s
                    """, (user_id, limit))

                    rows = await cur.fetchall()

                    # Convert to dictionaries
                    columns = ["id", "user_id", "generated_at", "hours_back", "include_read",
                              "digest_content", "status", "context", "email_count", "created_at"]

                    digests = []
                    for row in rows:
                        digest = dict(zip(columns, row))
                        # Convert datetime objects to ISO strings for JSON serialization
                        if digest["generated_at"]:
                            digest["generated_at"] = digest["generated_at"].isoformat()
                        if digest["created_at"]:
                            digest["created_at"] = digest["created_at"].isoformat()
                        digests.append(digest)

                    logger.info(f"Retrieved {len(digests)} recent digests for user {user_id}")
                    return digests

        except Exception as e:
            logger.error(f"Failed to retrieve recent digests for user {user_id}: {e}", exc_info=True)
            return []

    async def get_digest_stats(self, user_id: str) -> Dict[str, Any]:
        """
        Get digest statistics for a user.

        Args:
            user_id: User ID to get stats for

        Returns:
            Dictionary with digest statistics
        """
        try:
            db_manager = get_database_manager()

            async for conn in db_manager.get_connection():
                async with conn.cursor() as cur:
                    await cur.execute("""
                        SELECT
                            COUNT(*) as total_digests,
                            COUNT(CASE WHEN status = 'success' THEN 1 END) as successful_digests,
                            COUNT(CASE WHEN status = 'error' THEN 1 END) as failed_digests,
                            MAX(generated_at) as last_digest_at,
                            AVG(email_count) as avg_email_count
                        FROM email_digests
                        WHERE user_id = %s
                    """, (user_id,))

                    row = await cur.fetchone()

                    if row:
                        stats = {
                            "total_digests": row[0] or 0,
                            "successful_digests": row[1] or 0,
                            "failed_digests": row[2] or 0,
                            "last_digest_at": row[3].isoformat() if row[3] else None,
                            "avg_email_count": float(row[4]) if row[4] else 0.0
                        }

                        logger.info(f"Retrieved digest stats for user {user_id}: {stats}")
                        return stats
                    else:
                        return {
                            "total_digests": 0,
                            "successful_digests": 0,
                            "failed_digests": 0,
                            "last_digest_at": None,
                            "avg_email_count": 0.0
                        }

        except Exception as e:
            logger.error(f"Failed to retrieve digest stats for user {user_id}: {e}", exc_info=True)
            return {}


# Global instance
_storage_service = None

def get_email_digest_storage_service() -> EmailDigestStorageService:
    """Get the global EmailDigestStorageService instance."""
    global _storage_service
    if _storage_service is None:
        _storage_service = EmailDigestStorageService()
    return _storage_service
