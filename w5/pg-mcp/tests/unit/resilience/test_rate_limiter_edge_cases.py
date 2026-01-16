"""Edge case tests for rate limiter.

Tests cover:
- Concurrent requests
- Window boundary reset
- Token limit exact boundary
- Client isolation
- Stale bucket cleanup
"""

import asyncio
import time
from unittest.mock import patch

import pytest

from pg_mcp.resilience.rate_limiter import (
    ClientIdentifier,
    RateLimitBucket,
    RateLimitConfig,
    RateLimiter,
    RateLimitStrategy,
)


# ============================================================================
# Concurrent Requests Tests
# ============================================================================


class TestConcurrentRequests:
    """Tests for concurrent request handling."""

    @pytest.mark.asyncio
    async def test_concurrent_requests_same_client(self) -> None:
        """Test concurrent requests from same client."""
        config = RateLimitConfig(
            enabled=True,
            requests_per_minute=100,
            requests_per_hour=1000,
            per_client_per_minute=10,
        )
        limiter = RateLimiter(config)

        # Simulate concurrent requests
        with patch("time.time", return_value=1000.0):
            async def make_request() -> bool:
                result = limiter.check_request(client_ip="192.168.1.1")
                return result.allowed

            # Send 20 concurrent requests from same client
            # Only 10 should succeed due to per_client limit
            tasks = [make_request() for _ in range(20)]
            results = await asyncio.gather(*tasks)

            # Due to potential race conditions in the bucket implementation,
            # results may vary slightly
            allowed_count = sum(results)
            assert allowed_count == 10, f"Expected 10, got {allowed_count}"

    @pytest.mark.asyncio
    async def test_concurrent_requests_different_clients(self) -> None:
        """Test concurrent requests from different clients."""
        config = RateLimitConfig(
            enabled=True,
            requests_per_minute=10,  # Low global limit
            requests_per_hour=100,
            per_client_per_minute=5,
        )
        limiter = RateLimiter(config)

        with patch("time.time", return_value=1000.0):
            async def make_request(client_id: int) -> bool:
                result = limiter.check_request(client_ip=f"192.168.1.{client_id}")
                return result.allowed

            # Send requests from 10 different clients
            tasks = [make_request(i) for i in range(10)]
            results = await asyncio.gather(*tasks)

            # Global limit is 10, so all 10 should succeed
            allowed_count = sum(results)
            assert allowed_count == 10

    @pytest.mark.asyncio
    async def test_concurrent_requests_exceed_global_limit(self) -> None:
        """Test that global limit is respected with concurrent requests."""
        config = RateLimitConfig(
            enabled=True,
            requests_per_minute=5,
            requests_per_hour=100,
            per_client_per_minute=100,  # High client limit
        )
        limiter = RateLimiter(config)

        with patch("time.time", return_value=1000.0):
            async def make_request(client_id: int) -> bool:
                result = limiter.check_request(client_ip=f"192.168.1.{client_id}")
                return result.allowed

            # Send 20 requests from different clients
            tasks = [make_request(i) for i in range(20)]
            results = await asyncio.gather(*tasks)

            # Only 5 should succeed due to global limit
            allowed_count = sum(results)
            assert allowed_count == 5


# ============================================================================
# Window Boundary Reset Tests
# ============================================================================


