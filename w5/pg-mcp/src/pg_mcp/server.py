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
    ReturnType,
)
from pg_mcp.services.query_service import QueryService, QueryServiceConfig
from pg_mcp.utils.logging import get_logger, setup_logging

logger = get_logger(__name__)


class PgMcpServer:
    """PostgreSQL MCP Server.

    This class orchestrates all server components and delegates query execution
    to QueryService to avoid code duplication.
    """

    def __init__(self, config: AppConfig) -> None:
        """Initialize the server.

        Args:
            config: Application configuration
        """
        self.config = config
        self._pool_manager = DatabasePoolManager()
        self._schema_cache = SchemaCache(config.server.cache_refresh_interval)
        self._openai_client = OpenAIClient(config.openai)
        self._rate_limiter = RateLimiter(config.rate_limit)
        self._sql_parser = SQLParser()
        self._logger = logger

        # Create QueryService with all dependencies
        query_config = QueryServiceConfig.from_server_config(config.server)
        self._query_service = QueryService(
            config=query_config,
            app_config=config,
            pool_manager=self._pool_manager,
            schema_cache=self._schema_cache,
            openai_client=self._openai_client,
            sql_parser=self._sql_parser,
            rate_limiter=self._rate_limiter,
        )

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

        Delegates to QueryService to avoid code duplication.

        Args:
            request: Query request

        Returns:
            Query response
        """
        return await self._query_service.execute_query(request)

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
        except ValueError as e:
            # Invalid return_type or other validation errors
            logger.warning("Validation error in query", error=str(e))
            return {
                "success": False,
                "error_code": ErrorCode.INVALID_REQUEST.value,
                "error_message": str(e),
            }
        except KeyError as e:
            # Database not found
            logger.warning("Database not found", error=str(e))
            return {
                "success": False,
                "error_code": ErrorCode.DATABASE_NOT_FOUND.value,
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
                # Validate database exists
                db_config = server.config.get_database(database)
                if db_config is None:
                    return {
                        "success": False,
                        "error": f"Database '{database}' not found",
                    }
                db_name = db_config.name
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
        except KeyError as e:
            return {"success": False, "error": f"Database pool not found: {e}"}
        except ConnectionError as e:
            return {"success": False, "error": f"Connection error: {e}"}

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
