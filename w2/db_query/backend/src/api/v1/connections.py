"""Database connection management endpoints."""

from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status

from src.api.v1.dependencies import SettingsDep, StorageDep
from src.models.database import (
    DatabaseCreateRequest,
    DatabaseInfo,
    DatabaseMetadata,
    TableInfo,
)
from src.models.errors import ErrorCode, ErrorResponse
from src.services.registry import DatabaseRegistry
from src.utils.db_utils import detect_db_type, mask_password

router = APIRouter(prefix="/dbs", tags=["connections"])


async def _extract_metadata(url: str, db_type: str) -> tuple[list[TableInfo], list[TableInfo]]:
    """Extract metadata using the registry-based extractor.

    Args:
        url: Database connection URL
        db_type: Database type ('postgresql' or 'mysql')

    Returns:
        Tuple of (tables, views) with their column information

    Raises:
        ConnectionError: If unable to connect to database
    """
    extractor = DatabaseRegistry.get_extractor(db_type)
    return await extractor.extract(url)


@router.get(
    "",
    response_model=list[DatabaseInfo],
    summary="List all database connections",
    description="Returns all saved database connections",
)
async def list_databases(storage: StorageDep) -> list[DatabaseInfo]:
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
    storage: StorageDep,
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

    # Detect database type from URL
    db_type = detect_db_type(request.url)

    # Test connection and extract metadata
    try:
        tables, views = await _extract_metadata(request.url, db_type)
    except ConnectionError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ErrorResponse(
                detail=str(e),
                code=ErrorCode.CONNECTION_FAILED,
            ).model_dump(),
        )

    # Save connection with db_type
    storage.upsert_connection(name, request.url, db_type)

    # Save metadata cache
    storage.save_metadata(name, tables, views)

    # Return metadata
    return DatabaseMetadata(
        name=name,
        url=mask_password(request.url),
        db_type=db_type,
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
    storage: StorageDep,
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

    db_type = conn["db_type"]

    # If refresh requested, re-extract metadata and return directly
    if refresh:
        try:
            tables, views = await _extract_metadata(conn["url"], db_type)
            storage.save_metadata(name, tables, views)
            return DatabaseMetadata(
                name=name,
                url=mask_password(conn["url"]),
                db_type=db_type,
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
            tables, views = await _extract_metadata(conn["url"], db_type)
            storage.save_metadata(name, tables, views)
            # Return directly constructed metadata (handles empty database case)
            return DatabaseMetadata(
                name=name,
                url=mask_password(conn["url"]),
                db_type=db_type,
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
async def delete_database(name: str, storage: StorageDep) -> None:
    """Delete a database connection."""
    if not storage.delete_connection(name):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ErrorResponse(
                detail=f"Database connection '{name}' not found",
                code=ErrorCode.CONNECTION_NOT_FOUND,
            ).model_dump(),
        )
