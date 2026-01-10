"""Query service for executing natural language queries."""

import asyncio
from dataclasses import dataclass

import asyncpg
import structlog

from pg_mcp.config.models import AppConfig, ServerConfig
from pg_mcp.infrastructure.database import DatabasePool, DatabasePoolManager
from pg_mcp.infrastructure.openai_client import OpenAIClient
from pg_mcp.infrastructure.rate_limiter import RateLimiter
from pg_mcp.infrastructure.schema_cache import SchemaCache
from pg_mcp.infrastructure.sql_parser import SQLParser
from pg_mcp.models import (
    DatabaseSchema,
    ErrorCode,
    PgMcpError,
    QueryRequest,
    QueryResponse,
    QueryResult,
    QueryTimeoutError,
    ReturnType,
    SQLGenerationResult,
    UnsafeSQLError,
)

logger = structlog.get_logger(__name__)


@dataclass
class QueryServiceConfig:
    """Query service configuration."""

    query_timeout: float = 30.0
    max_result_rows: int = 1000
    max_sql_retry: int = 2
    use_readonly_transactions: bool = True
    enable_result_validation: bool = False

    @classmethod
    def from_server_config(cls, config: ServerConfig) -> "QueryServiceConfig":
        """Create from server configuration.

        Args:
            config: Server configuration

        Returns:
            QueryServiceConfig instance
        """
        return cls(
            query_timeout=config.query_timeout,
            max_result_rows=config.max_result_rows,
            max_sql_retry=config.max_sql_retry,
            use_readonly_transactions=config.use_readonly_transactions,
            enable_result_validation=config.enable_result_validation,
        )


