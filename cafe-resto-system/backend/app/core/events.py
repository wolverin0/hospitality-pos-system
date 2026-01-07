"""
Domain events system

Domain events represent important business events that can be published
and subscribed to by multiple parts of the system.
"""

from datetime import datetime
from typing import Any, Callable, Dict, List, Optional
import uuid
import structlog

logger = structlog.get_logger(__name__)


class DomainEvent:
    """Base class for domain events"""

    def __init__(self, event_id: uuid.UUID = None):
        self.event_id = event_id or uuid.uuid4()
        self.occurred_at = datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary"""
        return {
            "event_id": str(self.event_id),
            "occurred_at": self.occurred_at.isoformat(),
            "event_type": self.__class__.__name__
        }


class DraftCreated(DomainEvent):
    """Event fired when a draft is created"""

    def __init__(
        self,
        draft_id: uuid.UUID,
        table_session_id: uuid.UUID,
        tenant_id: uuid.UUID,
        event_id: uuid.UUID = None
    ):
        super().__init__(event_id)
        self.draft_id = draft_id
        self.table_session_id = table_session_id
        self.tenant_id = tenant_id

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            "draft_id": str(self.draft_id),
            "table_session_id": str(self.table_session_id),
            "tenant_id": str(self.tenant_id)
        })
        return data


class DraftSubmitted(DomainEvent):
    """Event fired when a guest submits a draft for review"""

    def __init__(
        self,
        draft_id: uuid.UUID,
        table_session_id: uuid.UUID,
        tenant_id: uuid.UUID,
        guest_count: int,
        event_id: uuid.UUID = None
    ):
        super().__init__(event_id)
        self.draft_id = draft_id
        self.table_session_id = table_session_id
        self.tenant_id = tenant_id
        self.guest_count = guest_count

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            "draft_id": str(self.draft_id),
            "table_session_id": str(self.table_session_id),
            "tenant_id": str(self.tenant_id),
            "guest_count": self.guest_count
        })
        return data


class DraftConfirmed(DomainEvent):
    """Event fired when a waiter confirms a draft and creates an order"""

    def __init__(
        self,
        draft_id: uuid.UUID,
        order_id: uuid.UUID,
        table_session_id: uuid.UUID,
        tenant_id: uuid.UUID,
        waiter_id: uuid.UUID,
        items: List[Dict[str, Any]],
        total_amount: float,
        event_id: uuid.UUID = None
    ):
        super().__init__(event_id)
        self.draft_id = draft_id
        self.order_id = order_id
        self.table_session_id = table_session_id
        self.tenant_id = tenant_id
        self.waiter_id = waiter_id
        self.items = items
        self.total_amount = total_amount

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            "draft_id": str(self.draft_id),
            "order_id": str(self.order_id),
            "table_session_id": str(self.table_session_id),
            "tenant_id": str(self.tenant_id),
            "waiter_id": str(self.waiter_id),
            "items": self.items,
            "total_amount": self.total_amount
        })
        return data


class DraftRejected(DomainEvent):
    """Event fired when a waiter rejects a draft"""

    def __init__(
        self,
        draft_id: uuid.UUID,
        table_session_id: uuid.UUID,
        tenant_id: uuid.UUID,
        waiter_id: uuid.UUID,
        reason: str,
        event_id: uuid.UUID = None
    ):
        super().__init__(event_id)
        self.draft_id = draft_id
        self.table_session_id = table_session_id
        self.tenant_id = tenant_id
        self.waiter_id = waiter_id
        self.reason = reason

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            "draft_id": str(self.draft_id),
            "table_session_id": str(self.table_session_id),
            "tenant_id": str(self.tenant_id),
            "waiter_id": str(self.waiter_id),
            "reason": self.reason
        })
        return data


class DraftReassigned(DomainEvent):
    """Event fired when a draft is reassigned to a different table"""

    def __init__(
        self,
        draft_id: uuid.UUID,
        old_table_session_id: uuid.UUID,
        new_table_session_id: uuid.UUID,
        tenant_id: uuid.UUID,
        reassigned_by: uuid.UUID,
        event_id: uuid.UUID = None
    ):
        super().__init__(event_id)
        self.draft_id = draft_id
        self.old_table_session_id = old_table_session_id
        self.new_table_session_id = new_table_session_id
        self.tenant_id = tenant_id
        self.reassigned_by = reassigned_by

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            "draft_id": str(self.draft_id),
            "old_table_session_id": str(self.old_table_session_id),
            "new_table_session_id": str(self.new_table_session_id),
            "tenant_id": str(self.tenant_id),
            "reassigned_by": str(self.reassigned_by)
        })
        return data


class DraftAcquired(DomainEvent):
    """Event fired when a waiter acquires lock on a draft"""

    def __init__(
        self,
        draft_id: uuid.UUID,
        table_session_id: uuid.UUID,
        tenant_id: uuid.UUID,
        waiter_id: uuid.UUID,
        event_id: uuid.UUID = None
    ):
        super().__init__(event_id)
        self.draft_id = draft_id
        self.table_session_id = table_session_id
        self.tenant_id = tenant_id
        self.waiter_id = waiter_id

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            "draft_id": str(self.draft_id),
            "table_session_id": str(self.table_session_id),
            "tenant_id": str(self.tenant_id),
            "waiter_id": str(self.waiter_id)
        })
        return data


class TicketCreated(DomainEvent):
    """Event fired when a ticket is created from a confirmed draft"""

    def __init__(
        self,
        ticket_id: uuid.UUID,
        draft_order_id: uuid.UUID,
        table_session_id: uuid.UUID,
        station_id: uuid.UUID,
        tenant_id: uuid.UUID,
        course_number: int,
        course_name: str,
        event_id: uuid.UUID = None
    ):
        super().__init__(event_id)
        self.ticket_id = ticket_id
        self.draft_order_id = draft_order_id
        self.table_session_id = table_session_id
        self.station_id = station_id
        self.tenant_id = tenant_id
        self.course_number = course_number
        self.course_name = course_name

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            "ticket_id": str(self.ticket_id),
            "draft_order_id": str(self.draft_order_id),
            "table_session_id": str(self.table_session_id),
            "station_id": str(self.station_id),
            "tenant_id": str(self.tenant_id),
            "course_number": self.course_number,
            "course_name": self.course_name
        })
        return data


class TicketUpdated(DomainEvent):
    """Event fired when a ticket is updated"""

    def __init__(
        self,
        ticket_id: uuid.UUID,
        station_id: uuid.UUID,
        tenant_id: uuid.UUID,
        status: str,
        previous_status: Optional[str] = None,
        event_id: uuid.UUID = None
    ):
        super().__init__(event_id)
        self.ticket_id = ticket_id
        self.station_id = station_id
        self.tenant_id = tenant_id
        self.status = status
        self.previous_status = previous_status

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            "ticket_id": str(self.ticket_id),
            "station_id": str(self.station_id),
            "tenant_id": str(self.tenant_id),
            "status": self.status,
            "previous_status": str(self.previous_status) if self.previous_status else None
        })
        return data


class TicketBumped(DomainEvent):
    """Event fired when a ticket is bumped to COMPLETED"""

    def __init__(
        self,
        ticket_id: uuid.UUID,
        station_id: uuid.UUID,
        tenant_id: uuid.UUID,
        bumped_by: uuid.UUID,
        event_id: uuid.UUID = None
    ):
        super().__init__(event_id)
        self.ticket_id = ticket_id
        self.station_id = station_id
        self.tenant_id = tenant_id
        self.bumped_by = bumped_by

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            "ticket_id": str(self.ticket_id),
            "station_id": str(self.station_id),
            "tenant_id": str(self.tenant_id),
            "bumped_by": str(self.bumped_by)
        })
        return data


class TicketHeld(DomainEvent):
    """Event fired when a ticket is held (Expo mode)"""

    def __init__(
        self,
        ticket_id: uuid.UUID,
        station_id: uuid.UUID,
        tenant_id: uuid.UUID,
        held_by: uuid.UUID,
        reason: str,
        event_id: uuid.UUID = None
    ):
        super().__init__(event_id)
        self.ticket_id = ticket_id
        self.station_id = station_id
        self.tenant_id = tenant_id
        self.held_by = held_by
        self.reason = reason

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            "ticket_id": str(self.ticket_id),
            "station_id": str(self.station_id),
            "tenant_id": str(self.tenant_id),
            "held_by": str(self.held_by),
            "reason": self.reason
        })
        return data


class TicketFired(DomainEvent):
    """Event fired when a held ticket is fired to kitchen"""

    def __init__(
        self,
        ticket_id: uuid.UUID,
        station_id: uuid.UUID,
        tenant_id: uuid.UUID,
        fired_by: uuid.UUID,
        event_id: uuid.UUID = None
    ):
        super().__init__(event_id)
        self.ticket_id = ticket_id
        self.station_id = station_id
        self.tenant_id = tenant_id
        self.fired_by = fired_by

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            "ticket_id": str(self.ticket_id),
            "station_id": str(self.station_id),
            "tenant_id": str(self.tenant_id),
            "fired_by": str(self.fired_by)
        })
        return data


class TicketVoided(DomainEvent):
    """Event fired when a ticket is voided"""

    def __init__(
        self,
        ticket_id: uuid.UUID,
        station_id: uuid.UUID,
        tenant_id: uuid.UUID,
        voided_by: uuid.UUID,
        reason: str,
        event_id: uuid.UUID = None
    ):
        super().__init__(event_id)
        self.ticket_id = ticket_id
        self.station_id = station_id
        self.tenant_id = tenant_id
        self.voided_by = voided_by
        self.reason = reason

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            "ticket_id": str(self.ticket_id),
            "station_id": str(self.station_id),
            "tenant_id": str(self.tenant_id),
            "voided_by": str(self.voided_by),
            "reason": self.reason
        })
        return data


class OrderCreated(DomainEvent):
    """Event fired when a new order is created from a confirmed draft"""

    def __init__(
        self,
        order_id: uuid.UUID,
        draft_order_id: uuid.UUID,
        table_session_id: uuid.UUID,
        tenant_id: uuid.UUID,
        server_id: uuid.UUID,
        total_amount: float,
        event_id: uuid.UUID = None
    ):
        super().__init__(event_id)
        self.order_id = order_id
        self.draft_order_id = draft_order_id
        self.table_session_id = table_session_id
        self.tenant_id = tenant_id
        self.server_id = server_id
        self.total_amount = total_amount

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            "order_id": str(self.order_id),
            "draft_order_id": str(self.draft_order_id),
            "table_session_id": str(self.table_session_id),
            "tenant_id": str(self.tenant_id),
            "server_id": str(self.server_id),
            "total_amount": self.total_amount
        })
        return data


class OrderUpdated(DomainEvent):
    """Event fired when an order status or details are updated"""

    def __init__(
        self,
        order_id: uuid.UUID,
        tenant_id: uuid.UUID,
        status: str,
        previous_status: Optional[str] = None,
        event_id: uuid.UUID = None
    ):
        super().__init__(event_id)
        self.order_id = order_id
        self.tenant_id = tenant_id
        self.status = status
        self.previous_status = previous_status

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            "order_id": str(self.order_id),
            "tenant_id": str(self.tenant_id),
            "status": self.status,
            "previous_status": self.previous_status if self.previous_status else None
        })
        return data


class OrderCompleted(DomainEvent):
    """Event fired when an order is completed"""

    def __init__(
        self,
        order_id: uuid.UUID,
        table_session_id: uuid.UUID,
        tenant_id: uuid.UUID,
        completed_at: datetime,
        total_amount: float,
        event_id: uuid.UUID = None
    ):
        super().__init__(event_id)
        self.order_id = order_id
        self.table_session_id = table_session_id
        self.tenant_id = tenant_id
        self.completed_at = completed_at
        self.total_amount = total_amount

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            "order_id": str(self.order_id),
            "table_session_id": str(self.table_session_id),
            "tenant_id": str(self.tenant_id),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "total_amount": self.total_amount
        })
        return data


class PaymentCreated(DomainEvent):
    """Event fired when a payment is initiated"""

    def __init__(
        self,
        payment_id: uuid.UUID,
        order_id: uuid.UUID,
        tenant_id: uuid.UUID,
        amount: float,
        method: str,
        processed_by: uuid.UUID,
        event_id: uuid.UUID = None
    ):
        super().__init__(event_id)
        self.payment_id = payment_id
        self.order_id = order_id
        self.tenant_id = tenant_id
        self.amount = amount
        self.method = method
        self.processed_by = processed_by

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            "payment_id": str(self.payment_id),
            "order_id": str(self.order_id),
            "tenant_id": str(self.tenant_id),
            "amount": self.amount,
            "method": self.method,
            "processed_by": str(self.processed_by)
        })
        return data


class PaymentCompleted(DomainEvent):
    """Event fired when a payment is successfully completed"""

    def __init__(
        self,
        payment_id: uuid.UUID,
        order_id: uuid.UUID,
        tenant_id: uuid.UUID,
        amount: float,
        method: str,
        processed_at: datetime,
        event_id: uuid.UUID = None
    ):
        super().__init__(event_id)
        self.payment_id = payment_id
        self.order_id = order_id
        self.tenant_id = tenant_id
        self.amount = amount
        self.method = method
        self.processed_at = processed_at

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            "payment_id": str(self.payment_id),
            "order_id": str(self.order_id),
            "tenant_id": str(self.tenant_id),
            "amount": self.amount,
            "method": self.method,
            "processed_at": self.processed_at.isoformat() if self.processed_at else None
        })
        return data


class PaymentFailed(DomainEvent):
    """Event fired when a payment fails"""

    def __init__(
        self,
        payment_id: uuid.UUID,
        order_id: uuid.UUID,
        tenant_id: uuid.UUID,
        amount: float,
        method: str,
        reason: str,
        event_id: uuid.UUID = None
    ):
        super().__init__(event_id)
        self.payment_id = payment_id
        self.order_id = order_id
        self.tenant_id = tenant_id
        self.amount = amount
        self.method = method
        self.reason = reason

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            "payment_id": str(self.payment_id),
            "order_id": str(self.order_id),
            "tenant_id": str(self.tenant_id),
            "amount": self.amount,
            "method": self.method,
            "reason": self.reason
        })
        return data


class RefundCreated(DomainEvent):
    """Event fired when a refund is processed"""

    def __init__(
        self,
        refund_id: uuid.UUID,
        payment_id: uuid.UUID,
        order_id: uuid.UUID,
        tenant_id: uuid.UUID,
        amount: float,
        reason: str,
        processed_by: uuid.UUID,
        event_id: uuid.UUID = None
    ):
        super().__init__(event_id)
        self.refund_id = refund_id
        self.payment_id = payment_id
        self.order_id = order_id
        self.tenant_id = tenant_id
        self.amount = amount
        self.reason = reason
        self.processed_by = processed_by

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            "refund_id": str(self.refund_id),
            "payment_id": str(self.payment_id),
            "order_id": str(self.order_id),
            "tenant_id": str(self.tenant_id),
            "amount": self.amount,
            "reason": self.reason,
            "processed_by": str(self.processed_by)
        })
        return data


class ShiftOpened(DomainEvent):
    """Event fired when a server opens a shift"""

    def __init__(
        self,
        shift_id: uuid.UUID,
        server_id: uuid.UUID,
        location_id: uuid.UUID,
        tenant_id: uuid.UUID,
        opening_balance: float,
        opened_by: uuid.UUID,
        event_id: uuid.UUID = None
    ):
        super().__init__(event_id)
        self.shift_id = shift_id
        self.server_id = server_id
        self.location_id = location_id
        self.tenant_id = tenant_id
        self.opening_balance = opening_balance
        self.opened_by = opened_by

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            "shift_id": str(self.shift_id),
            "server_id": str(self.server_id),
            "location_id": str(self.location_id),
            "tenant_id": str(self.tenant_id),
            "opening_balance": self.opening_balance,
            "opened_by": str(self.opened_by)
        })
        return data


class ShiftClosed(DomainEvent):
    """Event fired when a server closes a shift"""

    def __init__(
        self,
        shift_id: uuid.UUID,
        server_id: uuid.UUID,
        location_id: uuid.UUID,
        tenant_id: uuid.UUID,
        closed_by: uuid.UUID,
        cash_sales: float,
        card_sales: float,
        closing_cash_count: float,
        event_id: uuid.UUID = None
    ):
        super().__init__(event_id)
        self.shift_id = shift_id
        self.server_id = server_id
        self.location_id = location_id
        self.tenant_id = tenant_id
        self.closed_by = closed_by
        self.cash_sales = cash_sales
        self.card_sales = card_sales
        self.closing_cash_count = closing_cash_count

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            "shift_id": str(self.shift_id),
            "server_id": str(self.server_id),
            "location_id": str(self.location_id),
            "tenant_id": str(self.tenant_id),
            "closed_by": str(self.closed_by),
            "cash_sales": self.cash_sales,
            "card_sales": self.card_sales,
            "closing_cash_count": self.closing_cash_count
        })
        return data


class ShiftReconciled(DomainEvent):
    """Event fired when a shift is reconciled (cash counted)"""

    def __init__(
        self,
        shift_id: uuid.UUID,
        server_id: uuid.UUID,
        location_id: uuid.UUID,
        tenant_id: uuid.UUID,
        reconciled_by: uuid.UUID,
        expected_cash: float,
        actual_cash: float,
        variance: float,
        event_id: uuid.UUID = None
    ):
        super().__init__(event_id)
        self.shift_id = shift_id
        self.server_id = server_id
        self.location_id = location_id
        self.tenant_id = tenant_id
        self.reconciled_by = reconciled_by
        self.expected_cash = expected_cash
        self.actual_cash = actual_cash
        self.variance = variance

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            "shift_id": str(self.shift_id),
            "server_id": str(self.server_id),
            "location_id": str(self.location_id),
            "tenant_id": str(self.tenant_id),
            "reconciled_by": str(self.reconciled_by),
            "expected_cash": self.expected_cash,
            "actual_cash": self.actual_cash,
            "variance": self.variance
        })
        return data


class EventBus:
    """Simple in-memory event bus for publishing domain events"""

    def __init__(self):
        self._subscribers: Dict[str, List[Callable]] = {}

    def subscribe(self, event_type: str, handler: Callable):
        """Subscribe to a specific event type"""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(handler)
        logger.debug(f"Subscribed handler to event type: {event_type}")

    def unsubscribe(self, event_type: str, handler: Callable):
        """Unsubscribe from an event type"""
        if event_type in self._subscribers:
            self._subscribers[event_type].remove(handler)
            logger.debug(f"Unsubscribed handler from event type: {event_type}")

    async def publish(self, event: DomainEvent):
        """Publish an event to all subscribers"""
        event_type = event.__class__.__name__
        handlers = self._subscribers.get(event_type, [])

        if not handlers:
            logger.debug(f"No subscribers for event type: {event_type}")
            return

        logger.info(f"Publishing event {event_type}: {event.event_id}")

        for handler in handlers:
            try:
                await handler(event)
            except Exception as e:
                logger.error(f"Error in event handler for {event_type}: {e}", exc_info=True)

    def clear_subscribers(self):
        """Clear all subscribers (useful for testing)"""
        self._subscribers.clear()
        logger.debug("Cleared all event subscribers")


# Global event bus instance
event_bus = EventBus()
