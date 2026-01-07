"""
Floor model for organizing tables
"""

from sqlmodel import Field, SQLModel, Relationship
from sqlalchemy import Column, ForeignKey
from datetime import datetime
from typing import Optional, TYPE_CHECKING
import uuid

if TYPE_CHECKING:
    from app.models.table import Table


class Floor(SQLModel, table=True):
    """Floor model for organizing tables within a location"""

    __tablename__ = "floors"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(foreign_key="tenants.id", index=True, description="Tenant ID for multi-tenant isolation")
    location_id: uuid.UUID = Field(foreign_key="locations.id", index=True, description="Location this floor belongs to")

    # Floor details
    name: str = Field(max_length=100, nullable=False, description="Floor name (e.g., 'Main Floor', 'Patio')")
    description: Optional[str] = Field(max_length=500, nullable=True, description="Optional description of the floor")

    # Display order
    display_order: int = Field(default=0, description="Order to display floors in UI")

    # Status
    is_active: bool = Field(default=True, index=True)

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None

    # Relationships
    tables: list["Table"] = Relationship(back_populates="floor")

    class Config:
        indexes = [
            {"name": "idx_floor_tenant_id", "columns": ["tenant_id"]},
            {"name": "idx_floor_location_id", "columns": ["location_id"]},
            {"name": "idx_floor_is_active", "columns": ["is_active"]},
        ]
