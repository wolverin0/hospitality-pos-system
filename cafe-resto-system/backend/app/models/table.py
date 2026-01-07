"""
Table model for restaurant seating
"""

from sqlmodel import Field, SQLModel, Relationship
from sqlalchemy import Column, ForeignKey
from datetime import datetime
from typing import Optional, TYPE_CHECKING
import uuid

if TYPE_CHECKING:
    from app.models.floor import Floor
    from app.models.table_session import TableSession


class Table(SQLModel, table=True):
    """Table model for restaurant seating"""

    __tablename__ = "tables"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(foreign_key="tenants.id", index=True, description="Tenant ID for multi-tenant isolation")
    location_id: uuid.UUID = Field(foreign_key="locations.id", index=True, description="Location this table is in")
    floor_id: uuid.UUID = Field(foreign_key="floors.id", index=True, description="Floor this table is on")

    # Table details
    name: str = Field(max_length=50, nullable=False, description="Table identifier (e.g., 'A1', 'B3')")
    capacity: int = Field(default=4, description="Maximum number of guests")
    description: Optional[str] = Field(max_length=500, nullable=True, description="Optional description of the table")

    # Position (for visual floor plan)
    x_position: Optional[int] = Field(default=None, description="X coordinate on floor plan")
    y_position: Optional[int] = Field(default=None, description="Y coordinate on floor plan")
    width: Optional[int] = Field(default=None, description="Width on floor plan (pixels)")
    height: Optional[int] = Field(default=None, description="Height on floor plan (pixels)")

    # QR code for guest ordering
    qr_code: Optional[str] = Field(max_length=500, nullable=True, description="QR code URL or identifier")

    # Table type
    table_type: str = Field(default="standard", max_length=50, description="Table type: standard, booth, bar, patio, etc.")

    # Status
    is_active: bool = Field(default=True, index=True)
    is_reserved: bool = Field(default=False, description="Whether table is currently reserved")

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None

    # Relationships
    floor: Optional["Floor"] = Relationship(back_populates="tables")
    sessions: list["TableSession"] = Relationship(back_populates="table")

    class Config:
        indexes = [
            {"name": "idx_table_tenant_id", "columns": ["tenant_id"]},
            {"name": "idx_table_location_id", "columns": ["location_id"]},
            {"name": "idx_table_floor_id", "columns": ["floor_id"]},
            {"name": "idx_table_name", "columns": ["name"]},
            {"name": "idx_table_is_active", "columns": ["is_active"]},
        ]
