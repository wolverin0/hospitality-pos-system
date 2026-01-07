"""
Payment processing API endpoints
Handles payment intents, payment processing, refunds, and split payments
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from datetime import datetime
from typing import List, Optional
from decimal import Decimal
import uuid

from app.core.database import get_session
from app.core.dependencies import get_current_user
from app.core.websocket_manager import manager
from app.core.events import (
    PaymentCreated, PaymentCompleted, PaymentFailed, RefundCreated, event_bus
)
from app.models import (
    Payment, PaymentIntent, PaymentMethod, PaymentStatus,
    PaymentIntentStatus, Refund, RefundStatus, RefundReasonCode,
    User, Order, Shift, CashDrawerEvent, CashDrawerEventType, OrderStatus
)
from app.api.schemas import (
    PaymentIntentCreate, PaymentIntentRead,
    PaymentCreate, PaymentRead, PaymentUpdate,
    RefundCreate, RefundRead
)
from app.services.mercadopago import MercadoPagoService

router = APIRouter(prefix="/api/v1/payments", tags=["payments"])


@router.post("/intents", response_model=PaymentIntentRead, status_code=status.HTTP_201_CREATED)
def create_payment_intent(
    intent_data: PaymentIntentCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Create a payment intent (initiate payment flow)"""
    # Verify order exists
    order = session.get(Order, intent_data.order_id)
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

    # Create payment intent
    payment_intent = PaymentIntent(
        tenant_id=current_user.tenant_id,
        order_id=intent_data.order_id,
        amount=intent_data.amount,
        method=intent_data.method,
        status=PaymentIntentStatus.PENDING,
        initiated_by_user_id=current_user.id
    )

    session.add(payment_intent)
    session.commit()
    session.refresh(payment_intent)

    return payment_intent


@router.post("/qr-intent", response_model=PaymentIntentRead, status_code=status.HTTP_201_CREATED)
def create_qr_payment_intent(
    order_id: uuid.UUID,
    table_id: Optional[str] = None,
    expiration_minutes: int = 30,
    tip_amount: Optional[Decimal] = None,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """
    Create QR code payment intent via Mercado Pago

    Generates QR code for order and returns payment intent with QR data
    """
    # Verify order exists
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

    # Check order status (must be in PENDING or IN_PROGRESS)
    if order.status not in [OrderStatus.PENDING, OrderStatus.IN_PROGRESS, OrderStatus.PARTIALLY_PAID]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Order must be in PENDING, IN_PROGRESS, or PARTIALLY_PAID to create QR payment (current: {order.status.value})"
        )

    # Generate idempotency key
    import uuid
    from datetime import datetime
    idempotency_key = f"qr_order_{order_id}_{datetime.now().isoformat()}"

    # Get order line items for Mercado Pago
    from app.models.order_line_item import OrderLineItem
    from sqlmodel import select

    line_items = session.exec(
        select(OrderLineItem).where(OrderLineItem.order_id == order_id)
    ).all()

    items = [
        {
            "name": item.name,
            "unit_price": float(item.price_at_order),
            "quantity": item.quantity,
            "id": str(item.menu_item_id) if item.menu_item_id else ""
        }
        for item in line_items if not item.is_voided and not item.is_comped
    ]

    # Calculate total amount including tip
    total_amount = order.total_amount + (tip_amount or Decimal("0.00"))

    # Generate Mercado Pago QR order
    try:
        mp_service = MercadoPagoService()
        mp_result = mp_service.create_qr_order(
            table_id=table_id or f"TABLE_{order.table_session_id}" if order.table_session_id else "UNKNOWN",
            order_id=str(order_id),
            total_amount=total_amount,
            items=items,
            external_reference=idempotency_key,
            expiration_minutes=expiration_minutes,
            tip_amount=tip_amount
        )

        # Create payment intent with QR data
        payment_intent = PaymentIntent(
            tenant_id=current_user.tenant_id,
            order_id=order_id,
            amount=total_amount,
            method=PaymentMethod.QR,
            status=PaymentIntentStatus.PENDING,
            initiated_by_user_id=current_user.id,
            qr_code=mp_result.get("qr_data"),
            qr_provider="mercadopago",
            idempotency_key=idempotency_key,
            qr_expires_at=mp_result.get("expires_at"),
            tip_amount=tip_amount or Decimal("0.00")
        )

        session.add(payment_intent)
        session.commit()
        session.refresh(payment_intent)

        return payment_intent

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Payment service not configured: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create QR payment: {str(e)}"
        )


