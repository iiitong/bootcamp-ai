"""Natural language SQL query generation endpoints."""

from fastapi import APIRouter, HTTPException, status

from src.api.v1.dependencies import SettingsDep, StorageDep
from src.models.errors import ErrorCode, ErrorResponse
from src.models.query import NaturalLanguageQueryRequest, NaturalLanguageQueryResult
from src.services.llm import TextToSQLGenerator

router = APIRouter(prefix="/dbs", tags=["nl-queries"])


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
    storage: StorageDep,
    settings: SettingsDep,
) -> NaturalLanguageQueryResult:
    """Generate SQL from natural language description."""
    # Check API key
    if not settings.has_openai_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=ErrorResponse(
                detail="OpenAI API key not configured",
                code=ErrorCode.LLM_NOT_CONFIGURED,
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

    # Generate SQL with appropriate database type
    db_type = conn["db_type"]
    generator = TextToSQLGenerator(
        model=settings.openai_model,
        base_url=settings.openai_base_url,
        db_type=db_type,
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
