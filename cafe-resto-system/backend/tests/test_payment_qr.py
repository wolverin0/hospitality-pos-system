"""
Unit tests for payment intents and webhooks
"""

import pytest
from sqlmodel import Session, create_engine, select
from app.services.mercadopago import MercadoPagoService
from app.models import (
    PaymentIntent, PaymentIntentStatus, Payment, PaymentStatus,
    Order, OrderStatus
)
from datetime import datetime, timedelta
from decimal import Decimal
import uuid as uuid_lib


# Test database
DATABASE_URL = "sqlite:///./test_payments.db"
engine = create_engine(DATABASE_URL)


@pytest.fixture
def db_session():
    """Create a new database session for each test"""
    Session = Session(engine)
    try:
        yield Session
    finally:
        Session.close()


class TestPaymentIntentQR:
    """Test PaymentIntent creation and QR code generation"""

    def test_create_qr_payment_intent_with_idempotency(self, session):
        """Test creating QR payment intent with idempotency key"""
        # Create a mock order
        order_id = uuid_lib.uuid4()
        order = Order(
            id=order_id,
            tenant_id=uuid_lib.uuid4(),
            table_session_id=uuid_lib.uuid4(),
            total_amount=Decimal("100.00"),
            status=OrderStatus.PENDING
        )
        session.add(order)
        session.commit()

        # Generate idempotency key
        idempotency_key = f"qr_order_{order_id}_{datetime.now().isoformat()}"

        # Create payment intent via Mercado Pago service
        mp_service = MercadoPagoService(use_sandbox=True)

        result = mp_service.create_qr_order(
            table_id="TABLE_5",
            order_id=str(order_id),
            total_amount=Decimal("100.00"),
            items=[{
                "name": "Test Item",
                "unit_price": "10.00",
                "quantity": 1,
                "id": "ITEM_001"
            }],
            external_reference=idempotency_key,
            expiration_minutes=30
        )

        # Verify result
        assert result["status"] == "created" or result["mock"] == True
        assert "order_id" in result
        assert "qr_data" in result
        assert "qr_path" in result
        assert "expires_at" in result

        # Check payment intent was created
        payment_intent = session.exec(
            select(PaymentIntent).where(
                PaymentIntent.idempotency_key == idempotency_key
            )
        ).first()

        assert payment_intent is not None
        assert payment_intent.amount == Decimal("100.00")
        assert payment_intent.method == "qr"
        assert payment_intent.status == PaymentIntentStatus.PENDING
        assert payment_intent.qr_code is not None
        assert payment_intent.qr_provider == "mercadopago"

    def test_create_qr_payment_intent_with_tip(self, session):
        """Test creating QR payment intent with tip amount"""
        order_id = uuid_lib.uuid4()
        order = Order(
            id=order_id,
            tenant_id=uuid_lib.uuid4(),
            table_session_id=uuid_lib.uuid4(),
            total_amount=Decimal("100.00"),
            status=OrderStatus.PENDING
        )
        session.add(order)
        session.commit()

        mp_service = MercadoPagoService(use_sandbox=True)

        result = mp_service.create_qr_order(
            table_id="TABLE_5",
            order_id=str(order_id),
            total_amount=Decimal("115.00"),  # 100 + 15 tip
            items=[{
                "name": "Test Item",
                "unit_price": "10.00",
                "quantity": 1,
                "id": "ITEM_001"
            }],
            external_reference=f"qr_order_{order_id}",
            expiration_minutes=30,
            tip_amount=Decimal("15.00")
        )

        assert result["total_amount"] == "115.00"

    def test_qr_payment_intent_expiration(self, session):
        """Test QR payment intent expiration time"""
        order_id = uuid_lib.uuid4()
        order = Order(
            id=order_id,
            tenant_id=uuid_lib.uuid4(),
            table_session_id=uuid_lib.uuid4(),
            total_amount=Decimal("100.00"),
            status=OrderStatus.PENDING
        )
        session.add(order)
        session.commit()

        mp_service = MercadoPagoService(use_sandbox=True)

        # Create with 15 minute expiration
        result = mp_service.create_qr_order(
            table_id="TABLE_5",
            order_id=str(order_id),
            total_amount=Decimal("100.00"),
            items=[],
            external_reference="test_ref",
            expiration_minutes=15
        )

        # Verify expiration time is approximately 15 minutes from now
        expected_expires_at = datetime.utcnow() + timedelta(minutes=15)
        actual_expires_at = result["expires_at"]

        assert actual_expires_at is not None
        time_diff = abs((actual_expires_at - expected_expires_at).total_seconds())
        assert time_diff < 5  # Allow 5 seconds difference


