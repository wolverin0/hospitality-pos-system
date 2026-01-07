"""
Menu items API endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlmodel import Session, select, SQLModel
from typing import List, Optional
from datetime import datetime
import structlog
import uuid

from app.core.database import get_session
from app.core.dependencies import get_tenant_id, get_current_user_id
from app.models.menu_item import MenuItem, MenuItemType
from app.models.menu_category import MenuCategory

logger = structlog.get_logger(__name__)
router = APIRouter()


# Pydantic schemas
class MenuItemCreate(SQLModel):
    """Schema for creating a menu item"""
    name: str
    description: Optional[str] = None
    price: float
    category_id: uuid.UUID
    item_type: MenuItemType = MenuItemType.FOOD
    image_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    is_available: bool = True
    stock_count: Optional[int] = None
    display_order: int = 0
    is_featured: bool = False
    calories: Optional[int] = None
    is_vegetarian: bool = False
    is_vegan: bool = False
    is_gluten_free: bool = False
    has_modifiers: bool = False


class MenuItemResponse(SQLModel):
    """Schema for menu item response"""
    id: uuid.UUID
    tenant_id: uuid.UUID
    location_id: uuid.UUID
    category_id: uuid.UUID
    name: str
    description: Optional[str] = None
    price: float
    item_type: MenuItemType
    image_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    is_available: bool
    stock_count: Optional[int] = None
    display_order: int
    is_featured: bool
    calories: Optional[int] = None
    is_vegetarian: bool
    is_vegan: bool
    is_gluten_free: bool
    has_modifiers: bool
    created_at: datetime
    updated_at: Optional[datetime] = None


@router.post("/", response_model=MenuItemResponse)
async def create_menu_item(
    item_data: MenuItemCreate,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    current_user_id: uuid.UUID = Depends(get_current_user_id),
    session: Session = Depends(get_session)
):
    """Create a new menu item"""
    try:
        # Verify category exists and belongs to tenant
        category = session.exec(
            select(MenuCategory).where(
                MenuCategory.id == item_data.category_id,
                MenuCategory.tenant_id == tenant_id
            )
        ).first()

        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Menu category not found"
            )

        # Create menu item
        item = MenuItem(
            tenant_id=tenant_id,
            location_id=tenant_id,  # TODO: Add location_id parameter to create schema
            category_id=item_data.category_id,
            name=item_data.name,
            description=item_data.description,
            price=item_data.price,
            item_type=item_data.item_type,
            image_url=item_data.image_url,
            thumbnail_url=item_data.thumbnail_url,
            is_available=item_data.is_available,
            stock_count=item_data.stock_count,
            display_order=item_data.display_order,
            is_featured=item_data.is_featured,
            calories=item_data.calories,
            is_vegetarian=item_data.is_vegetarian,
            is_vegan=item_data.is_vegan,
            is_gluten_free=item_data.is_gluten_free,
            has_modifiers=item_data.has_modifiers
        )
        session.add(item)
        session.commit()
        session.refresh(item)

        logger.info(f"Created menu item {item.id}")
        return item

    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"Error creating menu item: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create menu item"
        )


@router.get("/", response_model=List[MenuItemResponse])
async def list_menu_items(
    category_id: Optional[uuid.UUID] = Query(None, description="Filter by category"),
    item_type: Optional[MenuItemType] = Query(None, description="Filter by item type"),
    is_available: Optional[bool] = Query(None, description="Filter by availability"),
    is_featured: Optional[bool] = Query(None, description="Filter by featured status"),
    search: Optional[str] = Query(None, description="Search by name or description"),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    current_user_id: uuid.UUID = Depends(get_current_user_id),
    session: Session = Depends(get_session)
):
    """List menu items with optional filters"""
    try:
        query = select(MenuItem).where(MenuItem.tenant_id == tenant_id)

        # Apply filters
        if category_id:
            query = query.where(MenuItem.category_id == category_id)

        if item_type:
            query = query.where(MenuItem.item_type == item_type)

        if is_available is not None:
            query = query.where(MenuItem.is_available == is_available)

        if is_featured is not None:
            query = query.where(MenuItem.is_featured == is_featured)

        if search:
            query = query.where(
                (MenuItem.name.ilike(f"%{search}%")) |
                (MenuItem.description.ilike(f"%{search}%"))
            )

        # Sort by display_order, then name
        query = query.order_by(MenuItem.display_order.asc(), MenuItem.name.asc())

        items = session.exec(query).all()
        return items

    except Exception as e:
        logger.error(f"Error listing menu items: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list menu items"
        )


@router.get("/{item_id}", response_model=MenuItemResponse)
async def get_menu_item(
    item_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    current_user_id: uuid.UUID = Depends(get_current_user_id),
    session: Session = Depends(get_session)
):
    """Get a specific menu item"""
    try:
        item = session.exec(
            select(MenuItem).where(
                MenuItem.id == item_id,
                MenuItem.tenant_id == tenant_id
            )
        ).first()

        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Menu item not found"
            )

        return item

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting menu item: {e}")
        raise HTTPException(
            status_code=status_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get menu item"
        )


@router.put("/{item_id}", response_model=MenuItemResponse)
async def update_menu_item(
    item_id: uuid.UUID,
    item_data: MenuItemCreate,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    current_user_id: uuid.UUID = Depends(get_current_user_id),
    session: Session = Depends(get_session)
):
    """Update a menu item"""
    try:
        item = session.exec(
            select(MenuItem).where(
                MenuItem.id == item_id,
                MenuItem.tenant_id == tenant_id
            )
        ).first()

        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Menu item not found"
            )

        # Update fields if provided
        if item_data.name:
            item.name = item_data.name
        if item_data.description is not None:
            item.description = item_data.description
        if item_data.price:
            item.price = float(item_data.price)
        if item_data.category_id:
            # Verify new category exists
            category = session.exec(
                select(MenuCategory).where(
                    MenuCategory.id == item_data.category_id,
                    MenuCategory.tenant_id == tenant_id
                )
            ).first()

            if not category:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Menu category not found"
                )

            item.category_id = item_data.category_id
        if item_data.item_type:
            item.item_type = item_data.item_type
        if item_data.image_url:
            item.image_url = item_data.image_url
        if item_data.thumbnail_url:
            item.thumbnail_url = item_data.thumbnail_url
        if item_data.is_available is not None:
            item.is_available = item_data.is_available
        if item_data.stock_count is not None:
            item.stock_count = item_data.stock_count
        if item_data.display_order is not None:
            item.display_order = item_data.display_order
        if item_data.is_featured is not None:
            item.is_featured = item_data.is_featured
        if item_data.calories is not None:
            item.calories = item_data.calories
        if item_data.is_vegetarian is not None:
            item.is_vegetarian = item_data.is_vegetarian
        if item_data.is_vegan is not None:
            item.is_vegan = item_data.is_vegan
        if item_data.is_gluten_free is not None:
            item.is_gluten_free = item_data.is_gluten_free
        if item_data.has_modifiers is not None:
            item.has_modifiers = item_data.has_modifiers

        item.updated_at = datetime.utcnow()

        session.commit()
        session.refresh(item)

        logger.info(f"Updated menu item {item_id}")
        return item

    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"Error updating menu item: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update menu item"
        )


@router.delete("/{item_id}")
async def delete_menu_item(
    item_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    current_user_id: uuid.UUID = Depends(get_current_user_id),
    session: Session = Depends(get_session)
):
    """Delete a menu item"""
    try:
        item = session.exec(
            select(MenuItem).where(
                MenuItem.id == item_id,
                MenuItem.tenant_id == tenant_id
            )
        ).first()

        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Menu item not found"
            )

        session.delete(item)
        session.commit()

        logger.info(f"Deleted menu item {item_id}")
        return {"message": "Menu item deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"Error deleting menu item: {e}")
        raise HTTPException(
            status_code=status_500_INTERNAL_SERVER_ERROR,
            detail="Failed to menu item"
        )
