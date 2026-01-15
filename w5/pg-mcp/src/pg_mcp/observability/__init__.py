"""Observability module for pg-mcp.

This module provides comprehensive observability capabilities:
- Structured logging with slow query detection
- Distributed tracing support (optional, requires opentelemetry)
- Metrics collection and monitoring
"""

from pg_mcp.observability.logging import (
    SlowQueryLogger,
    add_trace_id,
    setup_logging,
)
from pg_mcp.observability.metrics import MetricsCollector
from pg_mcp.observability.tracing import (
    TracingManager,
    get_tracing_manager,
    init_tracing,
    shutdown_tracing,
)

__all__ = [
    # Logging
    "SlowQueryLogger",
    "add_trace_id",
    "setup_logging",
    # Metrics
    "MetricsCollector",
    # Tracing
    "TracingManager",
    "get_tracing_manager",
    "init_tracing",
    "shutdown_tracing",
]
