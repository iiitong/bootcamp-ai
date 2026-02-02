"""Slide API endpoints."""

from fastapi import APIRouter, HTTPException, status

from ..services.image_service import get_image_service
from ..services.project_service import get_project_service
from ..services.slide_service import get_slide_service
from .schemas import (
    CreateSlideRequest,
    ErrorResponse,
    GenerateImageRequest,
    GenerateStyleRequest,
    ReorderSlidesRequest,
    ReorderSlidesResponse,
    SelectStyleRequest,
    SelectStyleResponse,
    SlideImage,
    SlideResponse,
    StyleConfig,
    TaskResponse,
    UpdateSlideRequest,
)

router = APIRouter(prefix="/projects/{slug}", tags=["slides"])


@router.get(
    "/slides/{sid}",
    response_model=SlideResponse,
    responses={404: {"model": ErrorResponse}},
)
async def get_slide(slug: str, sid: str) -> SlideResponse:
    """Get a single slide by ID."""
    project_service = get_project_service()
    slide_service = get_slide_service()

    project = project_service.get_project(slug)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "project_not_found", "message": "Project not found"},
        )

    slide = project.get_slide(sid)
    if not slide:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "slide_not_found", "message": "Slide not found"},
        )

    response_data = slide_service.get_slide_response(slide)

    return SlideResponse(
        sid=response_data["sid"],
        content=response_data["content"],
        images=[
            SlideImage(
                hash=img["hash"],
                url=img["url"],
                created_at=img["created_at"],
            )
            for img in response_data["images"]
        ],
        current_hash=response_data["current_hash"],
        has_matching_image=response_data["has_matching_image"],
    )


@router.post(
    "/slides",
    response_model=SlideResponse,
    status_code=status.HTTP_201_CREATED,
    responses={404: {"model": ErrorResponse}},
)
async def create_slide(slug: str, request: CreateSlideRequest) -> SlideResponse:
    """Create a new slide."""
    project_service = get_project_service()
    slide_service = get_slide_service()

    if not project_service.project_exists(slug):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "project_not_found", "message": "Project not found"},
        )

    slide = slide_service.create_slide(slug, request.content, request.after_sid)
    if not slide:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "create_failed", "message": "Failed to create slide"},
        )

    response_data = slide_service.get_slide_response(slide)

    return SlideResponse(
        sid=response_data["sid"],
        content=response_data["content"],
        images=[
            SlideImage(
                hash=img["hash"],
                url=img["url"],
                created_at=img["created_at"],
            )
            for img in response_data["images"]
        ],
        current_hash=response_data["current_hash"],
        has_matching_image=response_data["has_matching_image"],
    )


@router.patch(
    "/slides/{sid}",
    response_model=SlideResponse,
    responses={404: {"model": ErrorResponse}},
)
async def update_slide(slug: str, sid: str, request: UpdateSlideRequest) -> SlideResponse:
    """Update slide content."""
    project_service = get_project_service()
    slide_service = get_slide_service()

    if not project_service.project_exists(slug):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "project_not_found", "message": "Project not found"},
        )

    slide = slide_service.update_slide(slug, sid, request.content)
    if not slide:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "slide_not_found", "message": "Slide not found"},
        )

    response_data = slide_service.get_slide_response(slide)

    return SlideResponse(
        sid=response_data["sid"],
        content=response_data["content"],
        images=[
            SlideImage(
                hash=img["hash"],
                url=img["url"],
                created_at=img["created_at"],
            )
            for img in response_data["images"]
        ],
        current_hash=response_data["current_hash"],
        has_matching_image=response_data["has_matching_image"],
    )


@router.delete(
    "/slides/{sid}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={404: {"model": ErrorResponse}},
)
async def delete_slide(slug: str, sid: str) -> None:
    """Delete a slide."""
    project_service = get_project_service()
    slide_service = get_slide_service()

    if not project_service.project_exists(slug):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "project_not_found", "message": "Project not found"},
        )

    if not slide_service.delete_slide(slug, sid):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "slide_not_found", "message": "Slide not found"},
        )


@router.put(
    "/slides/order",
    response_model=ReorderSlidesResponse,
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
async def reorder_slides(slug: str, request: ReorderSlidesRequest) -> ReorderSlidesResponse:
    """Reorder slides."""
    project_service = get_project_service()
    slide_service = get_slide_service()

    if not project_service.project_exists(slug):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "project_not_found", "message": "Project not found"},
        )

    if not slide_service.reorder_slides(slug, request.order):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "invalid_order", "message": "Invalid slide order"},
        )

    return ReorderSlidesResponse(order=request.order)


@router.post(
    "/slides/{sid}/generate",
    response_model=TaskResponse,
    status_code=status.HTTP_202_ACCEPTED,
    responses={404: {"model": ErrorResponse}},
)
async def generate_slide_image(
    slug: str, sid: str, request: GenerateImageRequest | None = None
) -> TaskResponse:
    """Generate image for a slide."""
    project_service = get_project_service()
    image_service = get_image_service()

    project = project_service.get_project(slug)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "project_not_found", "message": "Project not found"},
        )

    slide = project.get_slide(sid)
    if not slide:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "slide_not_found", "message": "Slide not found"},
        )

    # Use provided content or slide's current content
    content = request.content if request and request.content else slide.content

    task_id = await image_service.generate_slide_image(slug, sid, content)

    return TaskResponse(task_id=task_id, status="pending")


@router.post(
    "/style/generate",
    response_model=TaskResponse,
    status_code=status.HTTP_202_ACCEPTED,
    responses={404: {"model": ErrorResponse}},
)
async def generate_style(slug: str, request: GenerateStyleRequest) -> TaskResponse:
    """Generate style candidate images."""
    project_service = get_project_service()
    image_service = get_image_service()

    if not project_service.project_exists(slug):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "project_not_found", "message": "Project not found"},
        )

    task_id = await image_service.generate_style_candidates(slug, request.prompt)

    return TaskResponse(task_id=task_id, status="pending")


@router.post(
    "/style/select",
    response_model=SelectStyleResponse,
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
async def select_style(slug: str, request: SelectStyleRequest) -> SelectStyleResponse:
    """Select a style candidate."""
    project_service = get_project_service()
    image_service = get_image_service()

    if not project_service.project_exists(slug):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "project_not_found", "message": "Project not found"},
        )

    result = image_service.select_style(slug, request.candidate_id, request.prompt)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "invalid_candidate", "message": "Style candidate not found"},
        )

    return SelectStyleResponse(
        style=StyleConfig(
            prompt=result["prompt"],
            image=result["image"],
        )
    )
