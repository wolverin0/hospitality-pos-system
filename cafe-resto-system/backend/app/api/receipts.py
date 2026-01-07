"""
Receipt generation and management API endpoints
Handles receipt creation, reprinting, and formatting
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from datetime import datetime
from typing import List, Optional
from decimal import Decimal
import uuid

from app.core.database import get_session
from app.core.dependencies import get_current_user
from app.models import (
    Receipt, ReceiptType, Order, Payment, Refund, Shift,
    OrderLineItem, OrderAdjustment, User, TableSession
)
from app.api.schemas import (
    ReceiptCreate, ReceiptRead, ReceiptPrintFormat
)

router = APIRouter(prefix="/api/v1/receipts", tags=["receipts"])


def _generate_receipt_number(session: Session, tenant_id: uuid.UUID) -> str:
    """Generate next receipt number for tenant"""
    # Get last receipt for this tenant
    last_receipt = session.exec(
        select(Receipt)
        .where(Receipt.tenant_id == tenant_id)
        .order_by(Receipt.printed_at.desc())
    ).first()

    if last_receipt and last_receipt.receipt_number:
        last_num = int(last_receipt.receipt_number)
        return str(last_num + 1)
    else:
        return "1001"  # Starting receipt number


def _format_order_receipt(
    order: Order,
    line_items: List[OrderLineItem],
    payments: List[Payment],
    adjustments: List[OrderAdjustment],
    table_session: Optional[TableSession]
) -> str:
    """Format order receipt as text for thermal printer"""
    lines = []
    lines.append("=" * 40)
    lines.append(f"Order #{order.id}")
    lines.append(f"Date: {order.created_at.strftime('%Y-%m-%d %H:%M')}")
    lines.append("=" * 40)
    lines.append("")

    if table_session:
        lines.append(f"Table: {table_session.table_number}")

    lines.append("")
    lines.append("Items:")
    lines.append("-" * 40)

    for item in line_items:
        if not item.is_voided:
            lines.append(f"{item.name} x{item.quantity}")
            lines.append(f"  ${item.price_at_order:.2f} each")
            if item.special_instructions:
                lines.append(f"  Note: {item.special_instructions}")

    lines.append("-" * 40)
    lines.append("")

    # Subtotal
    lines.append(f"Subtotal: ${order.subtotal:.2f}")

    # Adjustments
    if adjustments:
        lines.append("Discounts:")
        for adj in adjustments:
            if adj.is_visible_to_customer:
                display_name = adj.display_name or adj.adjustment_type.value
                lines.append(f"  {display_name}: -${adj.amount:.2f}")
        lines.append("")

    # Totals
    lines.append(f"Tax: ${order.tax_amount:.2f}")
    if order.service_charge > 0:
        lines.append(f"Service Charge: ${order.service_charge:.2f}")
    if order.tip_amount > 0:
        lines.append(f"Tip: ${order.tip_amount:.2f}")
    lines.append("-" * 40)
    lines.append(f"TOTAL: ${order.total_amount:.2f}")
    lines.append("=" * 40)
    lines.append("")

    # Payments
    if payments:
        lines.append("Payment Method:")
        for payment in payments:
            if payment.status == "completed":
                method_name = payment.method.value.title()
                lines.append(f"  {method_name}: ${payment.amount:.2f}")
        lines.append("")

    lines.append("=" * 40)
    lines.append("Thank you for dining with us!")
    lines.append("=" * 40)

    return "\n".join(lines)


def _format_refund_receipt(
    refund: Refund,
    payment: Payment,
    order: Order
) -> str:
    """Format refund receipt as text"""
    lines = []
    lines.append("=" * 40)
    lines.append("REFUND RECEIPT")
    lines.append(f"Date: {refund.created_at.strftime('%Y-%m-%d %H:%M')}")
    lines.append("=" * 40)
    lines.append("")
    lines.append(f"Refund Amount: ${refund.amount:.2f}")
    lines.append(f"Reason: {refund.reason}")
    lines.append(f"Reason Code: {refund.reason_code.value}")
    lines.append("")
    lines.append(f"Original Payment ID: {payment.id}")
    lines.append(f"Order ID: {order.id}")
    lines.append("")
    lines.append("=" * 40)
    lines.append("Refund processed successfully")
    lines.append("=" * 40)

    return "\n".join(lines)


def _format_shift_report_receipt(
    shift: Shift,
    cash_events: List
) -> str:
    """Format shift report receipt"""
    lines = []
    lines.append("=" * 40)
    lines.append("SHIFT REPORT")
    lines.append(f"Shift ID: {shift.id}")
    lines.append(f"Opened: {shift.opened_at.strftime('%Y-%m-%d %H:%M')}")
    if shift.closed_at:
        lines.append(f"Closed: {shift.closed_at.strftime('%Y-%m-%d %H:%M')}")
    lines.append("=" * 40)
    lines.append("")

    lines.append(f"Opening Balance: ${shift.opening_balance:.2f}")
    lines.append("")
    lines.append("Sales:")
    lines.append(f"  Cash Sales: ${shift.cash_sales:.2f}")
    lines.append(f"  Card Sales: ${shift.card_sales:.2f}")
    lines.append(f"  Total Sales: ${shift.cash_sales + shift.card_sales:.2f}")
    lines.append("")
    lines.append(f"Tips: ${shift.tip_sales:.2f}")
    lines.append("")

    if shift.closing_cash_count is not None:
        lines.append("Closing Counts:")
        lines.append(f"  Cash Count: ${shift.closing_cash_count:.2f}")
        lines.append(f"  Card Count: ${shift.card_count:.2f}")
        lines.append("")

        if shift.expected_cash is not None:
            lines.append("Reconciliation:")
            lines.append(f"  Expected Cash: ${shift.expected_cash:.2f}")
            lines.append(f"  Actual Cash: ${shift.closing_cash_count:.2f}")
            lines.append(f"  Variance: ${shift.cash_variance:.2f}")

            if shift.cash_variance == 0:
                lines.append("  Status: BALANCED")
            elif shift.cash_variance < 0:
                lines.append("  Status: SHORT")
            else:
                lines.append("  Status: OVER")
    lines.append("")

    lines.append("=" * 40)
    lines.append("End of Shift Report")
    lines.append("=" * 40)

    return "\n".join(lines)


@router.post("/", response_model=ReceiptRead, status_code=status.HTTP_201_CREATED)
def create_receipt(
    receipt_data: ReceiptCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Generate receipt for order, refund, or shift_report"""
    # Validate exactly one ID is provided
    ids_provided = sum([
        receipt_data.order_id is not None,
        receipt_data.refund_id is not None,
        receipt_data.shift_id is not None
    ])

    if ids_provided != 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Must provide exactly one of: order_id, refund_id, or shift_id"
        )

    # Generate receipt number
    receipt_number = _generate_receipt_number(session, current_user.tenant_id)

    receipt_data_json = {}

    # Build receipt data based on type
    if receipt_data.order_id:
        # Order receipt
        order = session.get(Order, receipt_data.order_id)
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

        # Get related data
        line_items = session.exec(
            select(OrderLineItem).where(OrderLineItem.order_id == order.id)
        ).all()

        payments = session.exec(
            select(Payment).where(Payment.order_id == order.id)
        ).all()

        adjustments = session.exec(
            select(OrderAdjustment).where(OrderAdjustment.order_id == order.id)
        ).all()

        table_session = session.get(TableSession, order.table_session_id)

        receipt_data_json = {
            "receipt_number": receipt_number,
            "printed_at": datetime.utcnow().isoformat(),
            "order_id": str(order.id),
            "table_number": table_session.table_number if table_session else None,
            "guest_count": order.guest_count,
            "server_name": f"{order.server.first_name} {order.server.last_name}" if order.server else None,
            "items": [
                {
                    "name": item.name,
                    "quantity": item.quantity,
                    "price": float(item.price_at_order),
                    "total": float(item.line_total)
                }
                for item in line_items if not item.is_voided
            ],
            "subtotal": float(order.subtotal),
            "tax": float(order.tax_amount),
            "discount": float(order.discount_amount),
            "service_charge": float(order.service_charge),
            "tip": float(order.tip_amount),
            "total": float(order.total_amount),
            "payment_methods": [
                f"{p.method.value}: ${p.amount:.2f}"
                for p in payments if p.status == "completed"
            ]
        }

    elif receipt_data.refund_id:
        # Refund receipt
        refund = session.get(Refund, receipt_data.refund_id)
        if not refund:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Refund not found"
            )

        if refund.tenant_id != current_user.tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )

        payment = session.get(Payment, refund.original_payment_id)
        order = session.get(Order, refund.order_id)

        receipt_data_json = {
            "receipt_number": receipt_number,
            "printed_at": datetime.utcnow().isoformat(),
            "refund_id": str(refund.id),
            "payment_id": str(refund.original_payment_id),
            "order_id": str(order.id),
            "amount": float(refund.amount),
            "reason": refund.reason,
            "reason_code": refund.reason_code.value
        }

    elif receipt_data.shift_id:
        # Shift report receipt
        shift = session.get(Shift, receipt_data.shift_id)
        if not shift:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Shift not found"
            )

        if shift.tenant_id != current_user.tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )

        cash_events = session.exec(
            select().where(CashDrawerEvent.shift_id == shift.id)
        ).all()

        server_name = f"{shift.server.first_name} {shift.server.last_name}" if shift.server else None

        receipt_data_json = {
            "receipt_number": receipt_number,
            "printed_at": datetime.utcnow().isoformat(),
            "shift_id": str(shift.id),
            "server_name": server_name,
            "opened_at": shift.opened_at.isoformat(),
            "closed_at": shift.closed_at.isoformat() if shift.closed_at else None,
            "opening_balance": float(shift.opening_balance),
            "cash_sales": float(shift.cash_sales),
            "card_sales": float(shift.card_sales),
            "tip_sales": float(shift.tip_sales),
            "closing_cash": float(shift.closing_cash_count) if shift.closing_cash_count else None,
            "expected_cash": float(shift.expected_cash) if shift.expected_cash else None,
            "variance": float(shift.cash_variance) if shift.cash_variance else None,
            "is_short": (shift.cash_variance < 0) if shift.cash_variance is not None else None,
            "cash_events": [
                {
                    "event_type": ce.event_type.value,
                    "amount": float(ce.amount),
                    "balance_after": float(ce.balance_after)
                }
                for ce in cash_events
            ]
        }

    # Create receipt
    receipt = Receipt(
        tenant_id=current_user.tenant_id,
        order_id=receipt_data.order_id,
        refund_id=receipt_data.refund_id,
        shift_id=receipt_data.shift_id,
        receipt_type=receipt_data.receipt_type,
        receipt_number=receipt_number,
        printed_by=current_user.id,
        receipt_data=receipt_data_json
    )

    session.add(receipt)
    session.commit()
    session.refresh(receipt)

    return receipt


