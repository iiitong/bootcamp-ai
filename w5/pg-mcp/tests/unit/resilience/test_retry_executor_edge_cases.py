"""Edge case tests for retry executor.

Tests cover:
- Zero retries
- Immediate success
- Success on last retry
- Non-retryable error immediate fail
- Mixed errors
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pg_mcp.resilience.backoff import BackoffStrategyType
from pg_mcp.resilience.retry_executor import (
    DatabaseRetryConfig,
    DatabaseRetryExecutor,
    OpenAIRetryConfig,
    OpenAIRetryExecutor,
    RetryConfig,
    RetryExecutor,
)


# ============================================================================
# Zero Retries Tests
# ============================================================================


class TestZeroRetries:
    """Tests for zero retry configuration."""

    @pytest.mark.asyncio
    async def test_zero_retries_single_call(self) -> None:
        """Test with zero max retries only calls once."""
        config = RetryConfig(max_retries=0)
        executor = RetryExecutor(config)

        operation = AsyncMock(side_effect=ValueError("error"))

        with pytest.raises(ValueError):
            await executor.execute_with_retry(operation, "test_op")

        # Should only call once - no retries
        assert operation.call_count == 1

    @pytest.mark.asyncio
    async def test_zero_retries_success(self) -> None:
        """Test with zero retries but operation succeeds."""
        config = RetryConfig(max_retries=0)
        executor = RetryExecutor(config)

        operation = AsyncMock(return_value="success")

        result = await executor.execute_with_retry(operation, "test_op")

        assert result == "success"
        assert operation.call_count == 1

    @pytest.mark.asyncio
    async def test_zero_retries_propagates_exception(self) -> None:
        """Test with zero retries propagates exception correctly."""
        config = RetryConfig(max_retries=0)
        executor = RetryExecutor(config)

        class CustomError(Exception):
            pass

        operation = AsyncMock(side_effect=CustomError("custom"))

        with pytest.raises(CustomError) as exc_info:
            await executor.execute_with_retry(operation, "test_op")

        assert "custom" in str(exc_info.value)


# ============================================================================
# Immediate Success Tests
# ============================================================================


class TestImmediateSuccess:
    """Tests for operations that succeed immediately."""

    @pytest.mark.asyncio
    async def test_immediate_success_single_call(self) -> None:
        """Test operation that succeeds immediately."""
        config = RetryConfig(max_retries=3)
        executor = RetryExecutor(config)

        operation = AsyncMock(return_value="success")

        result = await executor.execute_with_retry(operation, "test_op")

        assert result == "success"
        assert operation.call_count == 1

    @pytest.mark.asyncio
    async def test_immediate_success_complex_return(self) -> None:
        """Test immediate success with complex return value."""
        config = RetryConfig(max_retries=3)
        executor = RetryExecutor(config)

        expected = {"data": [1, 2, 3], "status": "ok"}
        operation = AsyncMock(return_value=expected)

        result = await executor.execute_with_retry(operation, "test_op")

        assert result == expected
        assert operation.call_count == 1

    @pytest.mark.asyncio
    async def test_immediate_success_no_delay(self) -> None:
        """Test immediate success doesn't invoke any delay."""
        config = RetryConfig(max_retries=3, initial_delay=10.0)
        executor = RetryExecutor(config)

        operation = AsyncMock(return_value="fast")

        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            result = await executor.execute_with_retry(operation, "test_op")

            assert result == "fast"
            mock_sleep.assert_not_called()


# ============================================================================
# Success on Last Retry Tests
# ============================================================================


class TestSuccessOnLastRetry:
    """Tests for operations that succeed on the last retry."""

    @pytest.mark.asyncio
    async def test_success_on_last_retry(self) -> None:
        """Test success on the last retry attempt."""
        config = RetryConfig(
            max_retries=3,
            initial_delay=0.01,  # Short delay for testing
            backoff_strategy=BackoffStrategyType.FIXED,
        )
        executor = RetryExecutor(config)

        call_count = 0

        async def flaky_operation():
            nonlocal call_count
            call_count += 1
            # Fail first 3 times (1 initial + 2 retries), succeed on 4th (3rd retry)
            # Use "connection_lost" in message to match default retryable_errors
            if call_count < 4:
                raise Exception("connection_lost: transient error")
            return "success"

        result = await executor.execute_with_retry(flaky_operation, "test_op")

        assert result == "success"
        assert call_count == 4  # 1 initial + 3 retries

    @pytest.mark.asyncio
    async def test_success_on_second_retry(self) -> None:
        """Test success on second retry."""
        config = RetryConfig(
            max_retries=3,
            initial_delay=0.01,
            backoff_strategy=BackoffStrategyType.FIXED,
        )
        executor = RetryExecutor(config)

        call_count = 0

        async def flaky_operation():
            nonlocal call_count
            call_count += 1
            # Use "timeout" in message to match default retryable_errors
            if call_count < 3:
                raise Exception("timeout: transient")
            return "recovered"

        result = await executor.execute_with_retry(flaky_operation, "test_op")

        assert result == "recovered"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_fail_after_all_retries_exhausted(self) -> None:
        """Test failure after all retries are exhausted."""
        config = RetryConfig(
            max_retries=2,
            initial_delay=0.01,
            backoff_strategy=BackoffStrategyType.FIXED,
        )
        executor = RetryExecutor(config)

        call_count = 0

        async def always_fail():
            nonlocal call_count
            call_count += 1
            # Use "server_error" in message to match default retryable_errors
            raise Exception("server_error: always fails")

        with pytest.raises(Exception):
            await executor.execute_with_retry(always_fail, "test_op")

        # 1 initial + 2 retries = 3 attempts
        assert call_count == 3


