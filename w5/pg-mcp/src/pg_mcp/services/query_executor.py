# src/pg_mcp/services/query_executor.py

"""Query executor for single database operations.

This module provides:
- Single database query execution with policy enforcement
- Access policy validation before SQL execution
- EXPLAIN-based query plan validation
- Audit logging for all query operations
"""

import time
from dataclasses import dataclass

import asyncpg
import structlog

from pg_mcp.infrastructure.database import DatabasePool
from pg_mcp.infrastructure.sql_parser import SQLParser
from pg_mcp.models.errors import PgMcpError
from pg_mcp.models.query import QueryResult
from pg_mcp.security.access_policy import (
    ColumnAccessDeniedError,
    DatabaseAccessPolicy,
    PolicyValidationResult,
    SchemaAccessDeniedError,
    TableAccessDeniedError,
)
from pg_mcp.security.audit_logger import AuditEventType, AuditLogger
from pg_mcp.security.explain_validator import (
    ExplainValidator,
    QueryTooExpensiveError,
)

logger = structlog.get_logger()


@dataclass
class ExecutionContext:
    """Execution context for query tracking.

    Attributes:
        request_id: Unique identifier for the request
        client_ip: Client IP address (optional, only available in SSE mode)
        session_id: Session identifier for tracking (optional)
    """

    request_id: str
    client_ip: str | None
    session_id: str | None


