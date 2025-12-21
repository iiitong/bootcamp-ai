"""API v1 router configuration."""

from fastapi import APIRouter

from src.api.v1.connections import router as connections_router
from src.api.v1.nl_queries import router as nl_queries_router
from src.api.v1.queries import router as queries_router

router = APIRouter(prefix="/api/v1")

# Include all routers - order matters for route matching
router.include_router(connections_router)
router.include_router(queries_router)
router.include_router(nl_queries_router)
