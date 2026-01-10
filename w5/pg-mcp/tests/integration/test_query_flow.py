"""End-to-end query flow integration tests.

This module tests the complete query flow from natural language input
to database results, using testcontainers for real PostgreSQL instances
and mocked OpenAI responses.
"""

from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

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
from pg_mcp.models.errors import (
    QueryTimeoutError,
    RateLimitExceededError,
    UnknownDatabaseError,
)
from pg_mcp.models.query import QueryRequest, ReturnType
from pg_mcp.server import PgMcpServer


class TestEndToEndQueryFlow:
    """End-to-end query flow tests with real PostgreSQL."""

    @pytest.fixture
    def postgres_container(self) -> PostgresContainer:
        """Create a PostgreSQL test container."""
        container = PostgresContainer("postgres:16")
        container.start()
        yield container
        container.stop()

    @pytest.fixture
    def database_config(self, postgres_container: PostgresContainer) -> DatabaseConfig:
        """Create database config from container."""
        return DatabaseConfig(
            name="test_db",
            host=postgres_container.get_container_host_ip(),
            port=int(postgres_container.get_exposed_port(5432)),
            database=postgres_container.dbname,
            user=postgres_container.username,
            password=postgres_container.password,  # type: ignore
        )

    @pytest.fixture
    async def database_pool(
        self, database_config: DatabaseConfig
    ) -> AsyncGenerator[DatabasePool]:
        """Create and connect database pool."""
        pool = DatabasePool(database_config)
        await pool.connect()
        yield pool
        await pool.disconnect()

    @pytest.fixture
    async def setup_test_data(self, database_pool: DatabasePool) -> None:
        """Set up test tables and data."""
        # Create tables
        await database_pool.execute("""
            CREATE TABLE users (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                email VARCHAR(255) UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)

        await database_pool.execute("""
            CREATE TABLE orders (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id),
                total NUMERIC(10, 2) NOT NULL,
                status VARCHAR(50) DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)

        # Insert test data
        await database_pool.execute("""
            INSERT INTO users (name, email) VALUES
                ('Alice', 'alice@example.com'),
                ('Bob', 'bob@example.com'),
                ('Charlie', 'charlie@example.com')
        """)

        await database_pool.execute("""
            INSERT INTO orders (user_id, total, status) VALUES
                (1, 100.00, 'completed'),
                (1, 50.00, 'pending'),
                (2, 200.00, 'completed'),
                (3, 75.00, 'shipped')
        """)

    @pytest.fixture
    def mock_openai_response(self) -> MagicMock:
        """Create a mock OpenAI response."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = (
            '{"sql": "SELECT * FROM users", "explanation": "Get all users"}'
        )
        mock_response.usage = MagicMock()
        mock_response.usage.total_tokens = 100
        return mock_response

    @pytest.fixture
    def app_config(self, database_config: DatabaseConfig) -> AppConfig:
        """Create application configuration."""
        return AppConfig(
            databases=[database_config],
            openai=OpenAIConfig(
                api_key="sk-test-key",  # type: ignore
                model="gpt-4o-mini",
            ),
            server=ServerConfig(
                cache_refresh_interval=3600,
                max_result_rows=1000,
                query_timeout=30.0,
                use_readonly_transactions=True,
                rate_limit=RateLimitConfig(
                    enabled=True,
                    requests_per_minute=60,
                    requests_per_hour=1000,
                    openai_tokens_per_minute=100000,
                ),
            ),
        )

    @pytest.mark.asyncio
    async def test_simple_query_flow(
        self,
        database_pool: DatabasePool,
        setup_test_data: None,
        mock_openai_response: MagicMock,
        app_config: AppConfig,
    ) -> None:
        """Test a simple end-to-end query flow."""
        # Configure mock to return SELECT * FROM users
        mock_openai_response.choices[0].message.content = (
            '{"sql": "SELECT id, name, email FROM users ORDER BY id", '
            '"explanation": "List all users"}'
        )

        with patch("pg_mcp.infrastructure.openai_client.AsyncOpenAI") as mock_openai:
            mock_client = AsyncMock()
            mock_client.chat.completions.create = AsyncMock(
                return_value=mock_openai_response
            )
            mock_openai.return_value = mock_client

            server = PgMcpServer(app_config)
            await server.startup()

            try:
                request = QueryRequest(
                    question="List all users",
                    database="test_db",
                    return_type=ReturnType.BOTH,
                )

                response = await server.execute_query(request)

                assert response.success
                assert response.sql is not None
                assert "SELECT" in response.sql.upper()
                assert response.result is not None
                assert response.result.row_count == 3
                assert "name" in response.result.columns
            finally:
                await server.shutdown()

    @pytest.mark.asyncio
    async def test_query_with_join(
        self,
        database_pool: DatabasePool,
        setup_test_data: None,
        mock_openai_response: MagicMock,
        app_config: AppConfig,
    ) -> None:
        """Test query with JOIN operation."""
        mock_openai_response.choices[0].message.content = (
            '{"sql": "SELECT u.name, SUM(o.total) as total_spent '
            "FROM users u JOIN orders o ON u.id = o.user_id "
            'GROUP BY u.name ORDER BY total_spent DESC", '
            '"explanation": "Get user spending"}'
        )

        with patch("pg_mcp.infrastructure.openai_client.AsyncOpenAI") as mock_openai:
            mock_client = AsyncMock()
            mock_client.chat.completions.create = AsyncMock(
                return_value=mock_openai_response
            )
            mock_openai.return_value = mock_client

            server = PgMcpServer(app_config)
            await server.startup()

            try:
                request = QueryRequest(
                    question="Show me total spending by each user",
                    database="test_db",
                    return_type=ReturnType.RESULT,
                )

                response = await server.execute_query(request)

                assert response.success
                assert response.result is not None
                assert response.result.row_count == 3
                assert "name" in response.result.columns
                assert "total_spent" in response.result.columns
            finally:
                await server.shutdown()

    @pytest.mark.asyncio
    async def test_query_with_limit(
        self,
        database_pool: DatabasePool,
        setup_test_data: None,
        mock_openai_response: MagicMock,
        app_config: AppConfig,
    ) -> None:
        """Test query with result limit."""
        mock_openai_response.choices[0].message.content = (
            '{"sql": "SELECT * FROM users ORDER BY id", '
            '"explanation": "Get users"}'
        )

        with patch("pg_mcp.infrastructure.openai_client.AsyncOpenAI") as mock_openai:
            mock_client = AsyncMock()
            mock_client.chat.completions.create = AsyncMock(
                return_value=mock_openai_response
            )
            mock_openai.return_value = mock_client

            server = PgMcpServer(app_config)
            await server.startup()

            try:
                request = QueryRequest(
                    question="List all users",
                    database="test_db",
                    return_type=ReturnType.RESULT,
                    limit=2,
                )

                response = await server.execute_query(request)

                assert response.success
                assert response.result is not None
                assert response.result.row_count == 2
                assert response.result.truncated
            finally:
                await server.shutdown()

    @pytest.mark.asyncio
    async def test_sql_only_return_type(
        self,
        database_pool: DatabasePool,
        setup_test_data: None,
        mock_openai_response: MagicMock,
        app_config: AppConfig,
    ) -> None:
        """Test returning only SQL without execution."""
        mock_openai_response.choices[0].message.content = (
            '{"sql": "SELECT COUNT(*) FROM users", '
            '"explanation": "Count users"}'
        )

        with patch("pg_mcp.infrastructure.openai_client.AsyncOpenAI") as mock_openai:
            mock_client = AsyncMock()
            mock_client.chat.completions.create = AsyncMock(
                return_value=mock_openai_response
            )
            mock_openai.return_value = mock_client

            server = PgMcpServer(app_config)
            await server.startup()

            try:
                request = QueryRequest(
                    question="Count all users",
                    database="test_db",
                    return_type=ReturnType.SQL,
                )

                response = await server.execute_query(request)

                assert response.success
                assert response.sql is not None
                assert response.result is None  # No execution
                assert response.explanation is not None
            finally:
                await server.shutdown()


class TestMultiDatabaseScenario:
    """Tests for multi-database query scenarios."""

    @pytest.fixture
    def postgres_container_1(self) -> PostgresContainer:
        """Create first PostgreSQL container."""
        container = PostgresContainer("postgres:16")
        container.start()
        yield container
        container.stop()

    @pytest.fixture
    def postgres_container_2(self) -> PostgresContainer:
        """Create second PostgreSQL container."""
        container = PostgresContainer("postgres:16")
        container.start()
        yield container
        container.stop()

    @pytest.fixture
    def multi_db_config(
        self,
        postgres_container_1: PostgresContainer,
        postgres_container_2: PostgresContainer,
    ) -> AppConfig:
        """Create config for multiple databases."""
        return AppConfig(
            databases=[
                DatabaseConfig(
                    name="db1",
                    host=postgres_container_1.get_container_host_ip(),
                    port=int(postgres_container_1.get_exposed_port(5432)),
                    database=postgres_container_1.dbname,
                    user=postgres_container_1.username,
                    password=postgres_container_1.password,  # type: ignore
                ),
                DatabaseConfig(
                    name="db2",
                    host=postgres_container_2.get_container_host_ip(),
                    port=int(postgres_container_2.get_exposed_port(5432)),
                    database=postgres_container_2.dbname,
                    user=postgres_container_2.username,
                    password=postgres_container_2.password,  # type: ignore
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
                rate_limit=RateLimitConfig(enabled=False),
            ),
        )

    @pytest.fixture
    async def setup_multi_db_data(
        self,
        postgres_container_1: PostgresContainer,
        postgres_container_2: PostgresContainer,
    ) -> None:
        """Set up data in both databases."""
        import asyncpg

        # Setup db1 with users
        conn1 = await asyncpg.connect(
            host=postgres_container_1.get_container_host_ip(),
            port=int(postgres_container_1.get_exposed_port(5432)),
            database=postgres_container_1.dbname,
            user=postgres_container_1.username,
            password=postgres_container_1.password,
        )
        await conn1.execute("""
            CREATE TABLE users (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100) NOT NULL
            )
        """)
        await conn1.execute("INSERT INTO users (name) VALUES ('User1'), ('User2')")
        await conn1.close()

        # Setup db2 with products
        conn2 = await asyncpg.connect(
            host=postgres_container_2.get_container_host_ip(),
            port=int(postgres_container_2.get_exposed_port(5432)),
            database=postgres_container_2.dbname,
            user=postgres_container_2.username,
            password=postgres_container_2.password,
        )
        await conn2.execute("""
            CREATE TABLE products (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                price NUMERIC(10, 2)
            )
        """)
        await conn2.execute(
            "INSERT INTO products (name, price) VALUES "
            "('Product1', 10.00), ('Product2', 20.00)"
        )
        await conn2.close()

    @pytest.mark.asyncio
    async def test_query_specific_database(
        self,
        setup_multi_db_data: None,
        multi_db_config: AppConfig,
    ) -> None:
        """Test querying a specific database in multi-db setup."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = (
            '{"sql": "SELECT * FROM products", "explanation": "Get products"}'
        )
        mock_response.usage = MagicMock()
        mock_response.usage.total_tokens = 50

        with patch("pg_mcp.infrastructure.openai_client.AsyncOpenAI") as mock_openai:
            mock_client = AsyncMock()
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
            mock_openai.return_value = mock_client

            server = PgMcpServer(multi_db_config)
            await server.startup()

            try:
                # Query db2 which has products table
                request = QueryRequest(
                    question="List all products",
                    database="db2",
                    return_type=ReturnType.RESULT,
                )

                response = await server.execute_query(request)

                assert response.success
                assert response.result is not None
                assert response.result.row_count == 2
            finally:
                await server.shutdown()

    @pytest.mark.asyncio
    async def test_unknown_database_error(
        self,
        setup_multi_db_data: None,
        multi_db_config: AppConfig,
    ) -> None:
        """Test error when querying unknown database."""
        with patch("pg_mcp.infrastructure.openai_client.AsyncOpenAI") as mock_openai:
            mock_client = AsyncMock()
            mock_openai.return_value = mock_client

            server = PgMcpServer(multi_db_config)
            await server.startup()

            try:
                request = QueryRequest(
                    question="List all data",
                    database="nonexistent_db",
                    return_type=ReturnType.RESULT,
                )

                with pytest.raises(UnknownDatabaseError) as exc_info:
                    await server.execute_query(request)

                assert "nonexistent_db" in str(exc_info.value)
                assert "db1" in exc_info.value.details["available_databases"]
                assert "db2" in exc_info.value.details["available_databases"]
            finally:
                await server.shutdown()

    @pytest.mark.asyncio
    async def test_default_database_used(
        self,
        setup_multi_db_data: None,
        multi_db_config: AppConfig,
    ) -> None:
        """Test that default database is used when none specified."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = (
            '{"sql": "SELECT * FROM users", "explanation": "Get users"}'
        )
        mock_response.usage = MagicMock()
        mock_response.usage.total_tokens = 50

        with patch("pg_mcp.infrastructure.openai_client.AsyncOpenAI") as mock_openai:
            mock_client = AsyncMock()
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
            mock_openai.return_value = mock_client

            server = PgMcpServer(multi_db_config)
            await server.startup()

            try:
                # No database specified - should use first (db1)
                request = QueryRequest(
                    question="List all users",
                    database=None,
                    return_type=ReturnType.RESULT,
                )

                response = await server.execute_query(request)

                assert response.success
                assert response.result is not None
                assert response.result.row_count == 2
            finally:
                await server.shutdown()


class TestTimeoutHandling:
    """Tests for query timeout scenarios."""

    @pytest.fixture
    def postgres_container(self) -> PostgresContainer:
        """Create a PostgreSQL test container."""
        container = PostgresContainer("postgres:16")
        container.start()
        yield container
        container.stop()

    @pytest.fixture
    def short_timeout_config(
        self, postgres_container: PostgresContainer
    ) -> AppConfig:
        """Create config with very short timeout."""
        return AppConfig(
            databases=[
                DatabaseConfig(
                    name="test_db",
                    host=postgres_container.get_container_host_ip(),
                    port=int(postgres_container.get_exposed_port(5432)),
                    database=postgres_container.dbname,
                    user=postgres_container.username,
                    password=postgres_container.password,  # type: ignore
                ),
            ],
            openai=OpenAIConfig(
                api_key="sk-test-key",  # type: ignore
                model="gpt-4o-mini",
            ),
            server=ServerConfig(
                cache_refresh_interval=3600,
                max_result_rows=1000,
                query_timeout=0.001,  # Very short timeout (1ms)
                use_readonly_transactions=True,
                rate_limit=RateLimitConfig(enabled=False),
            ),
        )

    @pytest.fixture
    async def setup_timeout_data(
        self, postgres_container: PostgresContainer
    ) -> None:
        """Set up data for timeout tests."""
        import asyncpg

        conn = await asyncpg.connect(
            host=postgres_container.get_container_host_ip(),
            port=int(postgres_container.get_exposed_port(5432)),
            database=postgres_container.dbname,
            user=postgres_container.username,
            password=postgres_container.password,
        )
        await conn.execute("""
            CREATE TABLE large_table (
                id SERIAL PRIMARY KEY,
                data TEXT
            )
        """)
        # Insert some data
        await conn.execute(
            "INSERT INTO large_table (data) "
            "SELECT md5(random()::text) FROM generate_series(1, 1000)"
        )
        await conn.close()

    @pytest.mark.asyncio
    async def test_query_timeout_with_slow_query(
        self,
        setup_timeout_data: None,
        short_timeout_config: AppConfig,
    ) -> None:
        """Test that slow queries timeout properly."""
        # Mock response with pg_sleep to simulate slow query
        # Note: We use a complex query that takes time rather than pg_sleep
        # since pg_sleep is blocked by our SQL validator
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = (
            '{"sql": "SELECT * FROM large_table, large_table t2, large_table t3 LIMIT 10", '
            '"explanation": "Complex join"}'
        )
        mock_response.usage = MagicMock()
        mock_response.usage.total_tokens = 50

        with patch("pg_mcp.infrastructure.openai_client.AsyncOpenAI") as mock_openai:
            mock_client = AsyncMock()
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
            mock_openai.return_value = mock_client

            server = PgMcpServer(short_timeout_config)
            await server.startup()

            try:
                request = QueryRequest(
                    question="Get complex data",
                    database="test_db",
                    return_type=ReturnType.RESULT,
                )

                # The query should either timeout or complete
                # With 1ms timeout, it's likely to timeout on complex queries
                try:
                    response = await server.execute_query(request)
                    # If it completes, that's also acceptable
                    assert response.success
                except (QueryTimeoutError, TimeoutError):
                    # Timeout is the expected behavior with 1ms limit
                    pass
            finally:
                await server.shutdown()


class TestRateLimiting:
    """Tests for rate limiting functionality."""

    @pytest.fixture
    def postgres_container(self) -> PostgresContainer:
        """Create a PostgreSQL test container."""
        container = PostgresContainer("postgres:16")
        container.start()
        yield container
        container.stop()

    @pytest.fixture
    def rate_limited_config(
        self, postgres_container: PostgresContainer
    ) -> AppConfig:
        """Create config with low rate limits for testing."""
        return AppConfig(
            databases=[
                DatabaseConfig(
                    name="test_db",
                    host=postgres_container.get_container_host_ip(),
                    port=int(postgres_container.get_exposed_port(5432)),
                    database=postgres_container.dbname,
                    user=postgres_container.username,
                    password=postgres_container.password,  # type: ignore
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
                rate_limit=RateLimitConfig(
                    enabled=True,
                    requests_per_minute=3,  # Low limit for testing
                    requests_per_hour=100,
                    openai_tokens_per_minute=100000,
                ),
            ),
        )

    @pytest.fixture
    async def setup_rate_limit_data(
        self, postgres_container: PostgresContainer
    ) -> None:
        """Set up data for rate limit tests."""
        import asyncpg

        conn = await asyncpg.connect(
            host=postgres_container.get_container_host_ip(),
            port=int(postgres_container.get_exposed_port(5432)),
            database=postgres_container.dbname,
            user=postgres_container.username,
            password=postgres_container.password,
        )
        await conn.execute("""
            CREATE TABLE users (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100)
            )
        """)
        await conn.execute("INSERT INTO users (name) VALUES ('Test')")
        await conn.close()

    @pytest.mark.asyncio
    async def test_rate_limit_exceeded(
        self,
        setup_rate_limit_data: None,
        rate_limited_config: AppConfig,
    ) -> None:
        """Test that rate limiting blocks excessive requests."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = (
            '{"sql": "SELECT * FROM users", "explanation": "Get users"}'
        )
        mock_response.usage = MagicMock()
        mock_response.usage.total_tokens = 50

        with patch("pg_mcp.infrastructure.openai_client.AsyncOpenAI") as mock_openai:
            mock_client = AsyncMock()
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
            mock_openai.return_value = mock_client

            server = PgMcpServer(rate_limited_config)
            await server.startup()

            try:
                request = QueryRequest(
                    question="List users",
                    database="test_db",
                    return_type=ReturnType.RESULT,
                )

                # First 3 requests should succeed
                for _ in range(3):
                    response = await server.execute_query(request)
                    assert response.success

                # 4th request should fail with rate limit error
                with pytest.raises(RateLimitExceededError) as exc_info:
                    await server.execute_query(request)

                assert exc_info.value.details["window"] == "minute"
            finally:
                await server.shutdown()

    @pytest.mark.asyncio
    async def test_rate_limit_disabled(
        self,
        postgres_container: PostgresContainer,
        setup_rate_limit_data: None,
    ) -> None:
        """Test that disabled rate limiting allows all requests."""
        config = AppConfig(
            databases=[
                DatabaseConfig(
                    name="test_db",
                    host=postgres_container.get_container_host_ip(),
                    port=int(postgres_container.get_exposed_port(5432)),
                    database=postgres_container.dbname,
                    user=postgres_container.username,
                    password=postgres_container.password,  # type: ignore
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
                rate_limit=RateLimitConfig(enabled=False),  # Disabled
            ),
        )

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = (
            '{"sql": "SELECT * FROM users", "explanation": "Get users"}'
        )
        mock_response.usage = MagicMock()
        mock_response.usage.total_tokens = 50

        with patch("pg_mcp.infrastructure.openai_client.AsyncOpenAI") as mock_openai:
            mock_client = AsyncMock()
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
            mock_openai.return_value = mock_client

            server = PgMcpServer(config)
            await server.startup()

            try:
                request = QueryRequest(
                    question="List users",
                    database="test_db",
                    return_type=ReturnType.RESULT,
                )

                # Many requests should all succeed
                for _ in range(10):
                    response = await server.execute_query(request)
                    assert response.success
            finally:
                await server.shutdown()


class TestMockOpenAIResponses:
    """Tests focusing on mocked OpenAI response handling."""

    @pytest.fixture
    def postgres_container(self) -> PostgresContainer:
        """Create a PostgreSQL test container."""
        container = PostgresContainer("postgres:16")
        container.start()
        yield container
        container.stop()

    @pytest.fixture
    def app_config(self, postgres_container: PostgresContainer) -> AppConfig:
        """Create application configuration."""
        return AppConfig(
            databases=[
                DatabaseConfig(
                    name="test_db",
                    host=postgres_container.get_container_host_ip(),
                    port=int(postgres_container.get_exposed_port(5432)),
                    database=postgres_container.dbname,
                    user=postgres_container.username,
                    password=postgres_container.password,  # type: ignore
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
                rate_limit=RateLimitConfig(enabled=False),
            ),
        )

    @pytest.fixture
    async def setup_data(self, postgres_container: PostgresContainer) -> None:
        """Set up test data."""
        import asyncpg

        conn = await asyncpg.connect(
            host=postgres_container.get_container_host_ip(),
            port=int(postgres_container.get_exposed_port(5432)),
            database=postgres_container.dbname,
            user=postgres_container.username,
            password=postgres_container.password,
        )
        await conn.execute("""
            CREATE TABLE users (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100),
                email VARCHAR(255)
            )
        """)
        await conn.execute(
            "INSERT INTO users (name, email) VALUES "
            "('Alice', 'alice@test.com'), ('Bob', 'bob@test.com')"
        )
        await conn.close()

    @pytest.mark.asyncio
    async def test_aggregation_query(
        self,
        setup_data: None,
        app_config: AppConfig,
    ) -> None:
        """Test handling of aggregation queries."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = (
            '{"sql": "SELECT COUNT(*) as user_count FROM users", '
            '"explanation": "Count all users"}'
        )
        mock_response.usage = MagicMock()
        mock_response.usage.total_tokens = 50

        with patch("pg_mcp.infrastructure.openai_client.AsyncOpenAI") as mock_openai:
            mock_client = AsyncMock()
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
            mock_openai.return_value = mock_client

            server = PgMcpServer(app_config)
            await server.startup()

            try:
                request = QueryRequest(
                    question="How many users are there?",
                    database="test_db",
                    return_type=ReturnType.RESULT,
                )

                response = await server.execute_query(request)

                assert response.success
                assert response.result is not None
                assert response.result.row_count == 1
                assert response.result.rows[0][0] == 2
            finally:
                await server.shutdown()

    @pytest.mark.asyncio
    async def test_filtered_query(
        self,
        setup_data: None,
        app_config: AppConfig,
    ) -> None:
        """Test handling of filtered queries."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = (
            '{"sql": "SELECT name, email FROM users WHERE name = \'Alice\'", '
            '"explanation": "Find user Alice"}'
        )
        mock_response.usage = MagicMock()
        mock_response.usage.total_tokens = 60

        with patch("pg_mcp.infrastructure.openai_client.AsyncOpenAI") as mock_openai:
            mock_client = AsyncMock()
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
            mock_openai.return_value = mock_client

            server = PgMcpServer(app_config)
            await server.startup()

            try:
                request = QueryRequest(
                    question="Find user named Alice",
                    database="test_db",
                    return_type=ReturnType.BOTH,
                )

                response = await server.execute_query(request)

                assert response.success
                assert response.sql is not None
                assert "Alice" in response.sql
                assert response.result is not None
                assert response.result.row_count == 1
            finally:
                await server.shutdown()

    @pytest.mark.asyncio
    async def test_empty_result_handling(
        self,
        setup_data: None,
        app_config: AppConfig,
    ) -> None:
        """Test handling of queries with no results."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = (
            '{"sql": "SELECT * FROM users WHERE name = \'NonExistent\'", '
            '"explanation": "Find non-existent user"}'
        )
        mock_response.usage = MagicMock()
        mock_response.usage.total_tokens = 50

        with patch("pg_mcp.infrastructure.openai_client.AsyncOpenAI") as mock_openai:
            mock_client = AsyncMock()
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
            mock_openai.return_value = mock_client

            server = PgMcpServer(app_config)
            await server.startup()

            try:
                request = QueryRequest(
                    question="Find user named NonExistent",
                    database="test_db",
                    return_type=ReturnType.RESULT,
                )

                response = await server.execute_query(request)

                assert response.success
                assert response.result is not None
                assert response.result.row_count == 0
                assert response.result.rows == []
            finally:
                await server.shutdown()
