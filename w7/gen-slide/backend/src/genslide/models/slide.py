"""Slide domain model."""

from dataclasses import dataclass, field
from datetime import UTC, datetime

from .image import ImageRecord


def _utc_now() -> datetime:
    """Get current UTC datetime."""
    return datetime.now(UTC)


@dataclass
class Slide:
    """Slide domain model."""

    sid: str
    content: str
    created_at: datetime = field(default_factory=_utc_now)
    updated_at: datetime = field(default_factory=_utc_now)
    images: list[ImageRecord] = field(default_factory=list)

    def update_content(self, content: str) -> None:
        """Update the slide content."""
        self.content = content
        self.updated_at = datetime.now(UTC)

    def add_image(self, image: ImageRecord) -> None:
        """Add an image to the slide."""
        self.images.append(image)

    def get_image_by_hash(self, hash_value: str) -> ImageRecord | None:
        """Get an image by its hash."""
        for image in self.images:
            if image.hash == hash_value:
                return image
        return None