class TestWindowBoundaryReset:
    """Tests for rate limit reset at window boundaries."""

    def test_minute_window_boundary_reset(self) -> None:
        """Test rate limit resets at minute window boundary."""
        config = RateLimitConfig(
            enabled=True,
            requests_per_minute=5,
            requests_per_hour=1000,
            per_client_per_minute=100,
        )
        limiter = RateLimiter(config)

        # Use up the minute quota
        with patch("time.time", return_value=1000.0):
            for _ in range(5):
                result = limiter.check_request()
                assert result.allowed is True

            # 6th request should be rejected
            result = limiter.check_request()
            assert result.allowed is False

        # After window expires (60 seconds), should reset
        with patch("time.time", return_value=1061.0):  # 61 seconds later
            result = limiter.check_request()
            assert result.allowed is True
            assert result.remaining == 4  # 5 - 1 = 4

    def test_hour_window_boundary_reset(self) -> None:
        """Test rate limit resets at hour window boundary."""
        config = RateLimitConfig(
            enabled=True,
            requests_per_minute=100,  # High minute limit
            requests_per_hour=5,      # Low hour limit
            per_client_per_minute=100,
        )
        limiter = RateLimiter(config)

        # Use up the hour quota
        with patch("time.time", return_value=1000.0):
            for _ in range(5):
                result = limiter.check_request()
                assert result.allowed is True

            result = limiter.check_request()
            assert result.allowed is False

        # After hour expires
        with patch("time.time", return_value=4601.0):  # 3601 seconds later
            result = limiter.check_request()
            assert result.allowed is True

    def test_client_window_boundary_reset(self) -> None:
        """Test per-client rate limit resets at window boundary."""
        config = RateLimitConfig(
            enabled=True,
            requests_per_minute=100,
            requests_per_hour=1000,
            per_client_per_minute=3,
        )
        limiter = RateLimiter(config)

        # Use up client quota
        with patch("time.time", return_value=1000.0):
            for _ in range(3):
                result = limiter.check_request(client_ip="192.168.1.1")
                assert result.allowed is True

            result = limiter.check_request(client_ip="192.168.1.1")
            assert result.allowed is False

        # After client window resets
        with patch("time.time", return_value=1061.0):
            result = limiter.check_request(client_ip="192.168.1.1")
            assert result.allowed is True

    def test_reset_method(self) -> None:
        """Test explicit reset clears all counters."""
        config = RateLimitConfig(
            enabled=True,
            requests_per_minute=5,
        )
        limiter = RateLimiter(config)

        with patch("time.time", return_value=1000.0):
            # Use up quota
            for _ in range(5):
                limiter.check_request()

            result = limiter.check_request()
            assert result.allowed is False

            # Reset
            limiter.reset()

            # Should be allowed again
            result = limiter.check_request()
            assert result.allowed is True


# ============================================================================
# Token Limit Exact Boundary Tests
# ============================================================================


class TestTokenLimitExactBoundary:
    """Tests for token limit at exact boundaries."""

    def test_token_limit_exactly_at_boundary(self) -> None:
        """Test token limit at exact boundary."""
        config = RateLimitConfig(
            enabled=True,
            requests_per_minute=100,
            tokens_per_minute=1000,
            tokens_per_hour=10000,
        )
        limiter = RateLimiter(config)

        with patch("time.time", return_value=1000.0):
            # Record exactly 1000 tokens
            result = limiter.record_tokens(1000)

            # At boundary, remaining should be 0
            assert result.remaining == 0
            # But allowed should still be True since we haven't exceeded
            # Actually, the check is >=, so at exactly the limit,
            # the next request that checks tokens would be blocked

    def test_token_limit_one_over_boundary(self) -> None:
        """Test token limit one over boundary."""
        config = RateLimitConfig(
            enabled=True,
            requests_per_minute=100,
            tokens_per_minute=1000,
        )
        limiter = RateLimiter(config)

        with patch("time.time", return_value=1000.0):
            # Record 1001 tokens (over limit)
            result = limiter.record_tokens(1001)
            assert result.remaining == 0
            assert result.allowed is False

    def test_token_limit_one_under_boundary(self) -> None:
        """Test token limit one under boundary."""
        config = RateLimitConfig(
            enabled=True,
            requests_per_minute=100,
            tokens_per_minute=1000,
        )
        limiter = RateLimiter(config)

        with patch("time.time", return_value=1000.0):
            # Record 999 tokens
            result = limiter.record_tokens(999)
            assert result.remaining == 1
            assert result.allowed is True

    def test_token_accumulation(self) -> None:
        """Test token accumulation over multiple recordings."""
        config = RateLimitConfig(
            enabled=True,
            requests_per_minute=100,
            tokens_per_minute=1000,
        )
        limiter = RateLimiter(config)

        with patch("time.time", return_value=1000.0):
            # Record tokens in chunks
            limiter.record_tokens(300)
            limiter.record_tokens(300)
            limiter.record_tokens(300)

            status = limiter.get_status()
            assert status["token_minute_count"] == 900
            assert status["token_minute_remaining"] == 100

            # One more should still be allowed
            result = limiter.record_tokens(99)
            assert result.allowed is True
            assert result.remaining == 1

            # Next one puts us at limit
            result = limiter.record_tokens(2)
            assert result.allowed is False
            assert result.remaining == 0

    def test_token_limit_window_reset(self) -> None:
        """Test token limit resets with new window."""
        config = RateLimitConfig(
            enabled=True,
            requests_per_minute=100,
            tokens_per_minute=1000,
        )
        limiter = RateLimiter(config)

        # Exceed limit
        with patch("time.time", return_value=1000.0):
            limiter.record_tokens(1500)
            result = limiter.record_tokens(0)
            assert result.allowed is False

        # After window resets
        with patch("time.time", return_value=1061.0):
            result = limiter.record_tokens(100)
            assert result.allowed is True
            assert result.remaining == 900


