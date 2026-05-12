"""Photo category compatibility helpers."""

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Category


@dataclass(frozen=True)
class PhotoCategoryDefinition:
    """Default category exposed to frontend clients."""

    slug: str
    name: str
    description: str
    legacy_slug: str | None
    sort_order: int
    is_active: bool = True


DEFAULT_PHOTO_CATEGORIES: tuple[PhotoCategoryDefinition, ...] = (
    PhotoCategoryDefinition(
        slug="life",
        name="生活照",
        description="家庭日常、聚会和普通生活记录",
        legacy_slug=None,
        sort_order=10,
    ),
    PhotoCategoryDefinition(
        slug="photography",
        name="摄影照",
        description="更偏摄影作品、旅行风景和构图记录",
        legacy_slug="travel",
        sort_order=20,
    ),
    PhotoCategoryDefinition(
        slug="pet",
        name="宠物照",
        description="家庭宠物和动物陪伴记录",
        legacy_slug=None,
        sort_order=30,
    ),
)

PHOTO_CATEGORY_SLUGS = {category.slug for category in DEFAULT_PHOTO_CATEGORIES}
PHOTO_LEGACY_CATEGORY_SLUGS = {
    category.legacy_slug for category in DEFAULT_PHOTO_CATEGORIES if category.legacy_slug is not None
}
PHOTO_ACCEPTED_CATEGORY_SLUGS = PHOTO_CATEGORY_SLUGS | PHOTO_LEGACY_CATEGORY_SLUGS


def photo_category_filter_values(category: str) -> set[str]:
    """Return storage values that should match a public category slug."""

    if category in {"photography", "travel"}:
        return {"photography", "travel"}
    return {category}


def is_photo_category_slug(value: str) -> bool:
    """Return whether a slug is accepted during the PRD transition."""

    return value in PHOTO_ACCEPTED_CATEGORY_SLUGS


def ensure_default_categories(db: Session) -> None:
    """Create missing default categories for metadata-only test databases."""

    existing_slugs = set(db.scalars(select(Category.slug)))
    changed = False
    for definition in DEFAULT_PHOTO_CATEGORIES:
        if definition.slug in existing_slugs:
            continue
        db.add(
            Category(
                slug=definition.slug,
                name=definition.name,
                description=definition.description,
                legacy_slug=definition.legacy_slug,
                sort_order=definition.sort_order,
                is_active=definition.is_active,
            )
        )
        changed = True
    if changed:
        db.commit()


def list_active_categories(db: Session) -> list[Category]:
    """Return active categories ordered for showcase navigation."""

    ensure_default_categories(db)
    return list(
        db.scalars(
            select(Category)
            .where(Category.is_active.is_(True))
            .order_by(Category.sort_order.asc(), Category.slug.asc())
        )
    )
