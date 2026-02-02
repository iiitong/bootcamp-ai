"""Image domain model."""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class ImageRecord:
    """Image record in a slide."""

    hash: str
    filename: str
    created_at: datetime = field(default_factory=datetime.utcnow)
