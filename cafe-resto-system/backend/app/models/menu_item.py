"""
Menu item model for menu items
"""

from sqlmodel import Field, SQLModel, Relationship
from sqlalchemy import Column, ForeignKey
from decimal import Decimal
from datetime import datetime
from typing import Optional, TYPE_CHECKING
from enum import Enum
import uuid

if TYPE_CHECKING:
    from app.models.menu_category import MenuCategory
    from app.models.menu_station import MenuStation
    from app.models.kitchen_course import KitchenCourse


class MenuItemType(str, Enum):
    """Type of menu item"""
    FOOD = "food"
    BEVERAGE = "beverage"
    ALCOHOL = "alcohol"
    MERCHANDISE = "merchandise"


class MenuItem(SQLModel, table=True):
    """Menu item for ordering"""

    __tablename__ = "menu_items"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(
        foreign_key="tenants.id",
        index=True,
        description="Tenant ID for multi-tenant isolation"
    )
    location_id: uuid.UUID = Field(
        foreign_key="locations.id",
        index=True,
        description="Location this item is available at"
    )
    category_id: uuid.UUID = Field(
        foreign_key="menu_categories.id",
        index=True,
        description="Category this item belongs to"
    )
    station_id: uuid.UUID = Field(
        foreign_key="menu_stations.id",
        index=True,
        description="Station this item goes to (bar, kitchen, etc.)"
    )
    course_id: uuid.UUID = Field(
        foreign_key="kitchen_courses.id",
        index=True,
        description="Default course this item belongs to (drinks, mains, etc.)"
    )
    default_prep_time_minutes: Optional[int] = Field(
        default=None,
        description="Default prep time for this item (in minutes), overrides course default if set"
    )

    # Item details
    name: str = Field(max_length=255, nullable=False, description="Item name")
    description: Optional[str] = Field(max_length=2000, nullable=True, description="Item description")

    # Pricing
    price: Decimal = Field(
        max_digits=10,
        decimal_places=2,
        description="Base price of item"
    )

    # Item type
    item_type: MenuItemType = Field(
        default=MenuItemType.FOOD,
        index=True,
        description="Type of menu item"
    )

    # Images
    image_url: Optional[str] = Field(max_length=1000, nullable=True, description="Primary image URL")
    thumbnail_url: Optional[str] = Field(max_length=1000, nullable=True, description="Thumbnail image URL")

    # Availability
    is_available: bool = Field(default=True, index=True, description="Whether item is currently available")
    stock_count: Optional[int] = Field(default=None, description="Stock count (if tracked)")

    # Display
    display_order: int = Field(default=0, description="Display order within category")
    is_featured: bool = Field(default=False, index=True, description="Whether item is featured")

    # Nutritional/allergen info
    calories: Optional[int] = Field(default=None, description="Calories per serving")
    is_vegetarian: bool = Field(default=False, description="Vegetarian option")
    is_vegan: bool = Field(default=False, description="Vegan option")
    is_gluten_free: bool = Field(default=False, description="Gluten-free option")

    # Modifiers
    has_modifiers: bool = Field(default=False, description="Whether item has available modifiers")

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None

    # Relationships
    category: Optional["MenuCategory"] = Relationship(back_populates="menu_items")
    station: Optional["MenuStation"] = Relationship()
    course: Optional["KitchenCourse"] = Relationship()

    class Config:
        indexes = [
            {"name": "idx_menu_item_tenant_id", "columns": ["tenant_id"]},
            {"name": "idx_menu_item_location_id", "columns": ["location_id"]},
            {"name": "idx_menu_item_category_id", "columns": ["category_id"]},
            {"name": "idx_menu_item_station_id", "columns": ["station_id"]},
            {"name": "idx_menu_item_course_id", "columns": ["course_id"]},
            {"name": "idx_menu_item_is_available", "columns": ["is_available"]},
            {"name": "idx_menu_item_is_featured", "columns": ["is_featured"]},
            {"name": "idx_menu_item_display_order", "columns": ["display_order"]},
            {"name": "idx_menu_item_item_type", "columns": ["item_type"]},
        ]
