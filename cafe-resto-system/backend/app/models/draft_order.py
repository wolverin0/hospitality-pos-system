"""
Draft order model with state machine for guest ordering
"""

from sqlmodel import Field, SQLModel, Relationship
from sqlalchemy import Column, ForeignKey
from datetime import datetime, timedelta
from typing import Optional, TYPE_CHECKING
from enum import Enum
import uuid

if TYPE_CHECKING:
    from app.models.table_session import TableSession
    from app.models.user import User
    from app.models.draft_line_item import DraftLineItem


class DraftStatus(str, Enum):
    """Status of a draft order"""
    DRAFT = "draft"                 # Guest is still editing
    PENDING = "pending"             # Submitted, waiting for waiter
    CONFIRMED = "confirmed"         # Accepted by waiter, converted to order
    REJECTED = "rejected"           # Rejected by waiter
    EXPIRED = "expired"             # TTL expired


class DraftOrder(SQLModel, table=True):
    """Draft order for guest self-service ordering"""

    __tablename__ = "draft_orders"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    tenant_id: uuid.UUID = Field(
        foreign_key="tenants.id",
        index=True,
        description="Tenant ID for multi-tenant isolation"
    )
    table_session_id: uuid.UUID = Field(
        foreign_key="table_sessions.id",
        index=True,
        description="Table session this draft belongs to"
    )

    # Draft status
    status: DraftStatus = Field(
        default=DraftStatus.DRAFT,
        index=True,
        description="Current status of the draft"
    )

    # Optimistic concurrency control
    version: int = Field(
        default=1,
        index=False,
        description="Version number for optimistic concurrency control"
    )

    # Draft lock mechanism
    locked_by: Optional[uuid.UUID] = Field(
        foreign_key="users.id",
        index=True,
        nullable=True,
        description="User ID who has locked this draft"
    )
    locked_at: Optional[datetime] = Field(
        default=None,
        nullable=True,
        description="Timestamp when draft was locked"
    )

    # Rejection details
    rejection_reason: Optional[str] = Field(
        max_length=1000,
        nullable=True,
        description="Reason for rejection (if rejected)"
    )
    rejected_by: Optional[uuid.UUID] = Field(
        foreign_key="users.id",
        index=True,
        nullable=True,
        description="User ID who rejected the draft"
    )
    rejected_at: Optional[datetime] = Field(
        default=None,
        nullable=True,
        description="Timestamp when draft was rejected"
    )

    # Confirmation details
    confirmed_by: Optional[uuid.UUID] = Field(
        foreign_key="users.id",
        index=True,
        nullable=True,
        description="User ID who confirmed the draft"
    )
    confirmed_at: Optional[datetime] = Field(
        default=None,
        nullable=True,
        description="Timestamp when draft was confirmed"
    )
    order_id: Optional[uuid.UUID] = Field(
        default=None,
        nullable=True,
        description="Order ID created from this draft (if confirmed)"
    )

    # TTL fields
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Draft creation timestamp"
    )
    updated_at: Optional[datetime] = Field(
        default=None,
        nullable=True,
        description="Last update timestamp"
    )
    expires_at: datetime = Field(
        default_factory=lambda: datetime.utcnow() + timedelta(hours=2),
        index=True,
        description="Draft expiration timestamp (default 2 hours)"
    )

    # Additional notes
    special_requests: Optional[str] = Field(
        max_length=2000,
        nullable=True,
        description="Special requests from guest for entire order"
    )

    # Relationships
    table_session: Optional["TableSession"] = Relationship(back_populates="drafts")
    line_items: list["DraftLineItem"] = Relationship(back_populates="draft_order")
    locked_by_user: Optional["User"] = Relationship(
        sa_relationship_kwargs={
            "foreign_keys": "DraftOrder.locked_by",
            "lazy": "select"
        }
    )
    confirmed_by_user: Optional["User"] = Relationship(
        sa_relationship_kwargs={
            "foreign_keys": "DraftOrder.confirmed_by",
            "lazy": "select"
        }
    )
    rejected_by_user: Optional["User"] = Relationship(
        sa_relationship_kwargs={
            "foreign_keys": "DraftOrder.rejected_by",
            "lazy": "select"
        }
    )

    class Config:
        indexes = [
            {"name": "idx_draft_tenant_id", "columns": ["tenant_id"]},
            {"name": "idx_draft_table_session_id", "columns": ["table_session_id"]},
            {"name": "idx_draft_status", "columns": ["status"]},
            {"name": "idx_draft_locked_by", "columns": ["locked_by"]},
            {"name": "idx_draft_expires_at", "columns": ["expires_at"]},
            {"name": "idx_draft_created_at", "columns": ["created_at"]},
            {"name": "idx_draft_version", "columns": ["version"]},
        ]

    # State machine methods
    def can_submit(self) -> bool:
        """Check if draft can be submitted by guest"""
        return self.status == DraftStatus.DRAFT

    def can_modify(self) -> bool:
        """Check if draft can be modified by guest"""
        return self.status == DraftStatus.DRAFT

    def can_acquire_lock(self, user_id: uuid.UUID) -> tuple[bool, str]:
        """Check if draft lock can be acquired by waiter"""
        # Draft must be pending
        if self.status != DraftStatus.PENDING:
            return False, "Draft is not in pending status"

        # Already locked?
        if self.locked_by is not None:
            # Check if lock is expired (30 minutes)
            if self.locked_at and (datetime.utcnow() - self.locked_at).total_seconds() > 1800:
                return True, "Lock expired, can acquire"
            # Locked by same user?
            if self.locked_by == user_id:
                return True, "Already locked by this user"
            # Locked by different user
            return False, "Draft is already locked by another user"

        return True, "Can acquire lock"

    def can_confirm(self, user_id: uuid.UUID) -> tuple[bool, str]:
        """Check if draft can be confirmed by waiter"""
        # Must be locked by this user
        if self.locked_by != user_id:
            return False, "Draft is not locked by this user"

        # Must be pending status
        if self.status != DraftStatus.PENDING:
            return False, "Draft is not in pending status"

        return True, "Can confirm draft"

    def can_reject(self, user_id: uuid.UUID) -> tuple[bool, str]:
        """Check if draft can be rejected by waiter"""
        # Must be locked by this user
        if self.locked_by != user_id:
            return False, "Draft is not locked by this user"

        # Must be pending status
        if self.status != DraftStatus.PENDING:
            return False, "Draft is not in pending status"

        return True, "Can reject draft"

    def can_expire(self) -> bool:
        """Check if draft can be expired"""
        # Only pending drafts can expire
        if self.status != DraftStatus.PENDING:
            return False

        # Check if expired
        return datetime.utcnow() > self.expires_at

    def transition_to_pending(self) -> None:
        """Transition draft to pending status (guest submits)"""
        if not self.can_submit():
            raise ValueError("Cannot transition to pending: draft is not in DRAFT status")

        self.status = DraftStatus.PENDING
        self.updated_at = datetime.utcnow()
        self.version += 1

    def transition_to_confirmed(self, user_id: uuid.UUID, order_id: uuid.UUID) -> None:
        """Transition draft to confirmed status (waiter accepts)"""
        can_confirm, reason = self.can_confirm(user_id)
        if not can_confirm:
            raise ValueError(f"Cannot confirm draft: {reason}")

        self.status = DraftStatus.CONFIRMED
        self.confirmed_by = user_id
        self.confirmed_at = datetime.utcnow()
        self.order_id = order_id
        self.locked_by = None  # Release lock
        self.locked_at = None
        self.updated_at = datetime.utcnow()
        self.version += 1

    def transition_to_rejected(self, user_id: uuid.UUID, reason: str) -> None:
        """Transition draft to rejected status (waiter rejects)"""
        can_reject, error = self.can_reject(user_id)
        if not can_reject:
            raise ValueError(f"Cannot reject draft: {error}")

        self.status = DraftStatus.REJECTED
        self.rejected_by = user_id
        self.rejected_at = datetime.utcnow()
        self.rejection_reason = reason
        self.locked_by = None  # Release lock
        self.locked_at = None
        self.updated_at = datetime.utcnow()
        self.version += 1

    def transition_to_expired(self) -> None:
        """Transition draft to expired status (TTL reached)"""
        if not self.can_expire():
            raise ValueError("Cannot expire draft: not in PENDING status or not expired")

        self.status = DraftStatus.EXPIRED
        self.locked_by = None  # Release lock
        self.locked_at = None
        self.updated_at = datetime.utcnow()
        self.version += 1

    def acquire_lock(self, user_id: uuid.UUID) -> None:
        """Acquire lock on draft"""
        can_lock, reason = self.can_acquire_lock(user_id)
        if not can_lock:
            raise ValueError(f"Cannot acquire lock: {reason}")

        self.locked_by = user_id
        self.locked_at = datetime.utcnow()
        self.version += 1

    def release_lock(self, user_id: uuid.UUID) -> None:
        """Release lock on draft"""
        if self.locked_by != user_id:
            raise ValueError("Cannot release lock: draft is not locked by this user")

        self.locked_by = None
        self.locked_at = None
        self.version += 1

    def is_locked(self) -> bool:
        """Check if draft is currently locked"""
        if self.locked_by is None or self.locked_at is None:
            return False

        # Check if lock is expired (30 minutes)
        if (datetime.utcnow() - self.locked_at).total_seconds() > 1800:
            return False

        return True

    def is_expired(self) -> bool:
        """Check if draft has expired"""
        return datetime.utcnow() > self.expires_at
