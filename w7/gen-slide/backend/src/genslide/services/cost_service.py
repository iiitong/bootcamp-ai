"""Cost calculation service."""

from ..storage import FileStorage, OutlineStore


class CostService:
    """Cost calculation business service."""

    def __init__(self) -> None:
        """Initialize cost service."""
        self.outline_store = OutlineStore()
        self.file_storage = FileStorage()

    def get_cost_breakdown(self, slug: str) -> dict | None:
        """
        Get cost breakdown for a project.

        Args:
            slug: Project identifier.

        Returns:
            Cost breakdown dict or None if project not found.
        """
        project = self.outline_store.load_project(slug)
        if not project:
            return None

        # Count all images
        image_count = 0
        for slide in project.slides:
            image_count += len(slide.images)

        return {
            "total_cost": project.cost.total,
            "breakdown": {
                "style_generation": project.cost.style_generation,
                "slide_images": project.cost.slide_images,
            },
            "image_count": image_count,
        }


# Global instance
_cost_service: CostService | None = None


def get_cost_service() -> CostService:
    """Get or create the cost service instance."""
    global _cost_service
    if _cost_service is None:
        _cost_service = CostService()
    return _cost_service
