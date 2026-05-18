"""Showcase API — bundled data for the full-screen playback page."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.deps import DbSession, get_current_user, get_object_storage
from app.models import User
from app.schemas.photo import PhotoCategoryRead, PhotoRead
from app.schemas.showcase import ShowcasePhotoItem, ShowcaseResponse
from app.services.categories import list_active_categories
from app.services.photos import PHOTO_STATUS_READY, list_photos
from app.services.slide_designs import get_latest_display_slide_design
from app.services.storage import ObjectStorage

router = APIRouter(prefix="/api/showcase", tags=["showcase"])


@router.get("", response_model=ShowcaseResponse)
def get_showcase(
    db: DbSession,
    _current_user: Annotated[User, Depends(get_current_user)],
    storage: Annotated[ObjectStorage, Depends(get_object_storage)],
    category: str | None = Query(default=None),
) -> ShowcaseResponse:
    categories = [PhotoCategoryRead.model_validate(c) for c in list_active_categories(db)]

    all_photos = list_photos(db, category)
    ready_photos = [
        p for p in all_photos
        if p.include_in_showcase and p.status == PHOTO_STATUS_READY
    ]
    ready_photos.sort(key=lambda p: p.taken_at or p.uploaded_at, reverse=True)

    items: list[ShowcasePhotoItem] = []
    for photo in ready_photos:
        preview_url: str | None = None
        if photo.object_key_preview is not None:
            preview_url = storage.presigned_get_url(photo.object_key_preview)

        slide_design = None
        design = get_latest_display_slide_design(db, photo.id)
        if design is not None:
            slide_design = design.design_json

        items.append(
            ShowcasePhotoItem(
                photo=PhotoRead.model_validate(photo),
                preview_url=preview_url,
                slide_design=slide_design,
            )
        )

    return ShowcaseResponse(categories=categories, photos=items)
