"""
API schemas for Order, Payment, Receipt, Shift, and related models
"""

from sqlmodel import SQLModel
from datetime import datetime
from typing import Optional, List
from decimal import Decimal
from app.models.order import Order, OrderStatus
from app.models.order_line_item import OrderLineItem, PreparationStatus
from app.models.payment import Payment, PaymentMethod, PaymentStatus
from app.models.payment_intent import PaymentIntent, PaymentIntentStatus
from app.models.refund import Refund, RefundStatus, RefundReasonCode
from app.models.receipt import Receipt, ReceiptType
from app.models.shift import Shift, ShiftStatus
from app.models.order_adjustment import OrderAdjustment, AdjustmentType
from app.models.cash_drawer_event import CashDrawerEvent, CashDrawerEventType
import uuid

# ============================================================================
# Order Schemas
# ============================================================================

class OrderCreate(SQLModel):
    draft_order_id: uuid.UUID
    server_id: uuid.UUID
    guest_count: Optional[int] = None
    special_requests: Optional[str] = None
    order_notes: Optional[str] = None


class OrderUpdate(SQLModel):
    status: Optional[OrderStatus] = None
    version: int


class OrderLineItemRead(SQLModel):
    id: uuid.UUID
    order_id: uuid.UUID
    menu_item_id: Optional[uuid.UUID] = None
    name: str
    description: Optional[str] = None
    quantity: int
    unit_price: Decimal
    price_at_order: Decimal
    line_total: Decimal
    special_instructions: Optional[str] = None
    preparation_status: PreparationStatus
    is_voided: bool
    is_comped: bool
    discount_amount: Decimal

    class Config:
        from_attributes = True


class OrderRead(SQLModel):
    id: uuid.UUID
    table_session_id: uuid.UUID
    server_id: uuid.UUID
    draft_order_id: uuid.UUID
    status: OrderStatus
    created_at: datetime
    updated_at: Optional[datetime] = None
    confirmed_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    subtotal: Decimal
    tax_amount: Decimal
    discount_amount: Decimal
    service_charge: Decimal
    total_amount: Decimal
    tip_amount: Decimal
    guest_count: Optional[int] = None
    special_requests: Optional[str] = None
    order_notes: Optional[str] = None
    is_rush: bool
    priority_level: Optional[int] = None
    version: int

    class Config:
        from_attributes = True


class OrderListResponse(SQLModel):
    items: List[OrderRead]
    total: int
    page: int
    page_size: int


# ============================================================================
# Payment Intent Schemas
# ============================================================================

class PaymentIntentCreate(SQLModel):
    order_id: uuid.UUID
    amount: Decimal
    method: PaymentMethod
    idempotency_key: Optional[str] = None
    qr_mode: Optional[str] = "static"  # "static" or "dynamic"
    table_id: Optional[str] = None
    expiration_minutes: Optional[int] = 30
    tip_amount: Optional[Decimal] = None


class PaymentIntentRead(SQLModel):
    id: uuid.UUID
    order_id: uuid.UUID
    amount: Decimal
    currency: str
    method: PaymentMethod
    status: PaymentIntentStatus
    qr_code: Optional[str] = None
    qr_provider: Optional[str] = None
    qr_expires_at: Optional[datetime] = None
    idempotency_key: Optional[str] = None
    tip_amount: Optional[Decimal] = None
    client_secret: Optional[str] = None
    payment_intent_reference: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    processed_at: Optional[datetime] = None
    failed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ============================================================================
# Payment Schemas
# ============================================================================

class PaymentCreate(SQLModel):
    order_id: uuid.UUID
    amount: Decimal
    method: PaymentMethod
    card_last_4: Optional[str] = None
    card_holder_name: Optional[str] = None
    terminal_reference_id: Optional[str] = None
    qr_code: Optional[str] = None
    qr_provider: Optional[str] = None


class PaymentUpdate(SQLModel):
    status: Optional[PaymentStatus] = None
    version: int


class PaymentRead(SQLModel):
    id: uuid.UUID
    order_id: uuid.UUID
    payment_intent_id: Optional[uuid.UUID] = None
    amount: Decimal
    currency: str
    method: PaymentMethod
    status: PaymentStatus
    created_at: datetime
    updated_at: Optional[datetime] = None
    processed_at: Optional[datetime] = None
    failed_at: Optional[datetime] = None
    refunded_at: Optional[datetime] = None
    card_last_4: Optional[str] = None
    card_holder_name: Optional[str] = None
    terminal_reference_id: Optional[str] = None
    qr_code: Optional[str] = None
    processing_fee: Optional[Decimal] = None
    version: int

    class Config:
        from_attributes = True


