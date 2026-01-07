"""
Webhook handlers for payment providers (Mercado Pago, etc.)
Handles IPN (Instant Payment Notification) webhooks with idempotency
"""

from fastapi import APIRouter, HTTPException, status, Request
from sqlmodel import Session, select
from datetime import datetime
from typing import Dict, Any, Optional
import logging

from app.core.database import get_session
from app.core.websocket_manager import manager
from app.core.events import PaymentCompleted, PaymentFailed, event_bus
from app.models import (
    Payment, PaymentStatus, PaymentIntent, PaymentIntentStatus,
    Order, OrderStatus
)
from app.services.mercadopago import MercadoPagoService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/webhooks", tags=["webhooks"])


class WebhookLog(SQLModel, table=True):
    """Webhook log for idempotency and debugging"""
    __tablename__ = "webhook_logs"

    id: str = Field(primary_key=True)
    external_reference: str = Field(index=True, max_length=255)
    provider: str = Field(max_length=50)
    action_type: str = Field(max_length=50)
    status: str = Field(max_length=50)
    payload: Optional[dict] = Field(default=None, sa_column=Column(JSON, nullable=True))
    processed_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        indexes = [
            {"name": "idx_webhook_external_ref", "columns": ["external_reference"]},
            {"name": "idx_webhook_processed_at", "columns": ["processed_at"]},
        ]


@router.post("/mercadopago")
async def mercadopago_webhook(
    request: Request,
    notification: Dict[str, Any],
    session: Session = Depends(get_session)
):
    """
    Handle Mercado Pago QR code payment webhooks

    IPN Flow:
    1. Receive notification (merchant_orders or payments)
    2. Verify (no signature for QR codes, validate via API)
    3. Check idempotency (external_reference)
    4. Update Payment/PaymentIntent status
    5. Update Order status if paid
    6. Broadcast WebSocket events
    """
    logger.info(f"Received Mercado Pago webhook: {notification.get('action_type')}")

    # Get service (will use mock mode if not configured)
    try:
        mp_service = MercadoPagoService()
    except ValueError as e:
        logger.error(f"Mercado Pago service not configured: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Payment service not configured"
        )

    # Verify webhook
    is_valid, error_msg, data = mp_service.verify_webhook_notification(notification)

    if not is_valid:
        logger.error(f"Webhook verification failed: {error_msg}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg
        )

    action_type = notification.get("action_type")
    external_reference = data.get("external_reference")
    mp_order_id = data.get("id")
    mp_status = data.get("status")

    # Idempotency check
    existing_log = session.exec(
        select(WebhookLog).where(
            (WebhookLog.external_reference == external_reference) &
            (WebhookLog.provider == "mercadopago")
        )
    ).first()

    if existing_log:
        logger.info(f"Duplicate webhook: {external_reference}, already processed at {existing_log.processed_at}")
        return {"status": "duplicate", "message": "Already processed"}

    # Find PaymentIntent by external reference
    payment_intent = session.exec(
        select(PaymentIntent).where(
            (PaymentIntent.idempotency_key == external_reference) &
            (PaymentIntent.method == "qr")
        )
    ).first()

    if not payment_intent:
        logger.error(f"PaymentIntent not found for external_reference: {external_reference}")
        return {"status": "error", "message": "PaymentIntent not found"}

    # Process based on status
    if mp_status == "paid" or mp_status == "closed":
        # Payment successful
        await process_successful_payment(
            session=session,
            payment_intent=payment_intent,
            mp_order_id=mp_order_id,
            mp_data=data,
            mp_service=mp_service
        )

    elif mp_status == "cancelled":
        # Payment cancelled
        process_cancelled_payment(
            session=session,
            payment_intent=payment_intent,
            reason="Customer cancelled payment"
        )

    elif mp_status == "expired":
        # Payment expired
        process_failed_payment(
            session=session,
            payment_intent=payment_intent,
            reason="Payment expired"
        )

    else:
        # Unknown status - query API
        logger.warning(f"Unknown status in webhook: {mp_status}, querying API")
        try:
            status_result = mp_service.get_order_status(mp_order_id)
            actual_status = status_result.get("status")

            if actual_status == "paid":
                await process_successful_payment(
                    session=session,
                    payment_intent=payment_intent,
                    mp_order_id=mp_order_id,
                    mp_data=data,
                    mp_service=mp_service
                )
            else:
                logger.info(f"Payment status: {actual_status}")
                return {"status": "processed", "mp_status": actual_status}

        except Exception as e:
            logger.error(f"Error querying MP API: {e}")

    # Log webhook as processed
    webhook_log = WebhookLog(
        id=f"mp_{external_reference}_{datetime.now().isoformat()}",
        external_reference=external_reference,
        provider="mercadopago",
        action_type=action_type,
        status=mp_status,
        payload=notification
    )
    session.add(webhook_log)
    session.commit()

    return {"status": "processed"}