# ============================================================================
# Client Isolation Tests
# ============================================================================


class TestClientIsolation:
    """Tests for client isolation."""

    def test_different_clients_have_separate_buckets(self) -> None:
        """Test that different clients have separate rate limit buckets."""
        config = RateLimitConfig(
            enabled=True,
            requests_per_minute=100,
            requests_per_hour=1000,
            per_client_per_minute=5,
        )
        limiter = RateLimiter(config)

        with patch("time.time", return_value=1000.0):
            # Client A uses all their quota
            for _ in range(5):
                result = limiter.check_request(client_ip="192.168.1.1")
                assert result.allowed is True

            result = limiter.check_request(client_ip="192.168.1.1")
            assert result.allowed is False

            # Client B should be unaffected
            for _ in range(5):
                result = limiter.check_request(client_ip="192.168.1.2")
                assert result.allowed is True

            result = limiter.check_request(client_ip="192.168.1.2")
            assert result.allowed is False

    def test_client_isolation_with_session_id(self) -> None:
        """Test client isolation using session ID."""
        config = RateLimitConfig(
            enabled=True,
            requests_per_minute=100,
            per_client_per_minute=3,
            client_identifier=ClientIdentifier.SESSION,
        )
        limiter = RateLimiter(config)

        with patch("time.time", return_value=1000.0):
            # Session A uses their quota
            for _ in range(3):
                result = limiter.check_request(session_id="session_A")
                assert result.allowed is True

            result = limiter.check_request(session_id="session_A")
            assert result.allowed is False

            # Session B should be unaffected
            result = limiter.check_request(session_id="session_B")
            assert result.allowed is True

    def test_many_clients_isolation(self) -> None:
        """Test isolation with many clients."""
        config = RateLimitConfig(
            enabled=True,
            requests_per_minute=1000,  # High global limit
            requests_per_hour=10000,
            per_client_per_minute=2,
        )
        limiter = RateLimiter(config)

        with patch("time.time", return_value=1000.0):
            # 100 different clients, each makes 2 requests
            for client_id in range(100):
                # First request
                result = limiter.check_request(client_ip=f"10.0.0.{client_id}")
                assert result.allowed is True

                # Second request
                result = limiter.check_request(client_ip=f"10.0.0.{client_id}")
                assert result.allowed is True

                # Third request should fail
                result = limiter.check_request(client_ip=f"10.0.0.{client_id}")
                assert result.allowed is False

        # Verify all 100 clients have buckets
        assert len(limiter._client_buckets) == 100

    def test_auto_identifier_prefers_ip(self) -> None:
        """Test AUTO identifier prefers IP when available."""
        config = RateLimitConfig(
            enabled=True,
            client_identifier=ClientIdentifier.AUTO,
            per_client_per_minute=1,
        )
        limiter = RateLimiter(config)

        with patch("time.time", return_value=1000.0):
            # Provide both IP and session
            limiter.check_request(client_ip="192.168.1.1", session_id="session_123")

            # Should use IP
            assert "ip:192.168.1.1" in limiter._client_buckets
            assert "session:session_123" not in limiter._client_buckets

    def test_auto_identifier_falls_back_to_session(self) -> None:
        """Test AUTO identifier uses session when IP not available."""
        config = RateLimitConfig(
            enabled=True,
            client_identifier=ClientIdentifier.AUTO,
            per_client_per_minute=1,
        )
        limiter = RateLimiter(config)

        with patch("time.time", return_value=1000.0):
            # Provide only session
            limiter.check_request(session_id="session_456")

            # Should use session
            assert "session:session_456" in limiter._client_buckets


