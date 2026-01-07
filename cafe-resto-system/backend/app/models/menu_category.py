"""
Menu category model for organizing menu items
"""

from sqlmodel import Field, SQLModel, Relationship
from sqlalchemy import Column, ForeignKey
from datetime import datetime
from typing import Optional, TYPE_CHECKING
import uuid

if TYPE_CHECKING:
    from app.models.menu_item import MenuItem


class MenuCategory(SQLModel, table=True):
    """Menu category for organizing menu items"""

    __tablename__ = "menu_categories"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(
        foreign_key="tenants.id",
        index=True,
        description="Tenant ID for multi-tenant isolation"
    )
    location_id: uuid.UUID = Field(
        foreign_key="locations.id",
        index=True,
        description="Location this category belongs to"
    )

    # Category details
    name: str = Field(max_length=255, nullable=False, description="Category name")
    description: Optional[str] = Field(max_length=1000, nullable=True, description="Optional description")

    # Display order
    display_order: int = Field(default=0, description="Order to display categories in UI")

    # Category image
    image_url: Optional[str] = Field(max_length=1000, nullable=True, description="Category image URL")

    # Status
    is_active: bool = Field(default=True, index=True, description="Whether category is active")

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None

    # Relationships
    menu_items: list["MenuItem"] = Relationship(back_populates="category")

    class Config:
        indexes = [
            {"name": "idx_menu_category_tenant_id", "columns": ["tenant_id"]},
            {"name": "idx_menu_category_location_id", "columns": ["location_id"]},
            {"name": "idx_menu_category_is_active", "columns": ["is_active"]},
            {"name": "idx_menu_category_display_order", "columns": ["display_order"]},
        ]
