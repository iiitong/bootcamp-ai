"""FastAPI application entry point for DB Query Tool."""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src import __version__
from src.api.v1 import router as api_v1_router
from src.config import get_settings
from src.exceptions import DBQueryException
from src.logging_config import configure_logging
from src.models.errors import ErrorResponse

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler for startup/shutdown events."""
    # Startup: configure logging (data directory is auto-created by Settings)
    configure_logging()
    logger.info("Starting DB Query Tool v%s", __version__)
    yield
    # Shutdown
    logger.info("Shutting down DB Query Tool")


app = FastAPI(
    title="DB Query Tool API",
    description="Database query tool with PostgreSQL support and natural language SQL generation",
    version=__version__,
    lifespan=lifespan,
)

# CORS configuration from environment
# Default: localhost dev ports. Set CORS_ALLOWED_ORIGINS for production.
settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(api_v1_router)


# Exception handlers
@app.exception_handler(DBQueryException)
async def db_query_exception_handler(
    request: Request,
    exc: DBQueryException,
) -> JSONResponse:
    """Handle all DBQueryException subclasses with proper error response."""
    logger.warning("DBQueryException: %s (code=%s)", exc.message, exc.error_code.value)
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            detail=exc.message,
            code=exc.error_code.value,
        ).model_dump(),
    )


@app.get("/", include_in_schema=False)
async def root() -> dict[str, str]:
    """Root endpoint - redirect info."""
    return {
        "message": "DB Query Tool API",
        "docs": "/docs",
        "version": __version__,
    }


@app.get("/health", tags=["health"])
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy"}
