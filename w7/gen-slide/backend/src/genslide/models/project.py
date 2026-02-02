"""Project domain model."""

from dataclasses import dataclass, field

from .slide import Slide


@dataclass
class StyleConfig:
    """Style configuration for a project."""

    prompt: str
    image: str  # filename of the style image


@dataclass
class CostRecord:
    """Cost tracking for a project."""

    total: float = 0.0
    style_generation: float = 0.0
    slide_images: float = 0.0


@dataclass
class Project:
    """Project domain model."""

    slug: str
    title: str
    style: StyleConfig | None = None
    cost: CostRecord = field(default_factory=CostRecord)
    slides: list[Slide] = field(default_factory=list)

    def get_slide(self, sid: str) -> Slide | None:
        """Get a slide by its ID."""
        for slide in self.slides:
            if slide.sid == sid:
                return slide
        return None

    def add_slide(self, slide: Slide, after_sid: str | None = None) -> None:
        """Add a slide to the project."""
        if after_sid is None:
            self.slides.append(slide)
        else:
            for i, s in enumerate(self.slides):
                if s.sid == after_sid:
                    self.slides.insert(i + 1, slide)
                    return
            # If after_sid not found, append to end
            self.slides.append(slide)

    def remove_slide(self, sid: str) -> bool:
        """Remove a slide from the project."""
        for i, slide in enumerate(self.slides):
            if slide.sid == sid:
                self.slides.pop(i)
                return True
        return False

    def reorder_slides(self, order: list[str]) -> bool:
        """Reorder slides according to the given order."""
        # Validate all sids exist
        existing_sids = {s.sid for s in self.slides}
        if set(order) != existing_sids:
            return False

        # Create new ordered list
        slide_map = {s.sid: s for s in self.slides}
        self.slides = [slide_map[sid] for sid in order]
        return True
