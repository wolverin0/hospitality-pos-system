"""
Tickets API endpoints for KDS ticket management
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlmodel import Session, select, SQLModel
from typing import List, Optional
from datetime import datetime
from decimal import Decimal
import structlog
import uuid

from app.core.database import get_session
from app.core.dependencies import get_tenant_id, get_current_user_id, get_user_role
from app.core.events import event_bus
from app.core.events import (
    TicketCreated, TicketUpdated, TicketBumped, TicketHeld,
    TicketFired, TicketVoided
)
from app.core.websocket_manager import manager
from app.models.ticket import Ticket, TicketStatus
from app.models.ticket_line_item import TicketLineItem, FiredStatus
from app.models.draft_order import DraftOrder
from app.models.draft_line_item import DraftLineItem
from app.models.table_session import TableSession
from app.models.menu_item import MenuItem
from app.models.menu_station import MenuStation
from app.models.kitchen_course import KitchenCourse

logger = structlog.get_logger(__name__)
router = APIRouter()


# Pydantic schemas for request/response
class TicketLineItemCreate(SQLModel):
    """Schema for creating a ticket line item"""
    menu_item_id: uuid.UUID
    name: str
    description: Optional[str] = None
    quantity: int
    price_at_order: Decimal
    line_total: Decimal
    course_number: int
    course_name: Optional[str] = None
    fired_status: FiredStatus = FiredStatus.PENDING
    special_instructions: Optional[str] = None
    modifiers: Optional[dict] = None
    sort_order: int = 0
    parent_line_item_id: Optional[uuid.UUID] = None


class TicketCreate(SQLModel):
    """Schema for creating a ticket from draft order"""
    draft_order_id: uuid.UUID


class TicketResponse(SQLModel):
    """Schema for ticket response"""
    id: uuid.UUID
    draft_order_id: uuid.UUID
    table_session_id: uuid.UUID
    station_id: uuid.UUID
    status: TicketStatus
    course_number: int
    course_name: Optional[str] = None
    table_number: Optional[str] = None
    server_name: Optional[str] = None
    is_rush: bool = False
    special_instructions: Optional[str] = None
    is_held: bool = False
    held_reason: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    fired_at: Optional[datetime] = None
    ready_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class TicketDetailResponse(TicketResponse):
    """Schema for ticket with line items"""
    line_items: List[TicketLineItem]


class TicketBumpRequest(SQLModel):
    """Schema for bumping a ticket"""
    version: int  # Required for optimistic concurrency


class TicketHoldRequest(SQLModel):
    """Schema for holding a ticket"""
    version: int  # Required for optimistic concurrency
    reason: str  # Required: reason for holding


class TicketFireRequest(SQLModel):
    """Schema for firing a held ticket"""
    version: int  # Required for optimistic concurrency


class TicketVoidRequest(SQLModel):
    """Schema for voiding a ticket"""
    version: int  # Required for optimistic concurrency
    reason: str  # Required: reason for voiding


class TicketStatusUpdateRequest(SQLModel):
    """Schema for updating ticket status"""
    version: int  # Required for optimistic concurrency
    status: TicketStatus  # New status to set


class TicketReassignRequest(SQLModel):
    """Schema for reassigning ticket to different station"""
    version: int  # Required for optimistic concurrency
    new_station_id: uuid.UUID
    reason: Optional[str] = None


@router.post("/generate", response_model=TicketResponse)
async def generate_tickets(
    ticket_data: TicketCreate,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    current_user_id: uuid.UUID = Depends(get_current_user_id),
    session: Session = Depends(get_session)
):
    """Generate tickets from a confirmed draft order

    Rules:
    - Group draft line items by station and course
    - Create one ticket per station per course
    - Auto-fire courses with auto_fire_on_confirm=True (usually DRINKS)
    - Set ticket status to PENDING for non-auto-fire tickets
    - Capture all draft line item data as snapshots
    - Calculate total price from draft line items
    """
    try:
        # Verify draft order exists and belongs to tenant
        draft = session.exec(
            select(DraftOrder).where(
                DraftOrder.id == ticket_data.draft_order_id,
                DraftOrder.tenant_id == tenant_id
            )
        ).first()

        if not draft:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Draft order not found"
            )

        # Verify draft is confirmed
        if draft.status != "confirmed":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot generate tickets from draft with status: {draft.status}. Must be confirmed."
            )

        # Get draft line items with menu items
        draft_line_items = session.exec(
            select(DraftLineItem)
            .where(DraftLineItem.draft_order_id == draft.id)
        ).all()

        if not draft_line_items:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Draft order has no line items"
            )

        # Get table session for display info
        table_session = session.exec(
            select(TableSession).where(TableSession.id == draft.table_session_id)
        ).first()

        # Group draft line items by (station_id, course_id)
        # This creates one ticket per station per course
        station_course_groups = {}
        for draft_item in draft_line_items:
            # Get menu item to get station_id and course_id
            menu_item = session.exec(
                select(MenuItem).where(MenuItem.id == draft_item.menu_item_id)
            ).first()

            if not menu_item:
                logger.warning(f"Menu item {draft_item.menu_item_id} not found, skipping")
                continue

            # Determine station and course
            station_id = menu_item.station_id
            course_id = menu_item.course_id

            # If no station_id or course_id on menu item, skip or use defaults
            # This should ideally be set by admin during menu setup
            if not station_id:
                logger.warning(f"Menu item {menu_item.name} has no station_id, skipping")
                continue

            if not course_id:
                logger.warning(f"Menu item {menu_item.name} has no course_id, skipping")
                continue

            # Get course info for display and auto-fire logic
            course_info = session.exec(
                select(KitchenCourse).where(KitchenCourse.id == course_id)
            ).first()

            if not course_info:
                logger.warning(f"Course {course_id} not found for menu item {menu_item.name}")
                continue

            # Create group key
            group_key = (station_id, course_id)

            if group_key not in station_course_groups:
                station_course_groups[group_key] = {
                    "station_id": station_id,
                    "course_id": course_id,
                    "course_number": course_info.course_number,
                    "course_name": course_info.name,
                    "auto_fire": course_info.auto_fire_on_confirm,
                    "draft_items": []
                }

            station_course_groups[group_key]["draft_items"].append(draft_item)

        # Create tickets from groups
        created_tickets = []
        now = datetime.utcnow()

        for (station_id, course_id), group in station_course_groups.items():
            # Determine initial ticket status
            if group["auto_fire"]:
                # Auto-fire courses (usually DRINKS) get FIRED status immediately
                ticket_status = TicketStatus.PENDING  # Will be sent to kitchen
                fired_at = now
            else:
                # Other courses start as NEW (not yet visible to kitchen until fired)
                ticket_status = TicketStatus.NEW
                fired_at = None

            # Create ticket
            ticket = Ticket(
                tenant_id=tenant_id,
                draft_order_id=draft.id,
                table_session_id=draft.table_session_id,
                station_id=station_id,
                status=ticket_status,
                course_number=group["course_number"],
                course_name=group["course_name"],
                table_number=str(table_session.table_number) if table_session else None,
                server_name=draft.confirmed_by_user.email if draft.confirmed_by_user else None,
                special_instructions=draft.special_requests,
                fired_at=fired_at,
                created_at=now
            )
            session.add(ticket)
            session.flush()  # Flush to get ticket.id

            # Create ticket line items from draft line items
            for draft_item in group["draft_items"]:
                # Get menu item for additional info
                menu_item = session.exec(
                    select(MenuItem).where(MenuItem.id == draft_item.menu_item_id)
                ).first()

                # Determine fired status for line item
                if group["auto_fire"]:
                    line_fired_status = FiredStatus.FIRED
                    line_fired_at = now
                else:
                    line_fired_status = FiredStatus.PENDING
                    line_fired_at = None

                # Create ticket line item
                ticket_line_item = TicketLineItem(
                    tenant_id=tenant_id,
                    ticket_id=ticket.id,
                    menu_item_id=draft_item.menu_item_id,
                    name=draft_item.name,
                    description=draft_item.description or (menu_item.description if menu_item else None),
                    quantity=draft_item.quantity,
                    price_at_order=draft_item.price_at_order,
                    line_total=draft_item.line_total,
                    course_number=group["course_number"],
                    course_name=group["course_name"],
                    fired_status=line_fired_status,
                    fired_at=line_fired_at,
                    special_instructions=draft_item.special_instructions,
                    modifiers=draft_item.modifiers,
                    sort_order=draft_item.sort_order,
                    parent_line_item_id=draft_item.parent_line_item_id,
                    created_at=now
                )
                session.add(ticket_line_item)

            created_tickets.append(ticket)

        session.commit()

        # Emit ticket created events for each ticket
        for ticket in created_tickets:
            # Note: We'll create proper event types in Phase 2.7
            # For now, just log
            logger.info(f"Created ticket {ticket.id} for station {ticket.station_id}, course {ticket.course_number}")

        logger.info(f"Generated {len(created_tickets)} tickets from draft {draft.id}")
        # Return first ticket (or could return list)
        return created_tickets[0] if created_tickets else None

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"Error generating tickets: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate tickets"
        )


@router.patch("/{ticket_id}/bump", response_model=TicketResponse)
async def bump_ticket(
    ticket_id: uuid.UUID,
    bump_data: TicketBumpRequest,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    current_user_id: uuid.UUID = Depends(get_current_user_id),
    user_role: str = Depends(get_user_role),
    session: Session = Depends(get_session)
):
    """Bump a ticket to COMPLETED status (move to top of completed queue)"""
    try:
        # Get ticket
        ticket = session.exec(
            select(Ticket).where(
                Ticket.id == ticket_id,
                Ticket.tenant_id == tenant_id
            )
        ).first()

        if not ticket:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ticket not found"
            )

        # Check optimistic concurrency
        if ticket.version != bump_data.version:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Ticket was modified by another user. Please refresh and try again."
            )

        # Update ticket status and timestamps
        ticket.status = TicketStatus.COMPLETED
        ticket.completed_at = datetime.utcnow()
        ticket.version += 1  # Increment version for optimistic concurrency

        session.commit()
        session.refresh(ticket)

        # Emit TicketBumped event to station
        await manager.send_ticket_bumped(
            manager=manager,
            ticket_id=ticket.id,
            station_id=ticket.station_id
        )

        logger.info(f"Ticket {ticket_id} bumped to COMPLETED by user {current_user_id}")

        return ticket

    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"Error bumping ticket: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to bump ticket"
        )


@router.patch("/{ticket_id}/hold", response_model=TicketResponse)
async def hold_ticket(
    ticket_id: uuid.UUID,
    hold_data: TicketHoldRequest,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    current_user_id: uuid.UUID = Depends(get_current_user_id),
    user_role: str = Depends(get_user_role),
    session: Session = Depends(get_session)
):
    """Hold a ticket (prevents firing, Expo mode)"""
    try:
        # Get ticket
        ticket = session.exec(
            select(Ticket).where(
                Ticket.id == ticket_id,
                Ticket.tenant_id == tenant_id
            )
        ).first()

        if not ticket:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ticket not found"
            )

        # Check optimistic concurrency
        if ticket.version != hold_data.version:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Ticket was modified by another user. Please refresh and try again."
            )

        # Update ticket hold status
        ticket.is_held = True
        ticket.held_reason = hold_data.reason
        ticket.held_at = datetime.utcnow()
        ticket.status = TicketStatus.PENDING  # Still pending but held
        ticket.version += 1

        session.commit()
        session.refresh(ticket)

        logger.info(f"Ticket {ticket_id} held by user {current_user_id}, reason: {hold_data.reason}")

        # Emit event
        # await event_bus.publish(...) - add in Phase 2.7

        return ticket

    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"Error holding ticket: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to hold ticket"
        )


@router.patch("/{ticket_id}/fire", response_model=TicketResponse)
async def fire_ticket(
    ticket_id: uuid.UUID,
    fire_data: TicketFireRequest,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    current_user_id: uuid.UUID = Depends(get_current_user_id),
    user_role: str = Depends(get_user_role),
    session: Session = Depends(get_session)
):
    """Fire a held ticket to kitchen (Expo mode)"""
    try:
        # Get ticket
        ticket = session.exec(
            select(Ticket).where(
                Ticket.id == ticket_id,
                Ticket.tenant_id == tenant_id
            )
        ).first()

        if not ticket:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ticket not found"
            )

        # Check if ticket is held
        if not ticket.is_held:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only held tickets can be fired"
            )

        # Check optimistic concurrency
        if ticket.version != fire_data.version:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Ticket was modified by another user. Please refresh and try again."
            )

        # Update ticket status
        now = datetime.utcnow()
        ticket.is_held = False
        ticket.held_reason = None
        ticket.held_at = None
        ticket.status = TicketStatus.PENDING
        ticket.fired_at = now
        ticket.version += 1

        # Update all line items to FIRED status
        session.exec(
            select(TicketLineItem).where(TicketLineItem.ticket_id == ticket_id)
        )

        line_items = session.exec(
            select(TicketLineItem).where(TicketLineItem.ticket_id == ticket_id)
        ).all()

        for line_item in line_items:
            if line_item.fired_status == FiredStatus.HELD or line_item.fired_status == FiredStatus.PENDING:
                line_item.fired_status = FiredStatus.FIRED
                line_item.fired_at = now

        session.commit()
        session.refresh(ticket)

        logger.info(f"Ticket {ticket_id} fired to kitchen by user {current_user_id}")

        # Emit event
        # await event_bus.publish(...) - add in Phase 2.7

        return ticket

    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"Error firing ticket: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fire ticket"
        )


@router.patch("/{ticket_id}/void", response_model=TicketResponse)
async def void_ticket(
    ticket_id: uuid.UUID,
    void_data: TicketVoidRequest,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    current_user_id: uuid.UUID = Depends(get_current_user_id),
    user_role: str = Depends(get_user_role),
    session: Session = Depends(get_session)
):
    """Void a ticket (cancel and mark as voided)"""
    try:
        # Only admins and managers can void tickets
        if user_role not in ["admin", "manager"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )

        # Get ticket
        ticket = session.exec(
            select(Ticket).where(
                Ticket.id == ticket_id,
                Ticket.tenant_id == tenant_id
            )
        ).first()

        if not ticket:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ticket not found"
            )

        # Check optimistic concurrency
        if ticket.version != void_data.version:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Ticket was modified by another user. Please refresh and try again."
            )

        # Update ticket to VOIDED
        now = datetime.utcnow()
        ticket.status = TicketStatus.VOIDED
        ticket.voided_at = now
        ticket.voided_by = current_user_id
        ticket.voided_reason = void_data.reason
        ticket.version += 1

        # Update all line items to VOIDED
        line_items = session.exec(
            select(TicketLineItem).where(TicketLineItem.ticket_id == ticket_id)
        ).all()

        for line_item in line_items:
            if line_item.fired_status not in [FiredStatus.VOIDED, FiredStatus.COMPLETED]:
                line_item.fired_status = FiredStatus.VOIDED
                line_item.voided_at = now
                line_item.voided_by = current_user_id
                line_item.voided_reason = void_data.reason

        session.commit()
        session.refresh(ticket)

        logger.info(f"Ticket {ticket_id} voided by user {current_user_id}, reason: {void_data.reason}")

        # Emit event
        # await event_bus.publish(...) - add in Phase 2.7

        return ticket

    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"Error voiding ticket: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to void ticket"
        )


@router.patch("/{ticket_id}/status", response_model=TicketResponse)
async def update_ticket_status(
    ticket_id: uuid.UUID,
    status_data: TicketStatusUpdateRequest,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    current_user_id: uuid.UUID = Depends(get_current_user_id),
    user_role: str = Depends(get_user_role),
    session: Session = Depends(get_session)
):
    """Update ticket status manually (admin/Expo only)"""
    try:
        # Get ticket
        ticket = session.exec(
            select(Ticket).where(
                Ticket.id == ticket_id,
                Ticket.tenant_id == tenant_id
            )
        ).first()

        if not ticket:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ticket not found"
            )

        # Check optimistic concurrency
        if ticket.version != status_data.version:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Ticket was modified by another user. Please refresh and try again."
            )

        # Update status based on new status
        ticket.status = status_data.status

        # Set appropriate timestamps based on status
        now = datetime.utcnow()
        if status_data.status == TicketStatus.PREPARING:
            ticket.prep_started_at = now
        elif status_data.status == TicketStatus.READY:
            ticket.ready_at = now
        elif status_data.status == TicketStatus.COMPLETED:
            ticket.completed_at = now

        ticket.version += 1

        session.commit()
        session.refresh(ticket)

        logger.info(f"Ticket {ticket_id} status updated to {status_data.status} by user {current_user_id}")

        # Emit event
        # await event_bus.publish(...) - add in Phase 2.7

        return ticket

    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"Error updating ticket status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update ticket status"
        )


@router.delete("/line-items/{line_item_id}")
async def void_line_item(
    line_item_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    current_user_id: uuid.UUID = Depends(get_current_user_id),
    user_role: str = Depends(get_user_role),
    session: Session = Depends(get_session)
):
    """Void an individual ticket line item"""
    try:
        # Only admins and managers can void line items
        if user_role not in ["admin", "manager"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )

        # Get line item with ticket
        line_item = session.exec(
            select(TicketLineItem).where(
                TicketLineItem.id == line_item_id,
                TicketLineItem.tenant_id == tenant_id
            )
        ).first()

        if not line_item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Line item not found"
            )

        # Update line item to VOIDED
        now = datetime.utcnow()
        line_item.fired_status = FiredStatus.VOIDED
        line_item.voided_at = now
        line_item.voided_by = current_user_id
        line_item.voided_reason = "Voided individually"

        session.commit()
        session.refresh(line_item)

        logger.info(f"Line item {line_item_id} voided by user {current_user_id}")

        # Emit event
        # await event_bus.publish(...) - add in Phase 2.7

        return {"message": "Line item voided successfully"}

    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"Error voiding line item: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to void line item"
        )


@router.post("/{ticket_id}/reassign", response_model=TicketResponse)
async def reassign_ticket(
    ticket_id: uuid.UUID,
    reassign_data: TicketReassignRequest,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    current_user_id: uuid.UUID = Depends(get_current_user_id),
    user_role: str = Depends(get_user_role),
    session: Session = Depends(get_session)
):
    """Reassign a ticket to a different station (Expo/manager only)"""
    try:
        # Only admins and managers can reassign tickets
        if user_role not in ["admin", "manager"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )

        # Get ticket
        ticket = session.exec(
            select(Ticket).where(
                Ticket.id == ticket_id,
                Ticket.tenant_id == tenant_id
            )
        ).first()

        if not ticket:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ticket not found"
            )

        # Verify new station exists
        new_station = session.exec(
            select(MenuStation).where(
                MenuStation.id == reassign_data.new_station_id,
                MenuStation.tenant_id == tenant_id
            )
        ).first()

        if not new_station:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="New station not found"
            )

        # Check optimistic concurrency
        if ticket.version != reassign_data.version:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Ticket was modified by another user. Please refresh and try again."
            )

        # Reassign ticket to new station
        ticket.station_id = reassign_data.new_station_id
        ticket.version += 1

        session.commit()
        session.refresh(ticket)

        logger.info(f"Ticket {ticket_id} reassigned to station {reassign_data.new_station_id} by user {current_user_id}, reason: {reassign_data.reason}")

        # Emit event
        # await event_bus.publish(...) - add in Phase 2.7

        return ticket

    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"Error reassigning ticket: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reassign ticket"
        )


@router.post("/{ticket_id}/reprint")
async def reprint_ticket(
    ticket_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    current_user_id: uuid.UUID = Depends(get_current_user_id),
    user_role: str = Depends(get_user_role),
    session: Session = Depends(get_session)
):
    """Reprint a ticket (Expo/manager only)"""
    try:
        # Only admins, managers, and kitchen staff can reprint
        if user_role not in ["admin", "manager", "kitchen"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )

        # Get ticket
        ticket = session.exec(
            select(Ticket).where(
                Ticket.id == ticket_id,
                Ticket.tenant_id == tenant_id
            )
        ).first()

        if not ticket:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ticket not found"
            )

        # Increment print count and update last_printed_at
        ticket.print_count += 1
        ticket.last_printed_at = datetime.utcnow()

        session.commit()
        session.refresh(ticket)

        logger.info(f"Ticket {ticket_id} reprinted (print #{ticket.print_count}) by user {current_user_id}")

        # Emit event
        # await event_bus.publish(...) - add in Phase 2.7

        return {
            "message": "Ticket reprinted successfully",
            "print_count": ticket.print_count
        }

    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"Error reprinting ticket: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reprint ticket"
        )


@router.get("/", response_model=List[TicketResponse])
async def list_tickets(
    station_id: Optional[uuid.UUID] = Query(None, description="Filter by station"),
    status_filter: Optional[TicketStatus] = Query(None, description="Filter by status"),
    course_number: Optional[int] = Query(None, description="Filter by course number"),
    table_session_id: Optional[uuid.UUID] = Query(None, description="Filter by table session"),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    current_user_id: uuid.UUID = Depends(get_current_user_id),
    user_role: str = Depends(get_user_role),
    session: Session = Depends(get_session)
):
    """List tickets for KDS (filtered by station, status, etc.)"""
    try:
        query = select(Ticket).where(Ticket.tenant_id == tenant_id)

        # Apply filters
        if station_id:
            query = query.where(Ticket.station_id == station_id)

        if status_filter:
            query = query.where(Ticket.status == status_filter)

        if course_number is not None:
            query = query.where(Ticket.course_number == course_number)

        if table_session_id:
            query = query.where(Ticket.table_session_id == table_session_id)

        # Don't show completed tickets older than 24 hours
        # KDS usually only shows active or recently completed tickets
        from datetime import timedelta
        cutoff = datetime.utcnow() - timedelta(hours=24)
        query = query.where(Ticket.created_at > cutoff)

        # Sort by: priority (rush first), course_number (low to high), created_at (newest first)
        query = query.order_by(
            Ticket.is_rush.desc(),
            Ticket.course_number.asc(),
            Ticket.created_at.asc()
        )

        tickets = session.exec(query).all()
        return tickets

    except Exception as e:
        logger.error(f"Error listing tickets: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list tickets"
        )


@router.get("/{ticket_id}", response_model=TicketDetailResponse)
async def get_ticket(
    ticket_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    current_user_id: uuid.UUID = Depends(get_current_user_id),
    session: Session = Depends(get_session)
):
    """Get ticket details with line items"""
    try:
        ticket = session.exec(
            select(Ticket).where(
                Ticket.id == ticket_id,
                Ticket.tenant_id == tenant_id
            )
        ).first()

        if not ticket:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ticket not found"
            )

        # Get line items sorted by sort_order
        line_items = session.exec(
            select(TicketLineItem)
            .where(TicketLineItem.ticket_id == ticket_id)
            .order_by(TicketLineItem.sort_order.asc())
        ).all()

        # Add line_items to ticket response
        ticket_dict = ticket.dict()
        ticket_dict["line_items"] = line_items
        return ticket_dict

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting ticket: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get ticket"
        )


@router.delete("/{ticket_id}")
async def delete_ticket(
    ticket_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    current_user_id: uuid.UUID = Depends(get_current_user_id),
    user_role: str = Depends(get_user_role),
    session: Session = Depends(get_session)
):
    """Delete/cancel a ticket (admin only)"""
    try:
        # Only admins and managers can delete tickets
        if user_role not in ["admin", "manager"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )

        ticket = session.exec(
            select(Ticket).where(
                Ticket.id == ticket_id,
                Ticket.tenant_id == tenant_id
            )
        ).first()

        if not ticket:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ticket not found"
            )

        session.delete(ticket)
        session.commit()

        logger.info(f"Deleted ticket {ticket_id} by user {current_user_id}")
        return {"message": "Ticket deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"Error deleting ticket: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete ticket"
        )
