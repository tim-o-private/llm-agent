"""Universal job queue service — CRUD and lifecycle operations."""

import json
import logging
from datetime import timedelta

logger = logging.getLogger(__name__)


class JobService:
    """Universal job queue operations. Uses psycopg pool directly (A3)."""

    def __init__(self, db_pool):
        self.pool = db_pool

    async def create(
        self,
        job_type: str,
        input: dict,
        user_id: str,
        priority: int = 0,
        max_retries: int = 3,
        scheduled_for=None,
        expires_at=None,
    ) -> str:
        """Insert a pending job. Returns job ID (UUID string)."""
        async with self.pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    INSERT INTO jobs (user_id, job_type, input, priority, max_retries,
                                     scheduled_for, expires_at)
                    VALUES (%s, %s, %s, %s, %s,
                            COALESCE(%s, NOW()), %s)
                    RETURNING id
                    """,
                    (
                        user_id,
                        job_type,
                        json.dumps(input),
                        priority,
                        max_retries,
                        scheduled_for,
                        expires_at,
                    ),
                )
                row = await cur.fetchone()
                return str(row[0])

    async def claim_next(self, job_types: list[str] | None = None) -> dict | None:
        """Atomically claim the next eligible job via SELECT FOR UPDATE SKIP LOCKED.

        Both the SELECT and UPDATE run in the same transaction.
        """
        async with self.pool.connection() as conn:
            async with conn.cursor() as cur:
                if job_types is not None:
                    await cur.execute(
                        """
                        SELECT id, user_id, job_type, status, input, priority,
                               retry_count, max_retries, scheduled_for, expires_at, created_at
                        FROM jobs
                        WHERE status = 'pending'
                          AND scheduled_for <= NOW()
                          AND (expires_at IS NULL OR expires_at > NOW())
                          AND job_type = ANY(%s)
                        ORDER BY priority DESC, scheduled_for ASC
                        LIMIT 1
                        FOR UPDATE SKIP LOCKED
                        """,
                        (job_types,),
                    )
                else:
                    await cur.execute(
                        """
                        SELECT id, user_id, job_type, status, input, priority,
                               retry_count, max_retries, scheduled_for, expires_at, created_at
                        FROM jobs
                        WHERE status = 'pending'
                          AND scheduled_for <= NOW()
                          AND (expires_at IS NULL OR expires_at > NOW())
                        ORDER BY priority DESC, scheduled_for ASC
                        LIMIT 1
                        FOR UPDATE SKIP LOCKED
                        """
                    )

                row = await cur.fetchone()
                if row is None:
                    return None

                job_id = row[0]

                await cur.execute(
                    """
                    UPDATE jobs
                    SET status = 'claimed', claimed_at = NOW(), updated_at = NOW()
                    WHERE id = %s
                    RETURNING id, user_id, job_type, status, input, priority, retry_count,
                              max_retries, scheduled_for, expires_at, created_at,
                              claimed_at, updated_at
                    """,
                    (job_id,),
                )
                updated_row = await cur.fetchone()
                if updated_row is None:
                    return None

                columns = [desc[0] for desc in cur.description]
                return dict(zip(columns, updated_row))

    async def mark_running(self, job_id: str) -> None:
        """Transition claimed -> running, set started_at=NOW()."""
        async with self.pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    UPDATE jobs
                    SET status = 'running', started_at = NOW(), updated_at = NOW()
                    WHERE id = %s
                    """,
                    (job_id,),
                )

    async def complete(self, job_id: str, output: dict) -> None:
        """Transition running -> complete, set output JSONB and completed_at=NOW()."""
        async with self.pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    """
                    UPDATE jobs
                    SET status = 'complete', output = %s, completed_at = NOW(),
                        updated_at = NOW()
                    WHERE id = %s
                    """,
                    (json.dumps(output), job_id),
                )

    async def fail(self, job_id: str, error: str, should_retry: bool = True) -> None:
        """Fail a job. If should_retry and retry_count < max_retries, requeue with backoff.

        Backoff formula: min(30 * 2^retry_count, 900) seconds (based on current retry_count).
        """
        async with self.pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "SELECT retry_count, max_retries FROM jobs WHERE id = %s",
                    (job_id,),
                )
                row = await cur.fetchone()
                if row is None:
                    logger.error(f"Job {job_id} not found in fail()")
                    return

                retry_count, max_retries = row

                if should_retry and retry_count < max_retries:
                    backoff_seconds = min(30 * (2 ** retry_count), 900)
                    backoff = timedelta(seconds=backoff_seconds)
                    await cur.execute(
                        """
                        UPDATE jobs
                        SET status = 'pending',
                            retry_count = retry_count + 1,
                            scheduled_for = NOW() + %s,
                            error = %s,
                            updated_at = NOW()
                        WHERE id = %s
                        """,
                        (backoff, error, job_id),
                    )
                else:
                    await cur.execute(
                        """
                        UPDATE jobs
                        SET status = 'failed',
                            error = %s,
                            completed_at = NOW(),
                            updated_at = NOW()
                        WHERE id = %s
                        """,
                        (error, job_id),
                    )

    async def expire_stale(self) -> int:
        """Call expire_stale_jobs() DB function, return count."""
        async with self.pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT expire_stale_jobs()")
                row = await cur.fetchone()
                return row[0] if row else 0
