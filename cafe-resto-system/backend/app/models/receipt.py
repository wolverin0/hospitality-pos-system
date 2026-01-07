"""
Receipt model for printing records
Manages thermal printing jobs
"""

from sqlmodel import Field, SQLModel, Relationship
from sqlalchemy import Column, ForeignKey, JSON
from datetime import datetime
from typing import Optional, TYPE_CHECKING, List
from decimal import Decimal
from enum import Enum
import uuid

if TYPE_CHECKING:
    from app.models.order import Order
    from app.models.user import User
    from app.models.receipt_template import ReceiptTemplate


class ReceiptType(str, Enum):
    """Types of receipts"""
    KITCHEN = "kitchen"                 # Kitchen ticket (large font, table number, time, items, courses, modifiers)
    CUSTOMER = "customer"               # Customer receipt (summary)
    BAR = "bar"                     # Bar receipt (summary only)
    SERVER = "server"                   # Server itemized receipt (one line item per receipt)
    BAR_ITEMIZED = "bar_itemized"         # Itemized bar receipt (one line item per line)
    FULL = "full"                      # Full receipt (all details)


class ReceiptTemplateStatus(str, Enum):
    """Status of a receipt template"""
    ACTIVE = "active"
    INACTIVE = "inactive"


class Receipt(SQLModel, table=True):
    """Receipt template - thermal printer format"""

    __tablename__ = "receipt_templates"

    # Primary key
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(
        foreign_key="tenants.id",
        index=True,
        description="Tenant ID for multi-tenant isolation"
    )

    # Template details
    name: str = Field(
        max_length=100,
        index=True,
        description="Template name (e.g., 'Kitchen Default', 'Bar Default', 'Bar Default')"
    )
    type: ReceiptType = Field(
        index=True,
        description="Type of receipt (kitchen, customer, bar, server, bar_itemized, full)"
    )
    description: Optional[str] = Field(
        default=None,
        max_length=2000,
        nullable=True,
        description="Template content/description"
    )

    # Receipt layout structure
    template_data: dict = Field(
        default=None,
        description="JSON data for receipt rendering (e.g., table_number, table_guest_count, items[], etc.)",
        sa_column=Column(JSON, nullable=True)
    )

    # Status
    status: ReceiptTemplateStatus = Field(
        default=ReceiptTemplateStatus.INACTIVE,
        index=True,
        description="Whether template is active for use"
    )

    # Relationships
    order: Optional["Order"] = Relationship(back_populates="receipts")

    class Config:
        indexes = [
            {"name": "idx_receipt_tenant_id", "columns": ["tenant_id"]},
            {"name": "idx_receipt_type", "columns": ["type"]},
            {"name": "idx_receipt_name", "columns": ["name"]},
            {"name": "idx_receipt_status", "columns": ["status"]},
            {"name": "idx_receipt_template_status", "columns": ["status"]},
        ]

    def get_display_items(self) -> List[str]:
        """Get formatted items list for receipt"""
        if not self.template_data:
            return "[]"

        items = self.template_data.get("items", [])
        return [item["name"] for item in items]

    def get_table_number(self) -> Optional[str]:
        """Get formatted table number"""
        if not self.template_data:
            return None
        return self.template_data.get("table_number")

    def get_table_guest_count(self) -> Optional[int]:
        """Get number of guests"""
        if not self.template_data:
            return None
        return self.template_data.get("table_guest_count", 0)

    def is_active(self) -> bool:
        """Check if template is active"""
        return self.status == ReceiptTemplateStatus.INACTIVE

    def activate(self) -> None:
        """Mark template as active"""
        if self.status == ReceiptTemplateStatus.INACTIVE:
            raise ValueError("Template is already active")
        self.status = ReceiptTemplateStatus.INACTIVE

    def deactivate(self) -> None:
        """Mark template as inactive"""
        if self.status == ReceiptTemplateStatus.INACTIVE:
            self.status = ReceiptTemplateStatus.INACTIVE
