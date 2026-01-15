"""Unit tests for resilience rate limiter module."""

from unittest.mock import patch

import pytest

from pg_mcp.resilience.rate_limiter import (
    ClientIdentifier,
    RateLimitBucket,
    RateLimitConfig,
    RateLimiter,
    RateLimitStrategy,
)


class TestRateLimitConfig:
    """Tests for RateLimitConfig."""

    def test_default_config(self) -> None:
        """Test default RateLimitConfig values."""
        config = RateLimitConfig()
        assert config.enabled is True
        assert config.requests_per_minute == 60
        assert config.requests_per_hour == 1000
        assert config.per_client_per_minute == 20
        assert config.client_identifier == ClientIdentifier.AUTO
        assert config.tokens_per_minute == 100000
        assert config.tokens_per_hour == 1000000
        assert config.strategy == RateLimitStrategy.REJECT
        assert config.max_queue_wait == 30.0
        assert config.include_headers is True

    def test_custom_config(self) -> None:
        """Test custom RateLimitConfig values."""
        config = RateLimitConfig(
            enabled=False,
            requests_per_minute=100,
            requests_per_hour=2000,
            per_client_per_minute=50,
            client_identifier=ClientIdentifier.IP,
            tokens_per_minute=200000,
            strategy=RateLimitStrategy.QUEUE,
        )
        assert config.enabled is False
        assert config.requests_per_minute == 100
        assert config.requests_per_hour == 2000
        assert config.per_client_per_minute == 50
        assert config.client_identifier == ClientIdentifier.IP
        assert config.tokens_per_minute == 200000
        assert config.strategy == RateLimitStrategy.QUEUE


class TestRateLimitBucket:
    """Tests for RateLimitBucket."""

    def test_initial_state(self) -> None:
        """Test initial bucket state."""
        bucket = RateLimitBucket()
        assert bucket.count == 0
        assert bucket.reset_at == 0.0

    def test_check_and_increment_first_request(self) -> None:
        """Test first request initializes bucket."""
        bucket = RateLimitBucket()
        with patch("time.time", return_value=1000.0):
            allowed, remaining, reset_at = bucket.check_and_increment(10, 60.0)
        assert allowed is True
        assert remaining == 9
        assert reset_at == 1060.0
        assert bucket.count == 1

    def test_check_and_increment_within_limit(self) -> None:
        """Test requests within limit are allowed."""
        bucket = RateLimitBucket()
        with patch("time.time", return_value=1000.0):
            for i in range(5):
                allowed, remaining, reset_at = bucket.check_and_increment(10, 60.0)
                assert allowed is True
                assert remaining == 10 - (i + 1)

    def test_check_and_increment_at_limit(self) -> None:
        """Test request at limit is rejected."""
        bucket = RateLimitBucket()
        with patch("time.time", return_value=1000.0):
            # Use up all quota
            for _ in range(10):
                bucket.check_and_increment(10, 60.0)
            # Next request should be rejected
            allowed, remaining, reset_at = bucket.check_and_increment(10, 60.0)
        assert allowed is False
        assert remaining == 0
        assert reset_at == 1060.0

    def test_bucket_reset_after_window(self) -> None:
        """Test bucket resets after window expires."""
        bucket = RateLimitBucket()

        # First window
        with patch("time.time", return_value=1000.0):
            for _ in range(10):
                bucket.check_and_increment(10, 60.0)
            # Now at limit
            allowed, _, _ = bucket.check_and_increment(10, 60.0)
            assert allowed is False

        # After window expires
        with patch("time.time", return_value=1061.0):
            allowed, remaining, reset_at = bucket.check_and_increment(10, 60.0)
        assert allowed is True
        assert remaining == 9
        assert reset_at == 1121.0
        assert bucket.count == 1


class TestRateLimiterConfig:
    """Tests for RateLimiter configuration."""

    def test_default_config(self) -> None:
        """Test RateLimiter with default config."""
        config = RateLimitConfig()
        limiter = RateLimiter(config)
        assert limiter.config.enabled is True
        assert limiter.config.requests_per_minute == 60

    def test_disabled_limiter(self) -> None:
        """Test disabled limiter always allows requests."""
        config = RateLimitConfig(enabled=False, requests_per_minute=1)
        limiter = RateLimiter(config)

        # Should allow many more requests than limit
        for _ in range(100):
            result = limiter.check_request()
            assert result.allowed is True
            assert result.limit == 1
            assert result.remaining == 1


