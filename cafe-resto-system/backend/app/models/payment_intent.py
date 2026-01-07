"""
Payment Intent model
Tracks payment initiation events before successful payment
Captures "intent" before completion: what the customer/staff wanted to pay with
"""

from sqlmodel import Field, SQLModel, Relationship
from sqlalchemy import Column, ForeignKey, JSON, Numeric, Index
from datetime import datetime
from typing import Optional, TYPE_CHECKING, List
from decimal import Decimal
from enum import Enum
import uuid

if TYPE_CHECKING:
    from app.models.order import Order
    from app.models.user import User


class PaymentMethod(str, Enum):
    """Payment methods supported by the system"""
    CASH = "cash"                     # Physical cash payment
    CARD = "card"                     # Credit/debit card
    TERMINAL = "terminal"               # External payment terminal (e.g., Verifone, PagoFacil)
    QR = "qr"                        # QR code payment (e.g., Mercado Pago)
    SPLIT = "split"                   # Split payment (cash + card, multiple cards)


class PaymentIntentStatus(str, Enum):
    """Status of a payment intent"""
    PENDING = "pending"                  # Intent created, waiting to be processed
    IN_PROGRESS = "in_progress"        # Being processed (card terminal, etc.)
    COMPLETED = "completed"              # Successfully captured as payment
    CANCELLED = "cancelled"            # Payment intent cancelled
    FAILED = "failed"                  # Payment failed (e.g., card declined)


