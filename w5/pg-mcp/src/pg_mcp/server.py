"""FastMCP server implementation for PostgreSQL MCP Server."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastmcp import FastMCP

from pg_mcp.config import AppConfig, load_config
from pg_mcp.infrastructure.database import DatabasePoolManager
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
    ReturnType,
)
from pg_mcp.utils.logging import get_logger, setup_logging

logger = get_logger(__name__)


class PgMcpServer:
    """PostgreSQL MCP Server."""

    def __init__(self, config: AppConfig) -> None:
        """Initialize the server.

        Args:
            config: Application configuration
        """
        self.config = config
        self._pool_manager = DatabasePoolManager()
        self._schema_cache = SchemaCache(config.server.cache_refresh_interval)
        self._openai_client = OpenAIClient(config.openai)
        self._rate_limiter = RateLimiter(config.server.rate_limit)
        self._sql_parser = SQLParser()
        self._logger = logger

    async def startup(self) -> None:
        """Initialize server resources."""
        self._logger.info("Starting PostgreSQL MCP Server")

        # Initialize database pools
        for db_config in self.config.databases:
            await self._pool_manager.add_database(db_config)
            self._logger.info("Database pool initialized", database=db_config.name)

        # Pre-load schema cache
        for db_name in self._pool_manager.database_names:
            pool = self._pool_manager.get_pool(db_name)
            await self._schema_cache.refresh(db_name, pool)
            self._logger.info("Schema cache loaded", database=db_name)

        self._logger.info("Server startup complete")

    async def shutdown(self) -> None:
        """Cleanup server resources."""
        self._logger.info("Shutting down PostgreSQL MCP Server")
        await self._pool_manager.close_all()
        await self._openai_client.close()
        self._logger.info("Server shutdown complete")

    def _resolve_database(self, database: str | None) -> str:
        """Resolve the target database name.

        Args:
            database: Requested database name or None for default

        Returns:
            Resolved database name

        Raises:
            PgMcpError: If database not found
        """
        if database is None:
            return self.config.get_default_database().name

        db_config = self.config.get_database(database)
        if db_config is None:
            from pg_mcp.models.errors import UnknownDatabaseError
            raise UnknownDatabaseError(database, self.config.database_names)

        return db_config.name

    async def get_schema(self, database: str) -> DatabaseSchema:
        """Get database schema.

        Args:
            database: Database name

        Returns:
            Database schema
        """
        pool = self._pool_manager.get_pool(database)
        return await self._schema_cache.get_or_refresh(database, pool)

    async def execute_query(self, request: QueryRequest) -> QueryResponse:
        """Execute a natural language query.

        Args:
            request: Query request

        Returns:
            Query response
        """
        # Check rate limit
        await self._rate_limiter.check_request()

        # Resolve database
        db_name = self._resolve_database(request.database)
        pool = self._pool_manager.get_pool(db_name)

        # Get schema
        schema = await self.get_schema(db_name)

        # Generate SQL
        sql_result = await self._openai_client.generate_sql(
            request.question,
            schema,
        )

        # Validate SQL
        self._sql_parser.validate_and_raise(sql_result.sql)

        # Record token usage
        await self._rate_limiter.record_tokens(sql_result.tokens_used)

        # If only SQL requested, return now
        if request.return_type == ReturnType.SQL:
            return QueryResponse(
                sql=sql_result.sql,
                explanation=sql_result.explanation,
            )

        # Execute query
        limit = request.limit or self.config.server.max_result_rows
        sql_with_limit = self._sql_parser.add_limit(sql_result.sql, limit + 1)

        try:
            if self.config.server.use_readonly_transactions:
                rows = await pool.fetch_readonly(
                    sql_with_limit,
                    timeout=self.config.server.query_timeout,
                )
            else:
                rows = await pool.fetch(
                    sql_with_limit,
                    timeout=self.config.server.query_timeout,
                )
        except TimeoutError as e:
            from pg_mcp.models.errors import QueryTimeoutError
            raise QueryTimeoutError(self.config.server.query_timeout) from e

        # Process results
        truncated = len(rows) > limit
        if truncated:
            rows = rows[:limit]

        columns = list(rows[0].keys()) if rows else []
        result_rows = [list(row.values()) for row in rows]

        result = QueryResult(
            columns=columns,
            rows=result_rows,
            row_count=len(result_rows),
            truncated=truncated,
        )

        response = QueryResponse(result=result)

        if request.return_type == ReturnType.BOTH:
            response.sql = sql_result.sql
            response.explanation = sql_result.explanation

        return response

    def list_databases(self) -> list[str]:
        """List available databases.

        Returns:
            List of database names
        """
        return self.config.database_names


def create_mcp_server(config: AppConfig) -> FastMCP:
    """Create and configure the FastMCP server.

    Args:
        config: Application configuration

    Returns:
        Configured FastMCP server
    """
    mcp = FastMCP("PostgreSQL MCP Server")
    server = PgMcpServer(config)

    @asynccontextmanager
    async def lifespan(app: Any) -> AsyncIterator[None]:
        """Server lifespan handler."""
        await server.startup()
        try:
            yield
        finally:
            await server.shutdown()

    mcp.settings.lifespan = lifespan

    @mcp.resource("databases://list")
    async def list_databases() -> str:
        """List all available databases."""
        databases = server.list_databases()
        return "\n".join(f"- {db}" for db in databases)

    @mcp.resource("schema://{database}")
    async def get_schema(database: str) -> str:
        """Get the schema for a specific database."""
        schema = await server.get_schema(database)
        return schema.to_prompt_text()

    @mcp.tool()
    async def query(
        question: str,
        database: str | None = None,
        return_type: str = "result",
        limit: int | None = None,
    ) -> dict[str, Any]:
        """
        Execute a natural language query against a PostgreSQL database.

        Args:
            question: The natural language question to answer
            database: Target database name (uses default if not specified)
            return_type: What to return - "sql", "result", or "both"
            limit: Maximum number of rows to return

        Returns:
            Query results with SQL and/or data
        """
        try:
            request = QueryRequest(
                question=question,
                database=database,
                return_type=ReturnType(return_type),
                limit=limit,
            )
            response = await server.execute_query(request)
            return response.model_dump(exclude_none=True)
        except PgMcpError as e:
            return e.to_response().model_dump()
        except Exception as e:
            logger.exception("Unexpected error", error=str(e))
            return {
                "success": False,
                "error_code": ErrorCode.INTERNAL_ERROR,
                "error_message": str(e),
            }

    @mcp.tool()
    async def refresh_schema(database: str | None = None) -> dict[str, Any]:
        """
        Refresh the schema cache for a database.

        Args:
            database: Database to refresh (refreshes all if not specified)

        Returns:
            Status of the refresh operation
        """
        try:
            if database:
                db_name = server._resolve_database(database)
                pool = server._pool_manager.get_pool(db_name)
                await server._schema_cache.refresh(db_name, pool)
                return {"success": True, "databases": [db_name]}
            else:
                refreshed = []
                for db_name in server._pool_manager.database_names:
                    pool = server._pool_manager.get_pool(db_name)
                    await server._schema_cache.refresh(db_name, pool)
                    refreshed.append(db_name)
                return {"success": True, "databases": refreshed}
        except Exception as e:
            return {"success": False, "error": str(e)}

    return mcp


def main() -> None:
    """Entry point for the MCP server."""
    setup_logging()

    try:
        config = load_config()
    except Exception as e:
        logger.error("Failed to load configuration", error=str(e))
        raise SystemExit(1) from None

    mcp = create_mcp_server(config)
    mcp.run()


if __name__ == "__main__":
    main()
