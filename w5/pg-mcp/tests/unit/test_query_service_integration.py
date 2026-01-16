# tests/unit/test_query_service_integration.py

"""Tests for QueryService integration with QueryExecutorManager.

This module tests the integration between QueryService and the new components:
- MetricsCollector for observability
- AuditLogger for security logging
- QueryExecutorManager for policy enforcement and EXPLAIN validation
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import SecretStr

from pg_mcp.config.models import (
    AccessPolicyConfig,
    AppConfig,
    ColumnAccessConfig,
    DatabaseConfig,
    ExplainPolicyConfig,
    OpenAISettings,
    RateLimitSettings,
    ServerSettings,
    SSLMode,
    TableAccessConfig,
)
from pg_mcp.infrastructure.database import DatabasePool, DatabasePoolManager
from pg_mcp.infrastructure.openai_client import OpenAIClient
from pg_mcp.infrastructure.rate_limiter import RateLimiter
from pg_mcp.infrastructure.schema_cache import SchemaCache
from pg_mcp.infrastructure.sql_parser import ParsedSQLInfo, SQLParser
from pg_mcp.models import QueryRequest, ReturnType, SQLGenerationResult
from pg_mcp.models.query import QueryResult
from pg_mcp.models.schema import ColumnInfo, DatabaseSchema, TableInfo
from pg_mcp.observability.metrics import MetricsCollector
from pg_mcp.security.access_policy import (
    ColumnAccessDeniedError,
    TableAccessDeniedError,
)
from pg_mcp.security.audit_logger import AuditLogger
from pg_mcp.security.explain_validator import QueryTooExpensiveError
from pg_mcp.services.query_executor import QueryExecutor
from pg_mcp.services.query_executor_manager import QueryExecutorManager
from pg_mcp.services.query_service import QueryService, QueryServiceConfig


class TestQueryServiceWithMetrics:
    """Tests for QueryService with MetricsCollector integration."""

    @pytest.fixture
    def sample_schema(self) -> DatabaseSchema:
        """Create sample database schema."""
        return DatabaseSchema(
            name="test_db",
            tables=[
                TableInfo(
                    name="users",
                    schema_name="public",
                    columns=[
                        ColumnInfo(name="id", data_type="integer", is_primary_key=True),
                        ColumnInfo(name="name", data_type="varchar(100)"),
                        ColumnInfo(name="email", data_type="varchar(100)"),
                    ],
                ),
            ],
        )

    @pytest.fixture
    def db_config(self) -> DatabaseConfig:
        """Create test database config."""
        return DatabaseConfig(
            name="test_db",
            host="localhost",
            dbname="testdb",
            user="testuser",
            ssl_mode=SSLMode.DISABLE,
        )

    @pytest.fixture
    def app_config(self, db_config) -> AppConfig:
        """Create test app config."""
        with patch.dict("os.environ", {"PG_MCP_OPENAI_API_KEY": "test-key"}):
            return AppConfig(
                databases=[db_config],
                openai=OpenAISettings(api_key=SecretStr("test-key")),
                server=ServerSettings(),
                rate_limit=RateLimitSettings(enabled=False),
            )

    @pytest.fixture
    def mock_pool_manager(self) -> MagicMock:
        """Create mock pool manager."""
        manager = MagicMock(spec=DatabasePoolManager)
        mock_pool = MagicMock(spec=DatabasePool)
        mock_pool.fetch_readonly = AsyncMock(
            return_value=[{"id": 1, "name": "Alice", "email": "alice@example.com"}]
        )
        manager.get_pool.return_value = mock_pool
        return manager

    @pytest.fixture
    def mock_schema_cache(self, sample_schema) -> MagicMock:
        """Create mock schema cache."""
        cache = MagicMock(spec=SchemaCache)
        cache.get_or_refresh = AsyncMock(return_value=sample_schema)
        return cache

    @pytest.fixture
    def mock_openai_client(self) -> MagicMock:
        """Create mock OpenAI client."""
        client = MagicMock(spec=OpenAIClient)
        client.generate_sql = AsyncMock(
            return_value=SQLGenerationResult(
                sql="SELECT id, name, email FROM users",
                explanation="Fetches all users",
                tokens_used=100,
            )
        )
        return client

    @pytest.fixture
    def mock_sql_parser(self) -> MagicMock:
        """Create mock SQL parser."""
        parser = MagicMock(spec=SQLParser)
        parser.validate_and_raise = MagicMock()
        parser.add_limit = MagicMock(
            side_effect=lambda sql, limit: f"{sql} LIMIT {limit}"
        )
        return parser

    @pytest.fixture
    def mock_rate_limiter(self) -> MagicMock:
        """Create mock rate limiter."""
        limiter = MagicMock(spec=RateLimiter)
        limiter.check_request = AsyncMock()
        limiter.record_tokens = AsyncMock()
        return limiter

    @pytest.fixture
    def metrics_collector(self) -> MetricsCollector:
        """Create real metrics collector for testing."""
        from prometheus_client import CollectorRegistry

        return MetricsCollector(registry=CollectorRegistry())

    @pytest.fixture
    def query_service_with_metrics(
        self,
        app_config,
        mock_pool_manager,
        mock_schema_cache,
        mock_openai_client,
        mock_sql_parser,
        mock_rate_limiter,
        metrics_collector,
    ) -> QueryService:
        """Create query service with metrics collector."""
        config = QueryServiceConfig()
        return QueryService(
            config=config,
            app_config=app_config,
            pool_manager=mock_pool_manager,
            schema_cache=mock_schema_cache,
            openai_client=mock_openai_client,
            sql_parser=mock_sql_parser,
            rate_limiter=mock_rate_limiter,
            metrics_collector=metrics_collector,
        )

    @pytest.mark.asyncio
    async def test_execute_with_metrics_success(
        self, query_service_with_metrics, metrics_collector
    ):
        """Test that metrics are recorded on successful query."""
        request = QueryRequest(
            question="Show all users",
            return_type=ReturnType.RESULT,
        )

        response = await query_service_with_metrics.execute_query(request)

        assert response.result is not None
        assert response.result.row_count == 1

        # Verify metrics were recorded
        metrics_output = metrics_collector.generate_metrics().decode("utf-8")
        assert "pg_mcp_requests_total" in metrics_output
        assert "pg_mcp_request_duration_seconds" in metrics_output

    @pytest.mark.asyncio
    async def test_execute_with_metrics_error(
        self,
        app_config,
        mock_pool_manager,
        mock_schema_cache,
        mock_openai_client,
        mock_sql_parser,
        mock_rate_limiter,
        metrics_collector,
    ):
        """Test that metrics are recorded on error."""
        # Make the rate limiter throw an error
        from pg_mcp.models.errors import RateLimitExceededError

        mock_rate_limiter.check_request = AsyncMock(
            side_effect=RateLimitExceededError("requests", 60, "minute")
        )

        config = QueryServiceConfig()
        service = QueryService(
            config=config,
            app_config=app_config,
            pool_manager=mock_pool_manager,
            schema_cache=mock_schema_cache,
            openai_client=mock_openai_client,
            sql_parser=mock_sql_parser,
            rate_limiter=mock_rate_limiter,
            metrics_collector=metrics_collector,
        )

        request = QueryRequest(question="Show all users")

        with pytest.raises(RateLimitExceededError):
            await service.execute_query(request)

        # Verify error metrics were recorded
        metrics_output = metrics_collector.generate_metrics().decode("utf-8")
        assert "pg_mcp_requests_total" in metrics_output


class TestQueryServiceWithExecutorManager:
    """Tests for QueryService with QueryExecutorManager integration."""

    @pytest.fixture
    def sample_schema(self) -> DatabaseSchema:
        """Create sample database schema."""
        return DatabaseSchema(
            name="test_db",
            tables=[
                TableInfo(
                    name="users",
                    schema_name="public",
                    columns=[
                        ColumnInfo(name="id", data_type="integer", is_primary_key=True),
                        ColumnInfo(name="name", data_type="varchar(100)"),
                        ColumnInfo(name="email", data_type="varchar(100)"),
                        ColumnInfo(name="password", data_type="varchar(100)"),
                    ],
                ),
                TableInfo(
                    name="orders",
                    schema_name="public",
                    columns=[
                        ColumnInfo(name="id", data_type="integer", is_primary_key=True),
                        ColumnInfo(name="user_id", data_type="integer"),
                        ColumnInfo(name="total", data_type="numeric"),
                    ],
                ),
            ],
        )

    @pytest.fixture
    def db_config(self) -> DatabaseConfig:
        """Create test database config with access policy."""
        return DatabaseConfig(
            name="test_db",
            host="localhost",
            dbname="testdb",
            user="testuser",
            ssl_mode=SSLMode.DISABLE,
            access_policy=AccessPolicyConfig(
                allowed_schemas=["public"],
                tables=TableAccessConfig(allowed=["users", "orders"]),
                columns=ColumnAccessConfig(denied=["users.password"]),
                explain_policy=ExplainPolicyConfig(enabled=True),
            ),
        )

    @pytest.fixture
    def app_config(self, db_config) -> AppConfig:
        """Create test app config."""
        with patch.dict("os.environ", {"PG_MCP_OPENAI_API_KEY": "test-key"}):
            return AppConfig(
                databases=[db_config],
                openai=OpenAISettings(api_key=SecretStr("test-key")),
                server=ServerSettings(),
                rate_limit=RateLimitSettings(enabled=False),
            )

    @pytest.fixture
    def mock_pool(self) -> MagicMock:
        """Create mock database pool."""
        pool = MagicMock(spec=DatabasePool)
        pool.fetch_readonly = AsyncMock(
            return_value=[{"id": 1, "name": "Alice", "email": "alice@example.com"}]
        )
        return pool

    @pytest.fixture
    def mock_pool_manager(self, mock_pool) -> MagicMock:
        """Create mock pool manager."""
        manager = MagicMock(spec=DatabasePoolManager)
        manager.get_pool.return_value = mock_pool
        return manager

    @pytest.fixture
    def mock_schema_cache(self, sample_schema) -> MagicMock:
        """Create mock schema cache."""
        cache = MagicMock(spec=SchemaCache)
        cache.get_or_refresh = AsyncMock(return_value=sample_schema)
        return cache

    @pytest.fixture
    def mock_openai_client(self) -> MagicMock:
        """Create mock OpenAI client."""
        client = MagicMock(spec=OpenAIClient)
        client.generate_sql = AsyncMock(
            return_value=SQLGenerationResult(
                sql="SELECT id, name, email FROM users",
                explanation="Fetches all users",
                tokens_used=100,
            )
        )
        return client

    @pytest.fixture
    def mock_sql_parser(self) -> MagicMock:
        """Create mock SQL parser with parse_for_policy support."""
        parser = MagicMock(spec=SQLParser)
        parser.validate_and_raise = MagicMock()
        parser.add_limit = MagicMock(
            side_effect=lambda sql, limit: f"{sql} LIMIT {limit}"
        )
        # Default parse_for_policy result
        parser.parse_for_policy = MagicMock(
            return_value=ParsedSQLInfo(
                sql="SELECT id, name, email FROM users",
                schemas=["public"],
                tables=["users"],
                columns=[("users", "id"), ("users", "name"), ("users", "email")],
                has_select_star=False,
                select_star_tables=[],
                is_readonly=True,
            )
        )
        return parser

    @pytest.fixture
    def mock_rate_limiter(self) -> MagicMock:
        """Create mock rate limiter."""
        limiter = MagicMock(spec=RateLimiter)
        limiter.check_request = AsyncMock()
        limiter.record_tokens = AsyncMock()
        return limiter

    @pytest.fixture
    def mock_audit_logger(self) -> MagicMock:
        """Create mock audit logger."""
        logger = MagicMock(spec=AuditLogger)
        logger.log = AsyncMock()
        return logger

    @pytest.fixture
    def mock_executor(self, mock_pool, mock_sql_parser, mock_audit_logger) -> MagicMock:
        """Create mock query executor."""
        executor = MagicMock(spec=QueryExecutor)
        executor.execute = AsyncMock(
            return_value=QueryResult(
                columns=["id", "name", "email"],
                rows=[[1, "Alice", "alice@example.com"]],
                row_count=1,
                truncated=False,
            )
        )
        return executor

    @pytest.fixture
    def mock_executor_manager(self, mock_executor) -> MagicMock:
        """Create mock executor manager."""
        manager = MagicMock(spec=QueryExecutorManager)
        manager.get_executor.return_value = mock_executor
        return manager

    @pytest.fixture
    def query_service_with_executor(
        self,
        app_config,
        mock_pool_manager,
        mock_schema_cache,
        mock_openai_client,
        mock_sql_parser,
        mock_rate_limiter,
        mock_audit_logger,
        mock_executor_manager,
    ) -> QueryService:
        """Create query service with executor manager."""
        config = QueryServiceConfig()
        return QueryService(
            config=config,
            app_config=app_config,
            pool_manager=mock_pool_manager,
            schema_cache=mock_schema_cache,
            openai_client=mock_openai_client,
            sql_parser=mock_sql_parser,
            rate_limiter=mock_rate_limiter,
            audit_logger=mock_audit_logger,
            executor_manager=mock_executor_manager,
        )

    @pytest.mark.asyncio
    async def test_execute_with_executor_manager(
        self, query_service_with_executor, mock_executor_manager, mock_executor
    ):
        """Test that executor manager is used when available."""
        request = QueryRequest(
            question="Show all users",
            return_type=ReturnType.RESULT,
        )

        response = await query_service_with_executor.execute_query(request)

        assert response.result is not None
        assert response.result.row_count == 1

        # Verify executor manager was used
        mock_executor_manager.get_executor.assert_called_once_with("test_db")
        mock_executor.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_passes_client_ip(
        self, query_service_with_executor, mock_executor
    ):
        """Test that client IP is passed to executor."""
        request = QueryRequest(question="Show all users")

        await query_service_with_executor.execute_query(
            request, client_ip="192.168.1.100", session_id="session-123"
        )

        # Verify context was passed with correct info
        call_args = mock_executor.execute.call_args
        context = call_args.kwargs.get("context")
        assert context is not None
        assert context.client_ip == "192.168.1.100"
        assert context.session_id == "session-123"

    @pytest.mark.asyncio
    async def test_execute_with_policy_check_success(
        self, query_service_with_executor, mock_executor
    ):
        """Test successful query with policy check."""
        request = QueryRequest(
            question="Show user names",
            return_type=ReturnType.BOTH,
        )

        response = await query_service_with_executor.execute_query(request)

        assert response.sql is not None
        assert response.result is not None
        mock_executor.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_denied_table(
        self, query_service_with_executor, mock_executor
    ):
        """Test that denied table access raises error."""
        mock_executor.execute = AsyncMock(
            side_effect=TableAccessDeniedError(["admin_users"])
        )

        request = QueryRequest(question="Show admin users")

        with pytest.raises(TableAccessDeniedError) as exc_info:
            await query_service_with_executor.execute_query(request)

        assert "admin_users" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_execute_denied_column(
        self, query_service_with_executor, mock_executor
    ):
        """Test that denied column access raises error."""
        mock_executor.execute = AsyncMock(
            side_effect=ColumnAccessDeniedError(["users.password"], is_select_star=False)
        )

        request = QueryRequest(question="Show user passwords")

        with pytest.raises(ColumnAccessDeniedError) as exc_info:
            await query_service_with_executor.execute_query(request)

        assert "users.password" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_execute_query_too_expensive(
        self, query_service_with_executor, mock_executor
    ):
        """Test that expensive queries are blocked."""
        mock_executor.execute = AsyncMock(
            side_effect=QueryTooExpensiveError(
                estimated_rows=1000000,
                estimated_cost=50000.0,
                limits={"max_rows": 100000, "max_cost": 10000.0},
            )
        )

        request = QueryRequest(question="Select all from huge table")

        with pytest.raises(QueryTooExpensiveError) as exc_info:
            await query_service_with_executor.execute_query(request)

        assert "exceeds resource limits" in str(exc_info.value)


class TestQueryServiceBackwardCompatibility:
    """Tests to ensure backward compatibility without new components."""

    @pytest.fixture
    def sample_schema(self) -> DatabaseSchema:
        """Create sample database schema."""
        return DatabaseSchema(
            name="test_db",
            tables=[
                TableInfo(
                    name="users",
                    schema_name="public",
                    columns=[
                        ColumnInfo(name="id", data_type="integer", is_primary_key=True),
                        ColumnInfo(name="name", data_type="varchar(100)"),
                    ],
                ),
            ],
        )

    @pytest.fixture
    def db_config(self) -> DatabaseConfig:
        """Create test database config."""
        return DatabaseConfig(
            name="test_db",
            host="localhost",
            dbname="testdb",
            user="testuser",
            ssl_mode=SSLMode.DISABLE,
        )

    @pytest.fixture
    def app_config(self, db_config) -> AppConfig:
        """Create test app config."""
        with patch.dict("os.environ", {"PG_MCP_OPENAI_API_KEY": "test-key"}):
            return AppConfig(
                databases=[db_config],
                openai=OpenAISettings(api_key=SecretStr("test-key")),
                server=ServerSettings(),
                rate_limit=RateLimitSettings(enabled=False),
            )

    @pytest.fixture
    def mock_pool_manager(self) -> MagicMock:
        """Create mock pool manager."""
        manager = MagicMock(spec=DatabasePoolManager)
        mock_pool = MagicMock(spec=DatabasePool)
        mock_pool.fetch_readonly = AsyncMock(
            return_value=[{"id": 1, "name": "Alice"}]
        )
        manager.get_pool.return_value = mock_pool
        return manager

    @pytest.fixture
    def mock_schema_cache(self, sample_schema) -> MagicMock:
        """Create mock schema cache."""
        cache = MagicMock(spec=SchemaCache)
        cache.get_or_refresh = AsyncMock(return_value=sample_schema)
        return cache

    @pytest.fixture
    def mock_openai_client(self) -> MagicMock:
        """Create mock OpenAI client."""
        client = MagicMock(spec=OpenAIClient)
        client.generate_sql = AsyncMock(
            return_value=SQLGenerationResult(
                sql="SELECT * FROM users",
                explanation="Fetches all users",
                tokens_used=100,
            )
        )
        return client

    @pytest.fixture
    def mock_sql_parser(self) -> MagicMock:
        """Create mock SQL parser."""
        parser = MagicMock(spec=SQLParser)
        parser.validate_and_raise = MagicMock()
        parser.add_limit = MagicMock(
            side_effect=lambda sql, limit: f"{sql} LIMIT {limit}"
        )
        return parser

    @pytest.fixture
    def mock_rate_limiter(self) -> MagicMock:
        """Create mock rate limiter."""
        limiter = MagicMock(spec=RateLimiter)
        limiter.check_request = AsyncMock()
        limiter.record_tokens = AsyncMock()
        return limiter

    @pytest.fixture
    def query_service_minimal(
        self,
        app_config,
        mock_pool_manager,
        mock_schema_cache,
        mock_openai_client,
        mock_sql_parser,
        mock_rate_limiter,
    ) -> QueryService:
        """Create query service without optional components."""
        config = QueryServiceConfig()
        return QueryService(
            config=config,
            app_config=app_config,
            pool_manager=mock_pool_manager,
            schema_cache=mock_schema_cache,
            openai_client=mock_openai_client,
            sql_parser=mock_sql_parser,
            rate_limiter=mock_rate_limiter,
            # No metrics_collector, audit_logger, or executor_manager
        )

    @pytest.mark.asyncio
    async def test_works_without_metrics_collector(self, query_service_minimal):
        """Test that service works without metrics collector."""
        assert query_service_minimal._metrics_collector is None

        request = QueryRequest(
            question="Show all users",
            return_type=ReturnType.RESULT,
        )

        response = await query_service_minimal.execute_query(request)

        assert response.result is not None

    @pytest.mark.asyncio
    async def test_works_without_audit_logger(self, query_service_minimal):
        """Test that service works without audit logger."""
        assert query_service_minimal._audit_logger is None

        request = QueryRequest(question="Show all users")

        response = await query_service_minimal.execute_query(request)

        assert response.result is not None

    @pytest.mark.asyncio
    async def test_works_without_executor_manager(
        self, query_service_minimal, mock_pool_manager
    ):
        """Test that service falls back to direct execution without executor manager."""
        assert query_service_minimal._executor_manager is None

        request = QueryRequest(question="Show all users")

        response = await query_service_minimal.execute_query(request)

        assert response.result is not None

        # Verify direct pool access was used (not executor)
        mock_pool = mock_pool_manager.get_pool.return_value
        mock_pool.fetch_readonly.assert_called()


class TestQueryServiceAuditLogging:
    """Tests for QueryService audit logging integration."""

    @pytest.fixture
    def sample_schema(self) -> DatabaseSchema:
        """Create sample database schema."""
        return DatabaseSchema(
            name="test_db",
            tables=[
                TableInfo(
                    name="users",
                    schema_name="public",
                    columns=[
                        ColumnInfo(name="id", data_type="integer", is_primary_key=True),
                        ColumnInfo(name="name", data_type="varchar(100)"),
                    ],
                ),
            ],
        )

    @pytest.fixture
    def db_config(self) -> DatabaseConfig:
        """Create test database config."""
        return DatabaseConfig(
            name="test_db",
            host="localhost",
            dbname="testdb",
            user="testuser",
            ssl_mode=SSLMode.DISABLE,
        )

    @pytest.fixture
    def app_config(self, db_config) -> AppConfig:
        """Create test app config."""
        with patch.dict("os.environ", {"PG_MCP_OPENAI_API_KEY": "test-key"}):
            return AppConfig(
                databases=[db_config],
                openai=OpenAISettings(api_key=SecretStr("test-key")),
                server=ServerSettings(),
                rate_limit=RateLimitSettings(enabled=False),
            )

    @pytest.fixture
    def mock_audit_logger(self) -> MagicMock:
        """Create mock audit logger."""
        logger = MagicMock(spec=AuditLogger)
        logger.log = AsyncMock()
        return logger

    @pytest.fixture
    def mock_executor(self) -> MagicMock:
        """Create mock query executor with audit logging."""
        executor = MagicMock(spec=QueryExecutor)
        executor.execute = AsyncMock(
            return_value=QueryResult(
                columns=["id", "name"],
                rows=[[1, "Alice"]],
                row_count=1,
                truncated=False,
            )
        )
        return executor

    @pytest.fixture
    def mock_executor_manager(self, mock_executor) -> MagicMock:
        """Create mock executor manager."""
        manager = MagicMock(spec=QueryExecutorManager)
        manager.get_executor.return_value = mock_executor
        return manager

    @pytest.fixture
    def query_service_with_audit(
        self,
        app_config,
        sample_schema,
        mock_audit_logger,
        mock_executor_manager,
    ) -> QueryService:
        """Create query service with audit logger."""
        mock_pool_manager = MagicMock(spec=DatabasePoolManager)
        mock_pool = MagicMock(spec=DatabasePool)
        mock_pool_manager.get_pool.return_value = mock_pool

        mock_schema_cache = MagicMock(spec=SchemaCache)
        mock_schema_cache.get_or_refresh = AsyncMock(return_value=sample_schema)

        mock_openai_client = MagicMock(spec=OpenAIClient)
        mock_openai_client.generate_sql = AsyncMock(
            return_value=SQLGenerationResult(
                sql="SELECT * FROM users",
                explanation="Fetches all users",
                tokens_used=100,
            )
        )

        mock_sql_parser = MagicMock(spec=SQLParser)
        mock_sql_parser.validate_and_raise = MagicMock()
        mock_sql_parser.add_limit = MagicMock(
            side_effect=lambda sql, limit: f"{sql} LIMIT {limit}"
        )

        mock_rate_limiter = MagicMock(spec=RateLimiter)
        mock_rate_limiter.check_request = AsyncMock()
        mock_rate_limiter.record_tokens = AsyncMock()

        config = QueryServiceConfig()
        return QueryService(
            config=config,
            app_config=app_config,
            pool_manager=mock_pool_manager,
            schema_cache=mock_schema_cache,
            openai_client=mock_openai_client,
            sql_parser=mock_sql_parser,
            rate_limiter=mock_rate_limiter,
            audit_logger=mock_audit_logger,
            executor_manager=mock_executor_manager,
        )

    @pytest.mark.asyncio
    async def test_audit_logger_passed_to_executor(
        self, query_service_with_audit, mock_executor
    ):
        """Test that audit logger is used via executor."""
        request = QueryRequest(question="Show all users")

        await query_service_with_audit.execute_query(request)

        # The executor should have been called (audit logging happens inside executor)
        mock_executor.execute.assert_called_once()
