"""Database service protocols for dependency injection and extensibility.

These protocols define the interfaces for database operations, enabling:
- Clean dependency injection in the API layer
- Easy addition of new database types (SQLite, MariaDB, etc.)
- Better testability through mock implementations
"""

from typing import Protocol, runtime_checkable

from src.models.database import TableInfo
from src.models.query import QueryResult


@runtime_checkable
class QueryExecutorProtocol(Protocol):
    """Protocol for database query execution.

    Implementations should handle database-specific connection and query execution.

    Example:
        class PostgreSQLExecutor:
            @staticmethod
            async def execute(connection_url: str, sql: str, timeout_seconds: int = 30) -> QueryResult:
                # PostgreSQL-specific implementation
                ...
    """

    @staticmethod
    async def execute(
        connection_url: str,
        sql: str,
        timeout_seconds: int = 30,
    ) -> QueryResult:
        """Execute a SQL query and return results.

        Args:
            connection_url: Database connection URL
            sql: SQL query to execute (should be pre-processed/validated)
            timeout_seconds: Query timeout in seconds

        Returns:
            QueryResult with columns, rows, row_count, and execution_time_ms

        Raises:
            ConnectionError: If unable to connect to database
            TimeoutError: If query exceeds timeout
            ValueError: For SQL execution errors
        """
        ...


@runtime_checkable
class MetadataExtractorProtocol(Protocol):
    """Protocol for database metadata extraction.

    Implementations should extract schema information (tables, views, columns)
    from the target database.

    Example:
        class MySQLMetadataExtractor:
            @staticmethod
            async def extract(connection_url: str) -> tuple[list[TableInfo], list[TableInfo]]:
                # MySQL-specific implementation
                ...
    """

    @staticmethod
    async def extract(
        connection_url: str,
    ) -> tuple[list[TableInfo], list[TableInfo]]:
        """Extract metadata from a database.

        Args:
            connection_url: Database connection URL

        Returns:
            Tuple of (tables, views) with their column information

        Raises:
            ConnectionError: If unable to connect to database
        """
        ...

    @staticmethod
    async def test_connection(connection_url: str) -> bool:
        """Test if connection to database is successful.

        Args:
            connection_url: Database connection URL

        Returns:
            True if connection successful

        Raises:
            ConnectionError: If unable to connect
        """
        ...
