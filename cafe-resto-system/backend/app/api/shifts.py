"""
Shift management API endpoints
Handles shift opening, closing, reconciliation, cash drops, tip payouts
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
    ShiftOpened, ShiftClosed, ShiftReconciled, event_bus
)
from app.models import (
    Shift, ShiftStatus, User, Location,
    CashDrawerEvent, CashDrawerEventType, Order, Payment
)
from app.api.schemas import (
    ShiftCreate, ShiftUpdate, ShiftRead,
    ShiftCashDropCreate, ShiftTipPayoutCreate, ShiftAdjustmentCreate
)

router = APIRouter(prefix="/api/v1/shifts", tags=["shifts"])


@router.post("/open", response_model=ShiftRead, status_code=status.HTTP_201_CREATED)
def open_shift(
    shift_data: ShiftCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Open a new shift"""
    # Check if server has an active shift
    existing_shift = session.exec(
        select(Shift).where(
            (Shift.server_id == shift_data.server_id) &
            (Shift.status == ShiftStatus.ACTIVE)
        )
    ).first()

    if existing_shift:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Server already has an active shift"
        )

    # Create shift
    shift = Shift(
        tenant_id=current_user.tenant_id,
        server_id=shift_data.server_id,
        location_id=shift_data.location_id,
        status=ShiftStatus.ACTIVE,
        opened_at=datetime.utcnow(),
        opening_balance=shift_data.opening_balance,
        opening_notes=shift_data.opening_notes,
        opened_by=current_user.id
    )

    session.add(shift)
    session.commit()
    session.refresh(shift)

    # Broadcast shift opened event
    from asyncio import create_task
    create_task(manager.send_shift_opened(
        shift_id=shift.id,
        server_id=shift.server_id,
        location_id=shift.location_id,
        opening_balance=float(shift.opening_balance)
    ))

    return shift


