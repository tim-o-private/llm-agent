"""Email Digest Scheduler for automated daily email digest generation."""

import logging
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, time, timedelta
import json

try:
    from ..agents.email_digest_agent import create_email_digest_agent
    from ..services.vault_token_service import VaultTokenService
    from ..database.connection import get_db_connection
except ImportError:
    from chatServer.agents.email_digest_agent import create_email_digest_agent
    from chatServer.services.vault_token_service import VaultTokenService
    from chatServer.database.connection import get_db_connection

logger = logging.getLogger(__name__)


class EmailDigestScheduler:
    """Scheduler for automated email digest generation."""
    
    def __init__(self):
        """Initialize email digest scheduler."""
        self.default_digest_time = time(7, 30)  # 7:30 AM
        self.default_hours_back = 24
        self.default_include_read = False
    
    async def get_users_with_gmail_connections(self) -> List[Dict[str, Any]]:
        """Get all users who have active Gmail connections.
        
        Returns:
            List of user information with Gmail connections
        """
        users = []
        
        try:
            async for db_conn in get_db_connection():
                async with db_conn.cursor() as cur:
                    # Get users with active Gmail connections
                    await cur.execute("""
                        SELECT DISTINCT 
                            eac.user_id,
                            u.email as user_email,
                            eac.service_user_email,
                            eac.created_at,
                            eac.is_active
                        FROM external_api_connections eac
                        JOIN auth.users u ON eac.user_id = u.id
                        WHERE eac.service_name = 'gmail' 
                        AND eac.is_active = true
                        AND eac.token_expires_at > NOW()
                        ORDER BY eac.created_at DESC
                    """)
                    
                    results = await cur.fetchall()
                    
                    for result in results:
                        users.append({
                            'user_id': str(result[0]),
                            'user_email': result[1],
                            'gmail_email': result[2],
                            'connection_created': result[3],
                            'is_active': result[4]
                        })
                    
                    logger.info(f"Found {len(users)} users with active Gmail connections")
                    return users
                    
        except Exception as e:
            logger.error(f"Failed to get users with Gmail connections: {e}")
            return []
    
    async def generate_digest_for_user(self, user_id: str, hours_back: int = None, 
                                     include_read: bool = None) -> Dict[str, Any]:
        """Generate email digest for a specific user.
        
        Args:
            user_id: User ID
            hours_back: Hours to look back (defaults to 24)
            include_read: Whether to include read emails (defaults to False)
            
        Returns:
            Digest generation result
        """
        hours_back = hours_back or self.default_hours_back
        include_read = include_read if include_read is not None else self.default_include_read
        
        try:
            logger.info(f"Generating email digest for user {user_id}")
            
            # Create email digest agent for the user
            agent = await create_email_digest_agent(user_id)
            
            # Generate the digest using the existing agent framework
            digest_content = await agent.generate_digest(
                hours_back=hours_back,
                include_read=include_read
            )
            
            # Create result structure
            digest_result = {
                "user_id": user_id,
                "generated_at": datetime.now().isoformat(),
                "hours_back": hours_back,
                "include_read": include_read,
                "digest": digest_content,
                "status": "success"
            }
            
            # Store the digest result in database
            await self._store_digest_result(digest_result)
            
            logger.info(f"Successfully generated digest for user {user_id}")
            return digest_result
            
        except Exception as e:
            logger.error(f"Failed to generate digest for user {user_id}: {e}")
            return {
                "user_id": user_id,
                "generated_at": datetime.now().isoformat(),
                "hours_back": hours_back,
                "include_read": include_read,
                "digest": f"Error: {str(e)}",
                "status": "error"
            }
    
    async def _store_digest_result(self, digest_result: Dict[str, Any]):
        """Store digest result in database.
        
        Args:
            digest_result: Digest generation result
        """
        try:
            async for db_conn in get_db_connection():
                async with db_conn.cursor() as cur:
                    # Store in email_digests table (create if needed)
                    await cur.execute("""
                        INSERT INTO email_digests 
                        (user_id, generated_at, hours_back, include_read, digest_content, status)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        ON CONFLICT (user_id, generated_at) DO UPDATE SET
                        digest_content = EXCLUDED.digest_content,
                        status = EXCLUDED.status
                    """, (
                        digest_result['user_id'],
                        digest_result['generated_at'],
                        digest_result['hours_back'],
                        digest_result['include_read'],
                        digest_result['digest'],
                        digest_result['status']
                    ))
                    await db_conn.commit()
                    
        except Exception as e:
            # Don't fail the main operation if storage fails
            logger.warning(f"Failed to store digest result: {e}")
    
    async def run_daily_digest_batch(self, max_concurrent: int = 5) -> Dict[str, Any]:
        """Run daily digest generation for all users with Gmail connections.
        
        Args:
            max_concurrent: Maximum number of concurrent digest generations
            
        Returns:
            Batch execution summary
        """
        start_time = datetime.now()
        logger.info("Starting daily email digest batch generation")
        
        # Get all users with Gmail connections
        users = await self.get_users_with_gmail_connections()
        
        if not users:
            logger.info("No users with Gmail connections found")
            return {
                "start_time": start_time.isoformat(),
                "end_time": datetime.now().isoformat(),
                "total_users": 0,
                "successful": 0,
                "failed": 0,
                "results": []
            }
        
        # Create semaphore to limit concurrent operations
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def generate_with_semaphore(user_info: Dict[str, Any]) -> Dict[str, Any]:
            async with semaphore:
                return await self.generate_digest_for_user(user_info['user_id'])
        
        # Execute digest generation for all users
        tasks = [generate_with_semaphore(user) for user in users]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        successful = 0
        failed = 0
        processed_results = []
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                failed += 1
                processed_results.append({
                    "user_id": users[i]['user_id'],
                    "status": "error",
                    "error": str(result)
                })
            elif result.get('status') == 'success':
                successful += 1
                processed_results.append(result)
            else:
                failed += 1
                processed_results.append(result)
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        summary = {
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "duration_seconds": duration,
            "total_users": len(users),
            "successful": successful,
            "failed": failed,
            "results": processed_results
        }
        
        logger.info(f"Daily digest batch completed: {successful}/{len(users)} successful in {duration:.2f}s")
        
        # Store batch summary
        await self._store_batch_summary(summary)
        
        return summary
    
    async def _store_batch_summary(self, summary: Dict[str, Any]):
        """Store batch execution summary in database.
        
        Args:
            summary: Batch execution summary
        """
        try:
            async for db_conn in get_db_connection():
                async with db_conn.cursor() as cur:
                    await cur.execute("""
                        INSERT INTO email_digest_batches 
                        (start_time, end_time, duration_seconds, total_users, successful, failed, summary)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """, (
                        summary['start_time'],
                        summary['end_time'],
                        summary['duration_seconds'],
                        summary['total_users'],
                        summary['successful'],
                        summary['failed'],
                        json.dumps(summary, default=str)
                    ))
                    await db_conn.commit()
                    
        except Exception as e:
            logger.warning(f"Failed to store batch summary: {e}")
    
    async def get_user_digest_history(self, user_id: str, days_back: int = 7) -> List[Dict[str, Any]]:
        """Get digest history for a user.
        
        Args:
            user_id: User ID
            days_back: Number of days to look back
            
        Returns:
            List of digest records
        """
        try:
            async for db_conn in get_db_connection():
                async with db_conn.cursor() as cur:
                    await cur.execute("""
                        SELECT generated_at, hours_back, include_read, status, 
                               LENGTH(digest_content) as digest_length
                        FROM email_digests
                        WHERE user_id = %s 
                        AND generated_at >= %s
                        ORDER BY generated_at DESC
                    """, (
                        user_id,
                        datetime.now() - timedelta(days=days_back)
                    ))
                    
                    results = await cur.fetchall()
                    
                    return [
                        {
                            'generated_at': result[0].isoformat(),
                            'hours_back': result[1],
                            'include_read': result[2],
                            'status': result[3],
                            'digest_length': result[4]
                        }
                        for result in results
                    ]
                    
        except Exception as e:
            logger.error(f"Failed to get digest history for user {user_id}: {e}")
            return []


# Global scheduler instance
email_digest_scheduler = EmailDigestScheduler()


async def run_daily_digest_batch() -> Dict[str, Any]:
    """Convenience function to run daily digest batch.
    
    Returns:
        Batch execution summary
    """
    return await email_digest_scheduler.run_daily_digest_batch()


async def generate_digest_for_user(user_id: str) -> Dict[str, Any]:
    """Convenience function to generate digest for a specific user.
    
    Args:
        user_id: User ID
        
    Returns:
        Digest generation result
    """
    return await email_digest_scheduler.generate_digest_for_user(user_id) 