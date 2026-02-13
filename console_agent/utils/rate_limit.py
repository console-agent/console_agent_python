"""
Token bucket rate limiter.
Controls the rate of API calls to prevent abuse and stay within budget.
"""

from __future__ import annotations

import time


class RateLimiter:
    """Token bucket rate limiter for API calls."""

    def __init__(self, max_calls_per_day: int) -> None:
        self._max_tokens = max_calls_per_day
        self._tokens = float(max_calls_per_day)
        # Refill rate: spread calls evenly across 24 hours (tokens per second)
        self._refill_rate = max_calls_per_day / (24 * 60 * 60)
        self._last_refill = time.monotonic()

    def try_consume(self) -> bool:
        """Attempt to consume one token. Returns True if allowed."""
        self._refill()
        if self._tokens >= 1:
            self._tokens -= 1
            return True
        return False

    def remaining(self) -> int:
        """Get remaining tokens (calls available)."""
        self._refill()
        return int(self._tokens)

    def reset(self) -> None:
        """Reset the limiter (e.g., for testing)."""
        self._tokens = float(self._max_tokens)
        self._last_refill = time.monotonic()

    def _refill(self) -> None:
        now = time.monotonic()
        elapsed = now - self._last_refill
        new_tokens = elapsed * self._refill_rate
        self._tokens = min(self._max_tokens, self._tokens + new_tokens)
        self._last_refill = now
