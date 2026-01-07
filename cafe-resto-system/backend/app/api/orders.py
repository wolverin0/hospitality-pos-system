"""
Order management API endpoints
Handles creation, retrieval, updating, and cancellation of orders
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from datetime import datetime
from typing import List, Optional
from decimal import Decimal
import uuid

from app.core.database import get_session
from app.core.dependencies import get_current_user_id, get_tenant_id
from app.core.websocket_manager import manager
from app.core.events import (
    OrderCreated, OrderUpdated, OrderCompleted, event_bus
)
from app.models import (
    Order, OrderStatus, OrderLineItem, OrderPayment, User, TableSession,
    DraftOrder, DraftLineItem, OrderAdjustment
)
from app.api.schemas import (
    OrderCreate, OrderUpdate, OrderRead, OrderListResponse,
    OrderLineItemRead
)

router = APIRouter(prefix="/api/v1/orders", tags=["orders"])


@router.post("/", response_model=OrderRead, status_code=status.HTTP_201_CREATED)
def create_order(
    order_data: OrderCreate,
    session: Session = Depends(get_session),
    current_user_id: uuid.UUID = Depends(get_current_user_id),
    tenant_id: uuid.UUID = Depends(get_tenant_id)
):
    """Create a new order from a confirmed draft order"""
    # Get user
    current_user = session.get(User, current_user_id)
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Get draft order
    draft = session.get(DraftOrder, order_data.draft_order_id)
    if not draft:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Draft order not found"
        )

    if draft.status != "confirmed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Draft order must be confirmed before creating order"
        )

    # Check if order already exists for this draft
    existing_order = session.exec(
        select(Order).where(Order.draft_order_id == order_data.draft_order_id)
    ).first()
    if existing_order:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Order already exists for this draft order"
        )

    # Create order
    order = Order(
        tenant_id=current_user.tenant_id,
        table_session_id=draft.table_session_id,
        server_id=order_data.server_id or current_user.id,
        draft_order_id=order_data.draft_order_id,
        status=OrderStatus.PENDING,
        subtotal=draft.subtotal,
        tax_amount=draft.tax_amount,
        discount_amount=draft.discount_amount,
        service_charge=draft.service_charge,
        total_amount=draft.total_amount,
        tip_amount=draft.tip_amount,
        guest_count=order_data.guest_count or draft.guest_count,
        special_requests=order_data.special_requests or draft.special_requests,
        order_notes=order_data.order_notes,
        is_rush=draft.is_rush,
        priority_level=draft.priority_level,
        confirmed_at=datetime.utcnow()
    )
    order.calculate_total()

    session.add(order)
    session.commit()
    session.refresh(order)

    # Copy line items from draft
    draft_line_items = session.exec(
        select(DraftLineItem).where(DraftLineItem.draft_order_id == order_data.draft_order_id)
    ).all()

    for draft_item in draft_line_items:
        line_item = OrderLineItem(
            tenant_id=current_user.tenant_id,
            order_id=order.id,
            menu_item_id=draft_item.menu_item_id,
            quantity=draft_item.quantity,
            unit_price=draft_item.unit_price,
            price_at_order=draft_item.unit_price * draft_item.quantity,
            name=draft_item.name,
            description=draft_item.description,
            special_instructions=draft_item.special_instructions,
            modifiers=draft_item.modifiers,
            discount_amount=draft_item.discount_amount,
            discount_percentage=draft_item.discount_percentage,
            is_comped=draft_item.is_comped,
            is_voided=False,
            course_number=draft_item.course_number,
            course_name=draft_item.course_name,
            sort_order=draft_item.sort_order,
            preparation_status=PreparationStatus.PENDING
        )
        line_item.calculate_line_total()
        session.add(line_item)

    session.commit()

    # Broadcast order created event
    from asyncio import create_task
    create_task(event_bus.publish(OrderCreated(
        order_id=order.id,
        draft_order_id=order_data.draft_order_id,
        table_session_id=order.table_session_id,
        tenant_id=order.tenant_id,
        server_id=order.server_id,
        total_amount=float(order.total_amount)
    )))

    return order


@router.get("/", response_model=OrderListResponse)
def list_orders(
    table_session_id: Optional[uuid.UUID] = None,
    server_id: Optional[uuid.UUID] = None,
    order_status: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    skip: int = 0,
    limit: int = 100,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """List orders with optional filters"""
    query = select(Order).where(Order.tenant_id == current_user.tenant_id)

    if table_session_id:
        query = query.where(Order.table_session_id == table_session_id)
    if server_id:
        query = query.where(Order.server_id == server_id)
    if order_status:
        query = query.where(Order.status == order_status)
    if date_from:
        query = query.where(Order.created_at >= date_from)
    if date_to:
        query = query.where(Order.created_at <= date_to)

    # Get total count
    total = len(session.exec(query).all())

    # Apply pagination
    query = query.offset(skip).limit(limit)
    orders = session.exec(query).all()

    return OrderListResponse(
        items=orders,
        total=total,
        page=skip // limit + 1 if limit > 0 else 1,
        page_size=limit
    )


@router.get("/{order_id}", response_model=OrderRead)
def get_order(
    order_id: uuid.UUID,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Get order by ID with line items, payments, and adjustments"""
    order = session.get(Order, order_id)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )

    if order.tenant_id != current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    return order


