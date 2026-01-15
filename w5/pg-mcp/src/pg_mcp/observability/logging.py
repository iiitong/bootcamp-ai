"""Logging utilities for PostgreSQL MCP Server observability.

This module provides structured logging capabilities with:
- Slow query detection and logging
- Trace ID injection for distributed tracing correlation
- Configurable log formats (JSON/text)

Example usage:
    from pg_mcp.observability.logging import setup_logging, SlowQueryLogger

    # Configure logging at application startup
    setup_logging(level="INFO", format="json", include_trace_id=True)

    # Create a slow query logger
    slow_logger = SlowQueryLogger(threshold=5.0, log_sql=False)
    slow_logger.log_if_slow(
        duration=6.5,
        database="analytics",
        sql="SELECT * FROM large_table",
        rows=10000
    )
"""

from __future__ import annotations

import logging
import sys
from typing import TYPE_CHECKING, Any

import structlog

if TYPE_CHECKING:
    from collections.abc import MutableMapping

# SQL truncation limit for security and log size management
_SQL_TRUNCATE_LENGTH = 500


class SlowQueryLogger:
    """Slow query logger that records queries exceeding a time threshold.

    This logger helps identify performance bottlenecks by logging queries
    that take longer than the configured threshold. For security, SQL content
    can be optionally masked (only logging length instead of actual content).

    Attributes:
        threshold: Duration threshold in seconds. Queries taking longer are logged.
        log_sql: If True, log truncated SQL content. If False, only log SQL length.
        logger: The structlog logger instance used for output.

    Example:
        >>> slow_logger = SlowQueryLogger(threshold=5.0, log_sql=False)
        >>> slow_logger.log_if_slow(6.5, "analytics", "SELECT ...", 100)
        # Logs: slow_query_detected database=analytics duration_seconds=6.5 ...
    """

    def __init__(self, threshold: float = 5.0, log_sql: bool = False) -> None:
        """Initialize the slow query logger.

        Args:
            threshold: Time threshold in seconds. Queries equal to or exceeding
                this duration will be logged. Default is 5.0 seconds.
            log_sql: Whether to include (truncated) SQL in logs. Set to False
                for production environments where SQL may contain sensitive data.
                Default is False.
        """
        self.threshold = threshold
        self.log_sql = log_sql
        self.logger = structlog.get_logger(__name__)

    def log_if_slow(
        self,
        duration: float,
        database: str,
        sql: str,
        rows: int,
    ) -> None:
        """Log the query if it exceeds the configured threshold.

        This method checks if the query duration meets or exceeds the threshold,
        and if so, logs a warning with relevant metrics. The SQL content is
        either truncated or replaced with its length depending on log_sql setting.

        Args:
            duration: Query execution time in seconds.
            database: Name of the database where the query was executed.
            sql: The SQL query string that was executed.
            rows: Number of rows returned by the query.
        """
        if duration < self.threshold:
            return

        log_data: dict[str, Any] = {
            "database": database,
            "duration_seconds": round(duration, 3),
            "rows_returned": rows,
        }

        if self.log_sql:
            # Truncate SQL for log size management and basic security
            log_data["sql"] = sql[:_SQL_TRUNCATE_LENGTH]
            if len(sql) > _SQL_TRUNCATE_LENGTH:
                log_data["sql_truncated"] = True
        else:
            # Only log length for security - don't expose SQL content
            log_data["sql_length"] = len(sql)

        self.logger.warning("slow_query_detected", **log_data)


def add_trace_id(
    logger: structlog.types.WrappedLogger,
    method_name: str,
    event_dict: MutableMapping[str, Any],
) -> MutableMapping[str, Any]:
    """Add trace_id to log entries for distributed tracing correlation.

    This is a structlog processor that injects the current trace ID from
    the TracingManager into log entries. This allows log entries to be
    correlated with distributed traces.

    Args:
        logger: The wrapped logger instance (unused but required by structlog).
        method_name: The name of the log method called (unused but required).
        event_dict: The event dictionary being processed.

    Returns:
        The event dictionary with trace_id added if available.

    Note:
        This function handles the case where the tracing module is not
        initialized or not available, silently skipping trace ID injection.
    """
    try:
        # Import lazily to avoid circular imports and handle optional dependency
        from pg_mcp.observability.tracing import get_tracing_manager

        manager = get_tracing_manager()
        if manager is not None:
            trace_id = manager.get_current_trace_id()
            if trace_id:
                event_dict["trace_id"] = trace_id
    except ImportError:
        # Tracing module not available - skip trace ID injection
        pass
    except Exception:
        # Tracing not initialized or other error - fail silently
        # We don't want logging to fail due to tracing issues
        pass

    return event_dict


def setup_logging(
    level: str = "INFO",
    format: str = "json",  # noqa: A002 - 'format' shadows builtin but matches spec
    include_trace_id: bool = True,
) -> None:
    """Configure structured logging with structlog.

    This function sets up structlog with a pipeline of processors for
    structured logging. It supports both JSON output (for production/log
    aggregation) and console output (for development).

    Args:
        level: Log level string. One of: DEBUG, INFO, WARNING, ERROR.
            Default is "INFO".
        format: Output format. Either "json" for machine-readable JSON
            or "text" for human-readable console output. Default is "json".
        include_trace_id: Whether to include trace IDs from the tracing
            module in log entries. Default is True.

    Example:
        >>> # Production setup
        >>> setup_logging(level="INFO", format="json", include_trace_id=True)

        >>> # Development setup
        >>> setup_logging(level="DEBUG", format="text", include_trace_id=False)
    """
    # Configure standard library logging as fallback
    log_level = getattr(logging, level.upper(), logging.INFO)
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stderr,
        level=log_level,
    )

    # Build the processor chain
    processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]

    # Optionally add trace_id processor
    if include_trace_id:
        processors.append(add_trace_id)

    # Add exception formatting
    processors.append(structlog.dev.set_exc_info)

    # Select output renderer based on format
    if format == "json":
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer(colors=True))

    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
