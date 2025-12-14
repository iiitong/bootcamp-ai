"""API v1 router configuration."""

from fastapi import APIRouter

from src.api.v1.databases import router as databases_router

router = APIRouter(prefix="/api/v1")

# Include all routers
router.include_router(databases_router)