class TestRateLimiterRequestLimits:
    """Tests for RateLimiter request limits."""

    @pytest.fixture
    def limiter(self) -> RateLimiter:
        """Create rate limiter with low limits for testing."""
        config = RateLimitConfig(
            enabled=True,
            requests_per_minute=5,
            requests_per_hour=20,
            per_client_per_minute=3,
        )
        return RateLimiter(config)

    def test_global_minute_limit(self) -> None:
        """Test global per-minute request limit."""
        # Use high per_client limit to test global limit specifically
        config = RateLimitConfig(
            enabled=True,
            requests_per_minute=5,
            requests_per_hour=100,
            per_client_per_minute=100,  # High to not interfere
        )
        limiter = RateLimiter(config)

        with patch("time.time", return_value=1000.0):
            # Use up minute limit
            for i in range(5):
                result = limiter.check_request()
                assert result.allowed is True
                assert result.remaining == 5 - (i + 1)

            # Next should be rejected
            result = limiter.check_request()
            assert result.allowed is False
            assert result.remaining == 0
            assert result.retry_after is not None
            assert result.retry_after > 0

    def test_global_hour_limit(self) -> None:
        """Test global per-hour request limit."""
        config = RateLimitConfig(
            enabled=True,
            requests_per_minute=100,  # High minute limit
            requests_per_hour=5,       # Low hour limit
            per_client_per_minute=100,
        )
        limiter = RateLimiter(config)

        with patch("time.time", return_value=1000.0):
            # Use up hour limit
            for _ in range(5):
                result = limiter.check_request()
                assert result.allowed is True

            # Next should be rejected by hour limit
            result = limiter.check_request()
            assert result.allowed is False
            assert result.limit == 5  # Hour limit

    def test_per_client_limit_by_ip(self) -> None:
        """Test per-client limit using IP identifier."""
        config = RateLimitConfig(
            enabled=True,
            requests_per_minute=100,
            requests_per_hour=1000,
            per_client_per_minute=3,
            client_identifier=ClientIdentifier.IP,
        )
        limiter = RateLimiter(config)

        with patch("time.time", return_value=1000.0):
            # Use up client limit for IP 192.168.1.1
            for _ in range(3):
                result = limiter.check_request(client_ip="192.168.1.1")
                assert result.allowed is True

            # Next from same IP should be rejected
            result = limiter.check_request(client_ip="192.168.1.1")
            assert result.allowed is False
            assert result.limit == 3

    def test_per_client_limit_by_session(self) -> None:
        """Test per-client limit using session identifier."""
        config = RateLimitConfig(
            enabled=True,
            requests_per_minute=100,
            requests_per_hour=1000,
            per_client_per_minute=3,
            client_identifier=ClientIdentifier.SESSION,
        )
        limiter = RateLimiter(config)

        with patch("time.time", return_value=1000.0):
            # Use up client limit for session_123
            for _ in range(3):
                result = limiter.check_request(session_id="session_123")
                assert result.allowed is True

            # Next from same session should be rejected
            result = limiter.check_request(session_id="session_123")
            assert result.allowed is False
            assert result.limit == 3

    def test_different_clients_independent(self) -> None:
        """Test that different clients have independent counters."""
        config = RateLimitConfig(
            enabled=True,
            requests_per_minute=100,
            requests_per_hour=1000,
            per_client_per_minute=2,
            client_identifier=ClientIdentifier.IP,
        )
        limiter = RateLimiter(config)

        with patch("time.time", return_value=1000.0):
            # Client A uses their limit
            for _ in range(2):
                result = limiter.check_request(client_ip="192.168.1.1")
                assert result.allowed is True
            result = limiter.check_request(client_ip="192.168.1.1")
            assert result.allowed is False

            # Client B should still be allowed
            result = limiter.check_request(client_ip="192.168.1.2")
            assert result.allowed is True
            result = limiter.check_request(client_ip="192.168.1.2")
            assert result.allowed is True
            result = limiter.check_request(client_ip="192.168.1.2")
            assert result.allowed is False


