"""Image API endpoints."""

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import Response

from ..services.image_service import get_image_service
from ..storage import FileStorage
from .schemas import ErrorResponse, TaskResponse

router = APIRouter(tags=["images"])


@router.get(
    "/images/{path:path}",
    responses={
        200: {"content": {"image/jpeg": {}}, "description": "Image file"},
        404: {"model": ErrorResponse},
    },
)
async def get_image(path: str) -> Response:
    """Get an image file."""
    storage = FileStorage()

    file_path = storage.resolve_image_path(path)
    if not file_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "image_not_found", "message": "Image not found"},
        )

    image_data = storage.read_image(file_path)
    if not image_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "image_not_found", "message": "Image not found"},
        )

    return Response(content=image_data, media_type="image/jpeg")


@router.get(
    "/tasks/{task_id}",
    response_model=TaskResponse,
    responses={404: {"model": ErrorResponse}},
)
async def get_task_status(task_id: str) -> TaskResponse:
    """Get task status."""
    image_service = get_image_service()

    task = image_service.get_task_status(task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "task_not_found", "message": "Task not found"},
        )

    return TaskResponse(
        task_id=task_id,
        status=task["status"],
        result=task.get("result"),
        error=task.get("error"),
    )


@router.get(
    "/tasks/style/{task_id}",
    response_model=TaskResponse,
    responses={404: {"model": ErrorResponse}},
)
async def get_style_task_status(task_id: str) -> TaskResponse:
    """Get style generation task status."""
    # Uses the same task storage as slide image generation
    return await get_task_status(task_id)
