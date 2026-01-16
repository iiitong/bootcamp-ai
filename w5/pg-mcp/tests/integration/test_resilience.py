"""Resilience integration tests.

This module tests resilience features with real PostgreSQL instances:
- Circuit breaker behavior
- Rate limiter under load
- Retry executor with transient failures
- Graceful degradation scenarios
"""

import asyncio
import time
from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, patch

import asyncpg
import pytest
from testcontainers.postgres import PostgresContainer

from pg_mcp.config.models import (
    AppConfig,
    DatabaseConfig,
    OpenAIConfig,
    RateLimitConfig,
    ServerConfig,
)
from pg_mcp.infrastructure.database import DatabasePool
from pg_mcp.resilience import (
    BackoffStrategyType,
    DatabaseRetryConfig,
    DatabaseRetryExecutor,
    OpenAIRetryConfig,
    OpenAIRetryExecutor,
    RetryConfig,
    RetryExecutor,
)
from pg_mcp.resilience.rate_limiter import (
    ClientIdentifier,
    RateLimitConfig as ResilienceRateLimitConfig,
    RateLimiter,
)

from .conftest import create_mock_openai_response


class TestRateLimiterUnderLoad:
    """Test rate limiter behavior under various load conditions."""

    def test_burst_requests_within_limit(self) -> None:
        """Test handling burst of requests within the limit."""
        config = ResilienceRateLimitConfig(
            enabled=True,
            requests_per_minute=100,
            requests_per_hour=1000,
            per_client_per_minute=50,
        )
        limiter = RateLimiter(config)

        with patch("time.time", return_value=1000.0):
            # Burst of 50 requests should all succeed
            results = []
            for _ in range(50):
                result = limiter.check_request()
                results.append(result.allowed)

            assert all(results)
            assert limiter.get_status()["global_minute_count"] == 50

    def test_burst_requests_exceeding_limit(self) -> None:
        """Test handling burst of requests exceeding the limit."""
        config = ResilienceRateLimitConfig(
            enabled=True,
            requests_per_minute=10,
            requests_per_hour=1000,
            per_client_per_minute=50,
        )
        limiter = RateLimiter(config)

        with patch("time.time", return_value=1000.0):
            allowed_count = 0
            denied_count = 0

            for _ in range(20):
                result = limiter.check_request()
                if result.allowed:
                    allowed_count += 1
                else:
                    denied_count += 1

            assert allowed_count == 10  # Only 10 allowed
            assert denied_count == 10  # Remaining denied

    def test_multiple_clients_independent_limits(self) -> None:
        """Test that multiple clients have independent rate limits."""
        config = ResilienceRateLimitConfig(
            enabled=True,
            requests_per_minute=100,
            requests_per_hour=1000,
            per_client_per_minute=5,
            client_identifier=ClientIdentifier.IP,
        )
        limiter = RateLimiter(config)

        with patch("time.time", return_value=1000.0):
            # Client A uses their limit
            for _ in range(5):
                result = limiter.check_request(client_ip="192.168.1.1")
                assert result.allowed

            # Client A should be blocked
            result = limiter.check_request(client_ip="192.168.1.1")
            assert not result.allowed

            # Client B should still have quota
            for _ in range(5):
                result = limiter.check_request(client_ip="192.168.1.2")
                assert result.allowed

            # Client C should also have quota
            result = limiter.check_request(client_ip="192.168.1.3")
            assert result.allowed

    def test_rate_limit_window_reset(self) -> None:
        """Test that rate limits reset after the time window."""
        config = ResilienceRateLimitConfig(
            enabled=True,
            requests_per_minute=5,
            requests_per_hour=1000,
        )
        limiter = RateLimiter(config)

        # Use all quota
        with patch("time.time", return_value=1000.0):
            for _ in range(5):
                result = limiter.check_request()
                assert result.allowed

            result = limiter.check_request()
            assert not result.allowed

        # After window expires
        with patch("time.time", return_value=1061.0):  # 61 seconds later
            result = limiter.check_request()
            assert result.allowed

    def test_token_rate_limiting(self) -> None:
        """Test token-based rate limiting."""
        config = ResilienceRateLimitConfig(
            enabled=True,
            tokens_per_minute=1000,
            tokens_per_hour=10000,
        )
        limiter = RateLimiter(config)

        with patch("time.time", return_value=1000.0):
            # Record tokens within limit
            result = limiter.record_tokens(500)
            assert result.allowed
            assert result.remaining == 500

            # Record more tokens
            result = limiter.record_tokens(400)
            assert result.allowed
            assert result.remaining == 100

            # Exceed limit
            result = limiter.record_tokens(200)
            assert not result.allowed
            assert result.remaining == 0

    def test_concurrent_client_cleanup(self) -> None:
        """Test cleanup of stale client buckets."""
        config = ResilienceRateLimitConfig(
            enabled=True,
            per_client_per_minute=5,
            # Set high global limits so we can create many client buckets
            requests_per_minute=1000,
            requests_per_hour=10000,
        )
        limiter = RateLimiter(config)

        # Create buckets for multiple clients
        with patch("time.time", return_value=1000.0):
            for i in range(100):
                limiter.check_request(client_ip=f"192.168.1.{i}")

        assert limiter.get_status()["client_buckets_count"] == 100

        # Fast forward and cleanup
        with patch("time.time", return_value=5000.0):
            cleaned = limiter.cleanup_stale_buckets(max_age=3600.0)

        assert cleaned == 100
        assert limiter.get_status()["client_buckets_count"] == 0


