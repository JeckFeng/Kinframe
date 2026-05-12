"""Schemas for the showcase API."""

from typing import Any

from pydantic import BaseModel

from app.schemas.photo import PhotoCategoryRead, PhotoRead


class ShowcasePhotoItem(BaseModel):
    """A photo bundled with its presigned preview URL and slide design for showcase rendering."""

    photo: PhotoRead
    preview_url: str | None
    slide_design: dict[str, Any] | None


class ShowcaseResponse(BaseModel):
    """Top-level showcase response: categories + filtered photos ready for playback."""

    categories: list[PhotoCategoryRead]
    photos: list[ShowcasePhotoItem]
