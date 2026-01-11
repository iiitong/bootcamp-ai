# tests/unit/test_query_service.py

"""Query service unit tests."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import SecretStr

from pg_mcp.config.models import (
    AppConfig,
    DatabaseConfig,
    OpenAISettings,
    RateLimitSettings,
    ServerSettings,
    SSLMode,
)
from pg_mcp.infrastructure.database import DatabasePool, DatabasePoolManager
from pg_mcp.infrastructure.openai_client import OpenAIClient
from pg_mcp.infrastructure.rate_limiter import RateLimiter
from pg_mcp.infrastructure.schema_cache import SchemaCache
from pg_mcp.infrastructure.sql_parser import SQLParser
from pg_mcp.models import (
    QueryRequest,
    QueryResult,
    ReturnType,
    SQLGenerationResult,
)
from pg_mcp.models.errors import (
    PgMcpError,
    QueryTimeoutError,
    UnknownDatabaseError,
    UnsafeSQLError,
)
from pg_mcp.models.schema import ColumnInfo, DatabaseSchema, TableInfo
from pg_mcp.services.query_service import QueryService, QueryServiceConfig


class TestQueryServiceConfig:
    """Query service configuration tests."""

    def test_default_config(self):
        """Test default configuration values."""
        config = QueryServiceConfig()

        assert config.query_timeout == 30.0
        assert config.max_result_rows == 1000
        assert config.max_sql_retry == 2
        assert config.use_readonly_transactions is True
        assert config.enable_result_validation is False

    def test_from_server_config(self):
        """Test creating config from ServerSettings."""
        with patch.dict("os.environ", {}, clear=False):
            server_config = ServerSettings(
                query_timeout=60.0,
                max_result_rows=500,
                max_sql_retry=3,
                use_readonly_transactions=False,
                enable_result_validation=True,
            )

        config = QueryServiceConfig.from_server_config(server_config)

        assert config.query_timeout == 60.0
        assert config.max_result_rows == 500
        assert config.max_sql_retry == 3
        assert config.use_readonly_transactions is False
        assert config.enable_result_validation is True


class TestQueryService:
    """Query service tests."""

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
        parser.validate_and_raise = MagicMock()  # Does nothing, passes validation
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
    def query_service(
        self,
        app_config,
        mock_pool_manager,
        mock_schema_cache,
        mock_openai_client,
        mock_sql_parser,
        mock_rate_limiter,
    ) -> QueryService:
        """Create query service with mocked dependencies."""
        config = QueryServiceConfig()
        return QueryService(
            config=config,
            app_config=app_config,
            pool_manager=mock_pool_manager,
            schema_cache=mock_schema_cache,
            openai_client=mock_openai_client,
            sql_parser=mock_sql_parser,
            rate_limiter=mock_rate_limiter,
        )

    def test_service_initialization(self, query_service):
        """Test service initializes with dependencies."""
        assert query_service.config is not None
        assert query_service._pool_manager is not None
        assert query_service._schema_cache is not None
        assert query_service._openai_client is not None
        assert query_service._sql_parser is not None
        assert query_service._rate_limiter is not None

    @pytest.mark.asyncio
    async def test_execute_query_sql_only(
        self, query_service, mock_openai_client
    ):
        """Test execute query returning SQL only."""
        request = QueryRequest(
            question="Show all users",
            return_type=ReturnType.SQL,
        )

        response = await query_service.execute_query(request)

        assert response.sql == "SELECT * FROM users"
        assert response.explanation == "Fetches all users"
        assert response.result is None

    @pytest.mark.asyncio
    async def test_execute_query_result_only(
        self,
        query_service,
        mock_pool_manager,
    ):
        """Test execute query returning results only."""
        # Setup mock pool to return results
        mock_pool = mock_pool_manager.get_pool.return_value
        mock_pool.fetch_readonly = AsyncMock(
            return_value=[
                {"id": 1, "name": "Alice"},
                {"id": 2, "name": "Bob"},
            ]
        )

        request = QueryRequest(
            question="Show all users",
            return_type=ReturnType.RESULT,
        )

        response = await query_service.execute_query(request)

        assert response.sql is None
        assert response.result is not None
        assert response.result.row_count == 2
        assert response.result.columns == ["id", "name"]

    @pytest.mark.asyncio
    async def test_execute_query_both(
        self,
        query_service,
        mock_pool_manager,
    ):
        """Test execute query returning both SQL and results."""
        mock_pool = mock_pool_manager.get_pool.return_value
        mock_pool.fetch_readonly = AsyncMock(
            return_value=[{"id": 1, "name": "Alice"}]
        )

        request = QueryRequest(
            question="Show all users",
            return_type=ReturnType.BOTH,
        )

        response = await query_service.execute_query(request)

        assert response.sql == "SELECT * FROM users"
        assert response.result is not None
        assert response.result.row_count == 1

    @pytest.mark.asyncio
    async def test_execute_query_with_limit(
        self,
        query_service,
        mock_pool_manager,
        mock_sql_parser,
    ):
        """Test execute query with custom limit."""
        mock_pool = mock_pool_manager.get_pool.return_value
        mock_pool.fetch_readonly = AsyncMock(return_value=[])

        request = QueryRequest(
            question="Show users",
            limit=50,
        )

        await query_service.execute_query(request)

        # Verify add_limit was called with limit + 1 (to detect truncation)
        mock_sql_parser.add_limit.assert_called_once_with(
            "SELECT * FROM users", 51
        )

    @pytest.mark.asyncio
    async def test_execute_query_result_truncated(
        self,
        query_service,
        mock_pool_manager,
    ):
        """Test result truncation when exceeding limit."""
        # Return more rows than the limit
        mock_pool = mock_pool_manager.get_pool.return_value
        mock_pool.fetch_readonly = AsyncMock(
            return_value=[{"id": i} for i in range(1002)]  # More than default 1000
        )

        request = QueryRequest(question="Show all")

        response = await query_service.execute_query(request)

        assert response.result.truncated is True
        assert response.result.row_count == 1000  # Limited to max

    @pytest.mark.asyncio
    async def test_execute_query_rate_limit_checked(
        self, query_service, mock_rate_limiter
    ):
        """Test rate limit is checked."""
        request = QueryRequest(question="Test")

        # Setup to avoid actual execution
        query_service._pool_manager.get_pool.return_value.fetch_readonly = AsyncMock(
            return_value=[]
        )

        await query_service.execute_query(request)

        mock_rate_limiter.check_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_query_tokens_recorded(
        self, query_service, mock_rate_limiter
    ):
        """Test token usage is recorded."""
        request = QueryRequest(question="Test", return_type=ReturnType.SQL)

        await query_service.execute_query(request)

        mock_rate_limiter.record_tokens.assert_called_once_with(100)

    @pytest.mark.asyncio
    async def test_resolve_database_default(
        self, query_service, db_config
    ):
        """Test database resolution with default."""
        result = query_service._resolve_database(None)

        assert result == "test_db"

    @pytest.mark.asyncio
    async def test_resolve_database_explicit(
        self, query_service
    ):
        """Test database resolution with explicit name."""
        result = query_service._resolve_database("test_db")

        assert result == "test_db"

    @pytest.mark.asyncio
    async def test_resolve_database_unknown(self, query_service):
        """Test database resolution with unknown database."""
        with pytest.raises(UnknownDatabaseError):
            query_service._resolve_database("unknown_db")


class TestQueryServiceSQLGeneration:
    """SQL generation with retry tests."""

    @pytest.fixture
    def sample_schema(self) -> DatabaseSchema:
        """Create sample schema."""
        return DatabaseSchema(
            name="test_db",
            tables=[
                TableInfo(
                    name="users",
                    schema_name="public",
                    columns=[
                        ColumnInfo(name="id", data_type="integer"),
                    ],
                ),
            ],
        )

    @pytest.fixture
    def query_service_with_mocks(self, sample_schema):
        """Create query service with mocked dependencies for retry tests."""
        with patch.dict("os.environ", {"PG_MCP_OPENAI_API_KEY": "test-key"}):
            db_config = DatabaseConfig(
                name="test_db",
                host="localhost",
                dbname="testdb",
                user="user",
                ssl_mode=SSLMode.DISABLE,
            )
            app_config = AppConfig(
                databases=[db_config],
                openai=OpenAISettings(api_key=SecretStr("test-key")),
                server=ServerSettings(),
                rate_limit=RateLimitSettings(enabled=False),
            )

        config = QueryServiceConfig(max_sql_retry=2)

        pool_manager = MagicMock(spec=DatabasePoolManager)
        schema_cache = MagicMock(spec=SchemaCache)
        schema_cache.get_or_refresh = AsyncMock(return_value=sample_schema)
        openai_client = MagicMock(spec=OpenAIClient)
        sql_parser = MagicMock(spec=SQLParser)
        rate_limiter = MagicMock(spec=RateLimiter)
        rate_limiter.check_request = AsyncMock()
        rate_limiter.record_tokens = AsyncMock()

        service = QueryService(
            config=config,
            app_config=app_config,
            pool_manager=pool_manager,
            schema_cache=schema_cache,
            openai_client=openai_client,
            sql_parser=sql_parser,
            rate_limiter=rate_limiter,
        )

        return service, openai_client, sql_parser

    @pytest.mark.asyncio
    async def test_generate_sql_success_first_try(
        self, query_service_with_mocks, sample_schema
    ):
        """Test SQL generation succeeds on first try."""
        service, openai_client, sql_parser = query_service_with_mocks

        openai_client.generate_sql = AsyncMock(
            return_value=SQLGenerationResult(sql="SELECT 1", tokens_used=10)
        )
        sql_parser.validate_and_raise = MagicMock()  # No exception = valid

        result = await service._generate_sql_with_retry(
            question="Test",
            schema=sample_schema,
            database="test_db",
        )

        assert result.sql == "SELECT 1"
        assert openai_client.generate_sql.call_count == 1

    @pytest.mark.asyncio
    async def test_generate_sql_retry_on_validation_error(
        self, query_service_with_mocks, sample_schema
    ):
        """Test SQL generation retries on validation error."""
        service, openai_client, sql_parser = query_service_with_mocks

        # First call returns unsafe SQL, second call returns safe SQL
        openai_client.generate_sql = AsyncMock(
            side_effect=[
                SQLGenerationResult(sql="DELETE FROM users", tokens_used=10),
                SQLGenerationResult(sql="SELECT * FROM users", tokens_used=10),
            ]
        )

        # First validation fails, second succeeds
        call_count = [0]

        def mock_validate(sql):
            call_count[0] += 1
            if call_count[0] == 1:
                raise UnsafeSQLError("DELETE not allowed")

        sql_parser.validate_and_raise = MagicMock(side_effect=mock_validate)

        result = await service._generate_sql_with_retry(
            question="Test",
            schema=sample_schema,
            database="test_db",
        )

        assert result.sql == "SELECT * FROM users"
        assert openai_client.generate_sql.call_count == 2

    @pytest.mark.asyncio
    async def test_generate_sql_max_retries_exceeded(
        self, query_service_with_mocks, sample_schema
    ):
        """Test SQL generation fails after max retries."""
        service, openai_client, sql_parser = query_service_with_mocks

        openai_client.generate_sql = AsyncMock(
            return_value=SQLGenerationResult(sql="DROP TABLE users", tokens_used=10)
        )
        sql_parser.validate_and_raise = MagicMock(
            side_effect=UnsafeSQLError("DROP not allowed")
        )

        with pytest.raises(UnsafeSQLError):
            await service._generate_sql_with_retry(
                question="Test",
                schema=sample_schema,
                database="test_db",
            )

        # Initial attempt + 2 retries = 3 calls
        assert openai_client.generate_sql.call_count == 3

    @pytest.mark.asyncio
    async def test_generate_sql_includes_error_context_on_retry(
        self, query_service_with_mocks, sample_schema
    ):
        """Test error context is passed on retry."""
        service, openai_client, sql_parser = query_service_with_mocks

        openai_client.generate_sql = AsyncMock(
            side_effect=[
                SQLGenerationResult(sql="BAD SQL", tokens_used=10),
                SQLGenerationResult(sql="SELECT 1", tokens_used=10),
            ]
        )

        call_count = [0]

        def mock_validate(sql):
            call_count[0] += 1
            if call_count[0] == 1:
                raise PgMcpError("SYNTAX_ERROR", "Syntax error at BAD")

        sql_parser.validate_and_raise = MagicMock(side_effect=mock_validate)

        await service._generate_sql_with_retry(
            question="Test",
            schema=sample_schema,
            database="test_db",
        )

        # Check second call had error_context
        second_call = openai_client.generate_sql.call_args_list[1]
        assert second_call.kwargs.get("error_context") is not None
        assert "Syntax error" in second_call.kwargs["error_context"]


class TestQueryServiceExecution:
    """SQL execution tests."""

    @pytest.fixture
    def query_service_for_execution(self):
        """Create query service for execution tests."""
        with patch.dict("os.environ", {"PG_MCP_OPENAI_API_KEY": "test-key"}):
            db_config = DatabaseConfig(
                name="test_db",
                host="localhost",
                dbname="testdb",
                user="user",
                ssl_mode=SSLMode.DISABLE,
            )
            app_config = AppConfig(
                databases=[db_config],
                openai=OpenAISettings(api_key=SecretStr("test-key")),
                server=ServerSettings(),
                rate_limit=RateLimitSettings(enabled=False),
            )

        config = QueryServiceConfig(
            query_timeout=5.0,
            use_readonly_transactions=True,
        )

        pool_manager = MagicMock(spec=DatabasePoolManager)
        mock_pool = MagicMock(spec=DatabasePool)
        pool_manager.get_pool.return_value = mock_pool

        sql_parser = MagicMock(spec=SQLParser)
        sql_parser.add_limit = MagicMock(
            side_effect=lambda sql, limit: f"{sql} LIMIT {limit}"
        )

        service = QueryService(
            config=config,
            app_config=app_config,
            pool_manager=pool_manager,
            schema_cache=MagicMock(),
            openai_client=MagicMock(),
            sql_parser=sql_parser,
            rate_limiter=MagicMock(),
        )

        return service, mock_pool

    @pytest.mark.asyncio
    async def test_execute_sql_success(self, query_service_for_execution):
        """Test successful SQL execution."""
        service, mock_pool = query_service_for_execution

        mock_pool.fetch_readonly = AsyncMock(
            return_value=[
                {"id": 1, "name": "Alice"},
                {"id": 2, "name": "Bob"},
            ]
        )

        result = await service._execute_sql(
            database="test_db",
            sql="SELECT * FROM users",
            limit=100,
        )

        assert result.row_count == 2
        assert result.columns == ["id", "name"]
        assert result.rows == [[1, "Alice"], [2, "Bob"]]
        assert result.truncated is False

    @pytest.mark.asyncio
    async def test_execute_sql_empty_result(self, query_service_for_execution):
        """Test SQL execution with empty result."""
        service, mock_pool = query_service_for_execution

        mock_pool.fetch_readonly = AsyncMock(return_value=[])

        result = await service._execute_sql(
            database="test_db",
            sql="SELECT * FROM users WHERE 1=0",
            limit=100,
        )

        assert result.row_count == 0
        assert result.columns == []
        assert result.rows == []

    @pytest.mark.asyncio
    async def test_execute_sql_uses_readonly_transaction(
        self, query_service_for_execution
    ):
        """Test that read-only transaction is used."""
        service, mock_pool = query_service_for_execution

        mock_pool.fetch_readonly = AsyncMock(return_value=[])

        await service._execute_sql(
            database="test_db",
            sql="SELECT 1",
            limit=100,
        )

        mock_pool.fetch_readonly.assert_called_once()
        mock_pool.fetch.assert_not_called()

    @pytest.mark.asyncio
    async def test_execute_sql_without_readonly_transaction(self):
        """Test execution without read-only transaction."""
        with patch.dict("os.environ", {"PG_MCP_OPENAI_API_KEY": "test-key"}):
            db_config = DatabaseConfig(
                name="test_db",
                host="localhost",
                dbname="testdb",
                user="user",
                ssl_mode=SSLMode.DISABLE,
            )
            app_config = AppConfig(
                databases=[db_config],
                openai=OpenAISettings(api_key=SecretStr("test-key")),
                server=ServerSettings(),
                rate_limit=RateLimitSettings(enabled=False),
            )

        config = QueryServiceConfig(use_readonly_transactions=False)

        pool_manager = MagicMock(spec=DatabasePoolManager)
        mock_pool = MagicMock(spec=DatabasePool)
        mock_pool.fetch = AsyncMock(return_value=[])
        pool_manager.get_pool.return_value = mock_pool

        sql_parser = MagicMock(spec=SQLParser)
        sql_parser.add_limit = MagicMock(side_effect=lambda sql, limit: sql)

        service = QueryService(
            config=config,
            app_config=app_config,
            pool_manager=pool_manager,
            schema_cache=MagicMock(),
            openai_client=MagicMock(),
            sql_parser=sql_parser,
            rate_limiter=MagicMock(),
        )

        await service._execute_sql("test_db", "SELECT 1", 100)

        mock_pool.fetch.assert_called_once()
        mock_pool.fetch_readonly.assert_not_called()
