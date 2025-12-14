"""FastAPI application entry point for DB Query Tool."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src import __version__
from src.api.v1 import router as api_v1_router
from src.config import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler for startup/shutdown events."""
    # Startup: ensure data directory exists
    settings = get_settings()
    settings.ensure_data_dir()
    yield
    # Shutdown: cleanup if needed
    pass


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
