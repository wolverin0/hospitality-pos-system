"""
Unit tests for draft state machine
"""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal
import uuid

from app.models.draft_order import DraftOrder, DraftStatus
from app.models.draft_line_item import DraftLineItem


class TestDraftOrderStateMachine:
    """Test draft order state machine transitions"""

    def test_initial_state(self):
        """Test draft starts in DRAFT status"""
        draft = DraftOrder(
            id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            table_session_id=uuid.uuid4(),
            status=DraftStatus.DRAFT,
            version=1
        )

        assert draft.status == DraftStatus.DRAFT
        assert draft.version == 1

    def test_can_submit_draft_status(self):
        """Test draft can be submitted from DRAFT status"""
        draft = DraftOrder(
            id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            table_session_id=uuid.uuid4(),
            status=DraftStatus.DRAFT,
            version=1
        )

        assert draft.can_submit() is True

    def test_cannot_submit_pending_status(self):
        """Test draft cannot be submitted from PENDING status"""
        draft = DraftOrder(
            id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            table_session_id=uuid.uuid4(),
            status=DraftStatus.PENDING,
            version=1
        )

        assert draft.can_submit() is False

    def test_can_modify_draft_status(self):
        """Test draft can be modified in DRAFT status"""
        draft = DraftOrder(
            id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            table_session_id=uuid.uuid4(),
            status=DraftStatus.DRAFT,
            version=1
        )

        assert draft.can_modify() is True

    def test_cannot_modify_pending_status(self):
        """Test draft cannot be modified in PENDING status"""
        draft = DraftOrder(
            id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            table_session_id=uuid.uuid4(),
            status=DraftStatus.PENDING,
            version=1
        )

        assert draft.can_modify() is False

    def test_transition_to_pending(self):
        """Test transitioning draft to PENDING status"""
        draft = DraftOrder(
            id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            table_session_id=uuid.uuid4(),
            status=DraftStatus.DRAFT,
            version=1,
            created_at=datetime.utcnow()
        )

        draft.transition_to_pending()

        assert draft.status == DraftStatus.PENDING
        assert draft.version == 2  # Version should increment

    def test_cannot_transition_to_pending_from_confirmed(self):
        """Test cannot transition to PENDING from CONFIRMED status"""
        draft = DraftOrder(
            id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            table_session_id=uuid.uuid4(),
            status=DraftStatus.CONFIRMED,
            version=1
        )

        with pytest.raises(ValueError, match="Cannot transition to pending"):
            draft.transition_to_pending()

    def test_acquire_lock_success(self):
        """Test successful lock acquisition"""
        user_id = uuid.uuid4()
        draft = DraftOrder(
            id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            table_session_id=uuid.uuid4(),
            status=DraftStatus.PENDING,
            version=1
        )

        can_lock, reason = draft.can_acquire_lock(user_id)

        assert can_lock is True
        assert reason == "Can acquire lock"

    def test_acquire_lock_locked_by_another(self):
        """Test cannot acquire lock when locked by another user"""
        user_id1 = uuid.uuid4()
        user_id2 = uuid.uuid4()
        draft = DraftOrder(
            id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            table_session_id=uuid.uuid4(),
            status=DraftStatus.PENDING,
            version=1,
            locked_by=user_id1,
            locked_at=datetime.utcnow()
        )

        can_lock, reason = draft.can_acquire_lock(user_id2)

        assert can_lock is False
        assert "already locked by another user" in reason

    def test_acquire_lock_expired(self):
        """Test can acquire expired lock"""
        user_id1 = uuid.uuid4()
        user_id2 = uuid.uuid4()
        draft = DraftOrder(
            id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            table_session_id=uuid.uuid4(),
            status=DraftStatus.PENDING,
            version=1,
            locked_by=user_id1,
            locked_at=datetime.utcnow() - timedelta(minutes=35)  # 35 minutes ago
        )

        can_lock, reason = draft.can_acquire_lock(user_id2)

        assert can_lock is True
        assert reason == "Lock expired, can acquire"

    def test_acquire_lock_same_user(self):
        """Test user can re-acquire their own lock"""
        user_id = uuid.uuid4()
        draft = DraftOrder(
            id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            table_session_id=uuid.uuid4(),
            status=DraftStatus.PENDING,
            version=1,
            locked_by=user_id,
            locked_at=datetime.utcnow()
        )

        can_lock, reason = draft.can_acquire_lock(user_id)

        assert can_lock is True
        assert reason == "Already locked by this user"

    def test_acquire_lock_non_pending_status(self):
        """Test cannot acquire lock on draft not in PENDING status"""
        user_id = uuid.uuid4()
        draft = DraftOrder(
            id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            table_session_id=uuid.uuid4(),
            status=DraftStatus.DRAFT,
            version=1
        )

        can_lock, reason = draft.can_acquire_lock(user_id)

        assert can_lock is False
        assert "not in pending status" in reason

    def test_confirm_draft_success(self):
        """Test successful draft confirmation"""
        user_id = uuid.uuid4()
        order_id = uuid.uuid4()
        draft = DraftOrder(
            id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            table_session_id=uuid.uuid4(),
            status=DraftStatus.PENDING,
            version=1,
            locked_by=user_id,
            locked_at=datetime.utcnow()
        )

        draft.transition_to_confirmed(user_id, order_id)

        assert draft.status == DraftStatus.CONFIRMED
        assert draft.confirmed_by == user_id
        assert draft.order_id == order_id
        assert draft.confirmed_at is not None
        assert draft.locked_by is None  # Lock should be released
        assert draft.locked_at is None
        assert draft.version == 2

    def test_confirm_draft_without_lock(self):
        """Test cannot confirm draft without holding lock"""
        user_id = uuid.uuid4()
        order_id = uuid.uuid4()
        draft = DraftOrder(
            id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            table_session_id=uuid.uuid4(),
            status=DraftStatus.PENDING,
            version=1
        )

        with pytest.raises(ValueError, match="not locked by this user"):
            draft.transition_to_confirmed(user_id, order_id)

    def test_confirm_draft_wrong_lock_holder(self):
        """Test cannot confirm draft if locked by different user"""
        user_id1 = uuid.uuid4()
        user_id2 = uuid.uuid4()
        order_id = uuid.uuid4()
        draft = DraftOrder(
            id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            table_session_id=uuid.uuid4(),
            status=DraftStatus.PENDING,
            version=1,
            locked_by=user_id1,
            locked_at=datetime.utcnow()
        )

        with pytest.raises(ValueError, match="not locked by this user"):
            draft.transition_to_confirmed(user_id2, order_id)

    def test_reject_draft_success(self):
        """Test successful draft rejection"""
        user_id = uuid.uuid4()
        draft = DraftOrder(
            id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            table_session_id=uuid.uuid4(),
            status=DraftStatus.PENDING,
            version=1,
            locked_by=user_id,
            locked_at=datetime.utcnow()
        )

        reason = "Item out of stock"
        draft.transition_to_rejected(user_id, reason)

        assert draft.status == DraftStatus.REJECTED
        assert draft.rejected_by == user_id
        assert draft.rejection_reason == reason
        assert draft.rejected_at is not None
        assert draft.locked_by is None  # Lock should be released
        assert draft.locked_at is None
        assert draft.version == 2

    def test_expire_draft_success(self):
        """Test successful draft expiration"""
        draft = DraftOrder(
            id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            table_session_id=uuid.uuid4(),
            status=DraftStatus.PENDING,
            version=1,
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() - timedelta(minutes=1)
        )

        draft.transition_to_expired()

        assert draft.status == DraftStatus.EXPIRED
        assert draft.locked_by is None
        assert draft.locked_at is None
        assert draft.version == 2

    def test_cannot_expire_non_pending_status(self):
        """Test cannot expire draft not in PENDING status"""
        draft = DraftOrder(
            id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            table_session_id=uuid.uuid4(),
            status=DraftStatus.CONFIRMED,
            version=1
        )

        with pytest.raises(ValueError, match="Cannot expire draft"):
            draft.transition_to_expired()

    def test_release_lock_success(self):
        """Test successful lock release"""
        user_id = uuid.uuid4()
        draft = DraftOrder(
            id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            table_session_id=uuid.uuid4(),
            status=DraftStatus.PENDING,
            version=1,
            locked_by=user_id,
            locked_at=datetime.utcnow()
        )

        draft.release_lock(user_id)

        assert draft.locked_by is None
        assert draft.locked_at is None
        assert draft.version == 2

    def test_release_lock_without_holding(self):
        """Test cannot release lock without holding it"""
        user_id1 = uuid.uuid4()
        user_id2 = uuid.uuid4()
        draft = DraftOrder(
            id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            table_session_id=uuid.uuid4(),
            status=DraftStatus.PENDING,
            version=1,
            locked_by=user_id1,
            locked_at=datetime.utcnow()
        )

        with pytest.raises(ValueError, match="not locked by this user"):
            draft.release_lock(user_id2)

    def test_is_locked_true(self):
        """Test draft is locked"""
        user_id = uuid.uuid4()
        draft = DraftOrder(
            id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            table_session_id=uuid.uuid4(),
            status=DraftStatus.PENDING,
            version=1,
            locked_by=user_id,
            locked_at=datetime.utcnow()
        )

        assert draft.is_locked() is True

    def test_is_locked_false(self):
        """Test draft is not locked"""
        draft = DraftOrder(
            id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            table_session_id=uuid.uuid4(),
            status=DraftStatus.PENDING,
            version=1
        )

        assert draft.is_locked() is False

    def test_is_locked_expired(self):
        """Test expired lock is not considered locked"""
        user_id = uuid.uuid4()
        draft = DraftOrder(
            id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            table_session_id=uuid.uuid4(),
            status=DraftStatus.PENDING,
            version=1,
            locked_by=user_id,
            locked_at=datetime.utcnow() - timedelta(minutes=35)
        )

        assert draft.is_locked() is False

    def test_is_expired_true(self):
        """Test draft is expired"""
        draft = DraftOrder(
            id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            table_session_id=uuid.uuid4(),
            status=DraftStatus.PENDING,
            version=1,
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() - timedelta(minutes=1)
        )

        assert draft.is_expired() is True

    def test_is_expired_false(self):
        """Test draft is not expired"""
        draft = DraftOrder(
            id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            table_session_id=uuid.uuid4(),
            status=DraftStatus.PENDING,
            version=1,
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(hours=2)
        )

        assert draft.is_expired() is False


