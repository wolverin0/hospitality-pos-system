"""
Locations model
"""

from sqlmodel import Field, SQLModel, Relationship
from datetime import datetime
from typing import Optional, List, TYPE_CHECKING
import uuid

from app.models.tenant import Tenant

if TYPE_CHECKING:
    from app.models.shift import Shift


class Location(SQLModel, table=True):
    """Location model with tenant isolation"""
    
    __tablename__ = "locations"
    
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(foreign_key="tenants.id", index=True, description="Tenant ID for multi-tenant isolation")
    
    # Basic info
    name: str = Field(index=True, nullable=False, max_length=255)
    address: Optional[str] = Field(default=None, max_length=500)
    phone: Optional[str] = Field(default=None, max_length=50)
    email: Optional[str] = Field(default=None, max_length=255)
    
    # Status
    is_active: bool = Field(default=True, index=True)
    
    # Configuration
    timezone: Optional[str] = Field(default="UTC")
    currency: Optional[str] = Field(default="USD", max_length=3)
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None

    # Relationships
    shifts: List["Shift"] = Relationship(back_populates="location")
    
    class Config:
        indexes = [
            {"name": "idx_location_tenant_id", "columns": ["tenant_id"]},
            {"name": "idx_location_name", "columns": ["name"]},
            {"name": "idx_location_is_active", "columns": ["is_active"]},
        ]
