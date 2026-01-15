"""Security module for pg-mcp server.

This module provides security-related functionality including:
- Audit logging for query tracking and compliance
- Access policy enforcement
- Schema/table/column access control
- EXPLAIN-based query plan validation
"""

from pg_mcp.security.access_policy import (
    ColumnAccessDeniedError,
    DatabaseAccessPolicy,
    PolicyCheckResult,
    PolicyValidationResult,
    PolicyViolation,
    SchemaAccessDeniedError,
    TableAccessDeniedError,
)
from pg_mcp.security.audit_logger import (
    AuditEvent,
    AuditEventType,
    AuditLogger,
    AuditStorage,
    ClientInfo,
    PolicyCheckInfo,
    QueryInfo,
    ResultInfo,
)
from pg_mcp.security.explain_validator import (
    ExplainResult,
    ExplainValidationResult,
    ExplainValidator,
    QueryTooExpensiveError,
    SeqScanDeniedError,
)

__all__ = [
    # Access policy
    "ColumnAccessDeniedError",
    "DatabaseAccessPolicy",
    "PolicyCheckResult",
    "PolicyValidationResult",
    "PolicyViolation",
    "SchemaAccessDeniedError",
    "TableAccessDeniedError",
    # Audit logging
    "AuditEvent",
    "AuditEventType",
    "AuditLogger",
    "AuditStorage",
    "ClientInfo",
    "PolicyCheckInfo",
    "QueryInfo",
    "ResultInfo",
    # EXPLAIN validation
    "ExplainResult",
    "ExplainValidationResult",
    "ExplainValidator",
    "QueryTooExpensiveError",
    "SeqScanDeniedError",
]
