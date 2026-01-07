"""
Order Line Item model
Individual items in a confirmed order with price snapshots
"""

from sqlmodel import Field, SQLModel, Relationship
from sqlalchemy import Column, ForeignKey, JSON
from decimal import Decimal
from datetime import datetime
from typing import Optional, TYPE_CHECKING, List
from enum import Enum
import uuid

if TYPE_CHECKING:
    from app.models.order import Order
    from app.models.menu_item import MenuItem


class PreparationStatus(str, Enum):
    """Preparation status of an order line item"""
    PENDING = "pending"             # Not started yet
    IN_PROGRESS = "in_progress"      # Kitchen is working on it
    COMPLETED = "completed"           # Ready to serve
    CANCELLED = "cancelled"         # Item cancelled/voided


class OrderLineItem(SQLModel, table=True):
    """Individual line item in a confirmed order"""

    __tablename__ = "order_line_items"

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
        description="Order this item belongs to"
    )
    menu_item_id: uuid.UUID = Field(
        foreign_key="menu_items.id",
        index=True,
        description="Menu item this line item represents"
    )

    # Item details (snapshot from menu at time of order)
    name: str = Field(
        max_length=255,
        description="Item name (snapshot from menu)"
    )
    description: Optional[str] = Field(
        default=None,
        max_length=2000,
        description="Item description (snapshot from menu)"
    )

    # Quantity and pricing (snapshot from menu)
    quantity: int = Field(
        default=1,
        description="Quantity ordered"
    )
    unit_price: Decimal = Field(
        default=Decimal("0.00"),
        max_digits=10,
        decimal_places=2,
        description="Unit price at time of order (snapshot)"
    )
    price_at_order: Decimal = Field(
        default=Decimal("0.00"),
        max_digits=10,
        decimal_places=2,
        description="Line item total at time of order (quantity * unit_price)"
    )

    # Course information
    course_number: int = Field(
        default=0,
        index=True,
        description="Course number (1, 2, 3...)"
    )
    course_name: Optional[str] = Field(
        default=None,
        max_length=255,
        description="Course name (Drinks, Apps, Mains, etc.)"
    )

    # Preparation status and timing
    preparation_status: PreparationStatus = Field(
        default=PreparationStatus.PENDING,
        index=True,
        description="Current preparation status"
    )
    preparation_started_at: Optional[datetime] = Field(
        default=None,
        nullable=True,
        description="When preparation started"
    )
    preparation_completed_at: Optional[datetime] = Field(
        default=None,
        nullable=True,
        description="When item was completed/served"
    )

    # Special instructions and modifiers
    special_instructions: Optional[str] = Field(
        default=None,
        max_length=1000,
        nullable=True,
        description="Special instructions for this item"
    )
    modifiers: Optional[dict] = Field(
        default=None,
        description="Item modifiers (JSON): {'size': 'large', 'add_ons': ['cheese', 'bacon']}",
        sa_column=Column(JSON)
    )

    # Sorting for display
    sort_order: int = Field(
        default=0,
        description="Display order in ticket"
    )

    # Parent item for modifications (e.g., "No onions" creates child item)
    parent_line_item_id: Optional[uuid.UUID] = Field(
        default=None,
        foreign_key="order_line_items.id",
        index=True,
        nullable=True,
        description="Parent line item if this is a modification"
    )
    child_items: List["OrderLineItem"] = Relationship(
        back_populates="order",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )

    # Relationships
    order: Optional["Order"] = Relationship(back_populates="line_items")
    menu_item: Optional["MenuItem"] = Relationship()

    class Config:
        indexes = [
            {"name": "idx_line_item_tenant_id", "columns": ["tenant_id"]},
            {"name": "idx_line_item_order_id", "columns": ["order_id"]},
            {"name": "idx_line_item_menu_item_id", "columns": ["menu_item_id"]},
            {"name": "idx_line_item_preparation_status", "columns": ["preparation_status"]},
            {"name": "idx_line_item_course_number", "columns": ["course_number"]},
            {"name": "idx_line_item_sort_order", "columns": ["sort_order"]},
            {"name": "idx_line_item_parent_id", "columns": ["parent_line_item_id"]},
        ]

    def calculate_line_total(self) -> None:
        """Calculate line total based on quantity and price"""
        self.line_total = self.quantity * self.unit_price

    def add_modifier(self, modifier_type: str, value: object, price_adjustment: Decimal = Decimal("0.00")) -> None:
        """Add a modifier to this item"""
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
        if price_adjustment != 0:
            self.unit_price += price_adjustment
            self.line_total = self.quantity * self.unit_price

    def get_modifier_summary(self) -> str:
        """Get a human-readable summary of modifiers"""
        if not self.modifiers or "modifiers" not in self.modifiers:
            return ""
        
        summary_parts = []
        for mod in self.modifiers.get("modifiers", []):
            summary_parts.append(f"{mod.get('value', '')}")
        
        return ", ".join(summary_parts)

    def is_modification(self) -> bool:
        """Check if this item is a modification of another"""
        return self.parent_line_item_id is not None

    def has_modifiers(self) -> bool:
        """Check if this item has modifiers"""
        return self.modifiers is not None and len(self.modifiers.get("modifiers", [])) > 0
