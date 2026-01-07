"""
Shift model for tracking server work sessions and cash drawer management
"""

from sqlmodel import Field, SQLModel, Relationship
from sqlalchemy import Column, ForeignKey, Numeric
from datetime import datetime
from typing import Optional, TYPE_CHECKING, List
from decimal import Decimal
from enum import Enum
import uuid

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.location import Location
    from app.models.cash_drawer_event import CashDrawerEvent


class ShiftStatus(str, Enum):
    """Status of a server shift"""
    OPENING = "opening"           # Shift started, opening balance set
    ACTIVE = "active"             # Shift is ongoing, drawer in use
    CLOSING = "closing"           # Shift ending, counting cash
    CLOSED = "closed"             # Shift ended, final counts recorded
    RECONCILED = "reconciled"     # Cash counted and reconciled


class Shift(SQLModel, table=True):
    """Server shift - tracks work session and cash drawer activity"""

    __tablename__ = "shifts"

    # Primary key
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(
        foreign_key="tenants.id",
        index=True,
        description="Tenant ID for multi-tenant isolation"
    )

    # User and location
    server_id: uuid.UUID = Field(
        foreign_key="users.id",
        index=True,
        description="Server/employee working this shift"
    )
    location_id: uuid.UUID = Field(
        foreign_key="locations.id",
        index=True,
        description="Location where shift is happening"
    )

    # Shift status
    status: ShiftStatus = Field(
        default=ShiftStatus.OPENING,
        index=True,
        description="Current status of the shift"
    )

    # Timestamps
    opened_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When shift was opened"
    )
    closed_at: Optional[datetime] = Field(
        default=None,
        nullable=True,
        description="When shift was closed"
    )
    reconciled_at: Optional[datetime] = Field(
        default=None,
        nullable=True,
        description="When cash was reconciled"
    )

    # Opening balance
    opening_balance: Decimal = Field(
        default=Decimal("0.00"),
        description="Starting cash amount in drawer",
        sa_column=Column(Numeric(10, 2))
    )

    # Sales summary (calculated from transactions)
    cash_sales: Decimal = Field(
        default=Decimal("0.00"),
        description="Total cash sales during shift",
        sa_column=Column(Numeric(12, 2))
    )
    card_sales: Decimal = Field(
        default=Decimal("0.00"),
        description="Total card payments during shift",
        sa_column=Column(Numeric(12, 2))
    )
    tip_sales: Decimal = Field(
        default=Decimal("0.00"),
        description="Total tips received",
        sa_column=Column(Numeric(10, 2))
    )

    # Cash counts (from closing process)
    closing_cash_count: Optional[Decimal] = Field(
        default=None,
        description="Physical cash counted at close",
        sa_column=Column(Numeric(12, 2), nullable=True)
    )
    card_count: Optional[Decimal] = Field(
        default=None,
        description="Total card payments recorded",
        sa_column=Column(Numeric(12, 2), nullable=True)
    )

    # Reconciliation
    expected_cash: Optional[Decimal] = Field(
        default=None,
        description="Expected cash (opening + cash_sales - tips)",
        sa_column=Column(Numeric(12, 2), nullable=True)
    )
    cash_variance: Optional[Decimal] = Field(
        default=None,
        description="Cash difference (closing_cash_count - expected_cash)",
        sa_column=Column(Numeric(10, 2), nullable=True)
    )
    is_over: Optional[bool] = Field(
        default=None,
        nullable=True,
        description="True if cash is over, False if short, None if not reconciled"
    )

    # Breaks
    total_break_time_minutes: int = Field(
        default=0,
        description="Total break time in minutes"
    )
    break_count: int = Field(
        default=0,
        description="Number of breaks taken"
    )

    # Notes
    opening_notes: Optional[str] = Field(
        default=None,
        max_length=1000,
        nullable=True,
        description="Notes when opening shift"
    )
    closing_notes: Optional[str] = Field(
        default=None,
        max_length=1000,
        nullable=True,
        description="Notes when closing shift"
    )
    reconciliation_notes: Optional[str] = Field(
        default=None,
        max_length=1000,
        nullable=True,
        description="Notes during reconciliation"
    )

    # Audit
    opened_by: uuid.UUID = Field(
        foreign_key="users.id",
        description="User who opened the shift (could be manager)"
    )
    closed_by: Optional[uuid.UUID] = Field(
        default=None,
        nullable=True,
        foreign_key="users.id",
        description="User who closed the shift"
    )
    reconciled_by: Optional[uuid.UUID] = Field(
        default=None,
        nullable=True,
        foreign_key="users.id",
        description="User who reconciled the shift"
    )

    # Optimistic concurrency
    version: int = Field(
        default=1,
        description="Version number for optimistic concurrency control"
    )

    # Relationships
    server: Optional["User"] = Relationship(
        sa_relationship_kwargs={"foreign_keys": "Shift.server_id"},
        back_populates="shifts"
    )
    location: Optional["Location"] = Relationship(back_populates="shifts")
    opener: Optional["User"] = Relationship(
        sa_relationship_kwargs={"foreign_keys": "Shift.opened_by"},
        back_populates="opened_shifts"
    )
    closer: Optional["User"] = Relationship(
        sa_relationship_kwargs={"foreign_keys": "Shift.closed_by"},
        back_populates="closed_shifts"
    )
    reconciler: Optional["User"] = Relationship(
        sa_relationship_kwargs={"foreign_keys": "Shift.reconciled_by"},
        back_populates="reconciled_shifts"
    )
    cash_drawer_events: List["CashDrawerEvent"] = Relationship(
        back_populates="shift",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )

    class Config:
        indexes = [
            {"name": "idx_shift_tenant_id", "columns": ["tenant_id"]},
            {"name": "idx_shift_server_id", "columns": ["server_id"]},
            {"name": "idx_shift_location_id", "columns": ["location_id"]},
            {"name": "idx_shift_status", "columns": ["status"]},
            {"name": "idx_shift_opened_at", "columns": ["opened_at"]},
            {"name": "idx_shift_closed_at", "columns": ["closed_at"]},
            {"name": "idx_shift_opening_balance", "columns": ["opening_balance"]},
        ]

    # State machine methods
    def can_transition_to(self, new_status: ShiftStatus) -> tuple[bool, str]:
        """Check if shift can transition to new status"""
        valid_transitions = {
            ShiftStatus.OPENING: [ShiftStatus.ACTIVE, ShiftStatus.CLOSED],
            ShiftStatus.ACTIVE: [ShiftStatus.CLOSING, ShiftStatus.CLOSED],
            ShiftStatus.CLOSING: [ShiftStatus.CLOSED, ShiftStatus.RECONCILED],
            ShiftStatus.CLOSED: [ShiftStatus.RECONCILED],
            ShiftStatus.RECONCILED: [],  # Final state
        }

        if new_status in valid_transitions.get(self.status, []):
            return True, "Can transition"
        return False, f"Cannot transition from {self.status.value} to {new_status.value}"

    def start_shift(self, opening_balance: Decimal, opened_by_id: uuid.UUID) -> None:
        """Open the shift"""
        if self.status != ShiftStatus.OPENING:
            raise ValueError(f"Cannot start shift with status {self.status.value}")
        self.opening_balance = opening_balance
        self.opened_by = opened_by_id
        self.status = ShiftStatus.ACTIVE

    def end_shift(self, closed_by_id: uuid.UUID) -> None:
        """Close the shift"""
        if not self.can_transition_to(ShiftStatus.CLOSED)[0]:
            raise ValueError(f"Cannot close shift with status {self.status.value}")
        self.closed_at = datetime.utcnow()
        self.closed_by = closed_by_id
        self.status = ShiftStatus.CLOSED

    def begin_closing(self) -> None:
        """Start the closing process"""
        if not self.can_transition_to(ShiftStatus.CLOSING)[0]:
            raise ValueError(f"Cannot start closing with status {self.status.value}")
        self.status = ShiftStatus.CLOSING

    def record_cash_count(
        self,
        closing_cash_count: Decimal,
        card_count: Decimal
    ) -> None:
        """Record cash counts during closing"""
        if self.status not in [ShiftStatus.CLOSING, ShiftStatus.CLOSED]:
            raise ValueError("Must be in closing or closed state to record counts")

        self.closing_cash_count = closing_cash_count
        self.card_count = card_count

        # Calculate expected cash
        self.expected_cash = self.opening_balance + self.cash_sales
        self.cash_variance = self.closing_cash_count - self.expected_cash
        self.is_over = self.cash_variance > Decimal("0")

    def reconcile(self, reconciled_by_id: uuid.UUID) -> None:
        """Reconcile the shift"""
        if not self.can_transition_to(ShiftStatus.RECONCILED)[0]:
            raise ValueError(f"Cannot reconcile shift with status {self.status.value}")

        if self.closing_cash_count is None:
            raise ValueError("Cannot reconcile without cash count")

        self.reconciled_at = datetime.utcnow()
        self.reconciled_by = reconciled_by_id
        self.status = ShiftStatus.RECONCILED

    def is_active(self) -> bool:
        """Check if shift is active"""
        return self.status in [ShiftStatus.OPENING, ShiftStatus.ACTIVE]

    def is_closed(self) -> bool:
        """Check if shift is closed"""
        return self.status in [ShiftStatus.CLOSED, ShiftStatus.RECONCILED]

    def calculate_total_sales(self) -> Decimal:
        """Calculate total sales (cash + card)"""
        return self.cash_sales + self.card_sales

    def add_break_time(self, minutes: int) -> None:
        """Add break time"""
        if not self.is_active():
            raise ValueError("Cannot add break time to inactive shift")
        self.total_break_time_minutes += minutes
        self.break_count += 1

    def get_variance_description(self) -> str:
        """Get human-readable variance description"""
        if self.cash_variance is None:
            return "Not reconciled"
        if self.cash_variance == 0:
            return "Balanced"
        if self.cash_variance > 0:
            return f"Over by ${self.cash_variance:.2f}"
        return f"Short by ${abs(self.cash_variance):.2f}"

    def get_duration_hours(self) -> float:
        """Get shift duration in hours"""
        end_time = self.closed_at or datetime.utcnow()
        duration = end_time - self.opened_at
        total_seconds = duration.total_seconds() - (self.total_break_time_minutes * 60)
        return max(0, total_seconds / 3600)