@router.get("/", response_model=List[ShiftRead])
def list_shifts(
    server_id: Optional[uuid.UUID] = None,
    location_id: Optional[uuid.UUID] = None,
    shift_status: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    skip: int = 0,
    limit: int = 100,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """List shifts with optional filters"""
    query = select(Shift).where(Shift.tenant_id == current_user.tenant_id)

    if server_id:
        query = query.where(Shift.server_id == server_id)
    if location_id:
        query = query.where(Shift.location_id == location_id)
    if shift_status:
        query = query.where(Shift.status == shift_status)
    if date_from:
        query = query.where(Shift.opened_at >= date_from)
    if date_to:
        query = query.where(Shift.opened_at <= date_to)

    # Apply pagination
    query = query.offset(skip).limit(limit)
    shifts = session.exec(query).all()

    return shifts


@router.get("/{shift_id}", response_model=ShiftRead)
def get_shift(
    shift_id: uuid.UUID,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Get shift by ID with cash drawer events"""
    shift = session.get(Shift, shift_id)
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

    return shift


@router.patch("/{shift_id}", response_model=ShiftRead)
def update_shift(
    shift_id: uuid.UUID,
    shift_update: ShiftUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Update shift (begin closing process)"""
    shift = session.get(Shift, shift_id)
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

    # Check version for optimistic concurrency
    if shift.version != shift_update.version:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Shift was modified by another user. Please refresh and try again."
        )

    # Begin closing
    shift.begin_closing()

    # Update fields
    if shift_update.closing_cash_count is not None:
        shift.closing_cash_count = shift_update.closing_cash_count
    if shift_update.card_count is not None:
        shift.card_count = shift_update.card_count
    if shift_update.closing_notes:
        shift.closing_notes = shift_update.closing_notes

    shift.updated_at = datetime.utcnow()
    shift.version += 1

    session.add(shift)
    session.commit()
    session.refresh(shift)

    return shift


@router.post("/{shift_id}/close", response_model=ShiftRead)
def close_shift(
    shift_id: uuid.UUID,
    closing_cash_count: Decimal,
    card_count: Optional[Decimal] = None,
    closing_notes: Optional[str] = None,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Close a shift (record cash counts)"""
    shift = session.get(Shift, shift_id)
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

    if shift.status not in [ShiftStatus.ACTIVE, ShiftStatus.CLOSING]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot close shift with status {shift.status.value}"
        )

    # Record cash counts
    shift.closing_cash_count = closing_cash_count
    shift.card_count = card_count or Decimal("0.00")
    shift.closing_notes = closing_notes
    shift.closed_by = current_user.id

    shift.end_shift()

    session.add(shift)
    session.commit()
    session.refresh(shift)

    # Broadcast shift closed event
    from asyncio import create_task
    create_task(manager.send_shift_closed(
        shift_id=shift.id,
        server_id=shift.server_id,
        cash_sales=float(shift.cash_sales),
        card_sales=float(shift.card_sales)
    ))

    return shift


@router.post("/{shift_id}/reconcile", response_model=ShiftRead)
def reconcile_shift(
    shift_id: uuid.UUID,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Reconcile shift (verify cash counts, calculate variance)"""
    shift = session.get(Shift, shift_id)
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

    if shift.status != ShiftStatus.CLOSED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Shift must be closed before reconciliation"
        )

    # Calculate variance
    expected_cash = shift.opening_balance + shift.cash_sales
    cash_variance = shift.closing_cash_count - expected_cash
    is_over = cash_variance > 0

    shift.expected_cash = expected_cash
    shift.cash_variance = cash_variance
    shift.is_over = is_over
    shift.reconciled_by = current_user.id

    shift.reconcile()

    session.add(shift)
    session.commit()
    session.refresh(shift)

    # Broadcast shift reconciled event
    from asyncio import create_task
    create_task(manager.send_shift_reconciled(
        shift_id=shift.id,
        server_id=shift.server_id,
        expected_cash=float(expected_cash),
        actual_cash=float(shift.closing_cash_count),
        variance=float(cash_variance)
    ))

    # Also broadcast domain event
    create_task(event_bus.publish(ShiftReconciled(
        shift_id=shift.id,
        server_id=shift.server_id,
        location_id=shift.location_id,
        tenant_id=shift.tenant_id,
        reconciled_by=current_user.id,
        expected_cash=float(expected_cash),
        actual_cash=float(shift.closing_cash_count),
        variance=float(cash_variance)
    )))

    return shift


@router.post("/{shift_id}/cash-drop", status_code=status.HTTP_201_CREATED)
def cash_drop(
    shift_id: uuid.UUID,
    drop_data: ShiftCashDropCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Cash drop (remove excess cash from drawer) - manager approval required"""
    # Check permissions
    if current_user.role not in ["admin", "manager"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin or manager can perform cash drops"
        )

    shift = session.get(Shift, shift_id)
    if not shift:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shift not found"
        )

    if shift.status != ShiftStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Shift must be active to perform cash drop"
        )

    # Calculate balance after drop (simplified)
    balance_after = shift.opening_balance + shift.cash_sales - drop_data.amount

    # Create cash drawer event
    cash_event = CashDrawerEvent(
        tenant_id=current_user.tenant_id,
        shift_id=shift.id,
        location_id=shift.location_id,
        event_type=CashDrawerEventType.CASH_DROP,
        amount=-drop_data.amount,  # Negative for removal
        balance_after=balance_after,
        description=f"Cash drop: {drop_data.reason}",
        reason=drop_data.reason,
        performed_by=current_user.id,
        approved_by=current_user.id  # Self-approved as manager
    )

    session.add(cash_event)
    session.commit()

    return {"message": "Cash drop recorded successfully"}


@router.post("/{shift_id}/tip-payout", status_code=status.HTTP_201_CREATED)
def tip_payout(
    shift_id: uuid.UUID,
    payout_data: ShiftTipPayoutCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Tip payout - manager approval required"""
    # Check permissions
    if current_user.role not in ["admin", "manager"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin or manager can perform tip payouts"
        )

    shift = session.get(Shift, shift_id)
    if not shift:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shift not found"
        )

    if shift.status != ShiftStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Shift must be active to perform tip payout"
        )

    # Calculate balance after payout (simplified)
    balance_after = shift.opening_balance + shift.cash_sales - payout_data.amount

    # Create cash drawer event
    cash_event = CashDrawerEvent(
        tenant_id=current_user.tenant_id,
        shift_id=shift.id,
        location_id=shift.location_id,
        event_type=CashDrawerEventType.TIP_PAYOUT,
        amount=-payout_data.amount,  # Negative for removal
        balance_after=balance_after,
        description=f"Tip payout: {payout_data.reason}",
        reason=payout_data.reason,
        performed_by=current_user.id,
        approved_by=current_user.id  # Self-approved as manager
    )

    session.add(cash_event)
    session.commit()

    return {"message": "Tip payout recorded successfully"}


@router.post("/{shift_id}/adjustment", status_code=status.HTTP_201_CREATED)
def cash_adjustment(
    shift_id: uuid.UUID,
    adjustment_data: ShiftAdjustmentCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Manual cash adjustment - manager approval required"""
    # Check permissions
    if current_user.role not in ["admin", "manager"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin or manager can perform cash adjustments"
        )

    shift = session.get(Shift, shift_id)
    if not shift:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shift not found"
        )

    if shift.status != ShiftStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Shift must be active to perform cash adjustment"
        )

    # Calculate balance after adjustment (simplified)
    balance_after = shift.opening_balance + shift.cash_sales + adjustment_data.amount

    # Create cash drawer event
    cash_event = CashDrawerEvent(
        tenant_id=current_user.tenant_id,
        shift_id=shift.id,
        location_id=shift.location_id,
        event_type=CashDrawerEventType.CASH_ADJUSTMENT,
        amount=adjustment_data.amount,  # Can be positive or negative
        balance_after=balance_after,
        description=f"Cash adjustment: {adjustment_data.reason}",
        reason=adjustment_data.reason,
        performed_by=current_user.id,
        approved_by=current_user.id  # Self-approved as manager
    )

    session.add(cash_event)
    session.commit()

    return {"message": "Cash adjustment recorded successfully"}
