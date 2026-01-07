"""
Payment model
Successful payment transactions with support for multiple methods
"""

from sqlmodel import Field, SQLModel, Relationship
from sqlalchemy import Column, ForeignKey, JSON, Numeric
from decimal import Decimal
from datetime import datetime
from typing import Optional, TYPE_CHECKING, List
from enum import Enum
import uuid

if TYPE_CHECKING:
    from app.models.order import Order
    from app.models.payment_intent import PaymentIntent
    from app.models.user import User
    from app.models.order_payment import OrderPayment


class PaymentMethod(str, Enum):
    """Payment methods supported by the system"""
    CASH = "cash"                       # Physical cash
    CARD = "card"                       # Credit/debit card
    TERMINAL = "terminal"                 # External terminal (Verifone, PagoFacil)
    QR = "qr"                            # QR code payment (Mercado Pago)
    SPLIT = "split"                     # Split payment (multiple methods)


class PaymentStatus(str, Enum):
    """Status of a payment"""
    PENDING = "pending"                   # Payment initiated, waiting to be processed
    PROCESSING = "processing"              # Being processed by terminal
    COMPLETED = "completed"              # Payment successfully captured
    FAILED = "failed"                    # Payment failed (declined, expired, etc.)
    REFUNDED = "refunded"              # Payment refunded


class Payment(SQLModel, table=True):
    """Successful payment transaction"""

    __tablename__ = "payments"

    # Primary key
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(
        foreign_key="tenants.id",
        index=True,
        description="Tenant ID for multi-tenant isolation"
    )

    # Order reference
    order_id: uuid.UUID = Field(
        foreign_key="orders.id",
        index=True,
        description="Order this payment belongs to"
    )
    payment_intent_id: uuid.UUID = Field(
        foreign_key="payment_intents.id",
        index=True,
        description="Payment intent this payment fulfills"
    )
    order_payment_id: Optional[uuid.UUID] = Field(
        default=None,
        foreign_key="order_payments.order_id",
        nullable=True,
        description="If part of split payment, reference to parent OrderPayment"
    )

    # Payment details
    method: PaymentMethod = Field(
        index=True,
        description="Payment method used (cash, card, terminal, qr, split)"
    )
    amount: Decimal = Field(
        description="Payment amount",
        sa_column=Column(Numeric(10, 2))
    )
    currency: Optional[str] = Field(
        default="USD",
        max_length=3,
        description="Currency code (default: USD)"
    )

    # Status
    status: PaymentStatus = Field(
        default=PaymentStatus.PENDING,
        index=True,
        description="Current status of payment"
    )

    # Status timestamps
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When payment record was created"
    )
    updated_at: Optional[datetime] = Field(
        default=None,
        nullable=True,
        description="When payment was last updated"
    )
    processed_at: Optional[datetime] = Field(
        default=None,
        nullable=True,
        description="When payment was successfully processed"
    )
    failed_at: Optional[datetime] = Field(
        default=None,
        nullable=True,
        description="When payment failed"
    )
    refunded_at: Optional[datetime] = Field(
        default=None,
        nullable=True,
        description="When payment was refunded"
    )

    # Card payment details
    card_last_4: Optional[str] = Field(
        max_length=4,
        nullable=True,
        description="Last 4 digits of card number"
    )
    card_holder_name: Optional[str] = Field(
        max_length=100,
        nullable=True,
        description="Cardholder name from card"
    )

    # Terminal payment details
    terminal_reference_id: Optional[str] = Field(
        max_length=50,
        nullable=True,
        description="Reference ID from terminal"
    )
    terminal_response: Optional[dict] = Field(
        default=None,
        description="Raw response from terminal",
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
        nullable=True,
        description="QR code provider (mercadopago, pix, etc.)"
    )

    # Payment processing fees (for terminal payments)
    processing_fee: Decimal = Field(
        default=Decimal("0.00"),
        description="Processing fee charged by terminal",
        sa_column=Column(Numeric(10, 2), nullable=True)
    )

    # Metadata for terminal responses
    payment_metadata: Optional[dict] = Field(
        default=None,
        description="Additional metadata from terminal",
        sa_column=Column(JSON, nullable=True)
    )

    # Reference to refund (immutable audit trail)
    refund_of_payment_id: Optional[uuid.UUID] = Field(
        default=None,
        foreign_key="payments.id",
        nullable=True,
        index=True,
        description="Reference to original payment if this is a refund"
    )

    # User who processed the payment
    processed_by_user_id: Optional[uuid.UUID] = Field(
        foreign_key="users.id",
        index=True,
        description="User who processed/confirmed the payment"
    )

    # Notes
    notes: Optional[str] = Field(
        max_length=500,
        nullable=True,
        description="Notes about this payment"
    )

    # Optimistic concurrency control
    version: int = Field(
        default=1,
        description="Version number for optimistic concurrency control"
    )

    # Relationships
    payment_intent: Optional["PaymentIntent"] = Relationship()
    order: Optional["Order"] = Relationship()
    order_payment: Optional["OrderPayment"] = Relationship(
        back_populates="payment"
    )

    class Config:
        indexes = [
            {"name": "idx_payment_tenant_id", "columns": ["tenant_id"]},
            {"name": "idx_payment_order_id", "columns": ["order_id"]},
            {"name": "idx_payment_method", "columns": ["method"]},
            {"name": "idx_payment_status", "columns": ["status"]},
            {"name": "idx_payment_created_at", "columns": ["created_at"]},
            {"name": "idx_payment_processed_at", "columns": ["processed_at"]},
        ]

    def is_successful(self) -> bool:
        """Check if payment was successful"""
        return self.status == PaymentStatus.COMPLETED

    def is_final_status(self) -> bool:
        """Check if payment is in a final state"""
        return self.status in [
            PaymentStatus.COMPLETED,
            PaymentStatus.FAILED,
            PaymentStatus.REFUNDED
        ]

    def calculate_total(self) -> None:
        """Calculate total amount including fees"""
        if self.processing_fee:
            return self.amount + self.processing_fee
        return self.amount
