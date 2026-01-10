"""Pytest configuration and fixtures."""

import asyncio
from collections.abc import Generator
from unittest.mock import AsyncMock, MagicMock

import pytest

from pg_mcp.config.models import (
    AppConfig,
    DatabaseConfig,
    OpenAIConfig,
    RateLimitConfig,
    ServerConfig,
)
from pg_mcp.infrastructure.database import DatabasePool, DatabasePoolManager
from pg_mcp.infrastructure.openai_client import OpenAIClient
from pg_mcp.infrastructure.rate_limiter import RateLimiter
from pg_mcp.infrastructure.schema_cache import SchemaCache
from pg_mcp.infrastructure.sql_parser import SQLParser
from pg_mcp.models.schema import (
    ColumnInfo,
    DatabaseSchema,
    IndexInfo,
    IndexType,
    TableInfo,
)


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop]:
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def sample_database_config() -> DatabaseConfig:
    """Sample database configuration."""
    return DatabaseConfig(
        name="test_db",
        host="localhost",
        port=5432,
        database="test",
        user="postgres",
        password="password",  # type: ignore
    )


@pytest.fixture
def sample_openai_config() -> OpenAIConfig:
    """Sample OpenAI configuration."""
    return OpenAIConfig(
        api_key="sk-test-key",  # type: ignore
        model="gpt-4o-mini",
    )


@pytest.fixture
def sample_rate_limit_config() -> RateLimitConfig:
    """Sample rate limit configuration."""
    return RateLimitConfig(
        enabled=True,
        requests_per_minute=10,
        requests_per_hour=100,
        openai_tokens_per_minute=10000,
    )


@pytest.fixture
def sample_server_config(sample_rate_limit_config: RateLimitConfig) -> ServerConfig:
    """Sample server configuration."""
    return ServerConfig(
        cache_refresh_interval=3600,
        max_result_rows=1000,
        query_timeout=30.0,
        use_readonly_transactions=True,
        rate_limit=sample_rate_limit_config,
    )


@pytest.fixture
def sample_app_config(
    sample_database_config: DatabaseConfig,
    sample_openai_config: OpenAIConfig,
    sample_server_config: ServerConfig,
) -> AppConfig:
    """Sample application configuration."""
    return AppConfig(
        databases=[sample_database_config],
        openai=sample_openai_config,
        server=sample_server_config,
    )


@pytest.fixture
def sample_schema() -> DatabaseSchema:
    """Sample database schema for testing."""
    return DatabaseSchema(
        name="test_db",
        tables=[
            TableInfo(
                name="users",
                schema_name="public",
                columns=[
                    ColumnInfo(
                        name="id",
                        data_type="integer",
                        is_nullable=False,
                        is_primary_key=True,
                    ),
                    ColumnInfo(
                        name="name",
                        data_type="varchar",
                        is_nullable=False,
                    ),
                    ColumnInfo(
                        name="email",
                        data_type="varchar",
                        is_nullable=False,
                        is_unique=True,
                    ),
                    ColumnInfo(
                        name="created_at",
                        data_type="timestamp",
                        is_nullable=False,
                    ),
                ],
                indexes=[
                    IndexInfo(
                        name="users_pkey",
                        columns=["id"],
                        index_type=IndexType.BTREE,
                        is_primary=True,
                    ),
                    IndexInfo(
                        name="users_email_idx",
                        columns=["email"],
                        index_type=IndexType.BTREE,
                        is_unique=True,
                    ),
                ],
            ),
            TableInfo(
                name="orders",
                schema_name="public",
                columns=[
                    ColumnInfo(
                        name="id",
                        data_type="integer",
                        is_nullable=False,
                        is_primary_key=True,
                    ),
                    ColumnInfo(
                        name="user_id",
                        data_type="integer",
                        is_nullable=False,
                        foreign_key_table="users",
                        foreign_key_column="id",
                    ),
                    ColumnInfo(
                        name="total",
                        data_type="numeric",
                        is_nullable=False,
                    ),
                    ColumnInfo(
                        name="status",
                        data_type="varchar",
                        is_nullable=False,
                    ),
                ],
            ),
        ],
        cached_at=1704067200.0,  # 2024-01-01
    )


@pytest.fixture
def sql_parser() -> SQLParser:
    """SQL parser instance."""
    return SQLParser()


@pytest.fixture
def schema_cache() -> SchemaCache:
    """Schema cache instance."""
    return SchemaCache(refresh_interval=3600)


@pytest.fixture
def rate_limiter(sample_rate_limit_config: RateLimitConfig) -> RateLimiter:
    """Rate limiter instance."""
    return RateLimiter(sample_rate_limit_config)


@pytest.fixture
def mock_database_pool() -> MagicMock:
    """Mock database pool."""
    pool = MagicMock(spec=DatabasePool)
    pool.fetch = AsyncMock(return_value=[])
    pool.fetch_readonly = AsyncMock(return_value=[])
    pool.fetchrow = AsyncMock(return_value=None)
    pool.execute = AsyncMock(return_value="OK")
    pool.health_check = AsyncMock(return_value=True)
    pool.connect = AsyncMock()
    pool.disconnect = AsyncMock()
    pool.is_connected = True
    return pool


@pytest.fixture
def mock_pool_manager(mock_database_pool: MagicMock) -> MagicMock:
    """Mock database pool manager."""
    manager = MagicMock(spec=DatabasePoolManager)
    manager.get_pool = MagicMock(return_value=mock_database_pool)
    manager.has_pool = MagicMock(return_value=True)
    manager.database_names = ["test_db"]
    manager.add_database = AsyncMock()
    manager.close_all = AsyncMock()
    return manager


@pytest.fixture
def mock_openai_client() -> MagicMock:
    """Mock OpenAI client."""
    client = MagicMock(spec=OpenAIClient)
    client.generate_sql = AsyncMock()
    client.close = AsyncMock()
    return client
