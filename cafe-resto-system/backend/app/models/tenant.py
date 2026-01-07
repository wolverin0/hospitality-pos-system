"""
Tenant model - Multi-tenancy foundation
"""

from sqlmodel import Field, SQLModel
from datetime import datetime
from typing import Optional
import uuid


class Tenant(SQLModel, table=True):
    """Tenant model for multi-tenant architecture"""
    
    __tablename__ = "tenants"
    
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str = Field(index=True)
    slug: str = Field(unique=True, index=True, description="Unique tenant identifier for subdomain routing")
    email: str = Field(index=True)
    phone: Optional[str] = None
    address: Optional[str] = None
    
    # Settings (JSON stored as text for simplicity, will use JSONB in production)
    settings: Optional[str] = None  # Feature flags, custom configuration
    
    # Plan
    plan: str = Field(default="basic", description="Subscription plan: basic, pro, enterprise")
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    is_active: bool = Field(default=True, index=True)
    
    class Config:
        indexes = [
            {"name": "idx_tenant_slug", "columns": ["slug"]},
            {"name": "idx_tenant_is_active", "columns": ["is_active"]},
        ]
