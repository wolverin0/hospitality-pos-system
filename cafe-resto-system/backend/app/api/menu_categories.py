"""
Menu categories API endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select, SQLModel
from typing import List, Optional
from datetime import datetime
import structlog
import uuid

from app.core.database import get_session
from app.core.dependencies import get_tenant_id, get_current_user_id
from app.models.menu_category import MenuCategory

logger = structlog.get_logger(__name__)
router = APIRouter()


# Pydantic schemas
class MenuCategoryCreate(SQLModel):
    """Schema for creating a menu category"""
    name: str
    description: Optional[str] = None
    display_order: int = 0
    image_url: Optional[str] = None
    is_active: bool = True


class MenuCategoryResponse(SQLModel):
    """Schema for menu category response"""
    id: uuid.UUID
    tenant_id: uuid.UUID
    location_id: uuid.UUID
    name: str
    description: Optional[str] = None
    display_order: int
    image_url: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None


@router.post("/", response_model=MenuCategoryResponse)
async def create_category(
    category_data: MenuCategoryCreate,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    current_user_id: uuid.UUID = Depends(get_current_user_id),
    session: Session = Depends(get_session)
):
    """Create a new menu category"""
    try:
        # TODO: Validate location_id belongs to tenant and user has permission
        # For now, use tenant_id as location_id placeholder
        category = MenuCategory(
            tenant_id=tenant_id,
            location_id=tenant_id,
            name=category_data.name,
            description=category_data.description,
            display_order=category_data.display_order,
            image_url=category_data.image_url,
            is_active=category_data.is_active
        )
        session.add(category)
        session.commit()
        session.refresh(category)

        logger.info(f"Created menu category {category.id}")
        return category

    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"Error creating menu category: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create menu category"
        )


@router.get("/", response_model=List[MenuCategoryResponse])
async def list_categories(
    location_id: Optional[uuid.UUID] = None,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    current_user_id: uuid.UUID = Depends(get_current_user_id),
    session: Session = Depends(get_session)
):
    """List all menu categories for a tenant/location"""
    try:
        query = select(MenuCategory).where(MenuCategory.tenant_id == tenant_id)

        if location_id:
            query = query.where(MenuCategory.location_id == location_id)

        # Filter to only active categories
        query = query.where(MenuCategory.is_active == True)

        # Order by display_order, then name
        query = query.order_by(MenuCategory.display_order.asc(), MenuCategory.name.asc())

        categories = session.exec(query).all()
        return categories

    except Exception as e:
        logger.error(f"Error listing menu categories: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list menu categories"
        )


@router.get("/{category_id}", response_model=MenuCategoryResponse)
async def get_category(
    category_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    current_user_id: uuid.UUID = Depends(get_current_user_id),
    session: Session = Depends(get_session)
):
    """Get a specific menu category"""
    try:
        category = session.exec(
            select(MenuCategory).where(
                MenuCategory.id == category_id,
                MenuCategory.tenant_id == tenant_id
            )
        ).first()

        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Menu category not found"
            )

        return category

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting menu category: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get menu category"
        )


@router.put("/{category_id}", response_model=MenuCategoryResponse)
async def update_category(
    category_id: uuid.UUID,
    category_data: MenuCategoryCreate,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    current_user_id: uuid.UUID = Depends(get_current_user_id),
    session: Session = Depends(get_session)
):
    """Update a menu category"""
    try:
        category = session.exec(
            select(MenuCategory).where(
                MenuCategory.id == category_id,
                MenuCategory.tenant_id == tenant_id
            )
        ).first()

        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Menu category not found"
            )

        # Update fields if provided
        if category_data.name:
            category.name = category_data.name
        if category_data.description is not None:
            category.description = category_data.description
        if category_data.display_order is not None:
            category.display_order = category_data.display_order
        if category_data.image_url is not None:
            category.image_url = category_data.image_url
        if category_data.is_active is not None:
            category.is_active = category_data.is_active

        category.updated_at = datetime.utcnow()

        session.commit()
        session.refresh(category)

        logger.info(f"Updated menu category {category_id}")
        return category

    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"Error updating menu category: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update menu category"
        )


@router.delete("/{category_id}")
async def delete_category(
    category_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    current_user_id: uuid.UUID = Depends(get_current_user_id),
    session: Session = Depends(get_session)
):
    """Delete a menu category (soft delete - set is_active=False)"""
    try:
        category = session.exec(
            select(MenuCategory).where(
                MenuCategory.id == category_id,
                MenuCategory.tenant_id == tenant_id
            )
        ).first()

        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Menu category not found"
            )

        category.is_active = False
        category.updated_at = datetime.utcnow()

        session.commit()
        session.refresh(category)

        logger.info(f"Deleted menu category {category_id}")
        return {"message": "Menu category deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"Error deleting menu category: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete menu category"
        )
