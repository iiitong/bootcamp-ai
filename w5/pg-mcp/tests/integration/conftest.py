"""Shared fixtures for integration tests.

This module provides:
- PostgreSQL container fixtures using testcontainers
- Database setup/teardown helpers
- Configuration fixtures for various test scenarios
"""

from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock

import asyncpg
import pytest
from testcontainers.postgres import PostgresContainer

from pg_mcp.config.models import (
    AccessPolicyConfig,
    AppConfig,
    ColumnAccessConfig,
    DatabaseConfig,
    ExplainPolicyConfig,
    OpenAIConfig,
    RateLimitConfig,
    SelectStarPolicy,
    ServerConfig,
    TableAccessConfig,
)
from pg_mcp.infrastructure.database import DatabasePool


# =============================================================================
# PostgreSQL Container Fixtures
# =============================================================================


@pytest.fixture(scope="function")
def postgres_container() -> PostgresContainer:
    """Create a PostgreSQL test container.

    This fixture creates a fresh PostgreSQL container for each test function.
    Use this for tests that need isolation or modify data.
    """
    container = PostgresContainer("postgres:16")
    container.start()
    yield container
    container.stop()


@pytest.fixture(scope="module")
def shared_postgres_container() -> PostgresContainer:
    """Create a shared PostgreSQL container for a module.

    This fixture creates a single container shared across all tests in a module.
    Use this for read-only tests to improve performance.
    """
    container = PostgresContainer("postgres:16")
    container.start()
    yield container
    container.stop()


# =============================================================================
# Database Configuration Fixtures
# =============================================================================


@pytest.fixture
def database_config(postgres_container: PostgresContainer) -> DatabaseConfig:
    """Create database config from container."""
    return DatabaseConfig(
        name="test_db",
        host=postgres_container.get_container_host_ip(),
        port=int(postgres_container.get_exposed_port(5432)),
        dbname=postgres_container.dbname,
        user=postgres_container.username,
        password=postgres_container.password,  # type: ignore
        ssl_mode="disable",  # testcontainers doesn't support SSL
    )


@pytest.fixture
def database_config_with_access_policy(
    postgres_container: PostgresContainer,
) -> DatabaseConfig:
    """Create database config with access policy for testing."""
    return DatabaseConfig(
        name="policy_test_db",
        host=postgres_container.get_container_host_ip(),
        port=int(postgres_container.get_exposed_port(5432)),
        dbname=postgres_container.dbname,
        user=postgres_container.username,
        password=postgres_container.password,  # type: ignore
        ssl_mode="disable",
        access_policy=AccessPolicyConfig(
            allowed_schemas=["public"],
            tables=TableAccessConfig(
                allowed=["users", "orders", "products"],
                denied=["audit_log", "system_config"],
            ),
            columns=ColumnAccessConfig(
                denied=["users.password_hash", "users.secret_key"],
                denied_patterns=["*._password*", "*._secret*", "*._token*"],
                select_star_policy=SelectStarPolicy.REJECT,
            ),
            explain_policy=ExplainPolicyConfig(
                enabled=True,
                max_estimated_rows=10000,
                max_estimated_cost=5000.0,
            ),
        ),
    )


# =============================================================================
# Database Pool Fixtures
# =============================================================================


@pytest.fixture
async def database_pool(
    database_config: DatabaseConfig,
) -> AsyncGenerator[DatabasePool]:
    """Create and connect database pool."""
    pool = DatabasePool(database_config)
    await pool.connect()
    yield pool
    await pool.disconnect()


@pytest.fixture
async def raw_connection(
    postgres_container: PostgresContainer,
) -> AsyncGenerator[asyncpg.Connection]:
    """Create a raw asyncpg connection for direct database operations."""
    conn = await asyncpg.connect(
        host=postgres_container.get_container_host_ip(),
        port=int(postgres_container.get_exposed_port(5432)),
        database=postgres_container.dbname,
        user=postgres_container.username,
        password=postgres_container.password,
    )
    yield conn
    await conn.close()


# =============================================================================
# Application Configuration Fixtures
# =============================================================================


@pytest.fixture
def openai_config() -> OpenAIConfig:
    """Create OpenAI configuration for testing."""
    return OpenAIConfig(
        api_key="sk-test-key",  # type: ignore
        model="gpt-4o-mini",
    )


@pytest.fixture
def server_config() -> ServerConfig:
    """Create server configuration for testing."""
    return ServerConfig(
        cache_refresh_interval=3600,
        max_result_rows=1000,
        query_timeout=30.0,
        use_readonly_transactions=True,
    )


@pytest.fixture
def rate_limit_config_low() -> RateLimitConfig:
    """Create rate limit config with low limits for testing."""
    return RateLimitConfig(
        enabled=True,
        requests_per_minute=5,
        requests_per_hour=20,
        openai_tokens_per_minute=1000,
    )


@pytest.fixture
def app_config(
    database_config: DatabaseConfig,
    openai_config: OpenAIConfig,
    server_config: ServerConfig,
) -> AppConfig:
    """Create application configuration."""
    return AppConfig(
        databases=[database_config],
        openai=openai_config,
        server=server_config,
        rate_limit=RateLimitConfig(enabled=False),
    )