class PaymentIntent(SQLModel, table=True):
    """Payment intent - tracks payment initiation before successful payment"""

    __tablename__ = "payment_intents"

    # Primary key
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(
        foreign_key="tenants.id",
        index=True,
        description="Tenant ID for multi-tenant isolation"
    )
    order_id: uuid.UUID = Field(
        foreign_key="orders.id",
        index=True,
        description="Order this payment intent belongs to"
    )

    # Payment method details
    method: PaymentMethod = Field(
        index=True,
        description="Intended payment method (cash, card, terminal, qr)"
    )
    amount: Decimal = Field(
        max_digits=10,
        decimal_places=2,
        description="Payment amount"
    )
    currency: Optional[str] = Field(
        default="USD",
        max_length=3,
        description="Currency code (default: USD)"
    )

    # Intent status
    status: PaymentIntentStatus = Field(
        default=PaymentIntentStatus.PENDING,
        index=True,
        description="Current status of the payment intent"
    )

    # Who initiated
    initiated_by_user_id: uuid.UUID = Field(
        foreign_key="users.id",
        index=True,
        nullable=True,
        description="User who initiated this payment"
    )
    initiated_by: Optional["User"] = Relationship()

    # Timestamps
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When payment intent was created"
    )
    updated_at: Optional[datetime] = Field(
        default=None,
        nullable=True,
        description="When payment intent was last updated"
    )
    processed_at: Optional[datetime] = Field(
        default=None,
        nullable=True,
        description="When payment was processed (completed)"
    )
    cancelled_at: Optional[datetime] = Field(
        default=None,
        nullable=True,
        description="When payment intent was cancelled"
    )
    failed_at: Optional[datetime] = Field(
        default=None,
        nullable=True,
        description="When payment failed"
    )

    # Card payment details (for terminal)
    card_last_4: Optional[str] = Field(
        max_length=4,
        nullable=True,
        description="Last 4 digits of card number"
    )
    card_holder_name: Optional[str] = Field(
        max_length=100,
        nullable=True,
        description="Card holder name if known"
    )
    terminal_reference_id: Optional[str] = Field(
        max_length=50,
        nullable=True,
        description="Reference ID from external terminal"
    )
    terminal_response: Optional[dict] = Field(
        default=None,
        description="Raw response from external terminal",
        sa_column=Column(JSON, nullable=True)
    )

    # QR payment details
    qr_code: Optional[str] = Field(
        max_length=255,
        nullable=True,
        description="QR code used for payment"
    )
    qr_provider: Optional[str] = Field(
        default="mercadopago",
        max_length=50,
        description="QR code provider (mercadopago, pix, etc.)"
    )
    qr_expires_at: Optional[datetime] = Field(
        default=None,
        nullable=True,
        description="When QR code expires (TTL)"
    )

    # Idempotency for preventing duplicate payment attempts
    idempotency_key: Optional[str] = Field(
        default=None,
        max_length=255,
        nullable=True,
        index=True,
        description="Unique key to prevent duplicate payment intents"
    )

    # Tip amount (optional for QR payments)
    tip_amount: Decimal = Field(
        default=Decimal("0.00"),
        description="Tip amount (optional for QR payments)",
        sa_column=Column(Numeric(10, 2), nullable=True)
    )

    # Notes
    notes: Optional[str] = Field(
        max_length=500,
        nullable=True,
        description="Notes about this payment intent"
    )

    # Reason fields for cancellation/failure
    cancelled_reason: Optional[str] = Field(
        default=None,
        max_length=500,
        nullable=True,
        description="Reason why payment intent was cancelled"
    )
    failed_reason: Optional[str] = Field(
        default=None,
        max_length=500,
        nullable=True,
        description="Reason why payment intent failed"
    )

    # Version for optimistic concurrency
    version: int = Field(
        default=1,
        description="Version for optimistic concurrency control"
    )

    # Relationships
    order: Optional["Order"] = Relationship(back_populates="payment_intents")
    initiated_by_user: Optional["User"] = Relationship()

    class Config:
        indexes = [
            {"name": "idx_payment_intent_tenant_id", "columns": ["tenant_id"]},
            {"name": "idx_payment_intent_order_id", "columns": ["order_id"]},
            {"name": "idx_payment_intent_status", "columns": ["status"]},
            {"name": "idx_payment_intent_method", "columns": ["method"]},
            {"name": "idx_payment_intent_created_at", "columns": ["created_at"]},
            {"name": "idx_payment_intent_idempotency_key", "columns": ["idempotency_key"]},
        ]

    def can_transition_to(self, new_status: PaymentIntentStatus) -> tuple[bool, str]:
        """Check if payment intent can transition to new status"""
        valid_transitions = {
            PaymentIntentStatus.PENDING: [
                PaymentIntentStatus.IN_PROGRESS,
                PaymentIntentStatus.COMPLETED,
                PaymentIntentStatus.CANCELLED,
                PaymentIntentStatus.FAILED
            ],
            PaymentIntentStatus.IN_PROGRESS: [
                PaymentIntentStatus.COMPLETED,
                PaymentIntentStatus.CANCELLED,
                PaymentIntentStatus.FAILED
            ],
            PaymentIntentStatus.COMPLETED: [],
            PaymentIntentStatus.CANCELLED: [],
            PaymentIntentStatus.FAILED: [],
        }

        if new_status in valid_transitions.get(self.status, []):
            return True, "Can transition"
        return False, f"Cannot transition from {self.status.value} to {new_status.value}"

    def transition_to_in_progress(self) -> None:
        """Transition to in_progress (being processed)"""
        if not self.can_transition_to(PaymentIntentStatus.IN_PROGRESS):
            raise ValueError(f"Cannot transition to IN_PROGRESS from {self.status.value}")
        self.status = PaymentIntentStatus.IN_PROGRESS
        self.updated_at = datetime.utcnow()
        self.version += 1

    def transition_to_completed(self, processed_at: datetime) -> None:
        """Transition to completed (payment successfully captured)"""
        if not self.can_transition_to(PaymentIntentStatus.COMPLETED):
            raise ValueError(f"Cannot transition to COMPLETED from {self.status.value}")
        self.status = PaymentIntentStatus.COMPLETED
        self.processed_at = processed_at
        self.updated_at = datetime.utcnow()
        self.version += 1

    def transition_to_cancelled(self, reason: str) -> None:
        """Cancel the payment intent"""
        if not self.can_transition_to(PaymentIntentStatus.CANCELLED):
            raise ValueError(f"Cannot cancel payment intent with status {self.status.value}")
        self.status = PaymentIntentStatus.CANCELLED
        self.cancelled_at = datetime.utcnow()
        self.cancelled_reason = reason
        self.updated_at = datetime.utcnow()
        self.version += 1

    def transition_to_failed(self, reason: str) -> None:
        """Mark payment as failed"""
        if not self.can_transition_to(PaymentStatus.FAILED):
            raise ValueError(f"Cannot mark as failed with status {self.status.value}")
        self.status = PaymentIntentStatus.FAILED
        self.failed_at = datetime.utcnow()
        self.failed_reason = reason
        self.updated_at = datetime.utcnow()
        self.version += 1
