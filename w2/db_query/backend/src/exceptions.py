"""Structured exception types for DB Query Tool.

This module provides a hierarchy of exception types that map directly to
HTTP status codes and error codes. This enables cleaner error handling
in the API layer through exception handlers.

Usage:
    from src.exceptions import ConnectionException, QueryTimeoutException

    # In service layer
    if not connected:
        raise ConnectionException("Failed to connect to database")

    # In API layer - automatic handling via exception handlers
"""

from src.models.errors import ErrorCode


class DBQueryException(Exception):
    """Base exception for DB Query Tool.

    All custom exceptions inherit from this class, enabling a single
    exception handler to catch all application-specific errors.

    Attributes:
        error_code: ErrorCode enum value for API responses
        status_code: HTTP status code to return
        message: Human-readable error message
    """

    error_code: ErrorCode = ErrorCode.CONNECTION_FAILED
    status_code: int = 400

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class ConnectionException(DBQueryException):
    """Raised when database connection fails."""

    error_code = ErrorCode.CONNECTION_FAILED
    status_code = 400


class ConnectionNotFoundException(DBQueryException):
    """Raised when a database connection is not found."""

    error_code = ErrorCode.CONNECTION_NOT_FOUND
    status_code = 404


class InvalidURLException(DBQueryException):
    """Raised when database URL is invalid."""

    error_code = ErrorCode.INVALID_URL
    status_code = 400


class InvalidSQLException(DBQueryException):
    """Raised when SQL query is invalid or not allowed."""

    error_code = ErrorCode.INVALID_SQL
    status_code = 400


class NonSelectQueryException(DBQueryException):
    """Raised when a non-SELECT query is attempted."""

    error_code = ErrorCode.NON_SELECT_QUERY
    status_code = 400


class QueryTimeoutException(DBQueryException):
    """Raised when a query exceeds the timeout."""

    error_code = ErrorCode.QUERY_TIMEOUT
    status_code = 408


class LLMException(DBQueryException):
    """Raised when LLM processing fails."""

    error_code = ErrorCode.LLM_ERROR
    status_code = 500


class LLMNotConfiguredException(DBQueryException):
    """Raised when LLM is not configured."""

    error_code = ErrorCode.LLM_NOT_CONFIGURED
    status_code = 503