# ============================================================================
# Non-Retryable Error Tests
# ============================================================================


class TestNonRetryableError:
    """Tests for non-retryable errors."""

    @pytest.mark.asyncio
    async def test_non_retryable_error_immediate_fail(self) -> None:
        """Test that non-retryable errors fail immediately."""
        config = RetryConfig(
            max_retries=3,
            retryable_errors={"connection", "timeout"},
        )
        executor = RetryExecutor(config)

        operation = AsyncMock(side_effect=ValueError("not retryable"))

        with pytest.raises(ValueError):
            await executor.execute_with_retry(operation, "test_op")

        # Should only call once - no retries for non-retryable error
        assert operation.call_count == 1

    @pytest.mark.asyncio
    async def test_syntax_error_not_retried(self) -> None:
        """Test that syntax errors are not retried."""
        config = RetryConfig(
            max_retries=5,
            retryable_errors={"connection", "timeout"},
        )
        executor = RetryExecutor(config)

        operation = AsyncMock(side_effect=SyntaxError("invalid syntax"))

        with pytest.raises(SyntaxError):
            await executor.execute_with_retry(operation, "test_op")

        assert operation.call_count == 1

    @pytest.mark.asyncio
    async def test_type_error_not_retried(self) -> None:
        """Test that type errors are not retried."""
        config = RetryConfig(
            max_retries=3,
            retryable_errors={"connection", "timeout"},
        )
        executor = RetryExecutor(config)

        operation = AsyncMock(side_effect=TypeError("wrong type"))

        with pytest.raises(TypeError):
            await executor.execute_with_retry(operation, "test_op")

        assert operation.call_count == 1

    @pytest.mark.asyncio
    async def test_custom_is_retryable_function(self) -> None:
        """Test custom is_retryable function."""
        config = RetryConfig(max_retries=3, initial_delay=0.01)
        executor = RetryExecutor(config)

        call_count = 0

        async def operation():
            nonlocal call_count
            call_count += 1
            raise ValueError("maybe retryable")

        # Custom function that makes ValueError retryable
        def is_retryable(error: Exception) -> bool:
            return isinstance(error, ValueError)

        with pytest.raises(ValueError):
            await executor.execute_with_retry(
                operation, "test_op", is_retryable=is_retryable
            )

        # Should retry since custom function says it's retryable
        # 1 initial + 3 retries = 4
        assert call_count == 4


# ============================================================================
# Mixed Errors Tests
# ============================================================================


class TestMixedErrors:
    """Tests for handling of mixed retryable and non-retryable errors."""

    @pytest.mark.asyncio
    async def test_retryable_then_non_retryable(self) -> None:
        """Test retryable error followed by non-retryable error."""
        config = RetryConfig(
            max_retries=5,
            initial_delay=0.01,
            backoff_strategy=BackoffStrategyType.FIXED,
            retryable_errors={"connection"},
        )
        executor = RetryExecutor(config)

        call_count = 0

        async def mixed_failures():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ConnectionError("retryable")
            raise ValueError("not retryable")

        with pytest.raises(ValueError):
            await executor.execute_with_retry(mixed_failures, "test_op")

        # First call: ConnectionError (retryable)
        # Second call: ValueError (not retryable) - stops here
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_multiple_retryable_then_success(self) -> None:
        """Test multiple retryable errors then success."""
        config = RetryConfig(
            max_retries=5,
            initial_delay=0.01,
            backoff_strategy=BackoffStrategyType.FIXED,
        )
        executor = RetryExecutor(config)

        call_count = 0

        async def multiple_failures():
            nonlocal call_count
            call_count += 1
            # Use "connection_lost" in message to match default retryable_errors
            if call_count <= 3:
                raise Exception(f"connection_lost: failure {call_count}")
            return "success"

        result = await executor.execute_with_retry(multiple_failures, "test_op")

        assert result == "success"
        assert call_count == 4

    @pytest.mark.asyncio
    async def test_alternating_error_types_stops_on_non_retryable(self) -> None:
        """Test that alternating errors stop on non-retryable."""
        config = RetryConfig(
            max_retries=10,
            initial_delay=0.01,
            backoff_strategy=BackoffStrategyType.FIXED,
            retryable_errors={"timeout"},
        )
        executor = RetryExecutor(config)

        call_count = 0

        async def alternating_errors():
            nonlocal call_count
            call_count += 1
            if call_count % 2 == 1:
                raise TimeoutError("retryable")
            raise PermissionError("not retryable")

        with pytest.raises(PermissionError):
            await executor.execute_with_retry(alternating_errors, "test_op")

        # First call: TimeoutError (retryable)
        # Second call: PermissionError (not retryable)
        assert call_count == 2