class TestRateLimiterTokenLimits:
    """Tests for RateLimiter token limits."""

    @pytest.fixture
    def limiter(self) -> RateLimiter:
        """Create rate limiter with token limits for testing."""
        config = RateLimitConfig(
            enabled=True,
            tokens_per_minute=1000,
            tokens_per_hour=10000,
        )
        return RateLimiter(config)

    def test_token_limit_minute(self, limiter: RateLimiter) -> None:
        """Test per-minute token limit."""
        with patch("time.time", return_value=1000.0):
            # Record tokens within limit
            result = limiter.record_tokens(500)
            assert result.allowed is True
            assert result.remaining == 500

            # Record more tokens to exceed limit
            result = limiter.record_tokens(600)
            assert result.allowed is False
            assert result.remaining == 0

    def test_record_tokens_updates_count(self, limiter: RateLimiter) -> None:
        """Test that recording tokens updates the count."""
        with patch("time.time", return_value=1000.0):
            result = limiter.record_tokens(200)
            assert result.remaining == 800

            result = limiter.record_tokens(300)
            assert result.remaining == 500

            status = limiter.get_status()
            assert status["token_minute_count"] == 500

    def test_token_limit_disabled(self) -> None:
        """Test token recording when limiter is disabled."""
        config = RateLimitConfig(enabled=False, tokens_per_minute=100)
        limiter = RateLimiter(config)

        # Should always return allowed with full remaining
        result = limiter.record_tokens(1000)
        assert result.allowed is True
        assert result.remaining == 100


class TestRateLimiterHelpers:
    """Tests for RateLimiter helper methods."""

    @pytest.fixture
    def limiter(self) -> RateLimiter:
        """Create rate limiter for testing."""
        config = RateLimitConfig(
            enabled=True,
            requests_per_minute=10,
            requests_per_hour=100,
            include_headers=True,
        )
        return RateLimiter(config)

    def test_get_headers(self, limiter: RateLimiter) -> None:
        """Test rate limit response headers."""
        with patch("time.time", return_value=1000.0):
            limiter.check_request()
            limiter.check_request()

            headers = limiter.get_headers()

        assert "X-RateLimit-Limit" in headers
        assert headers["X-RateLimit-Limit"] == "10"
        assert "X-RateLimit-Remaining" in headers
        assert headers["X-RateLimit-Remaining"] == "8"
        assert "X-RateLimit-Reset" in headers

    def test_get_headers_disabled(self) -> None:
        """Test headers when include_headers is False."""
        config = RateLimitConfig(include_headers=False)
        limiter = RateLimiter(config)

        headers = limiter.get_headers()
        assert headers == {}

    def test_cleanup_stale_buckets(self) -> None:
        """Test cleanup of stale client buckets."""
        config = RateLimitConfig(
            enabled=True,
            per_client_per_minute=3,
        )
        limiter = RateLimiter(config)

        # Create some client buckets
        with patch("time.time", return_value=1000.0):
            limiter.check_request(client_ip="192.168.1.1")
            limiter.check_request(client_ip="192.168.1.2")
            limiter.check_request(client_ip="192.168.1.3")

        assert len(limiter._client_buckets) == 3

        # Fast forward time and cleanup
        with patch("time.time", return_value=5000.0):  # Way past window
            cleaned = limiter.cleanup_stale_buckets(max_age=3600.0)

        assert cleaned == 3
        assert len(limiter._client_buckets) == 0

    def test_cleanup_stale_buckets_partial(self) -> None:
        """Test cleanup keeps recent buckets."""
        config = RateLimitConfig(
            enabled=True,
            per_client_per_minute=3,
        )
        limiter = RateLimiter(config)

        # Create old bucket
        with patch("time.time", return_value=1000.0):
            limiter.check_request(client_ip="192.168.1.1")

        # Create recent bucket
        with patch("time.time", return_value=5000.0):
            limiter.check_request(client_ip="192.168.1.2")

        # Cleanup with short max_age
        with patch("time.time", return_value=5100.0):
            cleaned = limiter.cleanup_stale_buckets(max_age=200.0)

        assert cleaned == 1
        assert len(limiter._client_buckets) == 1
        assert "ip:192.168.1.2" in limiter._client_buckets

    def test_get_status(self, limiter: RateLimiter) -> None:
        """Test status reporting."""
        with patch("time.time", return_value=1000.0):
            limiter.check_request(client_ip="192.168.1.1")
            limiter.check_request(client_ip="192.168.1.2")
            limiter.record_tokens(500)

        status = limiter.get_status()

        assert status["enabled"] is True
        assert status["global_minute_count"] == 2
        assert status["global_minute_remaining"] == 8
        assert status["global_hour_count"] == 2
        assert status["global_hour_remaining"] == 98
        assert status["token_minute_count"] == 500
        assert status["client_buckets_count"] == 2

    def test_reset(self, limiter: RateLimiter) -> None:
        """Test reset clears all counters."""
        with patch("time.time", return_value=1000.0):
            # Make some requests
            for _ in range(5):
                limiter.check_request(client_ip="192.168.1.1")
            limiter.record_tokens(500)

        assert limiter._global_minute_bucket.count == 5
        assert len(limiter._client_buckets) == 1

        # Reset
        limiter.reset()

        status = limiter.get_status()
        assert status["global_minute_count"] == 0
        assert status["global_hour_count"] == 0
        assert status["token_minute_count"] == 0
        assert status["token_hour_count"] == 0
        assert status["client_buckets_count"] == 0