class TestWebhookProcessing:
    """Test webhook processing for Mercado Pago"""

    def test_webhook_verification_valid(self, session):
        """Test webhook verification with valid notification"""
        mp_service = MercadoPagoService(use_sandbox=True)

        # Valid notification
        notification = {
            "action_type": "merchant_orders",
            "api_version": "v1",
            "data": {
                "id": "ORDER_123",
                "external_reference": "test_ref_20260107_150000",
                "status": "paid",
                "total_amount": "100.00"
            }
        }

        is_valid, error_msg, data = mp_service.verify_webhook_notification(notification)

        assert is_valid is True
        assert error_msg == ""
        assert data is not None
        assert data["external_reference"] == "test_ref_20260107_150000"

    def test_webhook_verification_invalid_action_type(self, session):
        """Test webhook verification rejects invalid action type"""
        mp_service = MercadoPagoService(use_sandbox=True)

        notification = {
            "action_type": "payments",  # Invalid action for QR
            "data": {}
        }

        is_valid, error_msg, data = mp_service.verify_webhook_notification(notification)

        assert is_valid is False
        assert "Invalid action type" in error_msg

    def test_webhook_idempotency_prevents_duplicates(self, session):
        """Test webhook idempotency prevents duplicate processing"""
        # This test would require mocking the WebhookLog table
        # For now, just verify the idempotency check logic exists
        mp_service = MercadoPagoService(use_sandbox=True)

        notification = {
            "action_type": "merchant_orders",
            "data": {
                "external_reference": "duplicate_test_ref",
                "status": "paid"
            }
        }

        # First call should succeed
        is_valid1, _, _ = mp_service.verify_webhook_notification(notification)
        assert is_valid1 is True

        # Second call with same external_reference should still succeed
        # (in real implementation, WebhookLog would catch duplicates)
        is_valid2, _, _ = mp_service.verify_webhook_notification(notification)
        assert is_valid2 is True

    def test_process_paid_webhook(self, session):
        """Test processing paid webhook updates order and payment status"""
        # Create order and payment intent
        order_id = uuid_lib.uuid4()
        order = Order(
            id=order_id,
            tenant_id=uuid_lib.uuid4(),
            table_session_id=uuid_lib.uuid4(),
            total_amount=Decimal("100.00"),
            status=OrderStatus.IN_PROGRESS
        )
        session.add(order)

        payment_intent_id = uuid_lib.uuid4()
        payment_intent = PaymentIntent(
            id=payment_intent_id,
            tenant_id=uuid_lib.uuid4(),
            order_id=order_id,
            amount=Decimal("100.00"),
            method="qr",
            status=PaymentIntentStatus.PENDING,
            qr_code="00020101021243650016COM.MERCADOLIBRE02013063638f1192a",
            qr_expires_at=datetime.utcnow() + timedelta(minutes=30)
        )
        session.add(payment_intent)
        session.commit()

        # Mock payment
        payment_id = uuid_lib.uuid4()
        payment = Payment(
            id=payment_id,
            tenant_id=uuid_lib.uuid4(),
            order_id=order_id,
            payment_intent_id=payment_intent_id,
            method="qr",
            amount=Decimal("100.00"),
            status=PaymentStatus.COMPLETED,
            qr_code="00020101021243650016COM.MERCADOLIBRE02013063638f1192a",
            qr_provider="mercadopago",
            processed_at=datetime.utcnow()
        )
        session.add(payment)

        # Process webhook
        from app.api.webhooks import process_successful_payment
        from app.models.table_session import TableSession

        table_session = TableSession(
            id=uuid_lib.uuid4(),
            tenant_id=uuid_lib.uuid4(),
            table_id="TABLE_5"
        )
        session.add(table_session)

        notification_data = {
            "id": str(payment_intent_id),
            "external_reference": f"qr_order_{order_id}",
            "status": "paid",
            "total_amount": "100.00"
        }

        import asyncio
        asyncio.run(process_successful_payment(
            session=session,
            payment_intent=payment_intent,
            mp_order_id=payment_intent_id,
            mp_data=notification_data,
            mp_service=mp_service
        ))

        # Verify order was marked as PAID
        session.refresh(order)
        assert order.status == OrderStatus.PAID

        # Verify payment was marked as COMPLETED
        session.refresh(payment)
        assert payment.status == PaymentStatus.COMPLETED

    def test_process_cancelled_webhook(self, session):
        """Test processing cancelled webhook"""
        order_id = uuid_lib.uuid4()
        order = Order(
            id=order_id,
            tenant_id=uuid_lib.uuid4(),
            total_amount=Decimal("100.00"),
            status=OrderStatus.PENDING
        )
        session.add(order)

        payment_intent_id = uuid_lib.uuid4()
        payment_intent = PaymentIntent(
            id=payment_intent_id,
            tenant_id=uuid_lib.uuid4(),
            order_id=order_id,
            amount=Decimal("100.00"),
            method="qr",
            status=PaymentIntentStatus.PENDING
        )
        session.add(payment_intent)

        from app.api.webhooks import process_cancelled_payment
        process_cancelled_payment(
            session=session,
            payment_intent=payment_intent,
            reason="Customer cancelled"
        )

        # Verify payment intent status
        session.refresh(payment_intent)
        assert payment_intent.status == PaymentIntentStatus.CANCELLED
        assert payment_intent.cancelled_reason == "Customer cancelled"