class QueryExecutor:
    """
    Single database query executor.

    Responsibilities:
    - Hold database connection pool and access policy
    - Enforce access policy before SQL execution
    - Validate query plan with EXPLAIN
    - Record audit logs for all operations

    Relationship with QueryService:
    - QueryService handles business flow orchestration (SQL generation, retry logic)
    - QueryExecutor handles single SQL execution (policy check, actual execution)
    """

    def __init__(
        self,
        database_name: str,
        pool: DatabasePool,
        access_policy: DatabaseAccessPolicy,
        explain_validator: ExplainValidator,
        audit_logger: AuditLogger,
        sql_parser: SQLParser,
    ):
        """Initialize the query executor.

        Args:
            database_name: Name of the database this executor is bound to
            pool: Database connection pool
            access_policy: Access policy for validation
            explain_validator: EXPLAIN validator for query plan analysis
            audit_logger: Audit logger for recording operations
            sql_parser: SQL parser for policy extraction
        """
        self.database_name = database_name
        self.pool = pool
        self.access_policy = access_policy
        self.explain_validator = explain_validator
        self.audit_logger = audit_logger
        self.sql_parser = sql_parser

    async def execute(
        self,
        sql: str,
        limit: int,
        context: ExecutionContext,
        question: str = "",
    ) -> QueryResult:
        """
        Execute query with policy enforcement.

        Args:
            sql: SQL statement to execute
            limit: Maximum number of rows to return
            context: Execution context for tracking
            question: Original natural language question

        Returns:
            QueryResult with columns, rows, and metadata

        Raises:
            TableAccessDeniedError: Table access is denied
            ColumnAccessDeniedError: Column access is denied
            SchemaAccessDeniedError: Schema access is denied
            QueryTooExpensiveError: Query cost exceeds limits
            SeqScanDeniedError: Sequential scan on large table is denied
        """
        start_time = time.monotonic()
        policy_checks: dict[str, str] = {}

        try:
            # 1. Parse SQL for policy validation
            parsed = self.sql_parser.parse_for_policy(sql)

            # 2. Access policy check
            policy_result = self.access_policy.validate_sql(parsed)
            policy_checks = {
                "table_access": "passed"
                if not any(v.check_type == "table" for v in policy_result.violations)
                else "denied",
                "column_access": "passed"
                if not any(v.check_type == "column" for v in policy_result.violations)
                else "denied",
                "explain_check": "pending",
            }

            if not policy_result.passed:
                # Raise appropriate exception based on violation type
                self._raise_policy_error(policy_result)

            # 3. EXPLAIN policy check
            async with self.pool.acquire() as conn:
                explain_result = await self.explain_validator.validate(conn, sql)
                policy_checks["explain_check"] = "passed" if explain_result.passed else "denied"

                if not explain_result.passed:
                    raise QueryTooExpensiveError(
                        estimated_rows=(
                            explain_result.result.estimated_rows if explain_result.result else 0
                        ),
                        estimated_cost=(
                            explain_result.result.total_cost if explain_result.result else 0
                        ),
                        limits={
                            "max_rows": self.explain_validator.config.max_estimated_rows,
                            "max_cost": self.explain_validator.config.max_estimated_cost,
                        },
                    )

                # 4. Execute query
                rows = await conn.fetch(sql, timeout=30.0)

                # 5. Build result
                result = self._build_result(rows, limit)

                # 6. Record audit log
                execution_time = (time.monotonic() - start_time) * 1000
                await self._log_success(
                    context, question, sql, result, execution_time, policy_checks
                )

                return result

        except PgMcpError:
            # Known error, record audit and re-raise
            execution_time = (time.monotonic() - start_time) * 1000
            await self._log_error(
                context,
                question,
                sql,
                execution_time,
                policy_checks,
                error=None,  # Exception will be captured by upper layer
            )
            raise
        except Exception as e:
            # Unknown error
            execution_time = (time.monotonic() - start_time) * 1000
            await self._log_error(context, question, sql, execution_time, policy_checks, error=e)
            raise

    def _raise_policy_error(self, result: PolicyValidationResult) -> None:
        """Raise appropriate exception based on violation type.

        Args:
            result: Policy validation result containing violations

        Raises:
            SchemaAccessDeniedError: For schema violations
            TableAccessDeniedError: For table violations
            ColumnAccessDeniedError: For column violations
        """
        for violation in result.violations:
            if violation.check_type == "schema":
                raise SchemaAccessDeniedError(
                    violation.resource, self.access_policy.config.allowed_schemas
                )
            elif violation.check_type == "table":
                # Collect all table violations
                denied_tables = [v.resource for v in result.violations if v.check_type == "table"]
                raise TableAccessDeniedError(denied_tables)
            elif violation.check_type == "column":
                # Collect all column violations
                denied_columns = [v.resource for v in result.violations if v.check_type == "column"]
                is_select_star = any("SELECT *" in w for w in result.warnings)
                raise ColumnAccessDeniedError(denied_columns, is_select_star)

    def _build_result(self, rows: list[asyncpg.Record], limit: int) -> QueryResult:
        """Build query result from database rows.

        Args:
            rows: Raw rows from database
            limit: Maximum number of rows to include

        Returns:
            QueryResult with formatted data
        """
        if not rows:
            return QueryResult(
                columns=[],
                rows=[],
                row_count=0,
                truncated=False,
            )

        columns = list(rows[0].keys())
        data = [list(row.values()) for row in rows]

        truncated = len(data) > limit
        if truncated:
            data = data[:limit]

        return QueryResult(
            columns=columns,
            rows=data,
            row_count=len(data),
            truncated=truncated,
        )

    async def _log_success(
        self,
        context: ExecutionContext,
        question: str,
        sql: str,
        result: QueryResult,
        execution_time_ms: float,
        policy_checks: dict[str, str],
    ) -> None:
        """Record successful query audit log.

        Args:
            context: Execution context
            question: Natural language question
            sql: Executed SQL
            result: Query result
            execution_time_ms: Execution time in milliseconds
            policy_checks: Policy check results
        """
        event = AuditLogger.create_event(
            event_type=AuditEventType.QUERY_EXECUTED,
            request_id=context.request_id,
            database=self.database_name,
            client_ip=context.client_ip,
            session_id=context.session_id,
            question=question,
            sql=sql,
            rows_returned=result.row_count,
            execution_time_ms=execution_time_ms,
            truncated=result.truncated,
            policy_checks=policy_checks,
        )
        await self.audit_logger.log(event)

    async def _log_error(
        self,
        context: ExecutionContext,
        question: str,
        sql: str,
        execution_time_ms: float,
        policy_checks: dict[str, str],
        error: Exception | None,
    ) -> None:
        """Record failed query audit log.

        Args:
            context: Execution context
            question: Natural language question
            sql: Attempted SQL
            execution_time_ms: Execution time in milliseconds
            policy_checks: Policy check results
            error: Exception that caused the failure (optional)
        """
        error_code = None
        error_message = None

        if isinstance(error, PgMcpError):
            error_code = error.code.value
            error_message = error.message
        elif error:
            error_code = "INTERNAL_ERROR"
            error_message = str(error)

        event = AuditLogger.create_event(
            event_type=AuditEventType.QUERY_DENIED,
            request_id=context.request_id,
            database=self.database_name,
            client_ip=context.client_ip,
            session_id=context.session_id,
            question=question,
            sql=sql,
            execution_time_ms=execution_time_ms,
            error_code=error_code,
            error_message=error_message,
            policy_checks=policy_checks,
        )
        await self.audit_logger.log(event)
