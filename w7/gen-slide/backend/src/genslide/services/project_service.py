"""Project management service."""

from ..models import Project
from ..storage import OutlineStore
from ..utils.hash import compute_content_hash


class ProjectService:
    """Project management business service."""

    def __init__(self) -> None:
        """Initialize project service."""
        self.outline_store = OutlineStore()

    def get_project(self, slug: str) -> Project | None:
        """
        Get a project by slug.

        Args:
            slug: Project identifier.

        Returns:
            Project or None if not found.
        """
        return self.outline_store.load_project(slug)

    def create_project(self, slug: str, title: str) -> Project:
        """
        Create a new project.

        Args:
            slug: Project identifier.
            title: Project title.

        Returns:
            Created project.
        """
        return self.outline_store.create_project(slug, title)

    def update_project(self, slug: str, title: str) -> Project | None:
        """
        Update project title.

        Args:
            slug: Project identifier.
            title: New title.

        Returns:
            Updated project or None if not found.
        """
        return self.outline_store.update_title(slug, title)

    def project_exists(self, slug: str) -> bool:
        """Check if a project exists."""
        return self.outline_store.exists(slug)

    def get_project_response(self, project: Project) -> dict:
        """
        Convert a project to API response format.

        Args:
            project: Project domain model.

        Returns:
            Dict suitable for API response.
        """
        slides_response = []
        for slide in project.slides:
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

            slides_response.append(
                {
                    "sid": slide.sid,
                    "content": slide.content,
                    "images": images_response,
                    "current_hash": current_hash,
                    "has_matching_image": has_matching,
                }
            )

        style_response = None
        if project.style:
            style_response = {
                "prompt": project.style.prompt,
                "image": f"/api/images/{project.slug}/{project.style.image}",
            }

        return {
            "slug": project.slug,
            "title": project.title,
            "style": style_response,
            "slides": slides_response,
            "total_cost": project.cost.total,
        }


# Global instance
_project_service: ProjectService | None = None


def get_project_service() -> ProjectService:
    """Get or create the project service instance."""
    global _project_service
    if _project_service is None:
        _project_service = ProjectService()
    return _project_service
