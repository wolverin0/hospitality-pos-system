"""
Ticket line item model for individual ticket items
"""

from sqlmodel import Field, SQLModel, Relationship
from sqlalchemy import Column, ForeignKey, JSON
from decimal import Decimal
from datetime import datetime
from typing import Optional, TYPE_CHECKING, Dict, Any
from enum import Enum
import uuid

if TYPE_CHECKING:
    from app.models.ticket import Ticket
    from app.models.menu_item import MenuItem


class FiredStatus(str, Enum):
    """Firing status of a ticket line item"""
    PENDING = "pending"           # Not yet fired to kitchen
    FIRED = "fired"               # Sent to kitchen
    HELD = "held"                 # Held by Expo, not sent
    VOIDED = "voided"             # Voided/cancelled
    COMPLETED = "completed"         # Item completed/served


class TicketLineItem(SQLModel, table=True):
    """Individual line item in a kitchen ticket"""

    __tablename__ = "ticket_line_items"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(
        foreign_key="tenants.id",
        index=True,
        description="Tenant ID for multi-tenant isolation"
    )
    ticket_id: uuid.UUID = Field(
        foreign_key="tickets.id",
        index=True,
        description="Ticket this item belongs to"
    )
    menu_item_id: uuid.UUID = Field(
        foreign_key="menu_items.id",
        index=True,
        description="Menu item being prepared"
    )

    # Item details (snapshot from menu)
    name: str = Field(max_length=255, description="Item name (snapshot from menu)")
    description: Optional[str] = Field(
        default=None,
        max_length=2000,
        description="Item description (snapshot from menu)"
    )

    # Quantity and pricing
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

    # Course assignment
    course_number: int = Field(
        default=0,
        index=True,
        description="Course number this item belongs to"
    )
    course_name: Optional[str] = Field(
        default=None,
        max_length=255,
        description="Course name for display"
    )

    # Firing status
    fired_status: FiredStatus = Field(
        default=FiredStatus.PENDING,
        index=True,
        description="Firing status of this item"
    )
    fired_at: Optional[datetime] = Field(
        default=None,
        description="When item was fired to kitchen"
    )
    held_at: Optional[datetime] = Field(
        default=None,
        description="When item was held by Expo"
    )
    held_reason: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Reason item is held"
    )
    voided_at: Optional[datetime] = Field(
        default=None,
        description="When item was voided"
    )
    voided_by: Optional[uuid.UUID] = Field(
        default=None,
        foreign_key="users.id",
        description="User who voided this item"
    )
    voided_reason: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Reason for voiding"
    )

    # Preparation tracking
    preparation_status: str = Field(
        default="pending",
        max_length=50,
        index=True,
        description="Preparation status: pending, started, completed"
    )
    preparation_started_at: Optional[datetime] = Field(
        default=None,
        description="When preparation started"
    )
    preparation_completed_at: Optional[datetime] = Field(
        default=None,
        description="When preparation completed"
    )

    # Special instructions and modifiers
    special_instructions: Optional[str] = Field(
        default=None,
        max_length=1000,
        description="Special instructions for this item"
    )
    modifiers: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Item modifiers (JSON): {'size': 'large', 'add_ons': ['cheese', 'bacon']}",
        sa_column=Column(JSON)
    )

    # Display order
    sort_order: int = Field(
        default=0,
        description="Display order within ticket"
    )

    # For modified items (e.g., "No onions" creates a child item)
    parent_line_item_id: Optional[uuid.UUID] = Field(
        foreign_key="ticket_line_items.id",
        index=True,
        nullable=True,
        description="Parent line item if this is a modification"
    )

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None

    # Optimistic concurrency
    version: int = Field(
        default=0,
        description="Optimistic concurrency version"
    )

    # Relationships
    ticket: Optional["Ticket"] = Relationship(back_populates="line_items")
    menu_item: Optional["MenuItem"] = Relationship()
    # Note: Self-referential relationships not defined here to avoid circular reference issues
    # Use queries with parent_line_item_id for modifications if needed

    class Config:
        indexes = [
            {"name": "idx_ticket_line_item_tenant_id", "columns": ["tenant_id"]},
            {"name": "idx_ticket_line_item_ticket_id", "columns": ["ticket_id"]},
            {"name": "idx_ticket_line_item_menu_item_id", "columns": ["menu_item_id"]},
            {"name": "idx_ticket_line_item_fired_status", "columns": ["fired_status"]},
            {"name": "idx_ticket_line_item_course_number", "columns": ["course_number"]},
            {"name": "idx_ticket_line_item_preparation_status", "columns": ["preparation_status"]},
            {"name": "idx_ticket_line_item_parent_line_item_id", "columns": ["parent_line_item_id"]},
            {"name": "idx_ticket_line_item_sort_order", "columns": ["sort_order"]},
        ]

    def calculate_line_total(self) -> Decimal:
        """Calculate line total based on quantity and price"""
        total = self.price_at_order * Decimal(self.quantity)
        self.line_total = total
        return total

    def is_modification(self) -> bool:
        """Check if this item is a modification of another item"""
        return self.parent_line_item_id is not None

    def has_modifications(self) -> bool:
        """Check if this item has modifications"""
        # This would require a query to check for child items
        # For now, just check if we have modifiers
        return self.modifiers is not None and len(self.modifiers) > 0

    def get_modifier_summary(self) -> str:
        """Get a human-readable summary of modifiers"""
        if not self.modifiers or "modifiers" not in self.modifiers:
            return ""

        summary_parts = []
        for mod in self.modifiers.get("modifiers", []):
            summary_parts.append(mod.get("value", ""))

        return ", ".join(summary_parts)
