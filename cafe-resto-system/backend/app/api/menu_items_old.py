"""
Menu items API endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlmodel import Session, select, SQLModel
from sqlmodel import Session, select
from sqlmodel import Session, select/from sqlmodel import Session, select, SQLModel/
from typing import List, Optional
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


@router.post("/", response_model=MenuItemResponse)
async def create_menu_item(
    item_data: MenuItemCreate,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    current_user_id: uuid.UUID = Depends(get_current_user_id),
    session: Session = Depends(get_session)
):
    """Create a new menu item"""
    # TODO: Verify category exists and belongs to tenant
    # TODO: Validate user has permission to create menu items

    item = MenuItem(
        tenant_id=tenant_id,
        location_id=tenant_id,  # TODO: Fix this
        category_id=item_data.category_id,
        name=item_data.name,
        description=item_data.description,
        price=float(item_data.price),
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
    query = select(MenuItem).where(
        MenuItem.tenant_id == tenant_id
    )

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

    # Sort by display_order
    query = query.order_by(MenuItem.display_order, MenuItem.name)

    items = session.exec(query).all()
    return items


@router.get("/{item_id}", response_model=MenuItemResponse)
async def get_menu_item(
    item_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    current_user_id: uuid.UUID = Depends(get_current_user_id),
    session: Session = Depends(get_session)
):
    """Get a menu item by ID"""
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
