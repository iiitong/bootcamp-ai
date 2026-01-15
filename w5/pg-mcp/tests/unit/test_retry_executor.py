"""Unit tests for retry executor."""

from unittest.mock import patch

import pytest

from pg_mcp.resilience import (
    BackoffStrategyType,
    DatabaseRetryConfig,
    DatabaseRetryExecutor,
    OpenAIRetryConfig,
    OpenAIRetryExecutor,
    RetryConfig,
    RetryExecutor,
)


class TestRetryConfig:
    """Tests for RetryConfig classes."""

    def test_default_config(self) -> None:
        """Test default RetryConfig values."""
        config = RetryConfig()
        assert config.max_retries == 3
        assert config.backoff_strategy == BackoffStrategyType.EXPONENTIAL
        assert config.initial_delay == 1.0
        assert config.max_delay == 30.0
        assert config.multiplier == 2.0
        assert "rate_limit" in config.retryable_errors
        assert "timeout" in config.retryable_errors

    def test_openai_config_defaults(self) -> None:
        """Test OpenAIRetryConfig defaults."""
        config = OpenAIRetryConfig()
        assert config.max_retries == 3
        assert config.backoff_strategy == BackoffStrategyType.EXPONENTIAL
        assert "server_error" in config.retryable_errors

    def test_database_config_defaults(self) -> None:
        """Test DatabaseRetryConfig defaults."""
        config = DatabaseRetryConfig()
        assert config.max_retries == 2
        assert config.backoff_strategy == BackoffStrategyType.FIXED
        assert config.initial_delay == 0.5
        assert "connection_lost" in config.retryable_errors


class TestRetryExecutor:
    """Tests for RetryExecutor."""

    @pytest.fixture
    def executor(self) -> RetryExecutor:
        """Create executor with fast delays for testing."""
        config = RetryConfig(
            max_retries=2,
            initial_delay=0.01,  # Very short delays for tests
            max_delay=0.1,
        )
        return RetryExecutor(config)

    @pytest.mark.asyncio
    async def test_successful_operation(self, executor: RetryExecutor) -> None:
        """Test successful operation without retries."""
        call_count = 0

        async def operation():
            nonlocal call_count
            call_count += 1
            return "success"

        result = await executor.execute_with_retry(operation, "test_op")
        assert result == "success"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_retry_on_retryable_error(self, executor: RetryExecutor) -> None:
        """Test retry on retryable error."""
        call_count = 0

        async def operation():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("connection_lost error")
            return "success"

        with patch("asyncio.sleep", return_value=None):
            result = await executor.execute_with_retry(operation, "test_op")
        assert result == "success"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_no_retry_on_non_retryable_error(self, executor: RetryExecutor) -> None:
        """Test no retry on non-retryable error."""
        call_count = 0

        async def operation():
            nonlocal call_count
            call_count += 1
            raise ValueError("Invalid input")

        with pytest.raises(ValueError):
            await executor.execute_with_retry(operation, "test_op")
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_max_retries_exceeded(self, executor: RetryExecutor) -> None:
        """Test that max retries is respected."""
        call_count = 0

        async def operation():
            nonlocal call_count
            call_count += 1
            raise Exception("timeout error")

        with patch("asyncio.sleep", return_value=None), pytest.raises(Exception, match="timeout"):
            await executor.execute_with_retry(operation, "test_op")
        # Initial try + 2 retries = 3 total calls
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_custom_is_retryable(self, executor: RetryExecutor) -> None:
        """Test custom is_retryable function."""
        call_count = 0

        async def operation():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ValueError("should retry")
            return "success"

        def custom_retryable(e: Exception) -> bool:
            return isinstance(e, ValueError)

        with patch("asyncio.sleep", return_value=None):
            result = await executor.execute_with_retry(
                operation, "test_op", is_retryable=custom_retryable
            )
        assert result == "success"
        assert call_count == 2


class TestOpenAIRetryExecutor:
    """Tests for OpenAIRetryExecutor."""

    @pytest.fixture
    def executor(self) -> OpenAIRetryExecutor:
        """Create OpenAI executor."""
        config = OpenAIRetryConfig(
            max_retries=2,
            initial_delay=0.01,
            max_delay=0.1,
        )
        return OpenAIRetryExecutor(config)

    def test_retryable_rate_limit_error(self, executor: OpenAIRetryExecutor) -> None:
        """Test RateLimitError is retryable."""

        class RateLimitError(Exception):
            pass

        error = RateLimitError("rate limit exceeded")
        assert executor._is_default_retryable(error) is True

    def test_retryable_timeout_error(self, executor: OpenAIRetryExecutor) -> None:
        """Test APITimeoutError is retryable."""

        class APITimeoutError(Exception):
            pass

        error = APITimeoutError("timeout")
        assert executor._is_default_retryable(error) is True

    def test_retryable_server_error(self, executor: OpenAIRetryExecutor) -> None:
        """Test InternalServerError is retryable."""

        class InternalServerError(Exception):
            pass

        error = InternalServerError("server error")
        assert executor._is_default_retryable(error) is True

    def test_non_retryable_auth_error(self, executor: OpenAIRetryExecutor) -> None:
        """Test AuthenticationError is not retryable."""

        class AuthenticationError(Exception):
            pass

        error = AuthenticationError("invalid api key")
        assert executor._is_default_retryable(error) is False

    def test_non_retryable_invalid_request(self, executor: OpenAIRetryExecutor) -> None:
        """Test InvalidRequestError is not retryable."""

        class InvalidRequestError(Exception):
            pass

        error = InvalidRequestError("invalid request")
        assert executor._is_default_retryable(error) is False


class TestDatabaseRetryExecutor:
    """Tests for DatabaseRetryExecutor."""

    @pytest.fixture
    def executor(self) -> DatabaseRetryExecutor:
        """Create Database executor."""
        config = DatabaseRetryConfig(
            max_retries=2,
            initial_delay=0.01,
        )
        return DatabaseRetryExecutor(config)

    def test_retryable_connection_lost(self, executor: DatabaseRetryExecutor) -> None:
        """Test connection lost error is retryable."""
        error = Exception("connection lost")
        assert executor._is_default_retryable(error) is True

    def test_retryable_connection_closed(self, executor: DatabaseRetryExecutor) -> None:
        """Test connection closed error is retryable."""
        error = Exception("connection closed unexpectedly")
        assert executor._is_default_retryable(error) is True

    def test_retryable_timeout(self, executor: DatabaseRetryExecutor) -> None:
        """Test timeout error is retryable."""
        error = Exception("query timeout exceeded")
        assert executor._is_default_retryable(error) is True

    def test_retryable_timeout_error_type(self, executor: DatabaseRetryExecutor) -> None:
        """Test TimeoutError type is retryable."""
        error = TimeoutError("operation timed out")
        assert executor._is_default_retryable(error) is True

    def test_non_retryable_syntax_error(self, executor: DatabaseRetryExecutor) -> None:
        """Test syntax error is not retryable."""
        error = Exception("syntax error at or near SELECT")
        assert executor._is_default_retryable(error) is False

    def test_non_retryable_unknown_error(self, executor: DatabaseRetryExecutor) -> None:
        """Test unknown error falls back to default."""
        error = ValueError("some unknown error")
        # Falls back to parent's _is_default_retryable which checks config.retryable_errors
        assert executor._is_default_retryable(error) is False