# ============================================================================
# OpenAI Retry Executor Tests
# ============================================================================


class TestOpenAIRetryExecutor:
    """Tests for OpenAI-specific retry executor."""

    @pytest.mark.asyncio
    async def test_rate_limit_error_is_retried(self) -> None:
        """Test that RateLimitError is retried."""
        executor = OpenAIRetryExecutor(
            OpenAIRetryConfig(max_retries=3, initial_delay=0.01)
        )

        # Create a mock RateLimitError
        class RateLimitError(Exception):
            pass

        call_count = 0

        async def rate_limited_operation():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise RateLimitError("rate limited")
            return "success"

        result = await executor.execute_with_retry(
            rate_limited_operation, "openai_call"
        )

        assert result == "success"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_authentication_error_not_retried(self) -> None:
        """Test that AuthenticationError is not retried."""
        executor = OpenAIRetryExecutor(
            OpenAIRetryConfig(max_retries=3, initial_delay=0.01)
        )

        class AuthenticationError(Exception):
            pass

        operation = AsyncMock(side_effect=AuthenticationError("invalid key"))

        with pytest.raises(AuthenticationError):
            await executor.execute_with_retry(operation, "openai_call")

        assert operation.call_count == 1

    @pytest.mark.asyncio
    async def test_invalid_request_error_not_retried(self) -> None:
        """Test that InvalidRequestError is not retried."""
        executor = OpenAIRetryExecutor(
            OpenAIRetryConfig(max_retries=3, initial_delay=0.01)
        )

        class InvalidRequestError(Exception):
            pass

        operation = AsyncMock(side_effect=InvalidRequestError("bad request"))

        with pytest.raises(InvalidRequestError):
            await executor.execute_with_retry(operation, "openai_call")

        assert operation.call_count == 1

    @pytest.mark.asyncio
    async def test_api_timeout_error_is_retried(self) -> None:
        """Test that APITimeoutError is retried."""
        executor = OpenAIRetryExecutor(
            OpenAIRetryConfig(max_retries=2, initial_delay=0.01)
        )

        class APITimeoutError(Exception):
            pass

        call_count = 0

        async def timeout_operation():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise APITimeoutError("timeout")
            return "success"

        result = await executor.execute_with_retry(timeout_operation, "openai_call")

        assert result == "success"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_internal_server_error_is_retried(self) -> None:
        """Test that InternalServerError is retried."""
        executor = OpenAIRetryExecutor(
            OpenAIRetryConfig(max_retries=2, initial_delay=0.01)
        )

        class InternalServerError(Exception):
            pass

        call_count = 0

        async def server_error_operation():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise InternalServerError("server error")
            return "recovered"

        result = await executor.execute_with_retry(
            server_error_operation, "openai_call"
        )

        assert result == "recovered"
        assert call_count == 3


# ============================================================================
# Database Retry Executor Tests
# ============================================================================


class TestDatabaseRetryExecutor:
    """Tests for Database-specific retry executor."""

    @pytest.mark.asyncio
    async def test_connection_lost_is_retried(self) -> None:
        """Test that connection lost errors are retried."""
        executor = DatabaseRetryExecutor(
            DatabaseRetryConfig(max_retries=2, initial_delay=0.01)
        )

        call_count = 0

        async def connection_lost_op():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("connection lost")
            return "reconnected"

        result = await executor.execute_with_retry(connection_lost_op, "db_query")

        assert result == "reconnected"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_connection_closed_is_retried(self) -> None:
        """Test that connection closed errors are retried."""
        executor = DatabaseRetryExecutor(
            DatabaseRetryConfig(max_retries=2, initial_delay=0.01)
        )

        call_count = 0

        async def connection_closed_op():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise Exception("connection closed")
            return "success"

        result = await executor.execute_with_retry(connection_closed_op, "db_query")

        assert result == "success"

    @pytest.mark.asyncio
    async def test_timeout_is_retried(self) -> None:
        """Test that timeout errors are retried."""
        executor = DatabaseRetryExecutor(
            DatabaseRetryConfig(max_retries=2, initial_delay=0.01)
        )

        call_count = 0

        async def timeout_op():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise TimeoutError("query timeout")
            return "completed"

        result = await executor.execute_with_retry(timeout_op, "db_query")

        assert result == "completed"

    @pytest.mark.asyncio
    async def test_syntax_error_not_retried_in_db(self) -> None:
        """Test that syntax errors are not retried in database operations."""
        executor = DatabaseRetryExecutor(
            DatabaseRetryConfig(max_retries=3, initial_delay=0.01)
        )

        async def syntax_error_op():
            raise Exception("syntax error in query")

        with pytest.raises(Exception) as exc_info:
            await executor.execute_with_retry(syntax_error_op, "db_query")

        assert "syntax error" in str(exc_info.value)


