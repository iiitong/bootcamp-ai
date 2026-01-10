"""Unit tests for data models."""

import pytest

from pg_mcp.models.errors import (
    ErrorCode,
    ErrorResponse,
    PgMcpError,
    QueryTimeoutError,
    RateLimitExceededError,
    UnknownDatabaseError,
    UnsafeSQLError,
)
from pg_mcp.models.query import (
    QueryRequest,
    QueryResponse,
    QueryResult,
    ReturnType,
    SQLValidationResult,
)
from pg_mcp.models.schema import (
    ColumnInfo,
    DatabaseSchema,
    TableInfo,
)


class TestErrorModels:
    """Tests for error models."""

    def test_error_response(self) -> None:
        """Test ErrorResponse creation."""
        response = ErrorResponse(
            error_code=ErrorCode.UNSAFE_SQL,
            error_message="SQL is not safe",
        )
        assert response.success is False
        assert response.error_code == ErrorCode.UNSAFE_SQL

    def test_pg_mcp_error_to_response(self) -> None:
        """Test converting exception to response."""
        error = PgMcpError(
            ErrorCode.INTERNAL_ERROR,
            "Something went wrong",
            {"detail": "more info"},
        )
        response = error.to_response()
        assert response.error_code == ErrorCode.INTERNAL_ERROR
        assert response.error_message == "Something went wrong"
        assert response.details == {"detail": "more info"}

    def test_unknown_database_error(self) -> None:
        """Test UnknownDatabaseError."""
        error = UnknownDatabaseError("mydb", ["db1", "db2"])
        assert "mydb" in error.message
        assert error.details["available_databases"] == ["db1", "db2"]

    def test_unsafe_sql_error(self) -> None:
        """Test UnsafeSQLError."""
        error = UnsafeSQLError("Contains DELETE statement")
        assert "DELETE" in error.message

    def test_query_timeout_error(self) -> None:
        """Test QueryTimeoutError."""
        error = QueryTimeoutError(30.0)
        assert "30" in error.message
        assert error.details["timeout_seconds"] == 30.0

    def test_rate_limit_error(self) -> None:
        """Test RateLimitExceededError."""
        error = RateLimitExceededError("requests", 60, "minute")
        assert "60" in error.message
        assert "minute" in error.message


class TestQueryModels:
    """Tests for query models."""

    def test_query_request_defaults(self) -> None:
        """Test QueryRequest default values."""
        request = QueryRequest(question="Show all users")
        assert request.return_type == ReturnType.RESULT
        assert request.database is None
        assert request.limit is None

    def test_query_request_validation(self) -> None:
        """Test QueryRequest validation."""
        with pytest.raises(ValueError):
            QueryRequest(question="")  # Too short

    def test_query_result(self) -> None:
        """Test QueryResult."""
        result = QueryResult(
            columns=["id", "name"],
            rows=[[1, "Alice"], [2, "Bob"]],
            row_count=2,
        )
        assert len(result.rows) == 2
        assert result.truncated is False

    def test_query_response(self) -> None:
        """Test QueryResponse."""
        response = QueryResponse(
            sql="SELECT * FROM users",
            result=QueryResult(
                columns=["id"],
                rows=[[1]],
                row_count=1,
            ),
        )
        assert response.success is True
        assert response.sql is not None

    def test_sql_validation_result(self) -> None:
        """Test SQLValidationResult."""
        result = SQLValidationResult(
            is_valid=True,
            is_safe=False,
            error_message="Contains INSERT",
        )
        assert result.is_valid
        assert not result.is_safe


class TestSchemaModels:
    """Tests for schema models."""

    def test_column_info(self) -> None:
        """Test ColumnInfo."""
        col = ColumnInfo(
            name="id",
            data_type="integer",
            is_primary_key=True,
            is_nullable=False,
        )
        assert col.name == "id"
        assert col.is_primary_key

    def test_table_info_full_name(self) -> None:
        """Test TableInfo full_name property."""
        table = TableInfo(
            name="users",
            schema_name="public",
        )
        assert table.full_name == "public.users"

    def test_database_schema_to_prompt(self, sample_schema: DatabaseSchema) -> None:
        """Test schema to prompt text conversion."""
        prompt = sample_schema.to_prompt_text()
        assert "users" in prompt
        assert "orders" in prompt
        assert "id" in prompt
        assert "PRIMARY KEY" in prompt
        assert "FK -> users.id" in prompt

    def test_database_schema_get_table(self, sample_schema: DatabaseSchema) -> None:
        """Test getting table by name."""
        table = sample_schema.get_table("users")
        assert table is not None
        assert table.name == "users"

        missing = sample_schema.get_table("nonexistent")
        assert missing is None
