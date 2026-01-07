"""
OrderPayment join table for 1:N Order:Payment relationship
"""

from sqlmodel import Field, SQLModel, Relationship
from sqlalchemy import Column, ForeignKey
from datetime import datetime
from typing import Optional, TYPE_CHECKING
from decimal import Decimal
import uuid

if TYPE_CHECKING:
    from app.models.order import Order
    from app.models.payment import Payment


class OrderPayment(SQLModel, table=True):
    """Join table linking Orders to Payments (1:N relationship)"""

    __tablename__ = "order_payments"

    # Composite primary key
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    order_id: uuid.UUID = Field(
        foreign_key="orders.id",
        index=True,
        description="Order that this payment is for"
    )
    payment_id: uuid.UUID = Field(
        foreign_key="payments.id",
        index=True,
        unique=True,  # Each payment belongs to only one order
        description="Payment for this order"
    )

    # Allocation amount (in case of split payments)
    allocated_amount: Decimal = Field(
        default=Decimal("0.00"),
        max_digits=10,
        decimal_places=2,
        description="Amount of this payment allocated to the order"
    )

    # Timestamps
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When this linkage was created"
    )

    class Config:
        indexes = [
            {"name": "idx_order_payment_order_id", "columns": ["order_id"]},
            {"name": "idx_order_payment_payment_id", "columns": ["payment_id"]},
        ]

    # Relationships
    order: Optional["Order"] = Relationship(
        sa_relationship_kwargs={
            "foreign_keys": "OrderPayment.order_id",
            "back_populates": "payments"
        }
    )
    payment: Optional["Payment"] = Relationship(
        sa_relationship_kwargs={
            "foreign_keys": "OrderPayment.payment_id",
            "back_populates": "order_payment"
        }
    )
