"""
Order model for confirmed sales orders
Immutable financial record created from confirmed DraftOrder
"""

from sqlmodel import Field, SQLModel, Relationship
from sqlalchemy import Column, ForeignKey
from datetime import datetime
from typing import Optional, TYPE_CHECKING, List
from decimal import Decimal
from enum import Enum
import uuid

if TYPE_CHECKING:
    from app.models.table_session import TableSession
    from app.models.user import User
    from app.models.order_line_item import OrderLineItem
    from app.models.refund import Refund
    from app.models.order_adjustment import OrderAdjustment
    from app.models.order_payment import OrderPayment


class OrderStatus(str, Enum):
    """Status of a confirmed order"""
    PENDING = "pending"               # Submitted, waiting to be processed
    IN_PROGRESS = "in_progress"      # Kitchen is preparing
    PARTIALLY_PAID = "partially_paid" # Partial payment received
    PAID = "paid"                  # Full payment completed
    COMPLETED = "completed"          # Items served, order closed
    CANCELLED = "cancelled"           # Order cancelled by staff
    VOIDED = "voided"              # Order voided by manager


class Order(SQLModel, table=True):
    """Confirmed order - immutable financial record"""

    __tablename__ = "orders"

    # Primary key
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(
        foreign_key="tenants.id",
        index=True,
        description="Tenant ID for multi-tenant isolation"
    )

    # Order linkage
    table_session_id: uuid.UUID = Field(
        foreign_key="table_sessions.id",
        index=True,
        description="Table session this order belongs to"
    )
    server_id: uuid.UUID = Field(
        foreign_key="users.id",
        index=True,
        description="Server who processed the order"
    )

    # Draft order reference (source)
    draft_order_id: uuid.UUID = Field(
        foreign_key="draft_orders.id",
        index=True,
        description="Draft order this order was created from"
    )

    # Order status
    status: OrderStatus = Field(
        default=OrderStatus.PENDING,
        index=True,
        description="Current status of the order"
    )

    # Status timestamps
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When order was created from draft"
    )
    updated_at: Optional[datetime] = Field(
        default=None,
        nullable=True,
        description="When order was last updated"
    )
    confirmed_at: Optional[datetime] = Field(
        default=None,
        nullable=True,
        description="When order was confirmed by server"
    )
    completed_at: Optional[datetime] = Field(
        default=None,
        nullable=True,
        description="When order was completed (all items served)"
    )
    cancelled_at: Optional[datetime] = Field(
        default=None,
        nullable=True,
        description="When order was cancelled"
    )

    # Financial amounts (immutable snapshots)
    subtotal: Decimal = Field(
        default=Decimal("0.00"),
        max_digits=10,
        decimal_places=2,
        description="Subtotal before tax"
    )
    tax_amount: Decimal = Field(
        default=Decimal("0.00"),
        max_digits=10,
        decimal_places=2,
        description="Total tax amount"
    )
    discount_amount: Decimal = Field(
        default=Decimal("0.00"),
        max_digits=10,
        decimal_places=2,
        description="Total discount applied"
    )
    service_charge: Decimal = Field(
        default=Decimal("0.00"),
        max_digits=10,
        decimal_places=2,
        description="Service charge (e.g., delivery fee)"
    )
    total_amount: Decimal = Field(
        default=Decimal("0.00"),
        max_digits=12,
        decimal_places=2,
        description="Final total amount (subtotal + tax + service_charge - discount)"
    )
    tip_amount: Decimal = Field(
        default=Decimal("0.00"),
        max_digits=10,
        decimal_places=2,
        description="Tip amount"
    )

    # Guest information (snapshot from draft)
    guest_count: Optional[int] = Field(
        default=None,
        nullable=True,
        description="Number of guests"
    )
    guest_names: Optional[str] = Field(
        default=None,
        max_length=500,
        nullable=True,
        description="Names of guests (comma separated)"
    )

    # Service information
    special_requests: Optional[str] = Field(
        default=None,
        max_length=2000,
        nullable=True,
        description="Special requests from guest"
    )
    order_notes: Optional[str] = Field(
        default=None,
        max_length=2000,
        nullable=True,
        description="Internal notes from server"
    )

    # Priority
    is_rush: bool = Field(
        default=False,
        index=True,
        description="Whether this is a rush order"
    )
    priority_level: Optional[int] = Field(
        default=None,
        nullable=True,
        description="Priority level (higher = more urgent)"
    )

    # Optimistic concurrency control
    version: int = Field(
        default=1,
        description="Version number for optimistic concurrency control"
    )

    # Relationships
    table_session: Optional["TableSession"] = Relationship(back_populates="orders")
    server: Optional["User"] = Relationship()
    line_items: List["OrderLineItem"] = Relationship(
        back_populates="order",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )
    payments: List["OrderPayment"] = Relationship(
        back_populates="order",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )
    refunds: List["Refund"] = Relationship(
        back_populates="order",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )
    adjustments: List["OrderAdjustment"] = Relationship(
        back_populates="order",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )

    class Config:
        indexes = [
            {"name": "idx_order_tenant_id", "columns": ["tenant_id"]},
            {"name": "idx_order_table_session_id", "columns": ["table_session_id"]},
            {"name": "idx_order_server_id", "columns": ["server_id"]},
            {"name": "idx_order_draft_order_id", "columns": ["draft_order_id"]},
            {"name": "idx_order_status", "columns": ["status"]},
            {"name": "idx_order_created_at", "columns": ["created_at"]},
            {"name": "idx_order_is_rush", "columns": ["is_rush"]},
            {"name": "idx_order_priority_level", "columns": ["priority_level"]},
            {"name": "idx_order_completed_at", "columns": ["completed_at"]},
        ]

    # State machine methods
    def can_transition_to(self, new_status: OrderStatus) -> tuple[bool, str]:
        """Check if order can transition to new status"""
        # Define valid transitions
        valid_transitions = {
            OrderStatus.PENDING: [
                OrderStatus.IN_PROGRESS,
                OrderStatus.CANCELLED
            ],
            OrderStatus.IN_PROGRESS: [
                OrderStatus.PAID,
                OrderStatus.COMPLETED,
                OrderStatus.CANCELLED
            ],
            OrderStatus.PAID: [
                OrderStatus.COMPLETED,
                OrderStatus.CANCELLED
            ],
            OrderStatus.COMPLETED: [],  # Final state, no transitions
            OrderStatus.CANCELLED: [],  # Final state, no transitions
            OrderStatus.VOIDED: [],     # Final state, no transitions
        }

        if new_status in valid_transitions.get(self.status, []):
            return True, "Can transition"
        return False, f"Cannot transition from {self.status.value} to {new_status.value}"

    def transition_to_pending(self) -> None:
        """Transition order to PENDING status"""
        if not self.can_transition_to(OrderStatus.PENDING):
            raise ValueError(f"Cannot transition to PENDING from {self.status.value}")
        self.status = OrderStatus.PENDING
        self.updated_at = datetime.utcnow()
        self.version += 1

    def transition_to_in_progress(self) -> None:
        """Transition order to IN_PROGRESS (kitchen working)"""
        if not self.can_transition_to(OrderStatus.IN_PROGRESS):
            raise ValueError(f"Cannot transition to IN_PROGRESS from {self.status.value}")
        self.status = OrderStatus.IN_PROGRESS
        self.updated_at = datetime.utcnow()
        self.version += 1

    def transition_to_paid(self) -> None:
        """Transition order to PAID status"""
        if not self.can_transition_to(OrderStatus.PAID):
            raise ValueError(f"Cannot transition to PAID from {self.status.value}")
        self.status = OrderStatus.PAID
        self.updated_at = datetime.utcnow()
        self.version += 1

    def transition_to_completed(self) -> None:
        """Transition order to COMPLETED status (all items served)"""
        if not self.can_transition_to(OrderStatus.COMPLETED):
            raise ValueError(f"Cannot transition to COMPLETED from {self.status.value}")
        self.status = OrderStatus.COMPLETED
        self.completed_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        self.version += 1

    def transition_to_cancelled(self, reason: str) -> None:
        """Cancel the order"""
        if not self.can_transition_to(OrderStatus.CANCELLED):
            raise ValueError(f"Cannot cancel order with status {self.status.value}")
        self.status = OrderStatus.CANCELLED
        self.cancelled_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        self.version += 1

    def is_editable(self) -> bool:
        """Check if order can be modified (only before completion)"""
        return self.status in [
            OrderStatus.PENDING,
            OrderStatus.IN_PROGRESS,
            OrderStatus.PAID
        ]

    def is_cancellable(self) -> bool:
        """Check if order can be cancelled"""
        return self.status in [
            OrderStatus.PENDING,
            OrderStatus.IN_PROGRESS,
            OrderStatus.PAID,
        ]

    def calculate_total(self) -> None:
        """Calculate total amount (subtotal + tax + service_charge - discount + tip)"""
        self.total_amount = (
            self.subtotal +
            self.tax_amount +
            self.service_charge -
            self.discount_amount +
            self.tip_amount
        )

    def get_amount_due(self) -> Decimal:
        """Get remaining amount to be paid"""
        return self.total_amount - Decimal("0.00")

    def add_payment(self, amount: Decimal) -> None:
        """Add payment to order (updates total)"""
        self.total_amount = self.total_amount + amount
        # Payment record will be created separately with OrderPayment
        self.calculate_total()

    def apply_discount(self, amount: Decimal) -> None:
        """Apply discount to order"""
        self.discount_amount = self.discount_amount + amount
        self.calculate_total()

    def add_tip(self, amount: Decimal) -> None:
        """Add tip to order"""
        self.tip_amount = self.tip_amount + amount
        self.calculate_total()
