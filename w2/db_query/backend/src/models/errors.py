"""Error response models."""

from enum import Enum

from pydantic import BaseModel, Field


class ErrorCode(str, Enum):
    """Error codes for API responses."""

    CONNECTION_FAILED = "CONNECTION_FAILED"
    CONNECTION_NOT_FOUND = "CONNECTION_NOT_FOUND"
    INVALID_URL = "INVALID_URL"
    INVALID_SQL = "INVALID_SQL"
    NON_SELECT_QUERY = "NON_SELECT_QUERY"
    QUERY_TIMEOUT = "QUERY_TIMEOUT"
    LLM_ERROR = "LLM_ERROR"


class ErrorResponse(BaseModel):
    """Unified error response format."""

    detail: str = Field(..., description="Error description")
    code: str = Field(..., description="Error code")