# ============================================================================
# Refund Schemas
# ============================================================================

class RefundCreate(SQLModel):
    payment_id: uuid.UUID
    order_id: uuid.UUID
    amount: Decimal
    reason_code: RefundReasonCode
    reason: str


class RefundRead(SQLModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    original_payment_id: uuid.UUID
    order_id: uuid.UUID
    amount: Decimal
    currency: str
    status: RefundStatus
    reason_code: RefundReasonCode
    reason: str
    created_by: uuid.UUID
    processed_by: Optional[uuid.UUID] = None
    authorized_by: Optional[uuid.UUID] = None
    refund_reference_id: Optional[str] = None
    external_refund_id: Optional[str] = None
    created_at: datetime
    processed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ============================================================================
# Receipt Schemas
# ============================================================================

class ReceiptCreate(SQLModel):
    order_id: Optional[uuid.UUID] = None
    refund_id: Optional[uuid.UUID] = None
    shift_id: Optional[uuid.UUID] = None
    receipt_type: ReceiptType


class ReceiptRead(SQLModel):
    id: uuid.UUID
    order_id: Optional[uuid.UUID] = None
    refund_id: Optional[uuid.UUID] = None
    payment_id: Optional[uuid.UUID] = None
    shift_id: Optional[uuid.UUID] = None
    receipt_type: ReceiptType
    receipt_number: str
    printed_at: datetime
    printed_by: uuid.UUID
    reprinted_at: Optional[datetime] = None
    reprint_count: int
    printed_to_printer: Optional[str] = None
    receipt_data: Optional[dict] = None

    class Config:
        from_attributes = True


class ReceiptPrintFormat(SQLModel):
    receipt_number: str
    printed_at: datetime
    formatted_text: str


# ============================================================================
# Shift Schemas
# ============================================================================

class ShiftCreate(SQLModel):
    server_id: uuid.UUID
    location_id: uuid.UUID
    opening_balance: Decimal
    opening_notes: Optional[str] = None


class ShiftUpdate(SQLModel):
    status: Optional[ShiftStatus] = None
    closing_cash_count: Optional[Decimal] = None
    card_count: Optional[Decimal] = None
    closing_notes: Optional[str] = None
    reconciliation_notes: Optional[str] = None
    version: int


class ShiftRead(SQLModel):
    id: uuid.UUID
    server_id: uuid.UUID
    location_id: uuid.UUID
    status: ShiftStatus
    opened_at: datetime
    closed_at: Optional[datetime] = None
    reconciled_at: Optional[datetime] = None
    opening_balance: Decimal
    cash_sales: Decimal
    card_sales: Decimal
    tip_sales: Decimal
    closing_cash_count: Optional[Decimal] = None
    card_count: Optional[Decimal] = None
    expected_cash: Optional[Decimal] = None
    cash_variance: Optional[Decimal] = None
    is_over: Optional[bool] = None
    total_break_time_minutes: int
    break_count: int
    opening_notes: Optional[str] = None
    closing_notes: Optional[str] = None
    reconciliation_notes: Optional[str] = None
    opened_by: uuid.UUID
    closed_by: Optional[uuid.UUID] = None
    reconciled_by: Optional[uuid.UUID] = None
    version: int

    class Config:
        from_attributes = True


class ShiftCashDropCreate(SQLModel):
    amount: Decimal
    reason: str


class ShiftTipPayoutCreate(SQLModel):
    amount: Decimal
    reason: str


class ShiftAdjustmentCreate(SQLModel):
    amount: Decimal
    reason: str


# ============================================================================
# Order Adjustment Schemas
# ============================================================================

class OrderAdjustmentCreate(SQLModel):
    order_id: uuid.UUID
    order_line_item_id: Optional[uuid.UUID] = None
    adjustment_type: AdjustmentType
    amount: Decimal
    percentage: Optional[Decimal] = None
    reason: str
    notes: Optional[str] = None
    promo_code: Optional[str] = None


class OrderAdjustmentRead(SQLModel):
    id: uuid.UUID
    order_id: uuid.UUID
    order_line_item_id: Optional[uuid.UUID] = None
    adjustment_type: AdjustmentType
    amount: Decimal
    percentage: Optional[Decimal] = None
    original_amount: Optional[Decimal] = None
    new_amount: Optional[Decimal] = None
    reason: str
    notes: Optional[str] = None
    authorized_by: uuid.UUID
    requires_manager_approval: bool
    is_visible_to_customer: bool
    display_name: Optional[str] = None
    promo_code: Optional[str] = None
    applied_at: datetime
    applied_by: uuid.UUID
    version: int

    class Config:
        from_attributes = True