class QueryService:
    """Service for executing natural language queries against PostgreSQL databases.

    This service orchestrates the full query flow:
    1. Rate limiting check
    2. Database resolution
    3. Schema retrieval
    4. SQL generation (with retry on syntax errors)
    5. SQL validation
    6. Query execution (with read-only transaction defense)
    7. Result processing
    """

    def __init__(
        self,
        config: QueryServiceConfig,
        app_config: AppConfig,
        pool_manager: DatabasePoolManager,
        schema_cache: SchemaCache,
        openai_client: OpenAIClient,
        sql_parser: SQLParser,
        rate_limiter: RateLimiter,
    ) -> None:
        """Initialize the query service.

        Args:
            config: Query service specific configuration
            app_config: Application configuration (for database resolution)
            pool_manager: Database connection pool manager
            schema_cache: Schema caching service
            openai_client: OpenAI client for SQL generation
            sql_parser: SQL parsing and validation
            rate_limiter: Request rate limiting
        """
        self.config = config
        self._app_config = app_config
        self._pool_manager = pool_manager
        self._schema_cache = schema_cache
        self._openai_client = openai_client
        self._sql_parser = sql_parser
        self._rate_limiter = rate_limiter
        self._logger = logger.bind(service="query_service")

    async def execute_query(self, request: QueryRequest) -> QueryResponse:
        """Execute a natural language query.

        This is the main entry point for query execution. It handles the full
        flow from natural language question to query results.

        Args:
            request: Query request containing the question and options

        Returns:
            Query response with SQL and/or results

        Raises:
            PgMcpError: On any query-related error
        """
        self._logger.info(
            "Executing query",
            question=request.question[:100],
            database=request.database,
            return_type=request.return_type.value,
        )

        # Check rate limit
        await self._rate_limiter.check_request()

        # Resolve database
        db_name = self._resolve_database(request.database)
        pool = self._pool_manager.get_pool(db_name)

        # Get schema
        schema = await self._get_schema(db_name, pool)

        # Generate SQL with retry logic
        sql_result = await self._generate_sql_with_retry(
            question=request.question,
            schema=schema,
            database=db_name,
        )

        # Record token usage
        await self._rate_limiter.record_tokens(sql_result.tokens_used)

        # If only SQL requested, return now
        if request.return_type == ReturnType.SQL:
            return QueryResponse(
                sql=sql_result.sql,
                explanation=sql_result.explanation,
            )

        # Execute query
        limit = request.limit or self.config.max_result_rows
        result = await self._execute_sql(db_name, sql_result.sql, limit)

        # Build response
        response = QueryResponse(result=result)

        if request.return_type == ReturnType.BOTH:
            response.sql = sql_result.sql
            response.explanation = sql_result.explanation

        self._logger.info(
            "Query completed",
            database=db_name,
            row_count=result.row_count,
            truncated=result.truncated,
        )

        return response

    def _resolve_database(self, database: str | None) -> str:
        """Resolve the target database name.

        Args:
            database: Requested database name or None for default

        Returns:
            Resolved database name

        Raises:
            UnknownDatabaseError: If database not found
        """
        if database is None:
            return self._app_config.get_default_database().name

        db_config = self._app_config.get_database(database)
        if db_config is None:
            from pg_mcp.models.errors import UnknownDatabaseError

            raise UnknownDatabaseError(database, self._app_config.database_names)

        return db_config.name

    async def _get_schema(self, database: str, pool: DatabasePool) -> DatabaseSchema:
        """Get database schema from cache.

        Args:
            database: Database name
            pool: Database connection pool

        Returns:
            Database schema
        """
        return await self._schema_cache.get_or_refresh(database, pool)

    async def _generate_sql_with_retry(
        self,
        question: str,
        schema: DatabaseSchema,
        database: str,
    ) -> SQLGenerationResult:
        """Generate SQL from natural language with retry on errors.

        If the generated SQL fails validation, retry with error context
        up to max_sql_retry times.

        Args:
            question: Natural language question
            schema: Database schema
            database: Database name (for logging)

        Returns:
            SQL generation result

        Raises:
            UnsafeSQLError: If generated SQL is unsafe after all retries
            SQLSyntaxError: If generated SQL has syntax errors after all retries
        """
        error_context: str | None = None
        last_error: Exception | None = None

        for attempt in range(self.config.max_sql_retry + 1):
            self._logger.debug(
                "Generating SQL",
                attempt=attempt + 1,
                max_attempts=self.config.max_sql_retry + 1,
                has_error_context=error_context is not None,
            )

            # Generate SQL
            sql_result = await self._openai_client.generate_sql(
                question=question,
                schema=schema,
                error_context=error_context,
            )

            # Validate SQL
            try:
                self._sql_parser.validate_and_raise(sql_result.sql)
                # Validation passed
                self._logger.info(
                    "SQL generated successfully",
                    database=database,
                    attempts=attempt + 1,
                    sql_length=len(sql_result.sql),
                )
                return sql_result
            except (UnsafeSQLError, PgMcpError) as e:
                last_error = e
                error_context = str(e)
                self._logger.warning(
                    "SQL validation failed, will retry",
                    attempt=attempt + 1,
                    error=str(e),
                    sql=sql_result.sql[:200],
                )

                # If this was the last attempt, raise
                if attempt >= self.config.max_sql_retry:
                    self._logger.error(
                        "SQL generation failed after all retries",
                        attempts=attempt + 1,
                        final_error=str(e),
                    )
                    raise

        # Should not reach here, but just in case
        if last_error:
            raise last_error
        raise PgMcpError(ErrorCode.INTERNAL_ERROR, "SQL generation failed unexpectedly")

    async def _execute_sql(
        self,
        database: str,
        sql: str,
        limit: int,
    ) -> QueryResult:
        """Execute SQL in a read-only transaction (defense in depth).

        This method implements multiple layers of protection:
        1. SQL is already validated by sql_parser
        2. LIMIT is enforced to prevent large result sets
        3. Query runs in a read-only transaction (if enabled)
        4. Timeout is enforced at both PostgreSQL and asyncio levels

        Args:
            database: Target database name
            sql: Validated SQL query
            limit: Maximum rows to return

        Returns:
            Query result with data

        Raises:
            QueryTimeoutError: If query exceeds timeout
            UnsafeSQLError: If query attempts to modify data (blocked by read-only transaction)
            PgMcpError: On other database errors
        """
        pool = self._pool_manager.get_pool(database)
        sql_with_limit = self._sql_parser.add_limit(sql, limit + 1)

        self._logger.debug(
            "Executing SQL",
            database=database,
            sql_length=len(sql_with_limit),
            limit=limit,
            use_readonly=self.config.use_readonly_transactions,
        )

        try:
            # Use read-only transaction for defense in depth
            if self.config.use_readonly_transactions:
                rows = await asyncio.wait_for(
                    pool.fetch_readonly(
                        sql_with_limit,
                        timeout=self.config.query_timeout,
                    ),
                    timeout=self.config.query_timeout + 5,  # Extra margin for asyncio
                )
            else:
                rows = await asyncio.wait_for(
                    pool.fetch(
                        sql_with_limit,
                        timeout=self.config.query_timeout,
                    ),
                    timeout=self.config.query_timeout + 5,
                )

        except TimeoutError as e:
            self._logger.error(
                "Query timeout",
                database=database,
                timeout=self.config.query_timeout,
            )
            raise QueryTimeoutError(self.config.query_timeout) from e

        except asyncpg.PostgresError as e:
            error_str = str(e).lower()
            # Read-only transaction will reject write operations
            if "cannot execute" in error_str and "read-only" in error_str:
                self._logger.error(
                    "Write attempt blocked by read-only transaction",
                    database=database,
                    error=str(e),
                )
                raise UnsafeSQLError(
                    "Query attempted to modify data (blocked by read-only transaction)"
                ) from e

            # Other PostgreSQL errors
            self._logger.error(
                "Database error during query execution",
                database=database,
                error=str(e),
            )
            raise PgMcpError(ErrorCode.SYNTAX_ERROR, str(e)) from e

        # Process results
        truncated = len(rows) > limit
        if truncated:
            rows = rows[:limit]

        columns = list(rows[0].keys()) if rows else []
        result_rows = [list(row.values()) for row in rows]

        self._logger.debug(
            "SQL execution completed",
            database=database,
            row_count=len(result_rows),
            truncated=truncated,
        )

        return QueryResult(
            columns=columns,
            rows=result_rows,
            row_count=len(result_rows),
            truncated=truncated,
        )

    async def validate_result(
        self,
        question: str,
        sql: str,
        result: QueryResult,
    ) -> tuple[bool, str | None]:
        """Validate query result using LLM (optional feature).

        This is an optional validation step that uses the LLM to check
        if the query result makes sense for the given question.

        Args:
            question: Original natural language question
            sql: Generated SQL
            result: Query result

        Returns:
            Tuple of (is_valid, explanation)
        """
        if not self.config.enable_result_validation:
            return True, None

        # Convert result to dict format for validation
        result_dicts = [
            dict(zip(result.columns, row, strict=False))
            for row in result.rows[:10]  # Limit for validation
        ]

        return await self._openai_client.validate_result(
            question=question,
            sql=sql,
            result=result_dicts,
        )
