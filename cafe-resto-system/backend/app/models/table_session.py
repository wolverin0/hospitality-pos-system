"""
Table session model for tracking dining sessions
"""

from sqlmodel import Field, SQLModel, Relationship
from sqlalchemy import Column, ForeignKey
from datetime import datetime
from typing import Optional, TYPE_CHECKING
from enum import Enum
import uuid

if TYPE_CHECKING:
    from app.models.table import Table
    from app.models.user import User
    from app.models.draft_order import DraftOrder


class TableSessionStatus(str, Enum):
    """Status of a table session"""
    SEATED = "seated"           # Guests just arrived
    ACTIVE = "active"           # Session in progress, orders placed
    PAYING = "paying"           # Payment in progress
    PAID = "paid"               # Payment completed
    CLOSED = "closed"           # Session completed


class TableSession(SQLModel, table=True):
    """Table session for tracking guest dining experience"""

    __tablename__ = "table_sessions"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(
        foreign_key="tenants.id",
        index=True,
        description="Tenant ID for multi-tenant isolation"
    )
    location_id: uuid.UUID = Field(
        foreign_key="locations.id",
        index=True,
        description="Location where session occurs"
    )
    table_id: uuid.UUID = Field(
        foreign_key="tables.id",
        index=True,
        description="Table being used for this session"
    )

    # Session details
    guest_count: int = Field(default=1, description="Number of guests at table")
    status: TableSessionStatus = Field(
        default=TableSessionStatus.SEATED,
        index=True,
        description="Current status of the session"
    )

    # Staff assignment
    server_id: Optional[uuid.UUID] = Field(
        foreign_key="users.id",
        index=True,
        nullable=True,
        description="Primary server/waiter assigned to this table"
    )

    # Notes
    notes: Optional[str] = Field(
        max_length=1000,
        nullable=True,
        description="Special notes about the session (allergies, preferences, etc.)"
    )

    # Timestamps
    seated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Time when guests were seated"
    )
    activated_at: Optional[datetime] = Field(
        default=None,
        description="Time when first order was placed"
    )
    paying_at: Optional[datetime] = Field(
        default=None,
        description="Time when payment was initiated"
    )
    paid_at: Optional[datetime] = Field(
        default=None,
        description="Time when payment was completed"
    )
    closed_at: Optional[datetime] = Field(
        default=None,
        description="Time when session was closed"
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Record creation timestamp"
    )
    updated_at: Optional[datetime] = Field(
        default=None,
        description="Last update timestamp"
    )

    # Relationships (defined with TYPE_CHECKING to avoid circular imports)
    table: Optional["Table"] = Relationship(back_populates="sessions")
    server: Optional["User"] = Relationship(back_populates="sessions")
    drafts: list["DraftOrder"] = Relationship(back_populates="table_session")

    class Config:
        indexes = [
            {"name": "idx_session_tenant_id", "columns": ["tenant_id"]},
            {"name": "idx_session_location_id", "columns": ["location_id"]},
            {"name": "idx_session_table_id", "columns": ["table_id"]},
            {"name": "idx_session_server_id", "columns": ["server_id"]},
            {"name": "idx_session_status", "columns": ["status"]},
            {"name": "idx_session_seated_at", "columns": ["seated_at"]},
            {"name": "idx_session_closed_at", "columns": ["closed_at"]},
        ]

    def can_add_order(self) -> bool:
        """Check if orders can be added to this session"""
        return self.status in [TableSessionStatus.SEATED, TableSessionStatus.ACTIVE]

    def can_start_payment(self) -> bool:
        """Check if payment can be started"""
        return self.status in [TableSessionStatus.SEATED, TableSessionStatus.ACTIVE]

    def can_complete_payment(self) -> bool:
        """Check if payment can be completed"""
        return self.status == TableSessionStatus.PAYING

    def can_close(self) -> bool:
        """Check if session can be closed"""
        return self.status == TableSessionStatus.PAID
