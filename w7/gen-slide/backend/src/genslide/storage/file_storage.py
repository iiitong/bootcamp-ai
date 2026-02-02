"""File system operations for image storage."""

from pathlib import Path

from ..config import settings


class FileStorage:
    """File storage operations for images."""

    def __init__(self) -> None:
        """Initialize file storage."""
        self.images_dir = settings.images_path
        self.slides_dir = settings.slides_path

    def ensure_directories(self) -> None:
        """Ensure all required directories exist."""
        self.images_dir.mkdir(parents=True, exist_ok=True)
        self.slides_dir.mkdir(parents=True, exist_ok=True)

    def get_project_dir(self, slug: str) -> Path:
        """Get the project directory path."""
        return self.slides_dir / slug

    def get_outline_path(self, slug: str) -> Path:
        """Get the outline.yml path for a project."""
        return self.get_project_dir(slug) / "outline.yml"

    def get_image_dir(self, sid: str) -> Path:
        """Get the image directory for a slide."""
        return self.images_dir / sid

    def get_image_path(self, sid: str, content_hash: str) -> Path:
        """Get the image file path for a slide and hash."""
        return self.get_image_dir(sid) / f"{content_hash}.jpg"

    def get_style_image_dir(self, slug: str) -> Path:
        """Get the style image directory for a project."""
        return self.images_dir / slug

    def get_style_image_path(self, slug: str) -> Path:
        """Get the style image path for a project."""
        return self.get_style_image_dir(slug) / "style.jpg"

    def get_style_candidate_path(self, slug: str, candidate_id: str) -> Path:
        """Get the style candidate image path."""
        return self.get_style_image_dir(slug) / f"style-candidate-{candidate_id}.jpg"

    def project_exists(self, slug: str) -> bool:
        """Check if a project exists."""
        return self.get_outline_path(slug).exists()

    def ensure_project_dir(self, slug: str) -> Path:
        """Ensure project directory exists and return its path."""
        project_dir = self.get_project_dir(slug)
        project_dir.mkdir(parents=True, exist_ok=True)
        return project_dir

    def ensure_image_dir(self, sid: str) -> Path:
        """Ensure image directory exists and return its path."""
        image_dir = self.get_image_dir(sid)
        image_dir.mkdir(parents=True, exist_ok=True)
        return image_dir

    def ensure_style_image_dir(self, slug: str) -> Path:
        """Ensure style image directory exists and return its path."""
        style_dir = self.get_style_image_dir(slug)
        style_dir.mkdir(parents=True, exist_ok=True)
        return style_dir

    def list_slide_images(self, sid: str) -> list[Path]:
        """List all image files for a slide."""
        image_dir = self.get_image_dir(sid)
        if not image_dir.exists():
            return []
        return list(image_dir.glob("*.jpg"))

    def image_exists(self, sid: str, content_hash: str) -> bool:
        """Check if an image exists for the given slide and hash."""
        return self.get_image_path(sid, content_hash).exists()

    def read_image(self, path: Path) -> bytes | None:
        """Read image bytes from a path."""
        if not path.exists():
            return None
        return path.read_bytes()

    def resolve_image_path(self, relative_path: str) -> Path | None:
        """
        Resolve a relative image path to an absolute path.

        Args:
            relative_path: Path like 'slide-001/abc123.jpg' or 'hello-world/style.jpg'

        Returns:
            Absolute path if valid, None otherwise.
        """
        # Prevent path traversal
        if ".." in relative_path:
            return None

        full_path = self.images_dir / relative_path
        if not full_path.exists():
            return None

        # Ensure the path is within images_dir
        try:
            full_path.resolve().relative_to(self.images_dir.resolve())
        except ValueError:
            return None

        return full_path
