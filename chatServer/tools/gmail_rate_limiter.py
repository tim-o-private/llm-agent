"""Per-user Gmail API rate limiter.

In-memory rate limiting keyed by (user_id, account_email).
Limits: 30/minute, 500/hour, 5000/day.
"""

import logging
import time
from dataclasses import dataclass, field
from typing import ClassVar, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

GMAIL_RATE_MINUTE = 30
GMAIL_RATE_HOUR = 500
GMAIL_RATE_DAY = 5000


@dataclass
class GmailRateLimitInfo:
    """Rate limit counters for a single (user_id, account) tuple."""
    minute_count: int = 0
    hour_count: int = 0
    day_count: int = 0
    minute_reset: float = field(default_factory=time.time)
    hour_reset: float = field(default_factory=time.time)
    day_reset: float = field(default_factory=time.time)


class GmailRateLimiter:
    """In-memory rate limiter for Gmail API calls.

    Singleton per process. Keyed by (user_id, account_email).
    """
    _limits: ClassVar[Dict[Tuple[str, str], GmailRateLimitInfo]] = {}

    @classmethod
    def check_and_increment(cls, user_id: str, account: str, call_count: int = 1) -> Optional[str]:
        """Check rate limits and increment counters.

        Args:
            user_id: User ID
            account: Gmail account email
            call_count: Number of API calls this operation will make

        Returns:
            None if OK, error message string if rate limited.
        """
        key = (user_id, account)
        now = time.time()

        if key not in cls._limits:
            cls._limits[key] = GmailRateLimitInfo()

        info = cls._limits[key]

        # Reset windows if expired
        if now - info.minute_reset >= 60:
            info.minute_count = 0
            info.minute_reset = now
        if now - info.hour_reset >= 3600:
            info.hour_count = 0
            info.hour_reset = now
        if now - info.day_reset >= 86400:
            info.day_count = 0
            info.day_reset = now

        # Check limits (check before incrementing)
        if info.minute_count + call_count > GMAIL_RATE_MINUTE:
            wait = int(60 - (now - info.minute_reset))
            return (
                f"Gmail rate limit reached ({info.minute_count}/{GMAIL_RATE_MINUTE} per minute). "
                f"Try again in {max(1, wait)} seconds."
            )

        if info.hour_count + call_count > GMAIL_RATE_HOUR:
            wait = int(3600 - (now - info.hour_reset)) // 60
            return (
                f"Gmail rate limit reached ({info.hour_count}/{GMAIL_RATE_HOUR} per hour). "
                f"Try again in {max(1, wait)} minutes."
            )

        if info.day_count + call_count > GMAIL_RATE_DAY:
            return (
                f"Gmail daily rate limit reached ({info.day_count}/{GMAIL_RATE_DAY} per day). "
                "Try again tomorrow."
            )

        # Warn at 80%
        if info.minute_count + call_count > GMAIL_RATE_MINUTE * 0.8:
            logger.warning(
                "Gmail rate limiter: %d/%d minute for %s/%s",
                info.minute_count + call_count, GMAIL_RATE_MINUTE, user_id, account,
            )
        if info.hour_count + call_count > GMAIL_RATE_HOUR * 0.8:
            logger.warning(
                "Gmail rate limiter: %d/%d hour for %s/%s",
                info.hour_count + call_count, GMAIL_RATE_HOUR, user_id, account,
            )

        # Increment
        info.minute_count += call_count
        info.hour_count += call_count
        info.day_count += call_count

        return None

    @classmethod
    def reset(cls):
        """Reset all limits. For testing."""
        cls._limits.clear()
