"""Prometheus metrics collector for pg-mcp.

This module provides comprehensive metrics collection for monitoring
the pg-mcp server, including request metrics, SQL generation metrics,
database pool metrics, OpenAI integration metrics, and rate limiting metrics.
"""

from typing import Any

import structlog
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    Info,
    generate_latest,
)

logger = structlog.get_logger(__name__)


class MetricsCollector:
    """Prometheus metrics collector for pg-mcp.

    This class is responsible for:
    - Defining and exposing all system metrics
    - Providing convenient methods for recording metrics
    - Supporting custom Registry for testing isolation

    Usage:
        collector = MetricsCollector()
        collector.record_request("mydb", "success", 0.5)
        metrics_output = collector.generate_metrics()
    """

    def __init__(self, registry: CollectorRegistry | None = None) -> None:
        """Initialize the metrics collector.

        Args:
            registry: Optional custom CollectorRegistry for testing isolation.
                     If not provided, a new registry is created.
        """
        self.registry = registry or CollectorRegistry()
        self._setup_metrics()
        logger.debug("MetricsCollector initialized")

    def _setup_metrics(self) -> None:
        """Initialize all Prometheus metrics."""
        # =============================================================
        # Request Metrics
        # =============================================================
        self.requests_total = Counter(
            "pg_mcp_requests_total",
            "Total number of requests",
            ["database", "status", "error_code"],
            registry=self.registry,
        )

        self.request_duration = Histogram(
            "pg_mcp_request_duration_seconds",
            "Request duration in seconds",
            ["database"],
            buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
            registry=self.registry,
        )

        self.requests_in_flight = Gauge(
            "pg_mcp_requests_in_flight",
            "Number of requests currently being processed",
            ["database"],
            registry=self.registry,
        )

        # =============================================================
        # SQL Generation Metrics
        # =============================================================
        self.sql_generation_total = Counter(
            "pg_mcp_sql_generation_total",
            "Total number of SQL generation attempts",
            ["database", "status"],
            registry=self.registry,
        )

        self.sql_generation_duration = Histogram(
            "pg_mcp_sql_generation_duration_seconds",
            "SQL generation duration in seconds",
            ["database"],
            buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0],
            registry=self.registry,
        )

        self.sql_retries_total = Counter(
            "pg_mcp_sql_retries_total",
            "Total number of SQL generation retries",
            ["database", "reason"],
            registry=self.registry,
        )

        # =============================================================
        # Database Pool Metrics
        # =============================================================
        self.db_pool_size = Gauge(
            "pg_mcp_db_pool_size",
            "Current size of the database connection pool",
            ["database"],
            registry=self.registry,
        )

        self.db_pool_available = Gauge(
            "pg_mcp_db_pool_available",
            "Number of available connections in the pool",
            ["database"],
            registry=self.registry,
        )

        self.db_query_duration = Histogram(
            "pg_mcp_db_query_duration_seconds",
            "Database query execution duration in seconds",
            ["database"],
            buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
            registry=self.registry,
        )

        # =============================================================
        # OpenAI Integration Metrics
        # =============================================================
        self.openai_tokens_total = Counter(
            "pg_mcp_openai_tokens_total",
            "Total number of OpenAI tokens used",
            ["type"],  # "prompt" or "completion"
            registry=self.registry,
        )

        self.openai_requests_total = Counter(
            "pg_mcp_openai_requests_total",
            "Total number of OpenAI API requests",
            ["status"],
            registry=self.registry,
        )

        self.openai_request_duration = Histogram(
            "pg_mcp_openai_request_duration_seconds",
            "OpenAI API request duration in seconds",
            buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0],
            registry=self.registry,
        )

        # =============================================================
        # Rate Limiting Metrics
        # =============================================================
        self.rate_limit_current = Gauge(
            "pg_mcp_rate_limit_current",
            "Current rate limit counters",
            ["limit_type"],  # "requests_minute", "requests_hour", "tokens_minute"
            registry=self.registry,
        )

        self.rate_limit_exceeded_total = Counter(
            "pg_mcp_rate_limit_exceeded_total",
            "Total number of rate limit exceeded events",
            ["limit_type"],
            registry=self.registry,
        )

        # =============================================================
        # Policy Check Metrics
        # =============================================================
        self.policy_check_total = Counter(
            "pg_mcp_policy_check_total",
            "Total number of policy checks",
            ["check_type", "result"],  # result: "allowed", "denied"
            registry=self.registry,
        )

        # =============================================================
        # Service Information
        # =============================================================
        self.service_info = Info(
            "pg_mcp_service",
            "Service information",
            registry=self.registry,
        )

    # =================================================================
    # Convenience Methods
    # =================================================================

    def record_request(
        self,
        database: str,
        status: str,
        duration: float,
        error_code: str | None = None,
    ) -> None:
        """Record a request metric.

        Args:
            database: The database name
            status: Request status (e.g., "success", "error")
            duration: Request duration in seconds
            error_code: Optional error code if the request failed
        """
        self.requests_total.labels(
            database=database,
            status=status,
            error_code=error_code or "",
        ).inc()
        self.request_duration.labels(database=database).observe(duration)
        logger.debug(
            "Recorded request metric",
            database=database,
            status=status,
            duration_ms=int(duration * 1000),
        )

    def record_sql_generation(
        self,
        database: str,
        status: str,
        duration: float,
    ) -> None:
        """Record SQL generation metrics.

        Args:
            database: The database name
            status: Generation status (e.g., "success", "error")
            duration: Generation duration in seconds
        """
        self.sql_generation_total.labels(database=database, status=status).inc()
        self.sql_generation_duration.labels(database=database).observe(duration)
        logger.debug(
            "Recorded SQL generation metric",
            database=database,
            status=status,
            duration_ms=int(duration * 1000),
        )

    def record_sql_retry(self, database: str, reason: str) -> None:
        """Record SQL generation retry.

        Args:
            database: The database name
            reason: Reason for retry (e.g., "syntax_error", "unsafe_sql")
        """
        self.sql_retries_total.labels(database=database, reason=reason).inc()
        logger.debug("Recorded SQL retry metric", database=database, reason=reason)

    def record_db_query(self, database: str, duration: float) -> None:
        """Record database query execution.

        Args:
            database: The database name
            duration: Query execution duration in seconds
        """
        self.db_query_duration.labels(database=database).observe(duration)
        logger.debug(
            "Recorded DB query metric",
            database=database,
            duration_ms=int(duration * 1000),
        )

    def record_openai_request(
        self,
        status: str,
        duration: float,
        prompt_tokens: int,
        completion_tokens: int,
    ) -> None:
        """Record OpenAI API request metrics.

        Args:
            status: Request status (e.g., "success", "error")
            duration: Request duration in seconds
            prompt_tokens: Number of prompt tokens used
            completion_tokens: Number of completion tokens used
        """
        self.openai_requests_total.labels(status=status).inc()
        self.openai_request_duration.observe(duration)
        self.openai_tokens_total.labels(type="prompt").inc(prompt_tokens)
        self.openai_tokens_total.labels(type="completion").inc(completion_tokens)
        logger.debug(
            "Recorded OpenAI request metric",
            status=status,
            duration_ms=int(duration * 1000),
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
        )

    def record_rate_limit_exceeded(self, limit_type: str) -> None:
        """Record rate limit exceeded event.

        Args:
            limit_type: Type of rate limit exceeded
                       (e.g., "requests_minute", "requests_hour", "tokens_minute")
        """
        self.rate_limit_exceeded_total.labels(limit_type=limit_type).inc()
        logger.debug("Recorded rate limit exceeded", limit_type=limit_type)

    def record_policy_check(self, check_type: str, result: str) -> None:
        """Record policy check result.

        Args:
            check_type: Type of policy check
                       (e.g., "table_access", "column_access", "query_cost")
            result: Check result ("allowed" or "denied")
        """
        self.policy_check_total.labels(check_type=check_type, result=result).inc()
        logger.debug(
            "Recorded policy check metric",
            check_type=check_type,
            result=result,
        )

    def update_pool_stats(self, database: str, size: int, available: int) -> None:
        """Update database connection pool statistics.

        Args:
            database: The database name
            size: Current pool size
            available: Number of available connections
        """
        self.db_pool_size.labels(database=database).set(size)
        self.db_pool_available.labels(database=database).set(available)
        logger.debug(
            "Updated pool stats",
            database=database,
            size=size,
            available=available,
        )

    def update_rate_limit_stats(
        self,
        requests_minute: int,
        requests_hour: int,
        tokens_minute: int,
    ) -> None:
        """Update rate limit current counters.

        Args:
            requests_minute: Current requests in the minute window
            requests_hour: Current requests in the hour window
            tokens_minute: Current tokens used in the minute window
        """
        self.rate_limit_current.labels(limit_type="requests_minute").set(requests_minute)
        self.rate_limit_current.labels(limit_type="requests_hour").set(requests_hour)
        self.rate_limit_current.labels(limit_type="tokens_minute").set(tokens_minute)
        logger.debug(
            "Updated rate limit stats",
            requests_minute=requests_minute,
            requests_hour=requests_hour,
            tokens_minute=tokens_minute,
        )

    def set_service_info(self, version: str, **kwargs: Any) -> None:
        """Set service information.

        Args:
            version: Service version
            **kwargs: Additional service information key-value pairs
        """
        info_dict = {"version": version, **kwargs}
        self.service_info.info(info_dict)
        logger.debug("Set service info", **info_dict)

    def generate_metrics(self) -> bytes:
        """Generate Prometheus metrics output.

        Returns:
            Prometheus exposition format metrics as bytes
        """
        return generate_latest(self.registry)

    def get_content_type(self) -> str:
        """Get the Prometheus content type header value.

        Returns:
            The content type string for Prometheus exposition format
        """
        return CONTENT_TYPE_LATEST

    # =================================================================
    # Context Managers for In-Flight Tracking
    # =================================================================

    def track_request(self, database: str) -> "_RequestTracker":
        """Create a context manager for tracking in-flight requests.

        Args:
            database: The database name

        Returns:
            A context manager that tracks the request lifecycle

        Usage:
            with collector.track_request("mydb") as tracker:
                # Request processing
                tracker.set_status("success")
        """
        return _RequestTracker(self, database)


class _RequestTracker:
    """Context manager for tracking in-flight requests."""

    def __init__(self, collector: MetricsCollector, database: str) -> None:
        self._collector = collector
        self._database = database
        self._status = "error"
        self._error_code: str | None = None
        self._start_time: float = 0.0

    def __enter__(self) -> "_RequestTracker":
        import time

        self._start_time = time.perf_counter()
        self._collector.requests_in_flight.labels(database=self._database).inc()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        import time

        duration = time.perf_counter() - self._start_time
        self._collector.requests_in_flight.labels(database=self._database).dec()
        self._collector.record_request(
            database=self._database,
            status=self._status,
            duration=duration,
            error_code=self._error_code,
        )

    def set_status(self, status: str, error_code: str | None = None) -> None:
        """Set the request status.

        Args:
            status: Request status (e.g., "success", "error")
            error_code: Optional error code
        """
        self._status = status
        self._error_code = error_code
