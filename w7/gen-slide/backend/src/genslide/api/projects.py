"""Project API endpoints."""

from fastapi import APIRouter, HTTPException, status

from ..services.cost_service import get_cost_service
from ..services.project_service import get_project_service
from .schemas import (
    CostBreakdown,
    CostResponse,
    CreateProjectRequest,
    ErrorResponse,
    ProjectResponse,
    SlideImage,
    SlideResponse,
    StyleConfig,
    UpdateProjectRequest,
    UpdateProjectResponse,
)

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get(
    "/{slug}",
    response_model=ProjectResponse,
    responses={404: {"model": ErrorResponse}},
)
async def get_project(slug: str) -> ProjectResponse:
    """Get project details."""
    service = get_project_service()
    project = service.get_project(slug)

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "project_not_found", "message": "Project not found"},
        )

    response_data = service.get_project_response(project)

    # Convert to response model
    slides = [
        SlideResponse(
            sid=s["sid"],
            content=s["content"],
            images=[
                SlideImage(
                    hash=img["hash"],
                    url=img["url"],
                    created_at=img["created_at"],
                )
                for img in s["images"]
            ],
            current_hash=s["current_hash"],
            has_matching_image=s["has_matching_image"],
        )
        for s in response_data["slides"]
    ]

    style = None
    if response_data["style"]:
        style = StyleConfig(
            prompt=response_data["style"]["prompt"],
            image=response_data["style"]["image"],
        )

    return ProjectResponse(
        slug=response_data["slug"],
        title=response_data["title"],
        style=style,
        slides=slides,
        total_cost=response_data["total_cost"],
    )


@router.post(
    "/{slug}",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
    responses={409: {"model": ErrorResponse}},
)
async def create_project(slug: str, request: CreateProjectRequest) -> ProjectResponse:
    """Create a new project."""
    service = get_project_service()

    if service.project_exists(slug):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": "project_exists", "message": "Project already exists"},
        )

    project = service.create_project(slug, request.title)

    return ProjectResponse(
        slug=project.slug,
        title=project.title,
        style=None,
        slides=[],
        total_cost=0,
    )


@router.patch(
    "/{slug}",
    response_model=UpdateProjectResponse,
    responses={404: {"model": ErrorResponse}},
)
async def update_project(slug: str, request: UpdateProjectRequest) -> UpdateProjectResponse:
    """Update project information (title)."""
    service = get_project_service()

    project = service.update_project(slug, request.title)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "project_not_found", "message": "Project not found"},
        )

    return UpdateProjectResponse(slug=project.slug, title=project.title)


@router.get(
    "/{slug}/cost",
    response_model=CostResponse,
    responses={404: {"model": ErrorResponse}},
)
async def get_project_cost(slug: str) -> CostResponse:
    """Get project cost statistics."""
    service = get_cost_service()

    result = service.get_cost_breakdown(slug)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "project_not_found", "message": "Project not found"},
        )

    return CostResponse(
        total_cost=result["total_cost"],
        breakdown=CostBreakdown(
            style_generation=result["breakdown"]["style_generation"],
            slide_images=result["breakdown"]["slide_images"],
        ),
        image_count=result["image_count"],
    )
