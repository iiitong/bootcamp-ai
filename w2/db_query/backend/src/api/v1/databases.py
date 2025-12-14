"""Database management and query API endpoints."""

from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.config import Settings, get_settings
from src.models.database import (
    DatabaseCreateRequest,
    DatabaseInfo,
    DatabaseMetadata,
)
from src.models.errors import ErrorCode, ErrorResponse
from src.models.query import (
    NaturalLanguageQueryRequest,
    NaturalLanguageQueryResult,
    QueryRequest,
    QueryResult,
)
from src.services.llm import TextToSQLGenerator
from src.services.metadata import MetadataExtractor
from src.services.query import QueryExecutor, SQLProcessor
from src.storage.sqlite import SQLiteStorage

router = APIRouter(prefix="/dbs", tags=["databases"])


def get_storage(settings: Annotated[Settings, Depends(get_settings)]) -> SQLiteStorage:
    """Get SQLite storage instance."""
    settings.ensure_data_dir()
    return SQLiteStorage(settings.db_path)


# Database connection endpoints


@router.get(
    "",
    response_model=list[DatabaseInfo],
    summary="List all database connections",
    description="Returns all saved database connections",
)
async def list_databases(
    storage: Annotated[SQLiteStorage, Depends(get_storage)],
) -> list[DatabaseInfo]:
    """Get all database connections."""
    return storage.list_connections()


@router.put(
    "/{name}",
    response_model=DatabaseMetadata,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid URL or connection failed"},
    },
    summary="Add or update database connection",
    description="Add a new database connection or update existing. Extracts metadata on success.",
)
async def upsert_database(
    name: str,
    request: DatabaseCreateRequest,
    storage: Annotated[SQLiteStorage, Depends(get_storage)],
) -> DatabaseMetadata:
    """Add or update a database connection."""
    # Validate name format
    if not name or not name[0].isalpha():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ErrorResponse(
                detail="Name must start with a letter",
                code=ErrorCode.INVALID_URL,
            ).model_dump(),
        )

    # Test connection and extract metadata
    try:
        tables, views = await MetadataExtractor.extract(request.url)
    except ConnectionError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ErrorResponse(
                detail=str(e),
                code=ErrorCode.CONNECTION_FAILED,
            ).model_dump(),
        )

    # Save connection
    storage.upsert_connection(name, request.url)

    # Save metadata cache
    storage.save_metadata(name, tables, views)

    # Return metadata
    return DatabaseMetadata(
        name=name,
        url=storage._mask_password(request.url),
        tables=tables,
        views=views,
        cached_at=datetime.now(timezone.utc),
    )


@router.get(
    "/{name}",
    response_model=DatabaseMetadata,
    responses={
        404: {"model": ErrorResponse, "description": "Connection not found"},
    },
    summary="Get database metadata",
    description="Returns complete metadata for a database including all tables and views",
)
async def get_database_metadata(
    name: str,
    storage: Annotated[SQLiteStorage, Depends(get_storage)],
    refresh: Annotated[bool, Query(description="Force refresh cached metadata")] = False,
) -> DatabaseMetadata:
    """Get metadata for a database connection."""
    # Check if connection exists
    conn = storage.get_connection(name)
    if conn is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ErrorResponse(
                detail=f"Database connection '{name}' not found",
                code=ErrorCode.CONNECTION_NOT_FOUND,
            ).model_dump(),
        )

    # If refresh requested, re-extract metadata and return directly
    if refresh:
        try:
            tables, views = await MetadataExtractor.extract(conn["url"])
            storage.save_metadata(name, tables, views)
            return DatabaseMetadata(
                name=name,
                url=storage._mask_password(conn["url"]),
                tables=tables,
                views=views,
                cached_at=datetime.now(timezone.utc),
            )
        except ConnectionError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ErrorResponse(
                    detail=str(e),
                    code=ErrorCode.CONNECTION_FAILED,
                ).model_dump(),
            )

    # Get cached metadata
    metadata = storage.get_metadata(name)
    if metadata is None:
        # No cached metadata, extract now
        try:
            tables, views = await MetadataExtractor.extract(conn["url"])
            storage.save_metadata(name, tables, views)
            # Return directly constructed metadata (handles empty database case)
            return DatabaseMetadata(
                name=name,
                url=storage._mask_password(conn["url"]),
                tables=tables,
                views=views,
                cached_at=datetime.now(timezone.utc),
            )
        except ConnectionError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ErrorResponse(
                    detail=str(e),
                    code=ErrorCode.CONNECTION_FAILED,
                ).model_dump(),
            )

    return metadata


@router.delete(
    "/{name}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        404: {"model": ErrorResponse, "description": "Connection not found"},
    },
    summary="Delete database connection",
    description="Delete a database connection and its cached metadata",
)
async def delete_database(
    name: str,
    storage: Annotated[SQLiteStorage, Depends(get_storage)],
) -> None:
    """Delete a database connection."""
    if not storage.delete_connection(name):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ErrorResponse(
                detail=f"Database connection '{name}' not found",
                code=ErrorCode.CONNECTION_NOT_FOUND,
            ).model_dump(),
        )


# Query execution endpoints


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
    storage: Annotated[SQLiteStorage, Depends(get_storage)],
    settings: Annotated[Settings, Depends(get_settings)],
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

    # Process SQL (validate and add LIMIT)
    try:
        processed_sql = SQLProcessor.process(request.sql, settings.default_query_limit)
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

    # Execute query
    try:
        result = await QueryExecutor.execute(
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


# Natural language query endpoint


@router.post(
    "/{name}/query/natural",
    response_model=NaturalLanguageQueryResult,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid request"},
        404: {"model": ErrorResponse, "description": "Connection not found"},
        500: {"model": ErrorResponse, "description": "LLM service error"},
    },
    summary="Generate SQL from natural language",
    description="Use LLM to generate SQL from natural language description. Returns SQL for user review.",
)
async def generate_natural_language_query(
    name: str,
    request: NaturalLanguageQueryRequest,
    storage: Annotated[SQLiteStorage, Depends(get_storage)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> NaturalLanguageQueryResult:
    """Generate SQL from natural language description."""
    # Check API key
    if not settings.has_openai_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                detail="OpenAI API key not configured",
                code=ErrorCode.LLM_ERROR,
            ).model_dump(),
        )

    # Get connection and metadata
    conn = storage.get_connection(name)
    if conn is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ErrorResponse(
                detail=f"Database connection '{name}' not found",
                code=ErrorCode.CONNECTION_NOT_FOUND,
            ).model_dump(),
        )

    metadata = storage.get_metadata(name)
    if metadata is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ErrorResponse(
                detail="No metadata cached for this database. Please refresh metadata first.",
                code=ErrorCode.CONNECTION_FAILED,
            ).model_dump(),
        )

    # Generate SQL
    generator = TextToSQLGenerator(
        model=settings.openai_model,
        base_url=settings.openai_base_url,
    )
    generator.set_schema_context(metadata.tables, metadata.views)

    try:
        generated_sql = generator.generate(request.prompt)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                detail=str(e),
                code=ErrorCode.LLM_ERROR,
            ).model_dump(),
        )

    return NaturalLanguageQueryResult(
        generated_sql=generated_sql,
        result=None,
        error=None,
    )
