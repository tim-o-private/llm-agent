"""Job runner service — polling loop that dispatches jobs to registered handlers."""

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Callable

from .job_service import JobService

logger = logging.getLogger(__name__)

_POLL_INTERVAL_SECONDS = 5
_EXPIRY_CHECK_INTERVAL = timedelta(minutes=5)


class JobRunnerService:
    """Single polling loop that dispatches jobs to registered handlers."""

    def __init__(self, job_service: JobService):
        self._handlers: dict[str, Callable] = {}
        self._job_service = job_service
        self._last_expiry_check: datetime | None = None

    def register_handler(self, job_type: str, handler: Callable) -> None:
        """Register a handler function for a job type."""
        self._handlers[job_type] = handler

    async def run(self) -> None:
        """Main loop: poll every 5s, claim, dispatch. Cancel-safe.

        Calls expire_stale() every 5 minutes.
        """
        while True:
            try:
                await asyncio.sleep(_POLL_INTERVAL_SECONDS)

                now = datetime.now(timezone.utc)
                if (
                    self._last_expiry_check is None
                    or now - self._last_expiry_check >= _EXPIRY_CHECK_INTERVAL
                ):
                    try:
                        expired = await self._job_service.expire_stale()
                        if expired:
                            logger.info(f"Expired {expired} stale jobs")
                    except Exception as e:
                        logger.error(f"Error expiring stale jobs: {e}", exc_info=True)
                    self._last_expiry_check = now

                job = await self._job_service.claim_next(
                    job_types=list(self._handlers.keys()) if self._handlers else None
                )
                if job is not None:
                    asyncio.create_task(self._dispatch(job))

            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.error(f"Error in job runner loop: {e}", exc_info=True)

    async def _dispatch(self, job: dict) -> None:
        """Dispatch to handler. mark_running before, complete/fail after.

        No handler → fail with should_retry=False.
        Handler exception → fail with should_retry=True.
        """
        job_id = str(job["id"])
        job_type = job.get("job_type", "unknown")
        handler = self._handlers.get(job_type)

        if handler is None:
            logger.error(
                f"No handler registered for job type '{job_type}' (job {job_id})"
            )
            await self._job_service.fail(
                job_id, f"No handler for job type '{job_type}'", should_retry=False
            )
            return

        try:
            await self._job_service.mark_running(job_id)
            result = await handler(job)
            await self._job_service.complete(job_id, result or {})
        except Exception as e:
            logger.error(
                f"Handler for job type '{job_type}' failed (job {job_id}): {e}",
                exc_info=True,
            )
            await self._job_service.fail(job_id, str(e), should_retry=True)
