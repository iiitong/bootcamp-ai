"""Storage layer protocols for abstraction and testability.

These protocols define the interfaces for storage operations, enabling:
- Alternative storage backends (e.g., PostgreSQL, Redis, in-memory)
- Clean dependency injection for testing
- Clear contract for storage implementations
"""

from typing import Any, Protocol, runtime_checkable

from src.models.database import DatabaseInfo, DatabaseMetadata, DbType, TableInfo


@runtime_checkable
class ConnectionRepositoryProtocol(Protocol):
    """Protocol for connection storage operations.

    Implementations should handle persisting and retrieving database
    connection information.
    """

    def list_connections(self) -> list[DatabaseInfo]:
        """List all database connections.

        Returns:
            List of DatabaseInfo objects with masked passwords
        """
        ...

    def get_connection(self, name: str) -> dict[str, Any] | None:
        """Get a connection by name.

        Args:
            name: Connection name

        Returns:
            Connection dict with full URL (including password), or None if not found
        """
        ...

    def upsert_connection(
        self,
        name: str,
        url: str,
        db_type: DbType | None = None,
    ) -> None:
        """Insert or update a database connection.

        Args:
            name: Connection name
            url: Database connection URL
            db_type: Database type (auto-detected from URL if None)
        """
        ...

    def delete_connection(self, name: str) -> bool:
        """Delete a connection.

        Args:
            name: Connection name

        Returns:
            True if deleted, False if not found
        """
        ...


@runtime_checkable
class MetadataCacheProtocol(Protocol):
    """Protocol for metadata cache operations.

    Implementations should handle caching and retrieving database schema
    metadata (tables, views, columns).
    """

    def get_metadata(self, connection_name: str) -> DatabaseMetadata | None:
        """Get cached metadata for a connection.

        Args:
            connection_name: Name of the connection

        Returns:
            DatabaseMetadata with tables/views, or None if not cached
        """
        ...

    def save_metadata(
        self,
        connection_name: str,
        tables: list[TableInfo],
        views: list[TableInfo],
    ) -> None:
        """Save metadata cache for a connection.

        Args:
            connection_name: Name of the connection
            tables: List of table metadata
            views: List of view metadata
        """
        ...

    def clear_metadata(self, connection_name: str) -> None:
        """Clear cached metadata for a connection.

        Args:
            connection_name: Name of the connection
        """
        ...


@runtime_checkable
class StorageProtocol(ConnectionRepositoryProtocol, MetadataCacheProtocol, Protocol):
    """Combined protocol for full storage operations.

    Implementations should provide both connection and metadata cache
    functionality. This is the interface used by API endpoints.
    """

    pass