# ============================================================================
# Stale Bucket Cleanup Tests
# ============================================================================


class TestStaleBucketCleanup:
    """Tests for stale bucket cleanup."""

    def test_cleanup_all_stale_buckets(self) -> None:
        """Test cleanup removes all stale buckets."""
        config = RateLimitConfig(
            enabled=True,
            per_client_per_minute=3,
        )
        limiter = RateLimiter(config)

        # Create buckets at time 1000
        with patch("time.time", return_value=1000.0):
            for i in range(50):
                limiter.check_request(client_ip=f"192.168.1.{i}")

        assert len(limiter._client_buckets) == 50

        # Cleanup at time 5000 (way past expiry)
        with patch("time.time", return_value=5000.0):
            cleaned = limiter.cleanup_stale_buckets(max_age=3600.0)

        assert cleaned == 50
        assert len(limiter._client_buckets) == 0

    def test_cleanup_preserves_recent_buckets(self) -> None:
        """Test cleanup preserves recently used buckets."""
        config = RateLimitConfig(
            enabled=True,
            per_client_per_minute=3,
        )
        limiter = RateLimiter(config)

        # Create old buckets
        with patch("time.time", return_value=1000.0):
            for i in range(25):
                limiter.check_request(client_ip=f"192.168.1.{i}")

        # Create recent buckets
        with patch("time.time", return_value=4500.0):
            for i in range(25, 50):
                limiter.check_request(client_ip=f"192.168.1.{i}")

        # Cleanup with 1 hour max_age at time 5000
        with patch("time.time", return_value=5000.0):
            cleaned = limiter.cleanup_stale_buckets(max_age=3600.0)

        # Only old buckets should be cleaned
        assert cleaned == 25
        assert len(limiter._client_buckets) == 25

        # Verify remaining buckets are the recent ones
        for i in range(25, 50):
            assert f"ip:192.168.1.{i}" in limiter._client_buckets

    def test_cleanup_with_custom_max_age(self) -> None:
        """Test cleanup with custom max_age.

        Buckets are considered stale when: now - bucket.reset_at > max_age
        At time 1000, buckets are created with reset_at = 1060 (1000 + 60s window)
        For buckets to be stale with max_age=50s, we need: now - 1060 > 50
        So now must be > 1110.
        """
        config = RateLimitConfig(
            enabled=True,
            per_client_per_minute=3,
        )
        limiter = RateLimiter(config)

        # Create buckets at time 1000, they will have reset_at = 1060
        with patch("time.time", return_value=1000.0):
            for i in range(10):
                limiter.check_request(client_ip=f"192.168.1.{i}")

        # Cleanup at time 1120, when buckets are definitely stale
        # now - reset_at = 1120 - 1060 = 60 > max_age (50)
        with patch("time.time", return_value=1120.0):
            cleaned = limiter.cleanup_stale_buckets(max_age=50.0)

        assert cleaned == 10
        assert len(limiter._client_buckets) == 0

    def test_cleanup_returns_count(self) -> None:
        """Test cleanup returns correct count of cleaned buckets."""
        config = RateLimitConfig(
            enabled=True,
            per_client_per_minute=3,
        )
        limiter = RateLimiter(config)

        with patch("time.time", return_value=1000.0):
            for i in range(7):
                limiter.check_request(client_ip=f"192.168.1.{i}")

        with patch("time.time", return_value=5000.0):
            cleaned = limiter.cleanup_stale_buckets(max_age=3600.0)

        assert cleaned == 7

    def test_cleanup_empty_buckets(self) -> None:
        """Test cleanup on empty buckets."""
        config = RateLimitConfig(enabled=True)
        limiter = RateLimiter(config)

        cleaned = limiter.cleanup_stale_buckets()
        assert cleaned == 0

    def test_cleanup_no_stale_buckets(self) -> None:
        """Test cleanup when no buckets are stale."""
        config = RateLimitConfig(
            enabled=True,
            per_client_per_minute=3,
        )
        limiter = RateLimiter(config)

        with patch("time.time", return_value=1000.0):
            for i in range(5):
                limiter.check_request(client_ip=f"192.168.1.{i}")

        # Immediate cleanup - nothing should be stale
        with patch("time.time", return_value=1001.0):
            cleaned = limiter.cleanup_stale_buckets(max_age=3600.0)

        assert cleaned == 0
        assert len(limiter._client_buckets) == 5