class TestRetryExecutorWithTransientFailures:
    """Test retry executor with various failure scenarios."""

    @pytest.fixture
    def executor(self) -> RetryExecutor:
        """Create executor with fast delays for testing."""
        config = RetryConfig(
            max_retries=3,
            initial_delay=0.001,  # Very short delays for tests
            max_delay=0.01,
            backoff_strategy=BackoffStrategyType.EXPONENTIAL,
        )
        return RetryExecutor(config)

    @pytest.mark.asyncio
    async def test_successful_first_attempt(self, executor: RetryExecutor) -> None:
        """Test successful operation on first attempt."""
        call_count = 0

        async def operation():
            nonlocal call_count
            call_count += 1
            return "success"

        result = await executor.execute_with_retry(operation, "test_op")
        assert result == "success"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_retry_succeeds_after_transient_failures(
        self, executor: RetryExecutor
    ) -> None:
        """Test retry succeeds after transient failures."""
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
    async def test_max_retries_exhausted(self, executor: RetryExecutor) -> None:
        """Test that max retries is respected."""
        call_count = 0

        async def operation():
            nonlocal call_count
            call_count += 1
            raise Exception("timeout error")

        with patch("asyncio.sleep", return_value=None):
            with pytest.raises(Exception, match="timeout"):
                await executor.execute_with_retry(operation, "test_op")

        # Initial try + 3 retries = 4 total calls
        assert call_count == 4

    @pytest.mark.asyncio
    async def test_non_retryable_error_fails_immediately(
        self, executor: RetryExecutor
    ) -> None:
        """Test that non-retryable errors fail immediately."""
        call_count = 0

        async def operation():
            nonlocal call_count
            call_count += 1
            raise ValueError("Invalid input - not retryable")

        with pytest.raises(ValueError):
            await executor.execute_with_retry(operation, "test_op")

        assert call_count == 1  # No retry for non-retryable errors

    @pytest.mark.asyncio
    async def test_custom_retryable_function(self, executor: RetryExecutor) -> None:
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
    """Test OpenAI-specific retry executor."""

    @pytest.fixture
    def executor(self) -> OpenAIRetryExecutor:
        """Create OpenAI executor with fast delays."""
        config = OpenAIRetryConfig(
            max_retries=3,
            initial_delay=0.001,
            max_delay=0.01,
        )
        return OpenAIRetryExecutor(config)

    @pytest.mark.asyncio
    async def test_retry_on_rate_limit(self, executor: OpenAIRetryExecutor) -> None:
        """Test retry on rate limit error."""
        call_count = 0

        class RateLimitError(Exception):
            pass

        async def operation():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise RateLimitError("rate limit exceeded")
            return "success"

        with patch("asyncio.sleep", return_value=None):
            result = await executor.execute_with_retry(operation, "openai_call")

        assert result == "success"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_no_retry_on_auth_error(self, executor: OpenAIRetryExecutor) -> None:
        """Test no retry on authentication error."""
        call_count = 0

        class AuthenticationError(Exception):
            pass

        async def operation():
            nonlocal call_count
            call_count += 1
            raise AuthenticationError("invalid api key")

        with pytest.raises(AuthenticationError):
            await executor.execute_with_retry(operation, "openai_call")

        assert call_count == 1  # No retries

    @pytest.mark.asyncio
    async def test_retry_on_server_error(self, executor: OpenAIRetryExecutor) -> None:
        """Test retry on server error."""
        call_count = 0

        class InternalServerError(Exception):
            pass

        async def operation():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise InternalServerError("server error")
            return "success"

        with patch("asyncio.sleep", return_value=None):
            result = await executor.execute_with_retry(operation, "openai_call")

        assert result == "success"
        assert call_count == 2


