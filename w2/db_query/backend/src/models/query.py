"""Query-related Pydantic models."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from src.utils.db_utils import to_camel


class QueryRequest(BaseModel):
    """Request body for executing SQL query."""

    sql: str = Field(
        ...,
        description="SQL query to execute",
        min_length=1,
        max_length=10000,
        examples=["SELECT * FROM users WHERE status = 'active'"],
    )


class QueryResult(BaseModel):
    """Query execution result."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    columns: list[str] = Field(..., description="Column names")
    rows: list[dict[str, Any]] = Field(..., description="Data rows")
    row_count: int = Field(..., description="Number of rows returned")
    execution_time_ms: float = Field(..., description="Execution time in milliseconds")


class NaturalLanguageQueryRequest(BaseModel):
    """Request body for natural language query."""

    prompt: str = Field(
        ...,
        description="Natural language query description",
        min_length=1,
        max_length=1000,
        examples=["Show all active users with their email and registration date"],
    )


class NaturalLanguageQueryResult(BaseModel):
    """Result of natural language SQL generation."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    generated_sql: str = Field(..., description="Generated SQL query")
    result: QueryResult | None = Field(None, description="Execution result if auto-executed")
    error: str | None = Field(None, description="Error message if any")
