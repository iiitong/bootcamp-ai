"""SQL query execution endpoints."""

from fastapi import APIRouter, HTTPException, status

from src.api.v1.dependencies import SettingsDep, StorageDep
from src.models.errors import ErrorCode, ErrorResponse
from src.models.query import QueryRequest, QueryResult
from src.services.query import SQLProcessor
from src.services.registry import DatabaseRegistry

router = APIRouter(prefix="/dbs", tags=["queries"])


@router.post(
    "/{name}/query",
    response_model=QueryResult,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid SQL or non-SELECT query"},
        404: {"model": ErrorResponse, "description": "Connection not found"},
        408: {"model": ErrorResponse, "description": "Query timeout"},
    },
    summary="Execute SQL query",
    description="Execute a SELECT query. Non-SELECT statements are blocked. LIMIT 1000 is auto-added if missing.",
)
async def execute_query(
    name: str,
    request: QueryRequest,
    storage: StorageDep,
    settings: SettingsDep,
) -> QueryResult:
    """Execute a SQL query against a database."""
    # Get connection
    conn = storage.get_connection(name)
    if conn is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ErrorResponse(
                detail=f"Database connection '{name}' not found",
                code=ErrorCode.CONNECTION_NOT_FOUND,
            ).model_dump(),
        )

    db_type = conn["db_type"]
    dialect = DatabaseRegistry.get_dialect(db_type)

    # Process SQL (validate and add LIMIT) with appropriate dialect
    try:
        processed_sql = SQLProcessor.process(request.sql, settings.default_query_limit, dialect)
    except ValueError as e:
        error_msg = str(e)
        if "Only SELECT" in error_msg or "not permitted" in error_msg:
            code = ErrorCode.NON_SELECT_QUERY
        else:
            code = ErrorCode.INVALID_SQL
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ErrorResponse(detail=error_msg, code=code).model_dump(),
        )

    # Execute query using registry-based executor
    try:
        executor = DatabaseRegistry.get_executor(db_type)
        result = await executor.execute(
            conn["url"],
            processed_sql,
            settings.query_timeout_seconds,
        )
    except TimeoutError:
        raise HTTPException(
            status_code=status.HTTP_408_REQUEST_TIMEOUT,
            detail=ErrorResponse(
                detail="Query execution timed out",
                code=ErrorCode.QUERY_TIMEOUT,
            ).model_dump(),
        )
    except ConnectionError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ErrorResponse(
                detail=str(e),
                code=ErrorCode.CONNECTION_FAILED,
            ).model_dump(),
        )

    return result
