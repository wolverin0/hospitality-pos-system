"""
OrderAdjustment model for tracking comps, discounts, and other order adjustments
"""

from sqlmodel import Field, SQLModel, Relationship
from sqlalchemy import Column, ForeignKey, Numeric
from datetime import datetime
from typing import Optional, TYPE_CHECKING
from decimal import Decimal
from enum import Enum
import uuid

if TYPE_CHECKING:
    from app.models.order import Order
    from app.models.user import User


class AdjustmentType(str, Enum):
    """Types of order adjustments"""
    COMP = "comp"                       # Complimentary item (full discount)
    DISCOUNT_PERCENT = "discount_percent"  # Percentage discount
    DISCOUNT_AMOUNT = "discount_amount"    # Fixed amount discount
    PROMO_CODE = "promo_code"            # Promotional code discount
    CUSTOMER_REWARD = "customer_reward"   # Loyalty reward
    VOID = "void"                        # Voided item
    PRICE_OVERRIDE = "price_override"     # Manual price change
    SERVICE_ADJUSTMENT = "service_adjustment"  # Service fee adjustment
    TAX_ADJUSTMENT = "tax_adjustment"     # Tax exemption or adjustment
    OTHER = "other"                      # Other adjustment


class OrderAdjustment(SQLModel, table=True):
    """Adjustments to orders (comps, discounts, voids, price overrides)"""

    __tablename__ = "order_adjustments"

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
        description="Order this adjustment applies to"
    )
    order_line_item_id: Optional[uuid.UUID] = Field(
        default=None,
        nullable=True,
        foreign_key="order_line_items.id",
        index=True,
        description="Specific line item if adjustment applies to single item (null = entire order)"
    )

    # Adjustment details
    adjustment_type: AdjustmentType = Field(
        index=True,
        description="Type of adjustment"
    )

    # Amounts
    amount: Decimal = Field(
        default=Decimal("0.00"),
        description="Adjustment amount (positive for discounts, negative for additions)",
        sa_column=Column(Numeric(10, 2))
    )
    percentage: Optional[Decimal] = Field(
        default=None,
        description="Percentage discount (for discount_percent type)",
        sa_column=Column(Numeric(5, 2), nullable=True)
    )

    # Original values (for voids and overrides)
    original_amount: Optional[Decimal] = Field(
        default=None,
        description="Original amount before adjustment (for voids/overrides)",
        sa_column=Column(Numeric(10, 2), nullable=True)
    )
    new_amount: Optional[Decimal] = Field(
        default=None,
        description="New amount after adjustment (for voids/overrides)",
        sa_column=Column(Numeric(10, 2), nullable=True)
    )

    # Reason and authorization
    reason: str = Field(
        max_length=500,
        description="Reason for the adjustment"
    )
    notes: Optional[str] = Field(
        default=None,
        max_length=1000,
        nullable=True,
        description="Additional notes about the adjustment"
    )

    # Authorization
    authorized_by: uuid.UUID = Field(
        foreign_key="users.id",
        description="Manager who authorized the adjustment"
    )
    requires_manager_approval: bool = Field(
        default=True,
        description="Whether this adjustment type requires manager approval"
    )

    # Customer-facing info
    is_visible_to_customer: bool = Field(
        default=True,
        description="Whether this adjustment shows on customer receipt"
    )
    display_name: Optional[str] = Field(
        default=None,
        max_length=100,
        nullable=True,
        description="Display name on receipt (e.g., 'Happy Hour Discount')"
    )

    # Promo code details
    promo_code: Optional[str] = Field(
        default=None,
        max_length=50,
        nullable=True,
        description="Promo code used (for promo_code adjustments)"
    )

    # Timestamps
    applied_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When adjustment was applied"
    )

    # Audit
    applied_by: uuid.UUID = Field(
        foreign_key="users.id",
        description="User who applied the adjustment"
    )

    # Optimistic concurrency
    version: int = Field(
        default=1,
        description="Version number for optimistic concurrency control"
    )

    class Config:
        indexes = [
            {"name": "idx_adjustment_tenant_id", "columns": ["tenant_id"]},
            {"name": "idx_adjustment_order_id", "columns": ["order_id"]},
            {"name": "idx_adjustment_order_line_item_id", "columns": ["order_line_item_id"]},
            {"name": "idx_adjustment_type", "columns": ["adjustment_type"]},
            {"name": "idx_adjustment_applied_at", "columns": ["applied_at"]},
            {"name": "idx_adjustment_authorized_by", "columns": ["authorized_by"]},
            {"name": "idx_adjustment_promo_code", "columns": ["promo_code"]},
        ]

    # Relationships
    order: Optional["Order"] = Relationship(back_populates="adjustments")
    applied_by_user: Optional["User"] = Relationship(
        sa_relationship_kwargs={"foreign_keys": "OrderAdjustment.applied_by"}
    )
    authorized_by_user: Optional["User"] = Relationship(
        sa_relationship_kwargs={"foreign_keys": "OrderAdjustment.authorized_by"}
    )

    def is_discount(self) -> bool:
        """Check if adjustment is a discount (reduces total)"""
        return self.adjustment_type in [
            AdjustmentType.COMP,
            AdjustmentType.DISCOUNT_PERCENT,
            AdjustmentType.DISCOUNT_AMOUNT,
            AdjustmentType.PROMO_CODE,
            AdjustmentType.CUSTOMER_REWARD,
        ]

    def is_void(self) -> bool:
        """Check if adjustment is a void"""
        return self.adjustment_type == AdjustmentType.VOID

    def is_price_override(self) -> bool:
        """Check if adjustment is a price override"""
        return self.adjustment_type == AdjustmentType.PRICE_OVERRIDE

    def affects_total(self) -> Decimal:
        """Get the amount this adjustment affects the order total by"""
        if self.is_discount():
            return -self.amount  # Discounts reduce total
        return self.amount  # Other adjustments may add to total

    def get_description(self) -> str:
        """Get human-readable description"""
        if self.display_name:
            return self.display_name

        if self.adjustment_type == AdjustmentType.COMP:
            return "Complimentary"
        elif self.adjustment_type == AdjustmentType.DISCOUNT_PERCENT:
            return f"{self.percentage}% Discount"
        elif self.adjustment_type == AdjustmentType.DISCOUNT_AMOUNT:
            return f"${self.amount:.2f} Discount"
        elif self.adjustment_type == AdjustmentType.PROMO_CODE:
            return f"Promo: {self.promo_code or 'Discount'}"
        elif self.adjustment_type == AdjustmentType.VOID:
            return "Void"
        elif self.adjustment_type == AdjustmentType.PRICE_OVERRIDE:
            return "Price Override"
        elif self.adjustment_type == AdjustmentType.CUSTOMER_REWARD:
            return "Loyalty Reward"

        return self.adjustment_type.value.replace('_', ' ').title()

    def is_applied_to_item(self) -> bool:
        """Check if adjustment applies to specific line item"""
        return self.order_line_item_id is not None

    def is_applied_to_order(self) -> bool:
        """Check if adjustment applies to entire order"""
        return self.order_line_item_id is None
