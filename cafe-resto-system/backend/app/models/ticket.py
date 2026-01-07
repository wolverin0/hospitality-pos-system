"""
Ticket model for KDS kitchen tickets
"""

from sqlmodel import Field, SQLModel, Relationship
from sqlalchemy import Column, ForeignKey
from datetime import datetime
from typing import Optional, TYPE_CHECKING
from enum import Enum
import uuid

if TYPE_CHECKING:
    from app.models.draft_order import DraftOrder
    from app.models.table_session import TableSession
    from app.models.menu_station import MenuStation
    from app.models.ticket_line_item import TicketLineItem
    from app.models.user import User


class TicketStatus(str, Enum):
    """Status of a kitchen ticket"""
    NEW = "new"                     # Just created, not yet visible to kitchen
    PENDING = "pending"             # Waiting to be fired/sent to kitchen
    PREPARING = "preparing"         # Kitchen is working on it
    READY = "ready"                 # Food is ready, waiting to be served
    IN_PROGRESS = "in_progress"      # Currently being prepared
    COMPLETED = "completed"          # Ticket completed, items served
    CANCELLED = "cancelled"         # Ticket cancelled before starting
    VOIDED = "voided"              # Ticket voided after being started


class Ticket(SQLModel, table=True):
    """Kitchen ticket for KDS display"""

    __tablename__ = "tickets"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(
        foreign_key="tenants.id",
        index=True,
        description="Tenant ID for multi-tenant isolation"
    )
    draft_order_id: uuid.UUID = Field(
        foreign_key="draft_orders.id",
        index=True,
        description="Draft order this ticket was created from"
    )
    table_session_id: uuid.UUID = Field(
        foreign_key="table_sessions.id",
        index=True,
        description="Table session this ticket belongs to"
    )
    station_id: uuid.UUID = Field(
        foreign_key="menu_stations.id",
        index=True,
        description="Kitchen station this ticket is for"
    )

    # Ticket status
    status: TicketStatus = Field(
        default=TicketStatus.NEW,
        index=True,
        description="Current status of the ticket"
    )

    # Course information
    course_number: int = Field(
        default=0,
        index=True,
        description="Course number (1, 2, 3, ...) for sequencing"
    )
    course_name: Optional[str] = Field(
        default=None,
        max_length=255,
        description="Course name (e.g., 'Drinks', 'Appetizers', 'Mains')"
    )

    # Ticket priority
    is_rush: bool = Field(
        default=False,
        index=True,
        description="Whether this is a rush/urgent ticket"
    )
    priority_level: Optional[int] = Field(
        default=None,
        description="Priority level (higher = more urgent)"
    )

    # Timing
    estimated_prep_time_minutes: Optional[int] = Field(
        default=None,
        description="Estimated preparation time in minutes"
    )
    prep_started_at: Optional[datetime] = Field(
        default=None,
        description="When preparation started"
    )
    ready_at: Optional[datetime] = Field(
        default=None,
        description="When ticket became ready"
    )
    completed_at: Optional[datetime] = Field(
        default=None,
        description="When ticket was completed"
    )

    # Display information
    table_number: Optional[str] = Field(
        default=None,
        max_length=50,
        description="Table number for display"
    )
    server_name: Optional[str] = Field(
        default=None,
        max_length=255,
        description="Server name who entered the order"
    )

    # Notes and instructions
    special_instructions: Optional[str] = Field(
        default=None,
        max_length=2000,
        description="Special instructions for this ticket"
    )

    # Expo mode fields
    is_held: bool = Field(
        default=False,
        index=True,
        description="Whether ticket is held by Expo (not sent to kitchen)"
    )
    held_reason: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Reason ticket is held"
    )
    held_at: Optional[datetime] = Field(
        default=None,
        description="When ticket was held"
    )

    # Printing
    print_count: int = Field(
        default=0,
        description="Number of times this ticket has been printed"
    )
    last_printed_at: Optional[datetime] = Field(
        default=None,
        description="When ticket was last printed"
    )

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    fired_at: Optional[datetime] = Field(
        default=None,
        description="When ticket was fired to kitchen"
    )
    voided_at: Optional[datetime] = Field(
        default=None,
        description="When ticket was voided"
    )
    voided_by: Optional[uuid.UUID] = Field(
        default=None,
        foreign_key="users.id",
        description="User who voided this ticket"
    )
    voided_reason: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Reason for voiding"
    )
    version: int = Field(
        default=0,
        description="Optimistic concurrency version"
    )

    # Relationships
    draft_order: Optional["DraftOrder"] = Relationship()
    table_session: Optional["TableSession"] = Relationship()
    station: Optional["MenuStation"] = Relationship()
    line_items: list["TicketLineItem"] = Relationship(back_populates="ticket")

    class Config:
        indexes = [
            {"name": "idx_ticket_tenant_id", "columns": ["tenant_id"]},
            {"name": "idx_ticket_draft_order_id", "columns": ["draft_order_id"]},
            {"name": "idx_ticket_table_session_id", "columns": ["table_session_id"]},
            {"name": "idx_ticket_station_id", "columns": ["station_id"]},
            {"name": "idx_ticket_status", "columns": ["status"]},
            {"name": "idx_ticket_course_number", "columns": ["course_number"]},
            {"name": "idx_ticket_is_rush", "columns": ["is_rush"]},
            {"name": "idx_ticket_is_held", "columns": ["is_held"]},
            {"name": "idx_ticket_created_at", "columns": ["created_at"]},
        ]
