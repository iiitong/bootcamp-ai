# src/pg_mcp/services/query_executor_manager.py

"""Query executor manager for multi-database environments.

This module provides:
- Management of multiple QueryExecutor instances
- Database routing based on request parameters
- Lifecycle management for all executors
"""

import structlog

from pg_mcp.config.models import AccessPolicyConfig, DatabaseConfig
from pg_mcp.infrastructure.database import DatabasePoolManager
from pg_mcp.infrastructure.sql_parser import SQLParser
from pg_mcp.models.errors import ErrorCode, PgMcpError, UnknownDatabaseError
from pg_mcp.security.access_policy import DatabaseAccessPolicy
from pg_mcp.security.audit_logger import AuditLogger
from pg_mcp.security.explain_validator import ExplainValidator
from pg_mcp.services.query_executor import QueryExecutor

logger = structlog.get_logger()


class AmbiguousDatabaseError(PgMcpError):
    """Database selection is ambiguous.

    Raised when no database is specified and multiple databases are available.
    """

    def __init__(self, available: list[str]):
        """Initialize the error.

        Args:
            available: List of available database names
        """
        super().__init__(
            ErrorCode.AMBIGUOUS_QUERY,
            f"Database not specified and multiple databases available. "
            f"Please specify one of: {', '.join(available)}",
            {"available_databases": available},
        )


class QueryExecutorManager:
    """
    Query executor manager for multi-database environments.

    Responsibilities:
    - Create independent QueryExecutor for each database
    - Route requests to the correct executor
    - Manage executor lifecycle
    """

    def __init__(
        self,
        pool_manager: DatabasePoolManager,
        sql_parser: SQLParser,
        audit_logger: AuditLogger,
    ):
        """Initialize the manager.

        Args:
            pool_manager: Database pool manager for connection pools
            sql_parser: SQL parser shared across executors
            audit_logger: Audit logger shared across executors
        """
        self.pool_manager = pool_manager
        self.sql_parser = sql_parser
        self.audit_logger = audit_logger
        self._executors: dict[str, QueryExecutor] = {}

    def register_database(
        self,
        config: DatabaseConfig,
        access_policy_config: AccessPolicyConfig | None = None,
    ) -> None:
        """
        Register a database and create its executor.

        Args:
            config: Database configuration
            access_policy_config: Access policy configuration (optional, defaults to empty policy)
        """
        policy_config = access_policy_config or AccessPolicyConfig()

        # Create access policy
        access_policy = DatabaseAccessPolicy(policy_config)

        # Create EXPLAIN validator
        explain_validator = ExplainValidator(policy_config.explain_policy)

        # Get connection pool
        pool = self.pool_manager.get_pool(config.name)

        # Create executor
        executor = QueryExecutor(
            database_name=config.name,
            pool=pool,
            access_policy=access_policy,
            explain_validator=explain_validator,
            audit_logger=self.audit_logger,
            sql_parser=self.sql_parser,
        )

        self._executors[config.name] = executor
        logger.info(
            "query_executor_registered",
            database=config.name,
            policy_enabled=policy_config.explain_policy.enabled,
        )

    def get_executor(self, database: str | None = None) -> QueryExecutor:
        """
        Get executor for specified database.

        If only one database is registered and no database is specified,
        automatically selects that database. If multiple databases are
        registered and no database is specified, raises AmbiguousDatabaseError.

        Args:
            database: Database name (optional)

        Returns:
            QueryExecutor for the specified or auto-selected database

        Raises:
            UnknownDatabaseError: Database does not exist
            AmbiguousDatabaseError: Database not specified with multiple databases available
        """
        available = list(self._executors.keys())

        if database is None:
            # No database specified
            if len(available) == 1:
                # Only one database, auto-select
                return self._executors[available[0]]
            else:
                # Multiple databases, require explicit specification
                raise AmbiguousDatabaseError(available)

        if database not in self._executors:
            raise UnknownDatabaseError(database, available)

        return self._executors[database]

    def list_databases(self) -> list[str]:
        """List all registered database names.

        Returns:
            List of registered database names
        """
        return list(self._executors.keys())

    async def close_all(self) -> None:
        """Close all executors.

        Clears the internal executor registry. Note that this does not
        close the underlying connection pools - that should be done
        through the DatabasePoolManager.
        """
        self._executors.clear()
        logger.info("all_query_executors_closed")