@router.post("/process", response_model=PaymentRead, status_code=status.HTTP_201_CREATED)
def process_payment(
    payment_data: PaymentCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Process a payment (cash, card, terminal, QR)"""
    # Verify order exists
    order = session.get(Order, payment_data.order_id)
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

    # Check order status
    if order.status not in [OrderStatus.PENDING, OrderStatus.IN_PROGRESS]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Order must be in PENDING or IN_PROGRESS to process payment"
        )

    # Create payment
    payment = Payment(
        tenant_id=current_user.tenant_id,
        order_id=payment_data.order_id,
        amount=payment_data.amount,
        method=payment_data.method,
        status=PaymentStatus.PENDING,
        card_last_4=payment_data.card_last_4,
        card_holder_name=payment_data.card_holder_name,
        terminal_reference_id=payment_data.terminal_reference_id,
        terminal_response=None,
        qr_code=payment_data.qr_code,
        qr_provider=payment_data.qr_provider or "mercadopago",
        processed_by_user_id=current_user.id,
        created_at=datetime.utcnow()
    )

    session.add(payment)
    session.commit()
    session.refresh(payment)

    # Broadcast payment created event
    from asyncio import create_task
    create_task(manager.send_payment_created(
        payment_id=payment.id,
        order_id=payment.order_id,
        table_session_id=order.table_session_id,
        amount=float(payment.amount),
        method=payment.method.value
    ))

    # Process payment based on method
    if payment_data.method == PaymentMethod.CASH:
        # Cash payment - immediate success
        payment.status = PaymentStatus.COMPLETED
        payment.processed_at = datetime.utcnow()

        # Create CashDrawerEvent
        cash_event = CashDrawerEvent(
            tenant_id=current_user.tenant_id,
            order_id=payment.order_id,
            payment_id=payment.id,
            location_id=order.location_id,
            event_type=CashDrawerEventType.PAYMENT_IN,
            amount=payment.amount,
            balance_after=payment.amount,  # Will need to get actual balance
            description=f"Payment in for order {payment.order_id}",
            performed_by=current_user.id
        )

        # Get or create active shift for cash tracking
        active_shift = session.exec(
            select(Shift).where(
                (Shift.server_id == current_user.id) &
                (Shift.status == ShiftStatus.ACTIVE)
            )
        ).first()

        if active_shift:
            cash_event.shift_id = active_shift.id
            active_shift.cash_sales += payment.amount

        session.add(cash_event)
        session.add(payment)
        session.commit()

        # Broadcast payment completed event
        create_task(manager.send_payment_completed(
            payment_id=payment.id,
            order_id=payment.order_id,
            table_session_id=order.table_session_id,
            amount=float(payment.amount),
            method=payment.method.value
        ))

    elif payment_data.method == PaymentMethod.TERMINAL:
        # Terminal payment - create payment, async processing
        payment.status = PaymentStatus.PROCESSING
        session.add(payment)
        session.commit()

        # TODO: Integrate with terminal API (Verifone, PagoFacil)
        # For now, mark as completed after simulated processing
        # In production, this would poll terminal status

    elif payment_data.method == PaymentMethod.QR:
        # QR payment - create pending payment
        # TODO: Integrate with Mercado Pago or other QR providers
        session.add(payment)
        session.commit()

    elif payment_data.method == PaymentMethod.CARD:
        # Card payment - create pending payment
        # TODO: Integrate with Stripe or other payment processor
        session.add(payment)
        session.commit()

    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported payment method: {payment_data.method}"
        )

    session.refresh(payment)
    return payment


@router.get("/", response_model=List[PaymentRead])
def list_payments(
    order_id: Optional[uuid.UUID] = None,
    payment_method: Optional[str] = None,
    payment_status: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    skip: int = 0,
    limit: int = 100,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """List payments with optional filters"""
    query = select(Payment).where(Payment.tenant_id == current_user.tenant_id)

    if order_id:
        query = query.where(Payment.order_id == order_id)
    if payment_method:
        query = query.where(Payment.method == payment_method)
    if payment_status:
        query = query.where(Payment.status == payment_status)
    if date_from:
        query = query.where(Payment.created_at >= date_from)
    if date_to:
        query = query.where(Payment.created_at <= date_to)

    # Apply pagination
    query = query.offset(skip).limit(limit)
    payments = session.exec(query).all()

    return payments


@router.get("/{payment_id}", response_model=PaymentRead)
def get_payment(
    payment_id: uuid.UUID,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Get payment by ID"""
    payment = session.get(Payment, payment_id)
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found"
        )

    if payment.tenant_id != current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    return payment


