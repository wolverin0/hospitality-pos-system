"""
CashDrawerEvent model for tracking all cash drawer activity during a shift
"""

from sqlmodel import Field, SQLModel, Relationship
from sqlalchemy import Column, ForeignKey, JSON, Numeric
from datetime import datetime
from typing import Optional, TYPE_CHECKING
from decimal import Decimal
from enum import Enum
import uuid

if TYPE_CHECKING:
    from app.models.shift import Shift
    from app.models.user import User
    from app.models.payment import Payment
    from app.models.order import Order


class CashDrawerEventType(str, Enum):
    """Types of cash drawer events"""
    OPENING_BALANCE = "opening_balance"     # Initial cash when shift starts
    CASH_DROP = "cash_drop"                # Removing excess cash from drawer
    TIP_PAYOUT = "tip_payout"               # Paying out tips to staff
    CASH_SHORTAGE = "cash_shortage"         # Recording shortage
    CASH_ADJUSTMENT = "cash_adjustment"     # Manual adjustment (with reason)
    PAYMENT_IN = "payment_in"               # Cash payment received
    CHANGE_OUT = "change_out"               # Change given to customer
    PETTY_CASH = "petty_cash"              # Petty cash withdrawal
    OTHER = "other"                         # Other event type


class CashDrawerEvent(SQLModel, table=True):
    """Event tracking all cash drawer activity during a shift"""

    __tablename__ = "cash_drawer_events"

    # Primary key
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(
        foreign_key="tenants.id",
        index=True,
        description="Tenant ID for multi-tenant isolation"
    )

    # Shift and location
    shift_id: uuid.UUID = Field(
        foreign_key="shifts.id",
        index=True,
        description="Shift this event belongs to"
    )
    location_id: uuid.UUID = Field(
        foreign_key="locations.id",
        index=True,
        description="Location where event occurred"
    )

    # Event details
    event_type: CashDrawerEventType = Field(
        index=True,
        description="Type of cash drawer event"
    )

    # Amounts
    amount: Decimal = Field(
        default=Decimal("0.00"),
        description="Amount affected by this event (positive = added, negative = removed)",
        sa_column=Column(Numeric(10, 2))
    )
    balance_after: Decimal = Field(
        default=Decimal("0.00"),
        description="Cash balance after this event",
        sa_column=Column(Numeric(12, 2))
    )

    # Payment references (for payment_in events)
    payment_id: Optional[uuid.UUID] = Field(
        default=None,
        nullable=True,
        foreign_key="payments.id",
        description="Payment reference (for payment_in events)"
    )
    order_id: Optional[uuid.UUID] = Field(
        default=None,
        nullable=True,
        foreign_key="orders.id",
        description="Order reference (for payment_in events)"
    )

    # Description and reason
    description: str = Field(
        max_length=500,
        description="Description of the event"
    )
    reason: Optional[str] = Field(
        default=None,
        max_length=500,
        nullable=True,
        description="Reason for the event (required for adjustments)"
    )

    # Who performed the action
    performed_by: uuid.UUID = Field(
        foreign_key="users.id",
        description="User who performed this event"
    )

    # Approval (for significant amounts or adjustments)
    approved_by: Optional[uuid.UUID] = Field(
        default=None,
        nullable=True,
        foreign_key="users.id",
        description="Manager who approved this event (for cash drops, adjustments)"
    )

    # Timestamps
    occurred_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When the event occurred"
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When the event was recorded in the system"
    )

    # Metadata
    event_metadata: Optional[dict] = Field(
        default=None,
        description="Additional event data (JSON)",
        sa_column=Column(JSON, nullable=True)
    )

    class Config:
        indexes = [
            {"name": "idx_cash_drawer_tenant_id", "columns": ["tenant_id"]},
            {"name": "idx_cash_drawer_shift_id", "columns": ["shift_id"]},
            {"name": "idx_cash_drawer_location_id", "columns": ["location_id"]},
            {"name": "idx_cash_drawer_event_type", "columns": ["event_type"]},
            {"name": "idx_cash_drawer_payment_id", "columns": ["payment_id"]},
            {"name": "idx_cash_drawer_order_id", "columns": ["order_id"]},
            {"name": "idx_cash_drawer_occurred_at", "columns": ["occurred_at"]},
            {"name": "idx_cash_drawer_performed_by", "columns": ["performed_by"]},
        ]

    # Relationships
    shift: Optional["Shift"] = Relationship(back_populates="cash_drawer_events")
    performed_by_user: Optional["User"] = Relationship(
        sa_relationship_kwargs={"foreign_keys": "CashDrawerEvent.performed_by"}
    )
    approved_by_user: Optional["User"] = Relationship(
        sa_relationship_kwargs={"foreign_keys": "CashDrawerEvent.approved_by"}
    )

    def __str__(self) -> str:
        return f"{self.event_type.value}: {self.amount} at {self.occurred_at}"

    def get_amount_signed(self) -> Decimal:
        """Get amount with sign based on event type"""
        # These events add cash (positive)
        if self.event_type in [
            CashDrawerEventType.OPENING_BALANCE,
            CashDrawerEventType.PAYMENT_IN,
        ]:
            return self.amount

        # These events remove cash (negative)
        if self.event_type in [
            CashDrawerEventType.CASH_DROP,
            CashDrawerEventType.TIP_PAYOUT,
            CashDrawerEventType.CASH_SHORTAGE,
            CashDrawerEventType.CHANGE_OUT,
            CashDrawerEventType.PETTY_CASH,
        ]:
            return -self.amount

        # Adjustments can be positive or negative (stored with sign)
        return self.amount

    def is_cash_in(self) -> bool:
        """Check if event adds cash to drawer"""
        return self.get_amount_signed() > 0

    def is_cash_out(self) -> bool:
        """Check if event removes cash from drawer"""
        return self.get_amount_signed() < 0

    def requires_approval(self) -> bool:
        """Check if event requires manager approval"""
        return self.event_type in [
            CashDrawerEventType.CASH_DROP,
            CashDrawerEventType.CASH_ADJUSTMENT,
            CashDrawerEventType.CASH_SHORTAGE,
        ]

    def is_approved(self) -> bool:
        """Check if event has required approval"""
        if not self.requires_approval():
            return True
        return self.approved_by is not None

    def get_description_with_context(self) -> str:
        """Get detailed description with context"""
        desc = f"{self.event_type.value.replace('_', ' ').title()}: ${abs(self.amount):.2f}"

        if self.event_type == CashDrawerEventType.PAYMENT_IN and self.payment_id:
            desc += f" (Payment: {self.payment_id})"
        elif self.event_type == CashDrawerEventType.CASH_DROP and self.reason:
            desc += f" - {self.reason}"
        elif self.event_type == CashDrawerEventType.CASH_ADJUSTMENT and self.reason:
            desc += f" - {self.reason}"
        elif self.event_type == CashDrawerEventType.TIP_PAYOUT:
            desc += " (Tip Payout)"

        return desc
