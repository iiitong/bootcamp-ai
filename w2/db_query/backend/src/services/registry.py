"""Database type registry for extensible database support.

This module provides a centralized registry for database-specific implementations,
eliminating if/else dispatch logic in the API layer and enabling easy addition
of new database types.

Usage:
    from src.services.registry import DatabaseRegistry

    # Get executor for a database type
    executor = DatabaseRegistry.get_executor("mysql")
    result = await executor.execute(url, sql, timeout)

    # Get extractor for metadata
    extractor = DatabaseRegistry.get_extractor("postgresql")
    tables, views = await extractor.extract(url)
"""

import logging
from typing import Type

from src.models.database import DbType
from src.services.protocols import MetadataExtractorProtocol, QueryExecutorProtocol

logger = logging.getLogger(__name__)


class DatabaseRegistry:
    """Registry for database type handlers.

    Provides a centralized way to look up database-specific implementations
    for query execution and metadata extraction.
    """

    _executors: dict[DbType, Type[QueryExecutorProtocol]] = {}
    _extractors: dict[DbType, Type[MetadataExtractorProtocol]] = {}
    _dialects: dict[DbType, str] = {
        "postgresql": "postgres",
        "mysql": "mysql",
    }

    @classmethod
    def register_executor(
        cls,
        db_type: DbType,
        executor: Type[QueryExecutorProtocol],
    ) -> None:
        """Register a query executor for a database type.

        Args:
            db_type: Database type identifier
            executor: Executor class implementing QueryExecutorProtocol
        """
        cls._executors[db_type] = executor
        logger.debug("Registered executor for %s: %s", db_type, executor.__name__)

    @classmethod
    def register_extractor(
        cls,
        db_type: DbType,
        extractor: Type[MetadataExtractorProtocol],
    ) -> None:
        """Register a metadata extractor for a database type.

        Args:
            db_type: Database type identifier
            extractor: Extractor class implementing MetadataExtractorProtocol
        """
        cls._extractors[db_type] = extractor
        logger.debug("Registered extractor for %s: %s", db_type, extractor.__name__)

    @classmethod
    def get_executor(cls, db_type: DbType) -> Type[QueryExecutorProtocol]:
        """Get the query executor for a database type.

        Args:
            db_type: Database type identifier

        Returns:
            Executor class for the database type

        Raises:
            ValueError: If no executor is registered for the db_type
        """
        if db_type not in cls._executors:
            raise ValueError(f"No executor registered for database type: {db_type}")
        return cls._executors[db_type]

    @classmethod
    def get_extractor(cls, db_type: DbType) -> Type[MetadataExtractorProtocol]:
        """Get the metadata extractor for a database type.

        Args:
            db_type: Database type identifier

        Returns:
            Extractor class for the database type

        Raises:
            ValueError: If no extractor is registered for the db_type
        """
        if db_type not in cls._extractors:
            raise ValueError(f"No extractor registered for database type: {db_type}")
        return cls._extractors[db_type]

    @classmethod
    def get_dialect(cls, db_type: DbType) -> str:
        """Get the SQL dialect for a database type (for sqlglot).

        Args:
            db_type: Database type identifier

        Returns:
            SQL dialect string for sqlglot
        """
        return cls._dialects.get(db_type, "postgres")

    @classmethod
    def supported_types(cls) -> list[DbType]:
        """Get list of supported database types.

        Returns:
            List of database type identifiers with registered executors
        """
        return list(cls._executors.keys())


def _register_default_implementations() -> None:
    """Register default database implementations.

    This is called at module import to register built-in database support.
    """
    # Import implementations here to avoid circular imports
    from src.services.metadata import MetadataExtractor
    from src.services.metadata_mysql import MySQLMetadataExtractor
    from src.services.query import QueryExecutor
    from src.services.query_mysql import MySQLQueryExecutor

    # Register PostgreSQL
    DatabaseRegistry.register_executor("postgresql", QueryExecutor)
    DatabaseRegistry.register_extractor("postgresql", MetadataExtractor)

    # Register MySQL
    DatabaseRegistry.register_executor("mysql", MySQLQueryExecutor)
    DatabaseRegistry.register_extractor("mysql", MySQLMetadataExtractor)


# Auto-register default implementations on module import
_register_default_implementations()