@pytest.fixture
def app_config_with_rate_limit(
    database_config: DatabaseConfig,
    openai_config: OpenAIConfig,
    server_config: ServerConfig,
    rate_limit_config_low: RateLimitConfig,
) -> AppConfig:
    """Create application configuration with rate limiting enabled."""
    return AppConfig(
        databases=[database_config],
        openai=openai_config,
        server=server_config,
        rate_limit=rate_limit_config_low,
    )


@pytest.fixture
def app_config_with_access_policy(
    database_config_with_access_policy: DatabaseConfig,
    openai_config: OpenAIConfig,
    server_config: ServerConfig,
) -> AppConfig:
    """Create application configuration with access policy."""
    return AppConfig(
        databases=[database_config_with_access_policy],
        openai=openai_config,
        server=server_config,
        rate_limit=RateLimitConfig(enabled=False),
    )


# =============================================================================
# Mock Fixtures
# =============================================================================


@pytest.fixture
def mock_openai_response() -> MagicMock:
    """Create a mock OpenAI response."""
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = (
        '{"sql": "SELECT * FROM users", "explanation": "Get all users"}'
    )
    mock_response.usage = MagicMock()
    mock_response.usage.total_tokens = 100
    return mock_response


def create_mock_openai_response(sql: str, explanation: str, tokens: int = 100) -> MagicMock:
    """Factory function to create mock OpenAI responses with custom SQL."""
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = (
        f'{{"sql": "{sql}", "explanation": "{explanation}"}}'
    )
    mock_response.usage = MagicMock()
    mock_response.usage.total_tokens = tokens
    return mock_response


# =============================================================================
# Test Data Setup Fixtures
# =============================================================================


@pytest.fixture
async def setup_basic_tables(database_pool: DatabasePool) -> None:
    """Set up basic test tables: users and orders."""
    await database_pool.execute("""
        CREATE TABLE users (
            id SERIAL PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            email VARCHAR(255) UNIQUE NOT NULL,
            password_hash VARCHAR(255),
            secret_key VARCHAR(255),
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
        INSERT INTO users (name, email, password_hash, secret_key) VALUES
            ('Alice', 'alice@example.com', 'hash123', 'secret_alice'),
            ('Bob', 'bob@example.com', 'hash456', 'secret_bob'),
            ('Charlie', 'charlie@example.com', 'hash789', 'secret_charlie')
    """)

    await database_pool.execute("""
        INSERT INTO orders (user_id, total, status) VALUES
            (1, 100.00, 'completed'),
            (1, 50.00, 'pending'),
            (2, 200.00, 'completed'),
            (3, 75.00, 'shipped')
    """)


@pytest.fixture
async def setup_products_table(database_pool: DatabasePool) -> None:
    """Set up products table for additional testing."""
    await database_pool.execute("""
        CREATE TABLE products (
            id SERIAL PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            price NUMERIC(10, 2) NOT NULL,
            stock INTEGER DEFAULT 0
        )
    """)

    await database_pool.execute("""
        INSERT INTO products (name, price, stock) VALUES
            ('Widget', 29.99, 100),
            ('Gadget', 49.99, 50),
            ('Gizmo', 19.99, 200)
    """)


@pytest.fixture
async def setup_sensitive_tables(database_pool: DatabasePool) -> None:
    """Set up tables with sensitive data for security testing."""
    await database_pool.execute("""
        CREATE TABLE audit_log (
            id SERIAL PRIMARY KEY,
            action VARCHAR(100) NOT NULL,
            user_id INTEGER,
            timestamp TIMESTAMP DEFAULT NOW(),
            details JSONB
        )
    """)

    await database_pool.execute("""
        CREATE TABLE system_config (
            id SERIAL PRIMARY KEY,
            key VARCHAR(100) NOT NULL,
            value TEXT,
            is_secret BOOLEAN DEFAULT FALSE
        )
    """)

    # Insert test data
    await database_pool.execute("""
        INSERT INTO audit_log (action, user_id, details) VALUES
            ('login', 1, '{"ip": "192.168.1.1"}'),
            ('query', 1, '{"sql": "SELECT * FROM users"}')
    """)

    await database_pool.execute("""
        INSERT INTO system_config (key, value, is_secret) VALUES
            ('app_name', 'Test App', FALSE),
            ('api_key', 'super_secret_key', TRUE)
    """)


@pytest.fixture
async def setup_large_table(database_pool: DatabasePool) -> None:
    """Set up a table with many rows for performance testing."""
    await database_pool.execute("""
        CREATE TABLE large_data (
            id SERIAL PRIMARY KEY,
            data TEXT,
            category INTEGER,
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)

    # Insert 10,000 rows
    await database_pool.execute("""
        INSERT INTO large_data (data, category)
        SELECT
            md5(random()::text),
            (random() * 10)::integer
        FROM generate_series(1, 10000)
    """)


@pytest.fixture
async def setup_all_tables(
    database_pool: DatabasePool,
    setup_basic_tables: None,
    setup_products_table: None,
    setup_sensitive_tables: None,
) -> None:
    """Set up all test tables."""
    # This fixture depends on others, so they will all run
    pass
