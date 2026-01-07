"""
Draft line item model for order items
"""

from sqlmodel import Field, SQLModel, Relationship
from sqlalchemy import Column, ForeignKey, JSON
from decimal import Decimal
from datetime import datetime
from typing import Optional, TYPE_CHECKING, Dict, Any
import uuid

if TYPE_CHECKING:
    from app.models.draft_order import DraftOrder
from sqlalchemy.orm import backref


class DraftLineItem(SQLModel, table=True):
    """Individual line item in a draft order"""

    __tablename__ = "draft_line_items"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(
        foreign_key="tenants.id",
        index=True,
        description="Tenant ID for multi-tenant isolation"
    )
    draft_order_id: uuid.UUID = Field(
        foreign_key="draft_orders.id",
        index=True,
        description="Draft order this item belongs to"
    )
    menu_item_id: uuid.UUID = Field(
        foreign_key="menu_items.id",
        index=True,
        description="Menu item being ordered"
    )

    # Item details
    name: str = Field(max_length=255, description="Item name (snapshot from menu)")
    quantity: int = Field(default=1, description="Quantity of this item")
    price_at_order: Decimal = Field(
        default=Decimal("0.00"),
        max_digits=10,
        decimal_places=2,
        description="Price at time of order (snapshot)"
    )
    line_total: Decimal = Field(
        default=Decimal("0.00"),
        max_digits=10,
        decimal_places=2,
        description="Line total (quantity * price_at_order)"
    )

    # Special instructions
    special_instructions: Optional[str] = Field(
        max_length=1000,
        nullable=True,
        description="Special instructions for this item"
    )

    # Modifiers (stored as JSON for flexibility)
    modifiers: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Item modifiers (JSON): {'size': 'large', 'add_ons': ['cheese', 'bacon']}",
        sa_column=Column(JSON)
    )

    # For modified items (e.g., "No onions" creates a child item)
    parent_line_item_id: Optional[uuid.UUID] = Field(
        foreign_key="draft_line_items.id",
        index=True,
        nullable=True,
        description="Parent line item if this is a modification"
    )

    # Display order
    sort_order: int = Field(
        default=0,
        description="Display order in draft"
    )

    # Timestamps
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Record creation timestamp"
    )
    updated_at: Optional[datetime] = Field(
        default=None,
        description="Last update timestamp"
    )

    # Relationships
    draft_order: Optional["DraftOrder"] = Relationship(back_populates="line_items")
    # Note: Self-referential relationships not defined here to avoid circular reference issues
    # Use queries with parent_line_item_id for modifications if needed

    class Config:
        indexes = [
            {"name": "idx_line_item_tenant_id", "columns": ["tenant_id"]},
            {"name": "idx_line_item_draft_order_id", "columns": ["draft_order_id"]},
            {"name": "idx_line_item_menu_item_id", "columns": ["menu_item_id"]},
            {"name": "idx_line_item_parent_line_item_id", "columns": ["parent_line_item_id"]},
            {"name": "idx_line_item_sort_order", "columns": ["sort_order"]},
        ]

    def calculate_line_total(self) -> Decimal:
        """Calculate line total based on quantity and price"""
        total = self.price_at_order * Decimal(self.quantity)
        self.line_total = total
        return total

    def add_modifier(self, modifier_type: str, value: Any, price_adjustment: Decimal = Decimal("0.00")) -> None:
        """Add a modifier to this line item"""
        if self.modifiers is None:
            self.modifiers = {}

        if "modifiers" not in self.modifiers:
            self.modifiers["modifiers"] = []

        self.modifiers["modifiers"].append({
            "type": modifier_type,
            "value": value,
            "price_adjustment": str(price_adjustment)
        })

        # Adjust price
        self.price_at_order += price_adjustment
        self.calculate_line_total()

    def get_modifier_summary(self) -> str:
        """Get a human-readable summary of modifiers"""
        if not self.modifiers or "modifiers" not in self.modifiers:
            return ""

        summary_parts = []
        for mod in self.modifiers.get("modifiers", []):
            summary_parts.append(mod.get("value", ""))

        return ", ".join(summary_parts)

    def is_modification(self) -> bool:
        """Check if this item is a modification of another item"""
        return self.parent_line_item_id is not None

    def has_modifications(self) -> bool:
        """Check if this item has modifications"""
        # This would require a query to check for child items
        # For now, just check if we have modifiers
        return self.modifiers is not None and len(self.modifiers) > 0
