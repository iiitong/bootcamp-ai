"""Image generation service."""

import asyncio
import shutil
from uuid import uuid4

from PIL import Image

from ..config import settings
from ..storage import FileStorage, OutlineStore
from ..utils.hash import compute_content_hash
from .gemini_client import GeminiImageClient


class ImageService:
    """Image generation business service."""

    def __init__(self) -> None:
        """Initialize image service."""
        self.gemini = GeminiImageClient(
            api_key=settings.openrouter_api_key,
            model=settings.image_model,
            base_url=settings.openrouter_base_url,
        )
        self.file_storage = FileStorage()
        self.outline_store = OutlineStore()

        # Task state storage (use Redis in production)
        self._tasks: dict[str, dict] = {}

    async def generate_slide_image(
        self,
        slug: str,
        sid: str,
        content: str,
    ) -> str:
        """
        Create a slide image generation task.

        Args:
            slug: Project slug.
            sid: Slide ID.
            content: Content to generate image for.

        Returns:
            Task ID.
        """
        task_id = str(uuid4())
        self._tasks[task_id] = {"status": "pending", "result": None, "error": None}

        # Start background task
        asyncio.create_task(self._do_generate(task_id, slug, sid, content))

        return task_id

    async def _do_generate(
        self,
        task_id: str,
        slug: str,
        sid: str,
        content: str,
    ) -> None:
        """Execute the actual image generation."""
        try:
            self._tasks[task_id]["status"] = "processing"

            # Compute content hash
            content_hash = compute_content_hash(content)

            # Get output path
            self.file_storage.ensure_image_dir(sid)
            output_path = self.file_storage.get_image_path(sid, content_hash)

            # Load style image if exists
            style_image = None
            outline = self.outline_store.load(slug)
            if outline.get("style", {}).get("image"):
                style_path = self.file_storage.get_style_image_path(slug)
                if style_path.exists():
                    style_image = Image.open(style_path)

            # Generate image
            await self.gemini.generate_image(
                prompt=content,
                output_path=output_path,
                aspect_ratio=settings.image_aspect_ratio,
                style_image=style_image,
            )

            # Update task status
            self._tasks[task_id] = {
                "status": "completed",
                "result": {
                    "hash": content_hash,
                    "url": f"/api/images/{sid}/{content_hash}.jpg",
                    "cost": settings.slide_image_cost,
                },
                "error": None,
            }

            # Update cost
            self.outline_store.add_cost(slug, settings.slide_image_cost)

        except Exception as e:
            self._tasks[task_id] = {
                "status": "failed",
                "result": None,
                "error": str(e),
            }

    async def generate_style_candidates(
        self,
        slug: str,
        prompt: str,
    ) -> str:
        """
        Create a style candidate generation task.

        Args:
            slug: Project slug.
            prompt: Style description.

        Returns:
            Task ID.
        """
        task_id = str(uuid4())
        self._tasks[task_id] = {"status": "pending", "result": None, "error": None}

        # Start background task
        asyncio.create_task(self._do_generate_style(task_id, slug, prompt))

        return task_id

    async def _do_generate_style(
        self,
        task_id: str,
        slug: str,
        prompt: str,
    ) -> None:
        """Execute style candidate generation."""
        try:
            self._tasks[task_id]["status"] = "processing"

            # Ensure output directory
            output_dir = self.file_storage.ensure_style_image_dir(slug)

            # Generate candidates
            paths = await self.gemini.generate_style_candidates(
                prompt=prompt,
                output_dir=output_dir,
                count=2,
            )

            # Build result
            candidates = []
            for i, _path in enumerate(paths):
                candidates.append(
                    {
                        "id": str(i + 1),
                        "url": f"/api/images/{slug}/style-candidate-{i + 1}.jpg",
                    }
                )

            total_cost = settings.style_image_cost * len(paths)

            self._tasks[task_id] = {
                "status": "completed",
                "result": {
                    "candidates": candidates,
                    "cost": total_cost,
                },
                "error": None,
            }

            # Update cost
            self.outline_store.add_cost(slug, total_cost, is_style=True)

        except Exception as e:
            self._tasks[task_id] = {
                "status": "failed",
                "result": None,
                "error": str(e),
            }

    def select_style(self, slug: str, candidate_id: str, prompt: str) -> dict | None:
        """
        Select a style candidate as the project style.

        Args:
            slug: Project slug.
            candidate_id: ID of the selected candidate.
            prompt: Style prompt.

        Returns:
            Style configuration dict or None if failed.
        """
        # Get candidate path
        candidate_path = self.file_storage.get_style_candidate_path(slug, candidate_id)
        if not candidate_path.exists():
            return None

        # Copy to final style path
        style_path = self.file_storage.get_style_image_path(slug)
        shutil.copy2(candidate_path, style_path)

        # Update outline
        self.outline_store.set_style(slug, prompt, "style.jpg")

        return {
            "prompt": prompt,
            "image": f"/api/images/{slug}/style.jpg",
        }

    def get_task_status(self, task_id: str) -> dict | None:
        """Get task status."""
        return self._tasks.get(task_id)


# Global instance
_image_service: ImageService | None = None


def get_image_service() -> ImageService:
    """Get or create the image service instance."""
    global _image_service
    if _image_service is None:
        _image_service = ImageService()
    return _image_service
