"""Map album API routes — v0.4."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select

from app.api.deps import DbSession, get_current_user, get_object_storage
from app.models import Photo, User
from app.schemas.photo import MapPhotoItem, MapPhotosResponse
from app.services.storage import ObjectStorage

router = APIRouter(prefix="/api/map", tags=["map"])


def _build_map_item(photo: Photo, storage: ObjectStorage) -> MapPhotoItem:
    """Convert a Photo ORM instance into a MapPhotoItem with presigned URLs."""
    return MapPhotoItem(
        photo_id=photo.id,
        preview_url=storage.presigned_get_url(photo.object_key_preview or photo.object_key_original),
        thumbnail_url=storage.presigned_get_url(photo.object_key_thumbnail),
        category=photo.category,
        gps_lat=photo.gps_lat,  # type: ignore[arg-type]
        gps_lng=photo.gps_lng,  # type: ignore[arg-type]
        location_name=photo.location_name,
        location_city=photo.location_city,
        location_region=photo.location_region,
        location_country=photo.location_country,
        location_district=photo.location_district,
        final_caption=photo.final_caption,
        taken_at=photo.taken_at,
    )


@router.get("/photos", response_model=MapPhotosResponse)
def get_map_photos(
    db: DbSession,
    current_user: Annotated[User, Depends(get_current_user)],
    storage: Annotated[ObjectStorage, Depends(get_object_storage)],
    category: str | None = Query(default=None),
) -> MapPhotosResponse:
    """Return geocoded photos for map marker rendering.

    Only returns ready photos with GPS coordinates and successful geocoding.
    """
    statement = (
        select(Photo)
        .where(
            Photo.status == "ready",
            Photo.gps_lat.isnot(None),
            Photo.gps_lng.isnot(None),
            Photo.geocoding_status == "succeeded",
        )
        .order_by(Photo.taken_at.desc())
    )

    if category is not None:
        statement = statement.where(Photo.category == category)

    photos = list(db.scalars(statement))
    return MapPhotosResponse(
        photos=[_build_map_item(photo, storage) for photo in photos]
    )
