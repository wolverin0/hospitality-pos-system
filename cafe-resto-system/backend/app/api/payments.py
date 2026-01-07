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
    User, Order, Shift, CashDrawerEvent, CashDrawerEventType
)
from app.api.schemas import (
    PaymentIntentCreate, PaymentIntentRead,
    PaymentCreate, PaymentRead, PaymentUpdate,
    RefundCreate, RefundRead
)

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

    # Update payment status to REFUNDED
    payment.status = PaymentStatus.REFUNDED
    payment.refunded_at = datetime.utcnow()
    session.add(payment)

    # Create CashDrawerEvent if cash refund
    if payment.method == PaymentMethod.CASH:
        cash_event = CashDrawerEvent(
            tenant_id=current_user.tenant_id,
            order_id=payment.order_id,
            payment_id=payment.id,
            location_id=payment.order.location_id,
            event_type=CashDrawerEventType.CASH_SHORTAGE,
            amount=-refund_data.amount,
            balance_after=0,  # Will need to calculate
            description=f"Refund for order {payment.order_id}",
            performed_by=current_user.id
        )

        session.add(cash_event)

    session.commit()

    # Broadcast refund created event
    from asyncio import create_task
    create_task(manager.send_refund_created(
        refund_id=refund.id,
        payment_id=payment.id,
        order_id=payment.order_id,
        table_session_id=payment.order.table_session_id,
        amount=float(refund.amount),
        reason=refund.reason
    ))

    return refund


@router.post("/split", response_model=List[PaymentRead], status_code=status.HTTP_201_CREATED)
def create_split_payment(
    order_id: uuid.UUID,
    payments: List[PaymentCreate],
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Create split payment (multiple methods)"""
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

    # Calculate total of split payments
    total_split_amount = sum(p.amount for p in payments)
    if abs(total_split_amount - order.total_amount) > Decimal("0.01"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Split payment total ({total_split_amount}) does not match order total ({order.total_amount})"
        )

    # Create each payment
    created_payments = []
    for payment_data in payments:
        payment = Payment(
            tenant_id=current_user.tenant_id,
            order_id=order_id,
            amount=payment_data.amount,
            method=payment_data.method,
            card_last_4=payment_data.card_last_4,
            card_holder_name=payment_data.card_holder_name,
            terminal_reference_id=payment_data.terminal_reference_id,
            qr_code=payment_data.qr_code,
            processed_by_user_id=current_user.id,
            created_at=datetime.utcnow()
        )

        session.add(payment)
        session.flush()  # Get IDs before commit
        created_payments.append(payment)

    session.commit()

    # Broadcast payment events
    from asyncio import create_task
    for payment in created_payments:
        create_task(manager.send_payment_created(
            payment_id=payment.id,
            order_id=payment.order_id,
            table_session_id=order.table_session_id,
            amount=float(payment.amount),
            method=payment.method.value
        ))

    return created_payments