@router.patch("/{payment_id}", response_model=PaymentRead)
def update_payment(
    payment_id: uuid.UUID,
    payment_update: PaymentUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Update payment status"""
    payment = session.get(Payment, payment_id)
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found"
        )

    if payment.tenant_id != current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    # Check version for optimistic concurrency
    if payment.version != payment_update.version:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Payment was modified by another user. Please refresh and try again."
        )

    # Update status
    if payment_update.status:
        if payment_update.status == PaymentStatus.COMPLETED:
            payment.status = PaymentStatus.COMPLETED
            payment.processed_at = datetime.utcnow()

            # Broadcast payment completed event
            from asyncio import create_task
            create_task(manager.send_payment_completed(
                payment_id=payment.id,
                order_id=payment.order_id,
                table_session_id=None,  # We'll look this up if needed
                amount=float(payment.amount),
                method=payment.method.value
            ))

        elif payment_update.status == PaymentStatus.FAILED:
            payment.status = PaymentStatus.FAILED
            payment.failed_at = datetime.utcnow()

            # Broadcast payment failed event
            create_task(manager.send_payment_failed(
                payment_id=payment.id,
                order_id=payment.order_id,
                table_session_id=None,
                amount=float(payment.amount),
                method=payment.method.value,
                reason="Payment failed"
            ))

        payment.version += 1

    session.add(payment)
    session.commit()
    session.refresh(payment)

    return payment


@router.post("/{payment_id}/refund", response_model=RefundRead, status_code=status.HTTP_201_CREATED)
def process_refund(
    payment_id: uuid.UUID,
    refund_data: RefundCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Process a refund"""
    # Verify payment exists
    payment = session.get(Payment, payment_id)
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found"
        )

    if payment.tenant_id != current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    # Verify payment was completed
    if payment.status != PaymentStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only refund completed payments"
        )

    # Check if already refunded
    existing_refund = session.exec(
        select(Refund).where(
            (Refund.original_payment_id == payment_id) &
            (Refund.status == RefundStatus.COMPLETED)
        )
    ).first()

    if existing_refund:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payment has already been refunded"
        )

    # Create refund
    refund = Refund(
        tenant_id=current_user.tenant_id,
        original_payment_id=payment_id,
        order_id=payment.order_id,
        amount=refund_data.amount,
        reason_code=refund_data.reason_code,
        reason=refund_data.reason,
        created_by=current_user.id,
        status=RefundStatus.REQUESTED
    )

    session.add(refund)
    session.commit()
    session.refresh(refund)

    return created_payments


@router.get("/qr-status/{payment_intent_id}", response_model=PaymentIntentRead)
def get_qr_payment_status(
    payment_intent_id: uuid.UUID,
    session: Session = Depends(get_session)
):
    """
    Poll payment intent status for guest app
    Guests can poll this endpoint to check if QR payment was completed
    """
    payment_intent = session.get(PaymentIntent, payment_intent_id)
    if not payment_intent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment intent not found"
        )

    # Check if expired
    if payment_intent.qr_expires_at and payment_intent.qr_expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Payment intent has expired"
        )

    return payment_intent


@router.get("/table-session/{table_session_id}/payments", response_model=List[PaymentRead])
def get_table_session_payments(
    table_session_id: uuid.UUID,
    session: Session = Depends(get_session)
):
    """
    Get payment history for a table session
    Shows all payments made for a table session
    """
    from app.models.table_session import TableSession

    # Verify table session exists
    table_session = session.get(TableSession, table_session_id)
    if not table_session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Table session not found"
        )

    # Get all payments for orders in this table session
    from sqlmodel import select

    payments = session.exec(
        select(Payment)
        .join(Order, Payment.order_id == Order.id)
        .where(
            (Order.table_session_id == table_session_id) &
            (Payment.status == PaymentStatus.COMPLETED)
        )
        .order_by(Payment.processed_at.desc())
    ).all()

    return payments


@router.get("/qr-status/{payment_intent_id}", response_model=PaymentIntentRead)
def get_qr_payment_status(
    payment_intent_id: uuid.UUID,
    session: Session = Depends(get_session)
):
    """
    Poll payment intent status for guest app
    Guests can poll this endpoint to check if QR payment was completed
    """
    payment_intent = session.get(PaymentIntent, payment_intent_id)
    if not payment_intent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment intent not found"
        )

    # Check if expired
    if payment_intent.qr_expires_at and payment_intent.qr_expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Payment intent has expired"
        )

    return payment_intent
