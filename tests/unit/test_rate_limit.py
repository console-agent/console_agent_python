"""Tests for the token bucket rate limiter."""

from console_agent.utils.rate_limit import RateLimiter


class TestRateLimiter:
    def test_allows_calls_within_limit(self):
        limiter = RateLimiter(10)
        for _ in range(10):
            assert limiter.try_consume() is True

    def test_blocks_when_exhausted(self):
        limiter = RateLimiter(2)
        assert limiter.try_consume() is True
        assert limiter.try_consume() is True
        assert limiter.try_consume() is False

    def test_remaining_count(self):
        limiter = RateLimiter(5)
        assert limiter.remaining() == 5
        limiter.try_consume()
        assert limiter.remaining() == 4

    def test_reset(self):
        limiter = RateLimiter(3)
        limiter.try_consume()
        limiter.try_consume()
        limiter.try_consume()
        assert limiter.try_consume() is False
        limiter.reset()
        assert limiter.try_consume() is True
        assert limiter.remaining() >= 2

    def test_single_call_limit(self):
        limiter = RateLimiter(1)
        assert limiter.try_consume() is True
        assert limiter.try_consume() is False
