"""Slide management service."""

from uuid import uuid4

from ..models import Slide
from ..storage import OutlineStore
from ..utils.hash import compute_content_hash


class SlideService:
    """Slide management business service."""

    def __init__(self) -> None:
        """Initialize slide service."""
        self.outline_store = OutlineStore()

    def create_slide(
        self, slug: str, content: str, after_sid: str | None = None
    ) -> Slide | None:
        """
        Create a new slide in a project.

        Args:
            slug: Project identifier.
            content: Slide content.
            after_sid: Optional slide ID to insert after.

        Returns:
            Created slide or None if project not found.
        """
        # Generate unique slide ID
        sid = f"slide-{uuid4().hex[:8]}"

        return self.outline_store.add_slide(slug, sid, content, after_sid)

    def update_slide(self, slug: str, sid: str, content: str) -> Slide | None:
        """
        Update a slide's content.

        Args:
            slug: Project identifier.
            sid: Slide ID.
            content: New content.

        Returns:
            Updated slide or None if not found.
        """
        return self.outline_store.update_slide(slug, sid, content)

    def delete_slide(self, slug: str, sid: str) -> bool:
        """
        Delete a slide from a project.

        Args:
            slug: Project identifier.
            sid: Slide ID.

        Returns:
            True if deleted, False otherwise.
        """
        return self.outline_store.delete_slide(slug, sid)

    def reorder_slides(self, slug: str, order: list[str]) -> bool:
        """
        Reorder slides in a project.

        Args:
            slug: Project identifier.
            order: List of slide IDs in new order.

        Returns:
            True if reordered, False otherwise.
        """
        return self.outline_store.reorder_slides(slug, order)

    def get_slide_response(self, slide: Slide) -> dict:
        """
        Convert a slide to API response format.

        Args:
            slide: Slide domain model.

        Returns:
            Dict suitable for API response.
        """
        current_hash = compute_content_hash(slide.content)
        has_matching = any(img.hash == current_hash for img in slide.images)

        images_response = [
            {
                "hash": img.hash,
                "url": f"/api/images/{slide.sid}/{img.filename}",
                "created_at": img.created_at.isoformat() + "Z",
            }
            for img in slide.images
        ]

        return {
            "sid": slide.sid,
            "content": slide.content,
            "images": images_response,
            "current_hash": current_hash,
            "has_matching_image": has_matching,
        }


# Global instance
_slide_service: SlideService | None = None


def get_slide_service() -> SlideService:
    """Get or create the slide service instance."""
    global _slide_service
    if _slide_service is None:
        _slide_service = SlideService()
    return _slide_service