class TestDraftLineItem:
    """Test draft line item functionality"""

    def test_calculate_line_total(self):
        """Test line total calculation"""
        item = DraftLineItem(
            id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            draft_order_id=uuid.uuid4(),
            menu_item_id=uuid.uuid4(),
            name="Burger",
            quantity=3,
            price_at_order=Decimal("10.50")
        )

        total = item.calculate_line_total()

        assert total == Decimal("31.50")
        assert item.line_total == Decimal("31.50")

    def test_add_modifier_with_price_adjustment(self):
        """Test adding modifier with price adjustment"""
        item = DraftLineItem(
            id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            draft_order_id=uuid.uuid4(),
            menu_item_id=uuid.uuid4(),
            name="Burger",
            quantity=1,
            price_at_order=Decimal("10.50")
        )

        item.add_modifier("size", "large", Decimal("2.00"))

        assert item.price_at_order == Decimal("12.50")
        assert item.line_total == Decimal("12.50")

    def test_get_modifier_summary(self):
        """Test getting modifier summary"""
        item = DraftLineItem(
            id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            draft_order_id=uuid.uuid4(),
            menu_item_id=uuid.uuid4(),
            name="Burger",
            quantity=1,
            price_at_order=Decimal("10.50"),
            modifiers={
                "modifiers": [
                    {"type": "size", "value": "large", "price_adjustment": "2.00"},
                    {"type": "add_on", "value": "cheese", "price_adjustment": "1.00"}
                ]
            }
        )

        summary = item.get_modifier_summary()

        assert summary == "large, cheese"

    def test_is_modification_true(self):
        """Test item is a modification"""
        parent_id = uuid.uuid4()
        item = DraftLineItem(
            id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            draft_order_id=uuid.uuid4(),
            menu_item_id=uuid.uuid4(),
            name="Burger - No Onions",
            quantity=1,
            price_at_order=Decimal("10.50"),
            parent_line_item_id=parent_id
        )

        assert item.is_modification() is True

    def test_is_modification_false(self):
        """Test item is not a modification"""
        item = DraftLineItem(
            id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            draft_order_id=uuid.uuid4(),
            menu_item_id=uuid.uuid4(),
            name="Burger",
            quantity=1,
            price_at_order=Decimal("10.50")
        )

        assert item.is_modification() is False