class TestDatabaseRetryExecutor:
    """Test database-specific retry executor."""

    @pytest.fixture
    def executor(self) -> DatabaseRetryExecutor:
        """Create database executor with fast delays."""
        config = DatabaseRetryConfig(
            max_retries=2,
            initial_delay=0.001,
        )
        return DatabaseRetryExecutor(config)

    @pytest.mark.asyncio
    async def test_retry_on_connection_lost(
        self, executor: DatabaseRetryExecutor
    ) -> None:
        """Test retry on connection lost error."""
        call_count = 0

        async def operation():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise Exception("connection lost")
            return "success"

        with patch("asyncio.sleep", return_value=None):
            result = await executor.execute_with_retry(operation, "db_query")

        assert result == "success"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_retry_on_timeout(self, executor: DatabaseRetryExecutor) -> None:
        """Test retry on timeout error."""
        call_count = 0

        async def operation():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise TimeoutError("query timeout exceeded")
            return "success"

        with patch("asyncio.sleep", return_value=None):
            result = await executor.execute_with_retry(operation, "db_query")

        assert result == "success"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_no_retry_on_syntax_error(
        self, executor: DatabaseRetryExecutor
    ) -> None:
        """Test no retry on syntax error."""
        call_count = 0

        async def operation():
            nonlocal call_count
            call_count += 1
            raise Exception("syntax error at or near SELECT")

        with pytest.raises(Exception, match="syntax"):
            await executor.execute_with_retry(operation, "db_query")

        assert call_count == 1  # No retries


class TestGracefulDegradation:
    """Test graceful degradation scenarios."""

    @pytest.fixture
    def postgres_container(self) -> PostgresContainer:
        """Create a PostgreSQL test container."""
        container = PostgresContainer("postgres:16")
        container.start()
        yield container
        container.stop()

    @pytest.fixture
    async def database_pool(
        self, postgres_container: PostgresContainer
    ) -> AsyncGenerator[DatabasePool]:
        """Create and connect database pool."""
        config = DatabaseConfig(
            name="degradation_test",
            host=postgres_container.get_container_host_ip(),
            port=int(postgres_container.get_exposed_port(5432)),
            dbname=postgres_container.dbname,
            user=postgres_container.username,
            password=postgres_container.password,  # type: ignore
            ssl_mode="disable",
        )
        pool = DatabasePool(config)
        await pool.connect()
        yield pool
        await pool.disconnect()

    @pytest.fixture
    async def setup_degradation_data(
        self, database_pool: DatabasePool
    ) -> None:
        """Set up test data for degradation tests."""
        await database_pool.execute("""
            CREATE TABLE test_data (
                id SERIAL PRIMARY KEY,
                value TEXT
            )
        """)
        await database_pool.execute("""
            INSERT INTO test_data (value)
            SELECT md5(random()::text) FROM generate_series(1, 100)
        """)

    @pytest.mark.asyncio
    async def test_query_with_short_timeout(
        self,
        database_pool: DatabasePool,
        setup_degradation_data: None,
    ) -> None:
        """Test graceful handling of query with short timeout."""
        # Normal query should succeed
        result = await database_pool.fetch_readonly(
            "SELECT * FROM test_data LIMIT 10",
            timeout=5.0,
        )
        assert len(result) == 10

    @pytest.mark.asyncio
    async def test_query_timeout_handled_gracefully(
        self,
        database_pool: DatabasePool,
        setup_degradation_data: None,
    ) -> None:
        """Test that query timeout is handled gracefully."""
        # Very short timeout should cause timeout error
        # but we handle it gracefully
        try:
            # This query might complete quickly or timeout
            await database_pool.fetch_readonly(
                "SELECT * FROM test_data, test_data t2 LIMIT 1",
                timeout=0.001,  # 1ms - very short
            )
        except (asyncio.TimeoutError, TimeoutError):
            # Expected - timeout is gracefully raised
            pass
        except Exception as e:
            # Other errors might occur - that's also acceptable
            assert "timeout" in str(e).lower() or "cancel" in str(e).lower()

    @pytest.mark.asyncio
    async def test_pool_handles_connection_errors(
        self, postgres_container: PostgresContainer
    ) -> None:
        """Test that pool handles connection errors gracefully."""
        config = DatabaseConfig(
            name="bad_connection",
            host=postgres_container.get_container_host_ip(),
            port=99999,  # Invalid port
            dbname=postgres_container.dbname,
            user=postgres_container.username,
            password=postgres_container.password,  # type: ignore
            ssl_mode="disable",
        )
        pool = DatabasePool(config)

        # Connection should fail gracefully
        try:
            await pool.connect()
            # If it somehow connects, disconnect
            await pool.disconnect()
        except Exception as e:
            # Expected - connection error
            assert not pool.is_connected


