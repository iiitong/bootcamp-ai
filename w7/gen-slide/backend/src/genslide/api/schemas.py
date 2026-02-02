"""Pydantic request/response schemas."""

from datetime import datetime

from pydantic import BaseModel


# Style schemas
class StyleConfig(BaseModel):
    """Style configuration."""

    prompt: str
    image: str


# Image schemas
class SlideImage(BaseModel):
    """Slide image response."""

    hash: str
    url: str
    created_at: datetime


# Slide schemas
class SlideResponse(BaseModel):
    """Slide response."""

    sid: str
    content: str
    images: list[SlideImage]
    current_hash: str
    has_matching_image: bool


class CreateSlideRequest(BaseModel):
    """Create slide request."""

    content: str
    after_sid: str | None = None


class UpdateSlideRequest(BaseModel):
    """Update slide request."""

    content: str


class ReorderSlidesRequest(BaseModel):
    """Reorder slides request."""

    order: list[str]


class ReorderSlidesResponse(BaseModel):
    """Reorder slides response."""

    order: list[str]


# Project schemas
class ProjectResponse(BaseModel):
    """Project response."""

    slug: str
    title: str
    style: StyleConfig | None
    slides: list[SlideResponse]
    total_cost: float


class CreateProjectRequest(BaseModel):
    """Create project request."""

    title: str


class UpdateProjectRequest(BaseModel):
    """Update project request."""

    title: str


class UpdateProjectResponse(BaseModel):
    """Update project response."""

    slug: str
    title: str


# Task schemas
class TaskResponse(BaseModel):
    """Task status response."""

    task_id: str
    status: str  # pending | processing | completed | failed
    result: dict | None = None
    error: str | None = None


class GenerateImageRequest(BaseModel):
    """Generate image request."""

    content: str | None = None


class GenerateStyleRequest(BaseModel):
    """Generate style request."""

    prompt: str


class SelectStyleRequest(BaseModel):
    """Select style request."""

    candidate_id: str
    prompt: str


class SelectStyleResponse(BaseModel):
    """Select style response."""

    style: StyleConfig


# Cost schemas
class CostBreakdown(BaseModel):
    """Cost breakdown details."""

    style_generation: float
    slide_images: float


class CostResponse(BaseModel):
    """Cost response."""

    total_cost: float
    breakdown: CostBreakdown
    image_count: int


# Error schemas
class ErrorResponse(BaseModel):
    """Error response."""

    error: str
    message: str
    details: dict | None = None
