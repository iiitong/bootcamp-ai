"""Data models."""

from pg_mcp.models.errors import (
    DatabaseConnectionError,
    ErrorCode,
    ErrorResponse,
    OpenAIError,
    PgMcpError,
    QueryTimeoutError,
    RateLimitExceededError,
    SQLSyntaxError,
    UnknownDatabaseError,
    UnsafeSQLError,
)
from pg_mcp.models.query import (
    QueryRequest,
    QueryResponse,
    QueryResult,
    ReturnType,
    SQLGenerationResult,
    SQLValidationResult,
)
from pg_mcp.models.schema import (
    ColumnInfo,
    DatabaseSchema,
    EnumTypeInfo,
    IndexInfo,
    IndexType,
    TableInfo,
    ViewInfo,
)

__all__ = [
    # Errors
    "DatabaseConnectionError",
    "ErrorCode",
    "ErrorResponse",
    "OpenAIError",
    "PgMcpError",
    "QueryTimeoutError",
    "RateLimitExceededError",
    "SQLSyntaxError",
    "UnknownDatabaseError",
    "UnsafeSQLError",
    # Query
    "QueryRequest",
    "QueryResponse",
    "QueryResult",
    "ReturnType",
    "SQLGenerationResult",
    "SQLValidationResult",
    # Schema
    "ColumnInfo",
    "DatabaseSchema",
    "EnumTypeInfo",
    "IndexInfo",
    "IndexType",
    "TableInfo",
    "ViewInfo",
]
