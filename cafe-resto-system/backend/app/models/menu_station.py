"""
Menu station model for kitchen/bar stations
"""

from sqlmodel import Field, SQLModel, Relationship
from sqlalchemy import Column, ForeignKey
from datetime import datetime
from typing import Optional, TYPE_CHECKING
from enum import Enum
import uuid

if TYPE_CHECKING:
    from app.models.kitchen_course import KitchenCourse


class StationType(str, Enum):
    """Type of kitchen station"""
    BAR = "bar"
    KITCHEN = "kitchen"
    EXPO = "expo"
    GRILL = "grill"
    FRYER = "fryer"
    SALAD = "salad"
    DESSERT = "dessert"
    PREP = "prep"
    SUSHI = "sushi"
    PIZZA = "pizza"
    CUSTOM = "custom"


class MenuStation(SQLModel, table=True):
    """Menu station for kitchen/bar operations"""

    __tablename__ = "menu_stations"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(
        foreign_key="tenants.id",
        index=True,
        description="Tenant ID for multi-tenant isolation"
    )
    location_id: uuid.UUID = Field(
        foreign_key="locations.id",
        index=True,
        description="Location this station belongs to"
    )

    # Station details
    name: str = Field(max_length=255, nullable=False, description="Station display name")
    station_type: StationType = Field(
        default=StationType.KITCHEN,
        index=True,
        description="Type of station (bar, kitchen, expo, etc.)"
    )

    # Station configuration
    display_order: int = Field(default=0, description="Display order in KDS")
    color: Optional[str] = Field(max_length=7, nullable=True, description="Hex color code for UI (e.g., #FF5733)")
    icon: Optional[str] = Field(max_length=50, nullable=True, description="Icon name/identifier for UI")

    # Station filter fields - determines which items go to this station
    # Items can be filtered by item_type, category_id, or custom rules
    filter_item_types: Optional[str] = Field(
        default=None,
        max_length=500,
        nullable=True,
        description="Comma-separated item types to filter (e.g., 'beverage,alcohol')"
    )
    filter_category_ids: Optional[str] = Field(
        default=None,
        max_length=2000,
        nullable=True,
        description="Comma-separated category IDs to filter"
    )
    filter_custom_rules: Optional[str] = Field(
        default=None,
        max_length=2000,
        nullable=True,
        description="Custom filter rules (JSON or structured text)"
    )

    # Printer configuration
    printer_ids: Optional[str] = Field(
        default=None,
        max_length=1000,
        nullable=True,
        description="Comma-separated printer IDs assigned to this station (0..n printers)"
    )

    # Display settings
    is_active: bool = Field(default=True, index=True, description="Whether station is active")
    is_visible_in_kds: bool = Field(default=True, description="Whether station appears in KDS")
    requires_expo_approval: bool = Field(default=False, description="Whether items need Expo approval before firing")

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None

    # Relationships
    # courses: list["KitchenCourse"] = Relationship(back_populates="station")

    class Config:
        indexes = [
            {"name": "idx_menu_station_tenant_id", "columns": ["tenant_id"]},
            {"name": "idx_menu_station_location_id", "columns": ["location_id"]},
            {"name": "idx_menu_station_station_type", "columns": ["station_type"]},
            {"name": "idx_menu_station_is_active", "columns": ["is_active"]},
            {"name": "idx_menu_station_display_order", "columns": ["display_order"]},
        ]
