"""YAML-based outline storage."""

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from ..models import ImageRecord, Project, Slide
from ..models.project import CostRecord, StyleConfig
from .file_storage import FileStorage


class OutlineStore:
    """Manages outline.yml files for projects."""

    def __init__(self) -> None:
        """Initialize outline store."""
        self.file_storage = FileStorage()

    def _get_outline_path(self, slug: str) -> Path:
        """Get the outline path for a project."""
        return self.file_storage.get_outline_path(slug)

    def exists(self, slug: str) -> bool:
        """Check if an outline exists for the project."""
        return self._get_outline_path(slug).exists()

    def load(self, slug: str) -> dict[str, Any]:
        """Load raw outline data from YAML."""
        outline_path = self._get_outline_path(slug)
        if not outline_path.exists():
            return {}
        with open(outline_path, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    def save(self, slug: str, data: dict[str, Any]) -> None:
        """Save raw outline data to YAML."""
        self.file_storage.ensure_project_dir(slug)
        outline_path = self._get_outline_path(slug)
        with open(outline_path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

    def load_project(self, slug: str) -> Project | None:
        """Load a project from its outline.yml."""
        data = self.load(slug)
        if not data:
            return None

        # Parse style
        style = None
        if "style" in data and data["style"]:
            style = StyleConfig(
                prompt=data["style"].get("prompt", ""),
                image=data["style"].get("image", ""),
            )

        # Parse cost
        cost = CostRecord()
        if "cost" in data and data["cost"]:
            cost = CostRecord(
                total=data["cost"].get("total", 0.0),
                style_generation=data["cost"].get("style_generation", 0.0),
                slide_images=data["cost"].get("slide_images", 0.0),
            )

        # Parse slides
        slides = []
        for slide_data in data.get("slides", []):
            # Parse images for this slide
            images = self._load_slide_images(slide_data["sid"])

            slide = Slide(
                sid=slide_data["sid"],
                content=slide_data.get("content", ""),
                created_at=self._parse_datetime(slide_data.get("created_at")),
                updated_at=self._parse_datetime(slide_data.get("updated_at")),
                images=images,
            )
            slides.append(slide)

        return Project(
            slug=slug,
            title=data.get("title", ""),
            style=style,
            cost=cost,
            slides=slides,
        )

    def _load_slide_images(self, sid: str) -> list[ImageRecord]:
        """Load images for a slide from the file system."""
        images = []
        image_paths = self.file_storage.list_slide_images(sid)
        for path in image_paths:
            # Extract hash from filename (e.g., "abc123.jpg" -> "abc123")
            hash_value = path.stem
            images.append(
                ImageRecord(
                    hash=hash_value,
                    filename=path.name,
                    created_at=datetime.fromtimestamp(path.stat().st_mtime),
                )
            )
        return sorted(images, key=lambda x: x.created_at, reverse=True)

    def save_project(self, project: Project) -> None:
        """Save a project to its outline.yml."""
        data: dict[str, Any] = {
            "title": project.title,
        }

        # Save style if exists
        if project.style:
            data["style"] = {
                "prompt": project.style.prompt,
                "image": project.style.image,
            }

        # Save cost
        data["cost"] = {
            "total": project.cost.total,
            "style_generation": project.cost.style_generation,
            "slide_images": project.cost.slide_images,
        }

        # Save slides (without images - they're stored in filesystem)
        data["slides"] = [
            {
                "sid": slide.sid,
                "content": slide.content,
                "created_at": slide.created_at.isoformat() + "Z",
                "updated_at": slide.updated_at.isoformat() + "Z",
            }
            for slide in project.slides
        ]

        self.save(project.slug, data)

    def create_project(self, slug: str, title: str) -> Project:
        """Create a new project."""
        project = Project(slug=slug, title=title)
        self.save_project(project)
        return project

    def update_title(self, slug: str, title: str) -> Project | None:
        """Update project title."""
        project = self.load_project(slug)
        if not project:
            return None
        project.title = title
        self.save_project(project)
        return project

    def add_cost(self, slug: str, amount: float, is_style: bool = False) -> None:
        """Add cost to a project."""
        project = self.load_project(slug)
        if not project:
            return

        project.cost.total += amount
        if is_style:
            project.cost.style_generation += amount
        else:
            project.cost.slide_images += amount

        self.save_project(project)

    def set_style(self, slug: str, prompt: str, image_filename: str) -> None:
        """Set the style for a project."""
        project = self.load_project(slug)
        if not project:
            return

        project.style = StyleConfig(prompt=prompt, image=image_filename)
        self.save_project(project)

    def add_slide(
        self, slug: str, sid: str, content: str, after_sid: str | None = None
    ) -> Slide | None:
        """Add a slide to a project."""
        project = self.load_project(slug)
        if not project:
            return None

        now = datetime.now(UTC)
        slide = Slide(sid=sid, content=content, created_at=now, updated_at=now)
        project.add_slide(slide, after_sid)
        self.save_project(project)
        return slide

    def update_slide(self, slug: str, sid: str, content: str) -> Slide | None:
        """Update a slide's content."""
        project = self.load_project(slug)
        if not project:
            return None

        slide = project.get_slide(sid)
        if not slide:
            return None

        slide.update_content(content)
        self.save_project(project)

        # Reload to get updated images
        project = self.load_project(slug)
        return project.get_slide(sid) if project else None

    def delete_slide(self, slug: str, sid: str) -> bool:
        """Delete a slide from a project."""
        project = self.load_project(slug)
        if not project:
            return False

        if project.remove_slide(sid):
            self.save_project(project)
            return True
        return False

    def reorder_slides(self, slug: str, order: list[str]) -> bool:
        """Reorder slides in a project."""
        project = self.load_project(slug)
        if not project:
            return False

        if project.reorder_slides(order):
            self.save_project(project)
            return True
        return False

    def _parse_datetime(self, value: str | datetime | None) -> datetime:
        """Parse a datetime value from various formats."""
        if value is None:
            return datetime.now(UTC)
        if isinstance(value, datetime):
            return value
        # Handle ISO format with Z suffix
        if value.endswith("Z"):
            value = value[:-1]
        return datetime.fromisoformat(value)