@router.get("/", response_model=List[ReceiptRead])
def list_receipts(
    order_id: Optional[uuid.UUID] = None,
    refund_id: Optional[uuid.UUID] = None,
    shift_id: Optional[uuid.UUID] = None,
    receipt_type: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    skip: int = 0,
    limit: int = 100,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """List receipts with optional filters"""
    query = select(Receipt).where(Receipt.tenant_id == current_user.tenant_id)

    if order_id:
        query = query.where(Receipt.order_id == order_id)
    if refund_id:
        query = query.where(Receipt.refund_id == refund_id)
    if shift_id:
        query = query.where(Receipt.shift_id == shift_id)
    if receipt_type:
        query = query.where(Receipt.receipt_type == receipt_type)
    if date_from:
        query = query.where(Receipt.printed_at >= date_from)
    if date_to:
        query = query.where(Receipt.printed_at <= date_to)

    # Apply pagination
    query = query.offset(skip).limit(limit)
    receipts = session.exec(query).all()

    return receipts


@router.get("/{receipt_id}", response_model=ReceiptRead)
def get_receipt(
    receipt_id: uuid.UUID,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Get receipt by ID"""
    receipt = session.get(Receipt, receipt_id)
    if not receipt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Receipt not found"
        )

    if receipt.tenant_id != current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    return receipt


@router.post("/{receipt_id}/reprint", response_model=ReceiptRead)
def reprint_receipt(
    receipt_id: uuid.UUID,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Reprint receipt (any staff can reprint)"""
    receipt = session.get(Receipt, receipt_id)
    if not receipt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Receipt not found"
        )

    if receipt.tenant_id != current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    # Update reprint info
    receipt.reprinted_at = datetime.utcnow()
    receipt.reprint_count += 1
    receipt.printed_by = current_user.id

    session.add(receipt)
    session.commit()
    session.refresh(receipt)

    return receipt


@router.get("/{receipt_id}/print", response_model=ReceiptPrintFormat)
def get_printable_receipt(
    receipt_id: uuid.UUID,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Get receipt formatted as text for thermal printer"""
    receipt = session.get(Receipt, receipt_id)
    if not receipt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Receipt not found"
        )

    if receipt.tenant_id != current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )

    # Get related data for formatting
    formatted_text = ""

    if receipt.order_id:
        order = session.get(Order, receipt.order_id)
        line_items = session.exec(
            select(OrderLineItem).where(OrderLineItem.order_id == order.id)
        ).all()
        payments = session.exec(
            select(Payment).where(Payment.order_id == order.id)
        ).all()
        adjustments = session.exec(
            select(OrderAdjustment).where(OrderAdjustment.order_id == order.id)
        ).all()
        table_session = session.get(TableSession, order.table_session_id)

        formatted_text = _format_order_receipt(
            order, line_items, payments, adjustments, table_session
        )

    elif receipt.refund_id:
        refund = session.get(Refund, receipt.refund_id)
        payment = session.get(Payment, refund.original_payment_id)
        order = session.get(Order, refund.order_id)

        formatted_text = _format_refund_receipt(refund, payment, order)

    elif receipt.shift_id:
        shift = session.get(Shift, receipt.shift_id)
        # In production, you'd get cash events properly
        # For now, use empty list
        formatted_text = _format_shift_report_receipt(shift, [])

    return ReceiptPrintFormat(
        receipt_number=receipt.receipt_number,
        printed_at=receipt.printed_at,
        formatted_text=formatted_text
    )
