"""
Kitchen course model for order coursing
"""

from sqlmodel import Field, SQLModel, Relationship
from sqlalchemy import Column, ForeignKey
from datetime import datetime
from typing import Optional, TYPE_CHECKING
from enum import Enum
import uuid

if TYPE_CHECKING:
    from app.models.menu_station import MenuStation


class CourseType(str, Enum):
    """Type of course"""
    DRINKS = "drinks"
    APPETIZERS = "appetizers"
    SOUPS = "soups"
    SALADS = "salads"
    MAINS = "mains"
    DESSERT = "dessert"
    COFFEE = "coffee"
    CUSTOM = "custom"


class KitchenCourse(SQLModel, table=True):
    """Kitchen course for order sequencing"""

    __tablename__ = "kitchen_courses"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(
        foreign_key="tenants.id",
        index=True,
        description="Tenant ID for multi-tenant isolation"
    )
    location_id: uuid.UUID = Field(
        foreign_key="locations.id",
        index=True,
        description="Location this course belongs to"
    )
    station_id: uuid.UUID = Field(
        foreign_key="menu_stations.id",
        index=True,
        description="Station this course is associated with"
    )

    # Course details
    name: str = Field(max_length=255, nullable=False, description="Course display name")
    course_type: CourseType = Field(
        default=CourseType.MAINS,
        index=True,
        description="Type of course (drinks, appetizers, mains, etc.)"
    )

    # Course configuration
    course_number: int = Field(
        default=0,
        index=True,
        description="Course number for sequencing (1, 2, 3, ...)"
    )
    display_order: int = Field(default=0, description="Display order in UI")
    color: Optional[str] = Field(max_length=7, nullable=True, description="Hex color code for UI (e.g., #3498DB)")
    icon: Optional[str] = Field(max_length=50, nullable=True, description="Icon name/identifier for UI")

    # Course behavior
    auto_fire_on_confirm: bool = Field(
        default=False,
        description="Whether this course fires automatically when order is confirmed (e.g., drinks)"
    )
    default_prep_time_minutes: Optional[int] = Field(
        default=None,
        description="Default prep time hint for this course (in minutes)"
    )

    # Course filtering - determines which items go to this course
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

    # Display settings
    is_active: bool = Field(default=True, index=True, description="Whether course is active")
    is_visible_in_menu: bool = Field(default=True, description="Whether course appears in menu/course selector")

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None

    # Relationships
    station: Optional["MenuStation"] = Relationship(sa_relationship_kwargs={"foreign_keys": "[KitchenCourse.station_id]"})

    class Config:
        indexes = [
            {"name": "idx_kitchen_course_tenant_id", "columns": ["tenant_id"]},
            {"name": "idx_kitchen_course_location_id", "columns": ["location_id"]},
            {"name": "idx_kitchen_course_station_id", "columns": ["station_id"]},
            {"name": "idx_kitchen_course_course_type", "columns": ["course_type"]},
            {"name": "idx_kitchen_course_course_number", "columns": ["course_number"]},
            {"name": "idx_kitchen_course_is_active", "columns": ["is_active"]},
        ]
