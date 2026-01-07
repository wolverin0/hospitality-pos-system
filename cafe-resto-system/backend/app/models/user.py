"""
User model with roles and tenant scoping
"""

from sqlmodel import Field, SQLModel, Relationship
from sqlalchemy import Column, ForeignKey, Enum as SQLEnum, JSON
from datetime import datetime
from typing import Optional, List, TYPE_CHECKING
import uuid
from enum import Enum

if TYPE_CHECKING:
    from app.models.table_session import TableSession
    from app.models.draft_order import DraftOrder
    from app.models.shift import Shift
    from app.models.cash_drawer_event import CashDrawerEvent
    from app.models.order_adjustment import OrderAdjustment


class UserRole(str, Enum):
    """User roles for RBAC"""
    ADMIN = "admin"
    MANAGER = "manager"
    WAITER = "waiter"
    CASHIER = "cashier"
    KITCHEN = "kitchen"
    EXPO = "expo"


class User(SQLModel, table=True):
    """User model with tenant isolation"""
    
    __tablename__ = "users"
    
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(foreign_key="tenants.id", index=True, description="Tenant ID for multi-tenant isolation")
    
    # Authentication
    email: str = Field(index=True, nullable=False, max_length=255)
    password_hash: str = Field(nullable=False)
    
    # Profile
    first_name: str = Field(nullable=False, max_length=100)
    last_name: str = Field(nullable=False, max_length=100)
    phone: Optional[str] = Field(max_length=50, nullable=True)
    
    # RBAC
    role: UserRole = Field(default=UserRole.WAITER, nullable=False)
    
    # Location assignments (stored as JSONB in PostgreSQL)
    location_ids: Optional[List[str]] = Field(default_factory=list, description="IDs of locations user can access", sa_column=Column(JSON))
    section_ids: Optional[List[str]] = Field(default_factory=list, description="IDs of sections waiter is assigned to", sa_column=Column(JSON))
    
    # Status
    is_active: bool = Field(default=True, index=True)
    email_verified: bool = Field(default=False)
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    last_login_at: Optional[datetime] = None

    # Relationships
    sessions: list["TableSession"] = Relationship(back_populates="server")
    locked_drafts: list["DraftOrder"] = Relationship(
        back_populates="locked_by_user",
        sa_relationship_kwargs={"foreign_keys": "DraftOrder.locked_by"}
    )
    confirmed_drafts: list["DraftOrder"] = Relationship(
        back_populates="confirmed_by_user",
        sa_relationship_kwargs={"foreign_keys": "DraftOrder.confirmed_by"}
    )
    rejected_drafts: list["DraftOrder"] = Relationship(
        back_populates="rejected_by_user",
        sa_relationship_kwargs={"foreign_keys": "DraftOrder.rejected_by"}
    )
    shifts: list["Shift"] = Relationship(
        back_populates="server",
        sa_relationship_kwargs={"foreign_keys": "Shift.server_id"}
    )
    opened_shifts: list["Shift"] = Relationship(
        back_populates="opener",
        sa_relationship_kwargs={"foreign_keys": "Shift.opened_by"}
    )
    closed_shifts: list["Shift"] = Relationship(
        back_populates="closer",
        sa_relationship_kwargs={"foreign_keys": "Shift.closed_by"}
    )
    reconciled_shifts: list["Shift"] = Relationship(
        back_populates="reconciler",
        sa_relationship_kwargs={"foreign_keys": "Shift.reconciled_by"}
    )
    performed_cash_events: list["CashDrawerEvent"] = Relationship(
        back_populates="performed_by",
        sa_relationship_kwargs={"foreign_keys": "CashDrawerEvent.performed_by"}
    )
    approved_cash_events: list["CashDrawerEvent"] = Relationship(
        back_populates="approved_by",
        sa_relationship_kwargs={"foreign_keys": "CashDrawerEvent.approved_by"}
    )
    applied_adjustments: list["OrderAdjustment"] = Relationship(
        back_populates="applied_by",
        sa_relationship_kwargs={"foreign_keys": "OrderAdjustment.applied_by"}
    )
    authorized_adjustments: list["OrderAdjustment"] = Relationship(
        back_populates="authorized_by",
        sa_relationship_kwargs={"foreign_keys": "OrderAdjustment.authorized_by"}
    )
    
    class Config:
        indexes = [
            {"name": "idx_user_tenant_id", "columns": ["tenant_id"]},
            {"name": "idx_user_email", "columns": ["email"]},
            {"name": "idx_user_role", "columns": ["role"]},
            {"name": "idx_user_is_active", "columns": ["is_active"]},
        ]