async def process_successful_payment(
    session: Session,
    payment_intent: PaymentIntent,
    mp_order_id: str,
    mp_data: Dict[str, Any],
    mp_service: MercadoPagoService
):
    """
    Process successful payment webhook

    Steps:
    1. Find associated Payment record
    2. Update Payment to COMPLETED
    3. Update PaymentIntent to COMPLETED
    4. Update Order to PAID
    5. Broadcast WebSocket events
    """
    logger.info(f"Processing successful payment: {payment_intent.id}")

    # Find or create Payment record
    payment = session.exec(
        select(Payment).where(
            (Payment.payment_intent_id == payment_intent.id) &
            (Payment.method == "qr")
        )
    ).first()

    if payment:
        # Update existing payment
        payment.status = PaymentStatus.COMPLETED
        payment.processed_at = datetime.utcnow()
        payment.qr_code = mp_data.get("qr_data")
        session.add(payment)
    else:
        # Create new payment record
        payment = Payment(
            tenant_id=payment_intent.tenant_id,
            order_id=payment_intent.order_id,
            payment_intent_id=payment_intent.id,
            method="qr",
            amount=payment_intent.amount,
            status=PaymentStatus.COMPLETED,
            qr_code=mp_data.get("qr_data"),
            qr_provider="mercadopago",
            processed_at=datetime.utcnow()
        )
        session.add(payment)

    # Update PaymentIntent
    payment_intent.transition_to_completed(datetime.utcnow())

    # Update Order status
    order = session.get(Order, payment_intent.order_id)
    if order and order.status != OrderStatus.PAID:
        # Check if fully paid (could be split payments)
        total_paid = calculate_order_paid_amount(session, order.id)
        if total_paid >= order.total_amount:
            order.status = OrderStatus.PAID
            session.add(order)
            logger.info(f"Order {order.id} marked as PAID")
        else:
            # Partial payment
            order.status = OrderStatus.IN_PROGRESS  # Keep in progress until fully paid
            session.add(order)
            logger.info(f"Order {order.id} partially paid: {total_paid}/{order.total_amount}")

    session.commit()

    # Broadcast WebSocket events
    import asyncio
    asyncio.create_task(manager.send_payment_completed(
        payment_id=payment.id,
        order_id=payment_intent.order_id,
        table_session_id=order.table_session_id if order else None,
        amount=float(payment.amount),
        method="qr"
    ))


def process_cancelled_payment(
    session: Session,
    payment_intent: PaymentIntent,
    reason: str
):
    """
    Process cancelled payment webhook
    """
    logger.info(f"Processing cancelled payment: {payment_intent.id}, reason: {reason}")

    payment = session.exec(
        select(Payment).where(
            (Payment.payment_intent_id == payment_intent.id) &
            (Payment.method == "qr")
        )
    ).first()

    if payment:
        payment.status = PaymentStatus.FAILED
        payment.failed_at = datetime.utcnow()
        session.add(payment)

    payment_intent.transition_to_cancelled(reason)

    session.commit()


def process_failed_payment(
    session: Session,
    payment_intent: PaymentIntent,
    reason: str
):
    """
    Process failed payment webhook
    """
    logger.info(f"Processing failed payment: {payment_intent.id}, reason: {reason}")

    payment = session.exec(
        select(Payment).where(
            (Payment.payment_intent_id == payment_intent.id) &
            (Payment.method == "qr")
        )
    ).first()

    if payment:
        payment.status = PaymentStatus.FAILED
        payment.failed_at = datetime.utcnow()
        session.add(payment)

    payment_intent.transition_to_failed(reason)

    session.commit()


def calculate_order_paid_amount(session: Session, order_id: str) -> float:
    """
    Calculate total amount paid for an order
    """
    from sqlmodel import sum as sql_sum

    total = session.exec(
        sql_sum(Payment.amount).where(
            (Payment.order_id == order_id) &
            (Payment.status == PaymentStatus.COMPLETED)
        )
    ).one()

    return total if total else 0.0