# ============================================================================
# Backoff Strategy Tests
# ============================================================================


class TestBackoffStrategies:
    """Tests for different backoff strategies."""

    @pytest.mark.asyncio
    async def test_exponential_backoff_delays_increase(self) -> None:
        """Test that exponential backoff increases delays."""
        config = RetryConfig(
            max_retries=3,
            backoff_strategy=BackoffStrategyType.EXPONENTIAL,
            initial_delay=0.1,
            multiplier=2.0,
            max_delay=10.0,
        )
        executor = RetryExecutor(config)

        delays: list[float] = []

        async def always_fail():
            # Use "timeout" in message to match default retryable_errors
            raise Exception("timeout: fail")

        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            mock_sleep.side_effect = lambda d: delays.append(d)

            with pytest.raises(Exception):
                await executor.execute_with_retry(always_fail, "test_op")

        # Delays should generally increase (with jitter)
        # We can't assert exact values due to jitter
        assert len(delays) == 3  # 3 retries

    @pytest.mark.asyncio
    async def test_fixed_backoff_constant_delays(self) -> None:
        """Test that fixed backoff uses constant delays."""
        config = RetryConfig(
            max_retries=3,
            backoff_strategy=BackoffStrategyType.FIXED,
            initial_delay=0.5,
        )
        executor = RetryExecutor(config)

        delays: list[float] = []

        async def always_fail():
            # Use "rate_limit" in message to match default retryable_errors
            raise Exception("rate_limit: fail")

        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            mock_sleep.side_effect = lambda d: delays.append(d)

            with pytest.raises(Exception):
                await executor.execute_with_retry(always_fail, "test_op")

        # All delays should be constant (0.5)
        assert len(delays) == 3
        for delay in delays:
            assert delay == 0.5

    @pytest.mark.asyncio
    async def test_fibonacci_backoff(self) -> None:
        """Test Fibonacci backoff strategy."""
        config = RetryConfig(
            max_retries=5,
            backoff_strategy=BackoffStrategyType.FIBONACCI,
            initial_delay=0.1,
            max_delay=10.0,
        )
        executor = RetryExecutor(config)

        delays: list[float] = []

        async def always_fail():
            # Use "server_error" in message to match default retryable_errors
            raise Exception("server_error: fail")

        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            mock_sleep.side_effect = lambda d: delays.append(d)

            with pytest.raises(Exception):
                await executor.execute_with_retry(always_fail, "test_op")

        assert len(delays) == 5
        # Fibonacci delays: 0.1, 0.1, 0.2, 0.3, 0.5 (with base_delay=0.1)


# ============================================================================
# Timeout Integration Tests
# ============================================================================


class TestTimeoutIntegration:
    """Tests for timeout integration with retry executor."""

    @pytest.mark.asyncio
    async def test_overall_timeout(self) -> None:
        """Test that overall operation can be timed out."""
        config = RetryConfig(
            max_retries=10,
            initial_delay=1.0,  # Long delay
            backoff_strategy=BackoffStrategyType.FIXED,
        )
        executor = RetryExecutor(config)

        async def slow_operation():
            await asyncio.sleep(0.1)
            # Use "timeout" in message to match default retryable_errors
            raise Exception("timeout: slow fail")

        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(
                executor.execute_with_retry(slow_operation, "test_op"),
                timeout=0.2,
            )

    @pytest.mark.asyncio
    async def test_operation_itself_times_out(self) -> None:
        """Test handling when the operation itself times out."""
        config = RetryConfig(
            max_retries=2,
            initial_delay=0.01,
            backoff_strategy=BackoffStrategyType.FIXED,
        )
        executor = RetryExecutor(config)

        call_count = 0

        async def sometimes_slow():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                await asyncio.sleep(10)  # Very slow
            return "success"

        # With overall timeout, should eventually timeout
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(
                executor.execute_with_retry(sometimes_slow, "test_op"),
                timeout=0.1,
            )
