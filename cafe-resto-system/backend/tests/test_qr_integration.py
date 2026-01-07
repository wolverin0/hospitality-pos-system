"""
Integration tests for QR payment flow
Tests end-to-end QR payment: create intent -> webhook -> payment completed
"""

import pytest
import asyncio
from sqlmodel import Session, create_engine, select
from app.services.mercadopago import MercadoPagoService
from app.models import (
    PaymentIntent, PaymentIntentStatus, Payment, PaymentStatus,
    Order, OrderStatus, TableSession
)
from app.api.webhooks import process_successful_payment
from datetime import datetime, timedelta
from decimal import Decimal
import uuid as uuid_lib


# Test database
DATABASE_URL = "sqlite:///./test_qr_integration.db"
engine = create_engine(DATABASE_URL)


@pytest.fixture
def session():
    """Create a new database session for each test"""
    Session = Session(engine)
    try:
        yield Session
    finally:
        Session.close()


class TestQRPaymentFlow:
    """End-to-end QR payment integration tests"""

    def test_complete_qr_payment_flow(self, session):
        """Test complete QR payment flow:
        1. Create order
        2. Create QR payment intent
        3. Simulate Mercado Pago webhook (paid)
        4. Verify payment status
        5. Verify order status
        """
        # Create table session and order
        table_session_id = uuid_lib.uuid4()
        table_session = TableSession(
            id=table_session_id,
            tenant_id=uuid_lib.uuid4(),
            table_id="TABLE_5",
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(hours=4)
        )
        session.add(table_session)

        order_id = uuid_lib.uuid4()
        order = Order(
            id=order_id,
            tenant_id=uuid_lib.uuid4(),
            table_session_id=table_session_id,
            status=OrderStatus.PENDING,
            total_amount=Decimal("100.00"),
            created_at=datetime.utcnow()
        )
        session.add(order)
        session.commit()

        # Create QR payment intent
        mp_service = MercadoPagoService(use_sandbox=True)
        idempotency_key = f"qr_order_{order_id}_{datetime.now().isoformat()}"

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

        assert result["status"] == "created" or result["mock"] == True
        qr_data = result["qr_data"]

        # Payment intent should be created
        payment_intent = session.exec(
            select(PaymentIntent).where(
                PaymentIntent.idempotency_key == idempotency_key
            )
        ).first()

        assert payment_intent is not None
        assert payment_intent.amount == Decimal("100.00")
        assert payment_intent.status == PaymentIntentStatus.PENDING
        assert payment_intent.qr_code == qr_data
        assert payment_intent.qr_provider == "mercadopago"

        # Simulate webhook notification
        notification = {
            "action_type": "merchant_orders",
            "api_version": "v1",
            "data": {
                "id": result.get("order_id", ""),
                "external_reference": idempotency_key,
                "status": "paid",
                "total_amount": "100.00"
            }
        }

        # Process webhook synchronously for test
        asyncio.run(process_successful_payment(
            session=session,
            payment_intent=payment_intent,
            mp_order_id=result.get("order_id", ""),
            mp_data=notification["data"],
            mp_service=mp_service
        ))

        # Verify payment is completed
        session.refresh(payment)
        assert payment_intent.status == PaymentIntentStatus.COMPLETED

        # Verify payment record exists
        payment = session.exec(
            select(Payment).where(
                (Payment.payment_intent_id == payment_intent.id) &
                (Payment.method == "qr")
            )
        ).first()

        assert payment is not None
        assert payment.status == PaymentStatus.COMPLETED
        assert payment.qr_code == qr_data
        assert payment.processed_at is not None

        # Verify order is marked as PAID
        session.refresh(order)
        assert order.status == OrderStatus.PAID

    def test_qr_payment_with_tip(self, session):
        """Test QR payment with tip amount"""
        # Create table session and order
        table_session_id = uuid_lib.uuid4()
        table_session = TableSession(
            id=table_session_id,
            tenant_id=uuid_lib.uuid4(),
            table_id="TABLE_5",
            created_at=datetime.utcnow()
        )
        session.add(table_session)

        order_id = uuid_lib.uuid4()
        order = Order(
            id=order_id,
            tenant_id=uuid_lib.uuid4(),
            table_session_id=table_session_id,
            status=OrderStatus.PENDING,
            total_amount=Decimal("100.00"),
            created_at=datetime.utcnow()
        )
        session.add(order)
        session.commit()

        # Create QR payment intent with tip
        mp_service = MercadoPagoService(use_sandbox=True)
        idempotency_key = f"qr_order_{order_id}_{datetime.now().isoformat()}"

        result = mp_service.create_qr_order(
            table_id="TABLE_5",
            order_id=str(order_id),
            total_amount=Decimal("115.00"),  # 100 + 15 tip
            items=[],
            external_reference=idempotency_key,
            expiration_minutes=30,
            tip_amount=Decimal("15.00")
        )

        assert result["total_amount"] == "115.00"

        # Process payment
        notification = {
            "action_type": "merchant_orders",
            "api_version": "v1",
            "data": {
                "id": result.get("order_id", ""),
                "external_reference": idempotency_key,
                "status": "paid",
                "total_amount": "115.00"
            }
        }

        asyncio.run(process_successful_payment(
            session=session,
            payment_intent=payment_intent,
            mp_order_id=result.get("order_id", ""),
            mp_data=notification["data"],
            mp_service=mp_service
        ))

        # Verify tip was included
        payment = session.exec(
            select(Payment).where(
                (Payment.payment_intent_id == payment_intent.id) &
                (Payment.method == "qr")
            )
        ).first()

        assert payment is not None
        assert payment.amount == Decimal("115.00")

    def test_qr_payment_expiry(self, session):
        """Test QR payment intent expiration"""
        table_session_id = uuid_lib.uuid4()
        table_session = TableSession(
            id=table_session_id,
            tenant_id=uuid_lib.uuid4(),
            table_id="TABLE_5",
            created_at=datetime.utcnow()
        )
        session.add(table_session)

        order_id = uuid_lib.uuid4()
        order = Order(
            id=order_id,
            tenant_id=uuid_lib.uuid4(),
            table_session_id=table_session_id,
            status=OrderStatus.PENDING,
            total_amount=Decimal("100.00"),
            created_at=datetime.utcnow()
        )
        session.add(order)
        session.commit()

        # Create QR payment intent with 1 minute expiration
        mp_service = MercadoPagoService(use_sandbox=True)
        idempotency_key = f"qr_order_{order_id}_{datetime.now().isoformat()}"

        result = mp_service.create_qr_order(
            table_id="TABLE_5",
            order_id=str(order_id),
            total_amount=Decimal("100.00"),
            items=[],
            external_reference=idempotency_key,
            expiration_minutes=1
        )

        # Verify expiration time is approximately 1 minute from now
        expected_expires_at = datetime.utcnow() + timedelta(minutes=1)
        actual_expires_at = result.get("expires_at")

        assert actual_expires_at is not None
        time_diff = abs((actual_expires_at - expected_expires_at).total_seconds())
        assert time_diff < 5  # Allow 5 seconds difference

    def test_partial_payment_updates_order_status(self, session):
        """Test that partial payment updates order to PARTIALLY_PAID"""
        table_session_id = uuid_lib.uuid4()
        table_session = TableSession(
            id=table_session_id,
            tenant_id=uuid_lib.uuid4(),
            table_id="TABLE_5",
            created_at=datetime.utcnow()
        )
        session.add(table_session)

        order_id = uuid_lib.uuid4()
        order = Order(
            id=order_id,
            tenant_id=uuid_lib.uuid4(),
            table_session_id=table_session_id,
            status=OrderStatus.PENDING,
            total_amount=Decimal("200.00"),  # Two payments of 100 each
            created_at=datetime.utcnow()
        )
        session.add(order)
        session.commit()

        # Create first QR payment (100.00)
        mp_service = MercadoPagoService(use_sandbox=True)
        idempotency_key_1 = f"qr_order_{order_id}_1_{datetime.now().isoformat()}"

        result1 = mp_service.create_qr_order(
            table_id="TABLE_5",
            order_id=str(order_id),
            total_amount=Decimal("100.00"),
            items=[],
            external_reference=idempotency_key_1,
            expiration_minutes=30
        )

        # Process payment
        notification1 = {
            "action_type": "merchant_orders",
            "api_version": "v1",
            "data": {
                "id": result1.get("order_id", ""),
                "external_reference": idempotency_key_1,
                "status": "paid",
                "total_amount": "100.00"
            }
        }

        asyncio.run(process_successful_payment(
            session=session,
            payment_intent_id=result1.get("order_id", ""),
            mp_data=notification1["data"],
            mp_service=mp_service
        ))

        # Create second QR payment (100.00)
        idempotency_key_2 = f"qr_order_{order_id}_2_{datetime.now().isoformat()}"

        result2 = mp_service.create_qr_order(
            table_id="TABLE_5",
            order_id=str(order_id),
            total_amount=Decimal("100.00"),
            items=[],
            external_reference=idempotency_key_2,
            expiration_minutes=30
        )

        # Process second payment
        notification2 = {
            "action_type": "merchant_orders",
            "api_version": "v1",
            "data": {
                "id": result2.get("order_id", ""),
                "external_reference": idempotency_key_2,
                "status": "paid",
                "total_amount": "100.00"
            }
        }

        asyncio.run(process_successful_payment(
            session=session,
            payment_intent_id=result2.get("order_id", ""),
            mp_data=notification2["data"],
            mp_service=mp_service
        ))

        # Verify order is PARTIALLY_PAID (not yet PAID)
        session.refresh(order)
        assert order.status == OrderStatus.PARTIALLY_PAID