@router.patch("/{order_id}", response_model=OrderRead)
def update_order(
    order_id: uuid.UUID,
    order_update: OrderUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Update order status with optimistic concurrency"""
    order = session.get(Order, order_id)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )

    if order.tenant_id != current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    # Check version for optimistic concurrency
    if order.version != order_update.version:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Order was modified by another user. Please refresh and try again."
        )

    # Update fields
    if order_update.status:
        can_transition, reason = order.can_transition_to(order_update.status)
        if not can_transition:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=reason
            )

        order.status = order_update.status
        order.updated_at = datetime.utcnow()

        # Set timestamps based on status
        if order_update.status == OrderStatus.COMPLETED:
            order.completed_at = datetime.utcnow()
        elif order_update.status == OrderStatus.CANCELLED:
            order.cancelled_at = datetime.utcnow()

        order.version += 1

    session.add(order)
    session.commit()
    session.refresh(order)

    # Broadcast order updated event
    from asyncio import create_task
    create_task(manager.send_order_updated(
        order_id=order.id,
        table_session_id=order.table_session_id,
        status=order.status.value,
        previous_status=None
    ))

    return order


@router.post("/{order_id}/complete", response_model=OrderRead)
def complete_order(
    order_id: uuid.UUID,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Complete an order (mark as COMPLETED)"""
    order = session.get(Order, order_id)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )

    if order.tenant_id != current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    order.transition_to_completed()
    session.add(order)
    session.commit()
    session.refresh(order)

    # Broadcast order completed event
    from asyncio import create_task
    create_task(manager.send_order_completed(
        order_id=order.id,
        table_session_id=order.table_session_id,
        total_amount=float(order.total_amount)
    ))

    # Also broadcast domain event
    create_task(event_bus.publish(OrderCompleted(
        order_id=order.id,
        table_session_id=order.table_session_id,
        tenant_id=order.tenant_id,
        completed_at=order.completed_at,
        total_amount=float(order.total_amount)
    )))

    return order


@router.post("/{order_id}/cancel", response_model=OrderRead)
def cancel_order(
    order_id: uuid.UUID,
    reason: str,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Cancel an order with reason"""
    order = session.get(Order, order_id)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )

    if order.tenant_id != current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    order.transition_to_cancelled(reason)
    session.add(order)
    session.commit()
    session.refresh(order)

    # Broadcast order cancelled event
    from asyncio import create_task
    create_task(manager.send_order_cancelled(
        order_id=order.id,
        table_session_id=order.table_session_id,
        reason=reason
    ))

    return order


@router.delete("/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_order(
    order_id: uuid.UUID,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Delete an order (admin/manager only)"""
    # Check permissions
    if current_user.role not in ["admin", "manager"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin or manager can delete orders"
        )

    order = session.get(Order, order_id)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )

    if order.tenant_id != current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    # Cannot delete completed or paid orders
    if order.status in [OrderStatus.COMPLETED, OrderStatus.PAID]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete completed or paid orders"
        )

    session.delete(order)
    session.commit()
