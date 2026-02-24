"""Tests for Gmail rate limiter."""

import logging
import pytest

from chatServer.tools.gmail_rate_limiter import (
    GmailRateLimiter,
    GmailRateLimitInfo,
    GMAIL_RATE_MINUTE,
    GMAIL_RATE_HOUR,
    GMAIL_RATE_DAY,
)


@pytest.fixture(autouse=True)
def reset_limiter():
    """Reset rate limiter state before each test."""
    GmailRateLimiter.reset()
    yield
    GmailRateLimiter.reset()


class TestGmailRateLimiter:

    def test_allows_under_limit(self):
        """Calls under threshold return None."""
        result = GmailRateLimiter.check_and_increment("user-1", "a@example.com", 1)
        assert result is None

    def test_blocks_after_minute_threshold(self):
        """AC-04: Hit 30/min, verify returns error message string."""
        for _ in range(GMAIL_RATE_MINUTE):
            result = GmailRateLimiter.check_and_increment("user-1", "a@example.com", 1)
            assert result is None

        result = GmailRateLimiter.check_and_increment("user-1", "a@example.com", 1)
        assert result is not None
        assert "rate limit" in result.lower()
        assert "per minute" in result

    def test_keyed_per_user_account(self):
        """AC-05: Different (user, account) tuples have independent limits."""
        for _ in range(GMAIL_RATE_MINUTE):
            GmailRateLimiter.check_and_increment("user-1", "a@example.com", 1)

        # user-1/a@example.com is at limit
        assert GmailRateLimiter.check_and_increment("user-1", "a@example.com", 1) is not None

        # user-1/b@example.com should still work
        assert GmailRateLimiter.check_and_increment("user-1", "b@example.com", 1) is None

        # user-2/a@example.com should still work
        assert GmailRateLimiter.check_and_increment("user-2", "a@example.com", 1) is None

    def test_returns_message_not_exception(self):
        """AC-06: Verify return type is str, not raised exception."""
        for _ in range(GMAIL_RATE_MINUTE):
            GmailRateLimiter.check_and_increment("user-1", "a@example.com", 1)

        result = GmailRateLimiter.check_and_increment("user-1", "a@example.com", 1)
        assert isinstance(result, str)
        # Should NOT raise — just returns a string

    def test_warns_at_80_percent(self, caplog):
        """AC-07: WARN logged when >80% consumed."""
        threshold = int(GMAIL_RATE_MINUTE * 0.8)

        with caplog.at_level(logging.WARNING, logger="chatServer.tools.gmail_rate_limiter"):
            for _ in range(threshold + 1):
                GmailRateLimiter.check_and_increment("user-1", "a@example.com", 1)

        warning_messages = [r.message for r in caplog.records if r.levelno == logging.WARNING]
        assert any("rate limiter" in msg.lower() for msg in warning_messages)

    def test_resets_after_window(self):
        """Verify counter resets after 60s."""
        for _ in range(GMAIL_RATE_MINUTE):
            GmailRateLimiter.check_and_increment("user-1", "a@example.com", 1)

        # At limit
        assert GmailRateLimiter.check_and_increment("user-1", "a@example.com", 1) is not None

        # Simulate time passing
        info = GmailRateLimiter._limits[("user-1", "a@example.com")]
        info.minute_reset -= 61  # 61 seconds ago

        # Should work again (minute window expired)
        result = GmailRateLimiter.check_and_increment("user-1", "a@example.com", 1)
        assert result is None

    def test_reset_method(self):
        """Verify reset() clears all state."""
        GmailRateLimiter.check_and_increment("user-1", "a@example.com", 1)
        assert len(GmailRateLimiter._limits) > 0

        GmailRateLimiter.reset()
        assert len(GmailRateLimiter._limits) == 0

    def test_call_count_parameter(self):
        """Verify call_count increments by the right amount."""
        # Use up most of the budget in one call
        result = GmailRateLimiter.check_and_increment("user-1", "a@example.com", GMAIL_RATE_MINUTE - 1)
        assert result is None

        # One more should work
        result = GmailRateLimiter.check_and_increment("user-1", "a@example.com", 1)
        assert result is None

        # One more should fail
        result = GmailRateLimiter.check_and_increment("user-1", "a@example.com", 1)
        assert result is not None