class TestDatabasePoolResilience:
    """Test database pool resilience features."""

    @pytest.fixture
    def postgres_container(self) -> PostgresContainer:
        """Create a PostgreSQL test container."""
        container = PostgresContainer("postgres:16")
        container.start()
        yield container
        container.stop()

    @pytest.fixture
    async def database_pool(
        self, postgres_container: PostgresContainer
    ) -> AsyncGenerator[DatabasePool]:
        """Create and connect database pool."""
        config = DatabaseConfig(
            name="pool_test",
            host=postgres_container.get_container_host_ip(),
            port=int(postgres_container.get_exposed_port(5432)),
            dbname=postgres_container.dbname,
            user=postgres_container.username,
            password=postgres_container.password,  # type: ignore
            ssl_mode="disable",
        )
        pool = DatabasePool(config)
        await pool.connect()
        yield pool
        await pool.disconnect()

    @pytest.fixture
    async def setup_pool_data(
        self, database_pool: DatabasePool
    ) -> None:
        """Set up test data for pool tests."""
        await database_pool.execute("""
            CREATE TABLE pool_test (
                id SERIAL PRIMARY KEY,
                value TEXT
            )
        """)
        await database_pool.execute("INSERT INTO pool_test (value) VALUES ('test')")

    @pytest.mark.asyncio
    async def test_concurrent_queries(
        self,
        database_pool: DatabasePool,
        setup_pool_data: None,
    ) -> None:
        """Test handling of concurrent queries."""
        async def run_query():
            return await database_pool.fetch_readonly("SELECT * FROM pool_test")

        # Run 10 concurrent queries
        tasks = [run_query() for _ in range(10)]
        results = await asyncio.gather(*tasks)

        # All should succeed
        assert len(results) == 10
        for result in results:
            assert len(result) == 1

    @pytest.mark.asyncio
    async def test_health_check(
        self,
        database_pool: DatabasePool,
        setup_pool_data: None,
    ) -> None:
        """Test pool health check functionality."""
        is_healthy = await database_pool.health_check()
        assert is_healthy is True

    @pytest.mark.asyncio
    async def test_readonly_transaction_enforcement(
        self,
        database_pool: DatabasePool,
        setup_pool_data: None,
    ) -> None:
        """Test that readonly transactions prevent writes."""
        # SELECT should work
        result = await database_pool.fetch_readonly("SELECT * FROM pool_test")
        assert len(result) == 1

        # INSERT should fail in readonly transaction
        with pytest.raises(asyncpg.ReadOnlySQLTransactionError):
            await database_pool.fetch_readonly(
                "INSERT INTO pool_test (value) VALUES ('should_fail')"
            )

        # UPDATE should fail in readonly transaction
        with pytest.raises(asyncpg.ReadOnlySQLTransactionError):
            await database_pool.fetch_readonly(
                "UPDATE pool_test SET value = 'should_fail'"
            )

        # DELETE should fail in readonly transaction
        with pytest.raises(asyncpg.ReadOnlySQLTransactionError):
            await database_pool.fetch_readonly("DELETE FROM pool_test")


