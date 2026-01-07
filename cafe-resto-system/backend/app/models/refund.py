"""
Refund model for audit trail
Immutable financial record for refund transactions
"""

from sqlmodel import Field, SQLModel, Relationship
from sqlalchemy import Column, ForeignKey, Numeric
from datetime import datetime
from typing import Optional, TYPE_CHECKING, List
from decimal import Decimal
from enum import Enum
import uuid

if TYPE_CHECKING:
    from app.models.order import Order
    from app.models.payment import Payment
    from app.models.refund import Refund
    from app.models.user import User


class RefundReasonCode(str, Enum):
    """Standardized reason codes for refunds"""
    CUSTOMER_REQUEST = "customer_request"
    ITEM_DISSATISFACTION = "item_dissatisfaction"
    WRONG_ORDER = "wrong_order"
    DUPLICATE_PAYMENT = "duplicate_payment"
    MISTAKE = "mistake"
    INSUFFICIENT_FUNDS = "insufficient_funds"
    PRICE_DISCREPANCY = "price_discrepancy"
    SERVICE_CHARGE_ADJUSTMENT = "service_charge_adjustment"
    COMP_DISCOUNT = "comp_discount"
    SYSTEM_ERROR = "system_error"


class RefundStatus(str, Enum):
    """Status of a refund"""
    REQUESTED = "requested"            # Refund requested
    PROCESSING = "processing"           # Being processed
    COMPLETED = "completed"            # Refund completed
    FAILED = "failed"                  # Refund failed


class Refund(SQLModel, table=True):
    """Immutable refund record for audit trail"""

    __tablename__ = "refunds"

    # Primary key
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(
        foreign_key="tenants.id",
        index=True,
        description="Tenant ID for multi-tenant isolation"
    )

    # References
    original_payment_id: uuid.UUID = Field(
        foreign_key="payments.id",
        index=True,
        description="Original payment being refunded"
    )
    order_id: uuid.UUID = Field(
        foreign_key="orders.id",
        index=True,
        description="Order this refund belongs to"
    )

    # Refund details (immutable snapshots)
    amount: Decimal = Field(
        description="Refund amount (always positive)",
        sa_column=Column(Numeric(10, 2))
    )

    # Reason codes
    reason_code: RefundReasonCode = Field(
        index=True,
        description="Standardized reason code for reporting"
    )

    # Detailed reason (free text)
    reason: Optional[str] = Field(
        max_length=500,
        description="Detailed explanation for refund"
    )

    # Audit fields
    created_by: uuid.UUID = Field(
        foreign_key="users.id",
        index=True,
        description="User who processed refund"
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When refund record was created"
    )

    # Processing
    processed_by: uuid.UUID = Field(
        foreign_key="users.id",
        index=True,
        nullable=True,
        description="User who processed refund"
    )
    processed_at: Optional[datetime] = Field(
        default=None,
        nullable=True,
        description="When refund was processed"
    )

    # Refund status
    status: RefundStatus = Field(
        default=RefundStatus.REQUESTED,
        index=True,
        description="Current status of the refund"
    )

    # Version for optimistic concurrency
    version: int = Field(
        default=1,
        description="Version number for optimistic concurrency control"
    )

    # Relationships
    payment: Optional["Payment"] = Relationship()
    order: Optional["Order"] = Relationship()
    original_payment: Optional["Payment"] = Relationship()
    created_by_user: Optional["User"] = Relationship()

    class Config:
        indexes = [
            {"name": "idx_refund_tenant_id", "columns": ["tenant_id"]},
            {"name": "idx_refund_original_payment_id", "columns": ["original_payment_id"]},
            {"name": "idx_refund_order_id", "columns": ["order_id"]},
            {"name": "idx_refund_reason_code", "columns": ["reason_code"]},
            {"name": "idx_refund_created_by", "columns": ["created_by"]},
            {"name": "idx_refund_processed_by", "columns": ["processed_by"]},
            {"name": "idx_refund_amount", "columns": ["amount"]},
        ]

    def is_final_status(self) -> bool:
        """Check if refund is in a final state (processed or cancelled)"""
        return self.status in [
            RefundStatus.COMPLETED,
            RefundStatus.CANCELLED
        ]

    def is_processed(self) -> bool:
        """Check if refund has been processed"""
        return self.status == RefundStatus.COMPLETED and self.processed_at is not None

    def is_cancelled(self) -> bool:
        """Check if refund was cancelled"""
        return self.status == RefundStatus.CANCELLED

    def get_amount_display(self) -> str:
        """Get formatted amount for display"""
        return f"${self.amount:,.2f}"
