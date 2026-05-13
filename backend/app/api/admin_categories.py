"""Admin category management routes."""

from typing import Annotated

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select

from app.api.deps import DbSession, get_current_admin
from app.models import Category, User
from app.services.audit_logs import create_audit_log


router = APIRouter(prefix="/api/admin/categories", tags=["admin-categories"])


class CategoryCreate(BaseModel):
    slug: str = Field(max_length=50)
    name: str = Field(max_length=100)
    description: str | None = None
    sort_order: int = 100
    is_active: bool = True


class CategoryUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=100)
    description: str | None = None
    sort_order: int | None = None
    is_active: bool | None = None


class CategoryRead(BaseModel):
    id: str
    slug: str
    name: str
    description: str | None
    legacy_slug: str | None
    sort_order: int
    is_active: bool
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


@router.get("", response_model=list[CategoryRead])
def list_categories(
    db: DbSession,
    _admin: Annotated[User, Depends(get_current_admin)],
) -> list[CategoryRead]:
    """List all categories (including inactive)."""
    rows = db.scalars(select(Category).order_by(Category.sort_order.asc(), Category.slug.asc()))
    return [CategoryRead.model_validate(r) for r in rows]


@router.post("", response_model=CategoryRead, status_code=status.HTTP_201_CREATED)
def create_category(
    payload: CategoryCreate,
    db: DbSession,
    admin: Annotated[User, Depends(get_current_admin)],
) -> CategoryRead:
    """Create a new category."""
    existing = db.scalar(select(Category).where(Category.slug == payload.slug))
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Category slug already exists")
    category = Category(
        slug=payload.slug,
        name=payload.name,
        description=payload.description,
        sort_order=payload.sort_order,
        is_active=payload.is_active,
    )
    db.add(category)
    db.commit()
    db.refresh(category)
    create_audit_log(
        db,
        admin_id=admin.id,
        action="category.create",
        target_type="category",
        target_id=category.id,
        detail={"summary": f"Admin {admin.username} created category {category.slug}"},
    )
    return CategoryRead.model_validate(category)


@router.patch("/{category_id}", response_model=CategoryRead)
def update_category(
    category_id: str,
    payload: CategoryUpdate,
    db: DbSession,
    admin: Annotated[User, Depends(get_current_admin)],
) -> CategoryRead:
    """Update a category. slug is immutable."""
    category = db.get(Category, category_id)
    if category is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")

    changed: list[str] = []
    before: dict = {}
    after: dict = {}
    data = payload.model_dump(exclude_unset=True)

    if "name" in data and data["name"] is not None and data["name"] != category.name:
        changed.append("name")
        before["name"] = category.name
        after["name"] = data["name"]
        category.name = data["name"]
    if "description" in data and data["description"] != category.description:
        changed.append("description")
        before["description"] = category.description
        after["description"] = data["description"]
        category.description = data["description"]
    if "sort_order" in data and data["sort_order"] is not None and data["sort_order"] != category.sort_order:
        changed.append("sort_order")
        before["sort_order"] = category.sort_order
        after["sort_order"] = data["sort_order"]
        category.sort_order = data["sort_order"]
    if "is_active" in data and data["is_active"] is not None and data["is_active"] != category.is_active:
        changed.append("is_active")
        before["is_active"] = category.is_active
        after["is_active"] = data["is_active"]
        category.is_active = data["is_active"]

    if changed:
        db.add(category)
        db.commit()
        db.refresh(category)
        create_audit_log(
            db,
            admin_id=admin.id,
            action="category.update",
            target_type="category",
            target_id=category.id,
            detail={"changed_fields": changed, "before": before, "after": after},
        )

    return CategoryRead.model_validate(category)
