"""SQL query processing and execution service."""

import time
from typing import Any

import psycopg
import sqlglot
from psycopg.rows import dict_row
from sqlglot import exp
from sqlglot.errors import ParseError

from src.models.query import QueryResult


class SQLProcessor:
    """SQL parsing, validation, and transformation."""

    DEFAULT_LIMIT = 1000
    BLOCKED_TYPES = (exp.Insert, exp.Update, exp.Delete, exp.Drop, exp.TruncateTable, exp.Create, exp.AlterTable)

    @classmethod
    def process(cls, sql: str, max_limit: int | None = None) -> str:
        """Process SQL: parse, validate SELECT-only, add LIMIT if missing.

        Args:
            sql: Raw SQL query string
            max_limit: Maximum LIMIT to apply (defaults to DEFAULT_LIMIT)

        Returns:
            Processed SQL string safe for execution

        Raises:
            ValueError: If SQL is invalid or not a SELECT statement
        """
        # 1. Validate non-empty
        if not sql or not sql.strip():
            raise ValueError("SQL query cannot be empty")

        # 2. Parse with PostgreSQL dialect
        try:
            parsed = sqlglot.parse_one(sql, dialect="postgres")
        except ParseError as e:
            raise ValueError(f"SQL syntax error: {e}")

        if parsed is None:
            raise ValueError("Unable to parse SQL statement")

        # 3. Validate SELECT only
        if isinstance(parsed, cls.BLOCKED_TYPES):
            stmt_type = type(parsed).__name__
            raise ValueError(f"Only SELECT queries are allowed, {stmt_type} is not permitted")

        if not isinstance(parsed, (exp.Select, exp.Union)):
            stmt_type = type(parsed).__name__
            raise ValueError(f"Unsupported statement type: {stmt_type}")

        # 4. Add LIMIT if missing (only for SELECT, not UNION)
        if isinstance(parsed, exp.Select) and parsed.find(exp.Limit) is None:
            parsed = parsed.limit(max_limit or cls.DEFAULT_LIMIT)

        # 5. Generate PostgreSQL-compatible SQL
        return parsed.sql(dialect="postgres")

    @classmethod
    def validate_only(cls, sql: str) -> bool:
        """Validate SQL without processing.

        Args:
            sql: SQL query string

        Returns:
            True if valid SELECT query

        Raises:
            ValueError: If SQL is invalid or not SELECT
        """
        cls.process(sql)  # Will raise if invalid
        return True


class QueryExecutor:
    """Execute SQL queries against PostgreSQL."""

    @staticmethod
    async def execute(
        connection_url: str,
        sql: str,
        timeout_seconds: int = 30,
    ) -> QueryResult:
        """Execute a SQL query and return results.

        Args:
            connection_url: PostgreSQL connection URL
            sql: SQL query to execute (should be pre-processed)
            timeout_seconds: Query timeout in seconds

        Returns:
            QueryResult with columns, rows, and execution time

        Raises:
            ConnectionError: If unable to connect
            TimeoutError: If query exceeds timeout
            Exception: For other execution errors
        """
        start_time = time.perf_counter()

        try:
            async with await psycopg.AsyncConnection.connect(
                connection_url,
                options=f"-c statement_timeout={timeout_seconds * 1000}",
            ) as conn:
                async with conn.cursor(row_factory=dict_row) as cur:
                    await cur.execute(sql)
                    rows = await cur.fetchall()

                    # Get column names
                    columns = [desc.name for desc in cur.description] if cur.description else []

        except psycopg.OperationalError as e:
            error_msg = str(e).lower()
            if "timeout" in error_msg or "cancel" in error_msg:
                raise TimeoutError("Query execution timed out") from e
            raise ConnectionError(f"Database error: {e}") from e

        execution_time_ms = (time.perf_counter() - start_time) * 1000

        return QueryResult(
            columns=columns,
            rows=[dict(row) for row in rows],
            row_count=len(rows),
            execution_time_ms=round(execution_time_ms, 2),
        )