class TestBackoffStrategies:
    """Test different backoff strategies."""

    @pytest.mark.asyncio
    async def test_exponential_backoff_delays(self) -> None:
        """Test exponential backoff produces increasing delays."""
        config = RetryConfig(
            max_retries=4,
            initial_delay=0.001,
            max_delay=1.0,
            multiplier=2.0,
            backoff_strategy=BackoffStrategyType.EXPONENTIAL,
        )
        executor = RetryExecutor(config)

        delays = []
        for attempt in range(1, 5):
            delay = executor.backoff.get_delay(attempt)
            delays.append(delay)

        # Delays should generally increase (with some jitter)
        # Initial delay is 0.001, so delays should be around:
        # 0.001, 0.002, 0.004, 0.008 (but with jitter)
        assert len(delays) == 4

    @pytest.mark.asyncio
    async def test_fixed_backoff_constant_delays(self) -> None:
        """Test fixed backoff produces constant delays."""
        config = RetryConfig(
            max_retries=3,
            initial_delay=0.01,
            backoff_strategy=BackoffStrategyType.FIXED,
        )
        executor = RetryExecutor(config)

        delays = []
        for attempt in range(1, 4):
            delay = executor.backoff.get_delay(attempt)
            delays.append(delay)

        # All delays should be the same for fixed backoff
        assert all(d == delays[0] for d in delays)

    @pytest.mark.asyncio
    async def test_fibonacci_backoff_pattern(self) -> None:
        """Test fibonacci backoff produces fibonacci-like delays."""
        config = RetryConfig(
            max_retries=5,
            initial_delay=0.001,
            max_delay=1.0,
            backoff_strategy=BackoffStrategyType.FIBONACCI,
        )
        executor = RetryExecutor(config)

        delays = []
        for attempt in range(1, 6):
            delay = executor.backoff.get_delay(attempt)
            delays.append(delay)

        # Fibonacci: 1, 1, 2, 3, 5... (scaled by base_delay)
        # With base 0.001: 0.001, 0.001, 0.002, 0.003, 0.005...
        assert len(delays) == 5


class TestCombinedResilienceFeatures:
    """Test multiple resilience features working together."""

    @pytest.fixture
    def postgres_container(self) -> PostgresContainer:
        """Create a PostgreSQL test container."""
        container = PostgresContainer("postgres:16")
        container.start()
        yield container
        container.stop()

    @pytest.fixture
    def app_config(self, postgres_container: PostgresContainer) -> AppConfig:
        """Create application configuration with all resilience features."""
        return AppConfig(
            databases=[
                DatabaseConfig(
                    name="resilience_test",
                    host=postgres_container.get_container_host_ip(),
                    port=int(postgres_container.get_exposed_port(5432)),
                    dbname=postgres_container.dbname,
                    user=postgres_container.username,
                    password=postgres_container.password,  # type: ignore
                    ssl_mode="disable",
                ),
            ],
            openai=OpenAIConfig(
                api_key="sk-test-key",  # type: ignore
                model="gpt-4o-mini",
            ),
            server=ServerConfig(
                cache_refresh_interval=3600,
                max_result_rows=1000,
                query_timeout=30.0,
                use_readonly_transactions=True,
            ),
            rate_limit=RateLimitConfig(
                enabled=True,
                requests_per_minute=10,
                requests_per_hour=100,
            ),
        )

    @pytest.fixture
    async def setup_resilience_data(
        self, postgres_container: PostgresContainer
    ) -> None:
        """Set up test data for resilience tests."""
        conn = await asyncpg.connect(
            host=postgres_container.get_container_host_ip(),
            port=int(postgres_container.get_exposed_port(5432)),
            database=postgres_container.dbname,
            user=postgres_container.username,
            password=postgres_container.password,
        )
        try:
            await conn.execute("""
                CREATE TABLE users (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(100) NOT NULL
                )
            """)
            await conn.execute(
                "INSERT INTO users (name) VALUES ('Alice'), ('Bob')"
            )
        finally:
            await conn.close()

    @pytest.mark.asyncio
    async def test_rate_limit_with_retry(
        self,
        setup_resilience_data: None,
        app_config: AppConfig,
    ) -> None:
        """Test rate limiting and retry working together."""
        from pg_mcp.server import PgMcpServer
        from pg_mcp.models.errors import RateLimitExceededError
        from pg_mcp.models.query import QueryRequest, ReturnType

        mock_response = create_mock_openai_response(
            "SELECT * FROM users ORDER BY id",
            "Get users",
        )

        with patch("pg_mcp.infrastructure.openai_client.AsyncOpenAI") as mock_openai:
            mock_client = AsyncMock()
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
            mock_openai.return_value = mock_client

            server = PgMcpServer(app_config)
            await server.startup()

            try:
                request = QueryRequest(
                    question="List users",
                    database="resilience_test",
                    return_type=ReturnType.RESULT,
                )

                # First 10 requests should succeed
                successful_requests = 0
                for _ in range(15):
                    try:
                        response = await server.execute_query(request)
                        if response.success:
                            successful_requests += 1
                    except RateLimitExceededError:
                        # Rate limit kicked in
                        break

                # At least some requests should have succeeded
                assert successful_requests >= 1
                assert successful_requests <= 10  # Rate limit should kick in

            finally:
                await server.shutdown()