# ============================================================================
# Additional Edge Cases
# ============================================================================


class TestAdditionalEdgeCases:
    """Additional edge case tests."""

    def test_disabled_limiter_ignores_all_limits(self) -> None:
        """Test disabled limiter allows everything."""
        config = RateLimitConfig(
            enabled=False,
            requests_per_minute=1,
            per_client_per_minute=1,
            tokens_per_minute=1,
        )
        limiter = RateLimiter(config)

        # Should allow many more than limits
        for _ in range(1000):
            result = limiter.check_request(client_ip="192.168.1.1")
            assert result.allowed is True

        result = limiter.record_tokens(1000000)
        assert result.allowed is True

    def test_zero_remaining_reporting(self) -> None:
        """Test remaining count never goes negative."""
        config = RateLimitConfig(
            enabled=True,
            requests_per_minute=3,
        )
        limiter = RateLimiter(config)

        with patch("time.time", return_value=1000.0):
            # Exhaust limit
            for _ in range(5):
                limiter.check_request()

            # Check status - remaining should be 0, not negative
            status = limiter.get_status()
            assert status["global_minute_remaining"] == 0

    def test_retry_after_calculation(self) -> None:
        """Test retry_after is calculated correctly."""
        config = RateLimitConfig(
            enabled=True,
            requests_per_minute=2,
        )
        limiter = RateLimiter(config)

        with patch("time.time", return_value=1000.0):
            # Use up limit
            limiter.check_request()
            limiter.check_request()

            # Third request should have retry_after
            result = limiter.check_request()
            assert result.allowed is False
            assert result.retry_after is not None
            # retry_after should be approximately 60 seconds
            assert 0 < result.retry_after <= 60

    def test_headers_include_limit_info(self) -> None:
        """Test headers include all rate limit info."""
        config = RateLimitConfig(
            enabled=True,
            requests_per_minute=10,
            include_headers=True,
        )
        limiter = RateLimiter(config)

        with patch("time.time", return_value=1000.0):
            for _ in range(3):
                limiter.check_request()

            headers = limiter.get_headers()

            assert "X-RateLimit-Limit" in headers
            assert headers["X-RateLimit-Limit"] == "10"
            assert "X-RateLimit-Remaining" in headers
            assert headers["X-RateLimit-Remaining"] == "7"
            assert "X-RateLimit-Reset" in headers

    def test_status_returns_all_counters(self) -> None:
        """Test get_status returns all counter information."""
        config = RateLimitConfig(
            enabled=True,
            requests_per_minute=10,
            requests_per_hour=100,
            tokens_per_minute=1000,
            tokens_per_hour=10000,
        )
        limiter = RateLimiter(config)

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
            assert status["token_minute_remaining"] == 500
            assert status["token_hour_count"] == 500
            assert status["token_hour_remaining"] == 9500
            assert status["client_buckets_count"] == 2

    def test_unknown_client_identifier(self) -> None:
        """Test handling when no client identifier is provided."""
        config = RateLimitConfig(
            enabled=True,
            client_identifier=ClientIdentifier.IP,
            per_client_per_minute=3,
        )
        limiter = RateLimiter(config)

        with patch("time.time", return_value=1000.0):
            # No client_ip provided
            limiter.check_request()

            # Should use "unknown" as identifier
            assert "ip:unknown" in limiter._client_buckets
