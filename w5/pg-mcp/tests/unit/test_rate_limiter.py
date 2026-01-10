"""Unit tests for rate limiter."""

from unittest.mock import patch

import pytest

from pg_mcp.config.models import RateLimitConfig
from pg_mcp.infrastructure.rate_limiter import (
    RateLimiter,
    SlidingWindowCounter,
    TokenBucket,
)
from pg_mcp.models.errors import RateLimitExceededError


class TestTokenBucket:
    """Tests for TokenBucket."""

    def test_initial_capacity(self) -> None:
        """Test initial token capacity."""
        bucket = TokenBucket(capacity=100, refill_rate=10.0)
        assert bucket.available() == 100

    def test_consume_tokens(self) -> None:
        """Test consuming tokens."""
        bucket = TokenBucket(capacity=100, refill_rate=10.0)
        assert bucket.consume(50)
        assert bucket.available() == 50

    def test_consume_too_many(self) -> None:
        """Test consuming more than available."""
        bucket = TokenBucket(capacity=100, refill_rate=10.0)
        bucket.consume(100)
        assert not bucket.consume(1)

    def test_refill(self) -> None:
        """Test token refill over time."""
        bucket = TokenBucket(capacity=100, refill_rate=100.0)  # 100 tokens/sec
        bucket.consume(100)

        # Mock time passing
        with patch("time.time") as mock_time:
            mock_time.return_value = bucket.last_refill + 0.5  # 0.5 seconds later
            assert bucket.available() == 50  # 50 tokens refilled


class TestSlidingWindowCounter:
    """Tests for SlidingWindowCounter."""

    def test_increment_within_limit(self) -> None:
        """Test incrementing within limit."""
        counter = SlidingWindowCounter(window_seconds=60, max_count=10)
        for _ in range(10):
            assert counter.increment()
        assert not counter.increment()  # 11th should fail

    def test_count(self) -> None:
        """Test current count."""
        counter = SlidingWindowCounter(window_seconds=60, max_count=10)
        counter.increment()
        counter.increment()
        assert counter.count() == 2

    def test_remaining(self) -> None:
        """Test remaining quota."""
        counter = SlidingWindowCounter(window_seconds=60, max_count=10)
        counter.increment()
        counter.increment()
        assert counter.remaining() == 8

    def test_cleanup_old_entries(self) -> None:
        """Test cleanup of old entries."""
        counter = SlidingWindowCounter(window_seconds=60, max_count=10)

        # Add some entries
        with patch("time.time") as mock_time:
            mock_time.return_value = 1000.0
            counter.increment()
            counter.increment()

        # Fast forward past window
        with patch("time.time") as mock_time:
            mock_time.return_value = 1061.0  # 61 seconds later
            assert counter.count() == 0  # All cleaned up


class TestRateLimiter:
    """Tests for RateLimiter."""

    @pytest.fixture
    def limiter(self) -> RateLimiter:
        """Create rate limiter with low limits for testing."""
        config = RateLimitConfig(
            enabled=True,
            requests_per_minute=5,
            requests_per_hour=20,
            openai_tokens_per_minute=1000,
        )
        return RateLimiter(config)

    @pytest.mark.asyncio
    async def test_check_request_within_limit(self, limiter: RateLimiter) -> None:
        """Test request check within limit."""
        await limiter.check_request()  # Should not raise

    @pytest.mark.asyncio
    async def test_check_request_exceeds_minute_limit(self, limiter: RateLimiter) -> None:
        """Test request exceeds per-minute limit."""
        # Use up the limit
        for _ in range(5):
            await limiter.check_request()

        # Next should fail
        with pytest.raises(RateLimitExceededError) as exc_info:
            await limiter.check_request()
        assert exc_info.value.details["window"] == "minute"

    @pytest.mark.asyncio
    async def test_check_tokens_within_limit(self, limiter: RateLimiter) -> None:
        """Test token check within limit."""
        await limiter.check_tokens(500)  # Should not raise

    @pytest.mark.asyncio
    async def test_check_tokens_exceeds_limit(self, limiter: RateLimiter) -> None:
        """Test token check exceeds limit."""
        await limiter.check_tokens(1000)  # Use up tokens

        with pytest.raises(RateLimitExceededError) as exc_info:
            await limiter.check_tokens(100)
        assert exc_info.value.details["limit_type"] == "tokens"

    @pytest.mark.asyncio
    async def test_disabled_limiter(self) -> None:
        """Test that disabled limiter allows all requests."""
        config = RateLimitConfig(enabled=False, requests_per_minute=1)
        limiter = RateLimiter(config)

        # Should allow more than limit
        for _ in range(10):
            await limiter.check_request()

    def test_get_status(self, limiter: RateLimiter) -> None:
        """Test getting status."""
        status = limiter.get_status()
        assert "enabled" in status
        assert "requests_per_minute_remaining" in status
        assert status["requests_per_minute_remaining"] == 5

    def test_reset(self, limiter: RateLimiter) -> None:
        """Test resetting limiter."""
        # Use some quota
        limiter._minute_counter.increment()
        limiter._minute_counter.increment()

        limiter.reset()

        status = limiter.get_status()
        assert status["requests_per_minute_remaining"] == 5