class TestClientIdentifierLogic:
    """Tests for client identifier selection logic."""

    def test_auto_identifier_prefers_ip(self) -> None:
        """Test AUTO identifier prefers IP when available."""
        config = RateLimitConfig(
            enabled=True,
            client_identifier=ClientIdentifier.AUTO,
            per_client_per_minute=1,
        )
        limiter = RateLimiter(config)

        with patch("time.time", return_value=1000.0):
            # With both IP and session, should use IP
            limiter.check_request(client_ip="192.168.1.1", session_id="session_123")

        assert "ip:192.168.1.1" in limiter._client_buckets
        assert "session:session_123" not in limiter._client_buckets

    def test_auto_identifier_falls_back_to_session(self) -> None:
        """Test AUTO identifier falls back to session when IP not available."""
        config = RateLimitConfig(
            enabled=True,
            client_identifier=ClientIdentifier.AUTO,
            per_client_per_minute=1,
        )
        limiter = RateLimiter(config)

        with patch("time.time", return_value=1000.0):
            # Without IP, should use session
            limiter.check_request(session_id="session_123")

        assert "session:session_123" in limiter._client_buckets

    def test_ip_identifier_ignores_session(self) -> None:
        """Test IP identifier ignores session when set."""
        config = RateLimitConfig(
            enabled=True,
            client_identifier=ClientIdentifier.IP,
            per_client_per_minute=1,
        )
        limiter = RateLimiter(config)

        with patch("time.time", return_value=1000.0):
            limiter.check_request(client_ip="192.168.1.1", session_id="session_123")

        assert "ip:192.168.1.1" in limiter._client_buckets
        assert "session:session_123" not in limiter._client_buckets

    def test_session_identifier_ignores_ip(self) -> None:
        """Test SESSION identifier ignores IP when set."""
        config = RateLimitConfig(
            enabled=True,
            client_identifier=ClientIdentifier.SESSION,
            per_client_per_minute=1,
        )
        limiter = RateLimiter(config)

        with patch("time.time", return_value=1000.0):
            limiter.check_request(client_ip="192.168.1.1", session_id="session_123")

        assert "session:session_123" in limiter._client_buckets
        assert "ip:192.168.1.1" not in limiter._client_buckets

    def test_unknown_client_handling(self) -> None:
        """Test handling of unknown client identifiers."""
        config = RateLimitConfig(
            enabled=True,
            client_identifier=ClientIdentifier.IP,
            per_client_per_minute=1,
        )
        limiter = RateLimiter(config)

        with patch("time.time", return_value=1000.0):
            # No IP provided
            limiter.check_request()

        assert "ip:unknown" in limiter._client_buckets
