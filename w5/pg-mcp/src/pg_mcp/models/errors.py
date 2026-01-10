from enum import Enum

from pydantic import BaseModel


class ErrorCode(str, Enum):
    """错误码"""
    UNKNOWN_DATABASE = "UNKNOWN_DATABASE"
    AMBIGUOUS_QUERY = "AMBIGUOUS_QUERY"
    UNSAFE_SQL = "UNSAFE_SQL"
    SYNTAX_ERROR = "SYNTAX_ERROR"
    EXECUTION_TIMEOUT = "EXECUTION_TIMEOUT"
    CONNECTION_ERROR = "CONNECTION_ERROR"
    OPENAI_ERROR = "OPENAI_ERROR"
    RESULT_TOO_LARGE = "RESULT_TOO_LARGE"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    INTERNAL_ERROR = "INTERNAL_ERROR"


class ErrorResponse(BaseModel):
    """错误响应"""
    success: bool = False
    error_code: ErrorCode
    error_message: str
    details: dict | None = None


class PgMcpError(Exception):
    """基础异常类"""
    def __init__(self, code: ErrorCode, message: str, details: dict | None = None):
        self.code = code
        self.message = message
        self.details = details
        super().__init__(message)

    def to_response(self) -> ErrorResponse:
        return ErrorResponse(
            error_code=self.code,
            error_message=self.message,
            details=self.details
        )


# 派生异常类
class UnknownDatabaseError(PgMcpError):
    def __init__(self, database: str, available: list[str]):
        super().__init__(
            ErrorCode.UNKNOWN_DATABASE,
            f"Database '{database}' not found. Available: {', '.join(available)}",
            {"available_databases": available}
        )


class UnsafeSQLError(PgMcpError):
    def __init__(self, reason: str):
        super().__init__(
            ErrorCode.UNSAFE_SQL,
            f"Generated SQL is not safe for execution: {reason}"
        )


class SQLSyntaxError(PgMcpError):
    def __init__(self, sql: str, error: str):
        super().__init__(
            ErrorCode.SYNTAX_ERROR,
            f"SQL syntax error: {error}",
            {"sql": sql}
        )


class QueryTimeoutError(PgMcpError):
    def __init__(self, timeout: float):
        super().__init__(
            ErrorCode.EXECUTION_TIMEOUT,
            f"Query execution timed out after {timeout} seconds",
            {"timeout_seconds": timeout}
        )


class DatabaseConnectionError(PgMcpError):
    def __init__(self, database: str, error: str):
        super().__init__(
            ErrorCode.CONNECTION_ERROR,
            f"Failed to connect to database '{database}': {error}",
            {"database": database}
        )


class OpenAIError(PgMcpError):
    def __init__(self, error: str):
        super().__init__(
            ErrorCode.OPENAI_ERROR,
            f"OpenAI API error: {error}"
        )


class RateLimitExceededError(PgMcpError):
    def __init__(self, limit_type: str, limit: int, window: str):
        super().__init__(
            ErrorCode.RATE_LIMIT_EXCEEDED,
            f"Rate limit exceeded: {limit} {limit_type} per {window}",
            {"limit_type": limit_type, "limit": limit, "window": window}
        )
