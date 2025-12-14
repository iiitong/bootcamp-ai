"""Pydantic models for request/response DTOs."""

from src.models.database import (
    ColumnInfo,
    DatabaseCreateRequest,
    DatabaseInfo,
    DatabaseMetadata,
    TableInfo,
)
from src.models.errors import ErrorCode, ErrorResponse
from src.models.query import (
    NaturalLanguageQueryRequest,
    NaturalLanguageQueryResult,
    QueryRequest,
    QueryResult,
)

__all__ = [
    # Database models
    "ColumnInfo",
    "DatabaseCreateRequest",
    "DatabaseInfo",
    "DatabaseMetadata",
    "TableInfo",
    # Query models
    "NaturalLanguageQueryRequest",
    "NaturalLanguageQueryResult",
    "QueryRequest",
    "QueryResult",
    # Error models
    "ErrorCode",
    "ErrorResponse",
]
