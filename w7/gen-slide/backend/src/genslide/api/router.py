"""API router registration."""

from fastapi import APIRouter

from . import images, projects, slides

router = APIRouter(prefix="/api")

# Include all routers
router.include_router(projects.router)
router.include_router(slides.router)
router.include_router(images.router)
