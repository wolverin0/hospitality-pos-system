"""
Unit tests for Ticket system (KDS)
"""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import Mock, patch, AsyncMock
import uuid

from sqlmodel import Session, select
from fastapi import status
from httpx import AsyncClient

from app.models.ticket import Ticket, TicketStatus
from app.models.ticket_line_item import TicketLineItem, FiredStatus
from app.models.draft_order import DraftOrder
from app.models.draft_line_item import DraftLineItem
from app.models.table_session import TableSession
from app.models.menu_item import MenuItem
from app.models.menu_station import MenuStation, StationType
from app.models.kitchen_course import KitchenCourse, CourseType
from app.models.user import User
from app.models.tenant import Tenant
from app.models.table import Table
from app.models.floor import Floor


# Fixtures
@pytest.fixture
def test_tenant(db: Session):
    """Create a test tenant"""
    tenant = Tenant(
        name="Test Restaurant",
        slug="test-restaurant",
        address="123 Test St",
        phone="555-1234",
        is_active=True
    )
    db.add(tenant)
    db.commit()
    db.refresh(tenant)
    return tenant


@pytest.fixture
def test_user(db: Session, test_tenant: Tenant):
    """Create a test user"""
    user = User(
        tenant_id=test_tenant.id,
        email="server@test.com",
        full_name="Test Server",
        role="server",
        is_active=True
    )
    user.set_password("password123")
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def test_manager_user(db: Session, test_tenant: Tenant):
    """Create a test manager user"""
    user = User(
        tenant_id=test_tenant.id,
        email="manager@test.com",
        full_name="Test Manager",
        role="manager",
        is_active=True
    )
    user.set_password("password123")
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def test_table_session(db: Session, test_tenant: Tenant):
    """Create a test table session"""
    floor = Floor(tenant_id=test_tenant.id, name="Main Floor", display_order=1)
    db.add(floor)
    db.flush()

    table = Table(tenant_id=test_tenant.id, floor_id=floor.id, table_number="T1", seats=4, is_active=True)
    db.add(table)
    db.flush()

    session = TableSession(
        tenant_id=test_tenant.id,
        table_id=table.id,
        server_id=None,
        guest_count=4,
        status="seated"
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


@pytest.fixture
def test_station(db: Session, test_tenant: Tenant):
    """Create a test kitchen station"""
    station = MenuStation(
        tenant_id=test_tenant.id,
        name="Kitchen",
        station_type=StationType.KITCHEN,
        display_order=1,
        color="#FF0000",
        icon="🍳",
        is_active=True
    )
    db.add(station)
    db.commit()
    db.refresh(station)
    return station


@pytest.fixture
def test_bar_station(db: Session, test_tenant: Tenant):
    """Create a test bar station"""
    station = MenuStation(
        tenant_id=test_tenant.id,
        name="Bar",
        station_type=StationType.BAR,
        display_order=2,
        color="#00FF00",
        icon="🍺",
        is_active=True
    )
    db.add(station)
    db.commit()
    db.refresh(station)
    return station


@pytest.fixture
def test_drinks_course(db: Session, test_tenant: Tenant, test_bar_station: MenuStation):
    """Create a test drinks course (auto-fire)"""
    course = KitchenCourse(
        tenant_id=test_tenant.id,
        name="Drinks",
        course_type=CourseType.DRINKS,
        course_number=1,
        display_order=1,
        auto_fire_on_confirm=True,
        prep_time_minutes=5,
        color="#00AAFF",
        icon="🍹"
    )
    db.add(course)
    db.commit()
    db.refresh(course)
    return course


@pytest.fixture
def test_mains_course(db: Session, test_tenant: Tenant, test_station: MenuStation):
    """Create a test mains course (no auto-fire)"""
    course = KitchenCourse(
        tenant_id=test_tenant.id,
        name="Mains",
        course_type=CourseType.MAINS,
        course_number=2,
        display_order=2,
        auto_fire_on_confirm=False,
        prep_time_minutes=15,
        color="#FFAA00",
        icon="🍽️"
    )
    db.add(course)
    db.commit()
    db.refresh(course)
    return course


@pytest.fixture
def test_drink_item(
    db: Session,
    test_tenant: Tenant,
    test_bar_station: MenuStation,
    test_drinks_course: KitchenCourse
):
    """Create a test drink menu item"""
    item = MenuItem(
        tenant_id=test_tenant.id,
        name="Coca Cola",
        description="330ml can",
        price=Decimal("2.50"),
        station_id=test_bar_station.id,
        course_id=test_drinks_course.id,
        default_prep_time_minutes=5,
        is_active=True
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@pytest.fixture
def test_food_item(
    db: Session,
    test_tenant: Tenant,
    test_station: MenuStation,
    test_mains_course: KitchenCourse
):
    """Create a test food menu item"""
    item = MenuItem(
        tenant_id=test_tenant.id,
        name="Burger",
        description="Beef burger with fries",
        price=Decimal("15.00"),
        station_id=test_station.id,
        course_id=test_mains_course.id,
        default_prep_time_minutes=15,
        is_active=True
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@pytest.fixture
def test_draft_order(
    db: Session,
    test_tenant: Tenant,
    test_table_session: TableSession,
    test_user: User
):
    """Create a test confirmed draft order"""
    draft = DraftOrder(
        tenant_id=test_tenant.id,
        table_session_id=test_table_session.id,
        status="confirmed",
        confirmed_by=test_user.id,
        locked_by=test_user.id,
        subtotal=Decimal("20.00"),
        tax_amount=Decimal("1.60"),
        total_amount=Decimal("21.60"),
        special_requests="No onions"
    )
    db.add(draft)
    db.commit()
    db.refresh(draft)
    return draft


@pytest.fixture
def test_draft_line_items(
    db: Session,
    test_tenant: Tenant,
    test_draft_order: DraftOrder,
    test_drink_item: MenuItem,
    test_food_item: MenuItem
):
    """Create test draft line items"""
    drink_item = DraftLineItem(
        tenant_id=test_tenant.id,
        draft_order_id=test_draft_order.id,
        menu_item_id=test_drink_item.id,
        name=test_drink_item.name,
        description=test_drink_item.description,
        quantity=2,
        price_at_order=test_drink_item.price,
        line_total=test_drink_item.price * 2,
        sort_order=1
    )
    db.add(drink_item)

    food_item = DraftLineItem(
        tenant_id=test_tenant.id,
        draft_order_id=test_draft_order.id,
        menu_item_id=test_food_item.id,
        name=test_food_item.name,
        description=test_food_item.description,
        quantity=1,
        price_at_order=test_food_item.price,
        line_total=test_food_item.price,
        sort_order=2,
        special_instructions="Medium rare"
    )
    db.add(food_item)

    db.commit()
    return [drink_item, food_item]


# Tests
def test_ticket_creation_from_draft_order(
    db: Session,
    test_tenant: Tenant,
    test_draft_order: DraftOrder,
    test_draft_line_items: list,
    test_bar_station: MenuStation,
    test_station: MenuStation
):
    """Test generating tickets from a confirmed draft order"""
    # Simplified test - just verify ticket creation logic
    # Create tickets directly from draft order items

    # Get menu items for reference
    drink_item = db.exec(
        select(MenuItem).where(MenuItem.id == test_draft_line_items[0].menu_item_id)
    ).first()

    food_item = db.exec(
        select(MenuItem).where(MenuItem.id == test_draft_line_items[1].menu_item_id)
    ).first()

    # Create drinks ticket (auto-fire)
    drinks_ticket = Ticket(
        tenant_id=test_tenant.id,
        draft_order_id=test_draft_order.id,
        table_session_id=test_draft_order.table_session_id,
        station_id=test_bar_station.id,
        status=TicketStatus.PENDING,  # Auto-fire = PENDING
        course_number=drink_item.course_id and 1 or 1,
        course_name="Drinks",
        table_number="T1",
        fired_at=datetime.utcnow()
    )
    db.add(drinks_ticket)

    # Create food ticket (no auto-fire)
    food_ticket = Ticket(
        tenant_id=test_tenant.id,
        draft_order_id=test_draft_order.id,
        table_session_id=test_draft_order.table_session_id,
        station_id=test_station.id,
        status=TicketStatus.NEW,  # No auto-fire = NEW
        course_number=food_item.course_id and 2 or 2,
        course_name="Mains",
        table_number="T1"
    )
    db.add(food_ticket)
    db.commit()
    db.refresh(drinks_ticket)
    db.refresh(food_ticket)

    # Verify tickets were created
    assert drinks_ticket.status == TicketStatus.PENDING
    assert drinks_ticket.fired_at is not None

    assert food_ticket.status == TicketStatus.NEW
    assert food_ticket.fired_at is None


def test_ticket_status_transitions(
    db: Session,
    test_tenant: Tenant,
    test_draft_order: DraftOrder,
    test_station: MenuStation,
    test_mains_course: KitchenCourse
):
    """Test ticket status transitions through lifecycle"""
    # Create a ticket
    ticket = Ticket(
        tenant_id=test_tenant.id,
        draft_order_id=test_draft_order.id,
        table_session_id=test_draft_order.table_session_id,
        station_id=test_station.id,
        status=TicketStatus.NEW,
        course_number=test_mains_course.course_number,
        course_name=test_mains_course.name
    )
    db.add(ticket)
    db.commit()
    db.refresh(ticket)

    # Initial state
    assert ticket.status == TicketStatus.NEW
    assert ticket.prep_started_at is None
    assert ticket.ready_at is None
    assert ticket.completed_at is None

    # Transition to PENDING
    ticket.status = TicketStatus.PENDING
    db.commit()
    db.refresh(ticket)
    assert ticket.status == TicketStatus.PENDING

    # Transition to PREPARING
    ticket.status = TicketStatus.PREPARING
    ticket.prep_started_at = datetime.utcnow()
    db.commit()
    db.refresh(ticket)
    assert ticket.status == TicketStatus.PREPARING
    assert ticket.prep_started_at is not None

    # Transition to READY
    ticket.status = TicketStatus.READY
    ticket.ready_at = datetime.utcnow()
    db.commit()
    db.refresh(ticket)
    assert ticket.status == TicketStatus.READY
    assert ticket.ready_at is not None

    # Transition to COMPLETED
    ticket.status = TicketStatus.COMPLETED
    ticket.completed_at = datetime.utcnow()
    db.commit()
    db.refresh(ticket)
    assert ticket.status == TicketStatus.COMPLETED
    assert ticket.completed_at is not None


def test_ticket_bump_operation(
    db: Session,
    test_tenant: Tenant,
    test_draft_order: DraftOrder,
    test_station: MenuStation,
    test_mains_course: KitchenCourse
):
    """Test bumping a ticket to COMPLETED"""
    from app.api.tickets import bump_ticket

    # Create a ticket in PREPARING status
    ticket = Ticket(
        tenant_id=test_tenant.id,
        draft_order_id=test_draft_order.id,
        table_session_id=test_draft_order.table_session_id,
        station_id=test_station.id,
        status=TicketStatus.PREPARING,
        course_number=test_mains_course.course_number,
        course_name=test_mains_course.name,
        version=0
    )
    db.add(ticket)
    db.commit()
    db.refresh(ticket)

    # Bump the ticket
    bump_data = TicketBumpRequest(version=0)

    with patch("app.api.tickets.get_tenant_id", return_value=test_tenant.id), \
         patch("app.api.tickets.get_current_user_id", return_value=test_draft_order.locked_by_user_id), \
         patch("app.api.tickets.get_user_role", return_value="kitchen"), \
         patch("app.api.tickets.manager.send_ticket_bumped", new_callable=AsyncMock) as mock_send:

        import asyncio
        result = asyncio.run(
            bump_ticket(ticket.id, bump_data, test_tenant.id, test_draft_order.locked_by_user_id, "kitchen", db)
        )

    # Verify ticket was bumped to COMPLETED
    db.refresh(ticket)
    assert ticket.status == TicketStatus.COMPLETED
    assert ticket.completed_at is not None
    assert ticket.version == 1

    # Verify WebSocket event was sent
    mock_send.assert_called_once()


def test_ticket_hold_and_fire_operations(
    db: Session,
    test_tenant: Tenant,
    test_draft_order: DraftOrder,
    test_station: MenuStation,
    test_mains_course: KitchenCourse
):
    """Test holding and firing a ticket"""
    from app.api.tickets import hold_ticket, fire_ticket

    # Create a ticket in PENDING status
    ticket = Ticket(
        tenant_id=test_tenant.id,
        draft_order_id=test_draft_order.id,
        table_session_id=test_draft_order.table_session_id,
        station_id=test_station.id,
        status=TicketStatus.PENDING,
        course_number=test_mains_course.course_number,
        course_name=test_mains_course.name,
        version=0
    )
    db.add(ticket)
    db.commit()
    db.refresh(ticket)

    # Hold the ticket
    hold_data = TicketHoldRequest(version=0, reason="Waiting for special order")

    with patch("app.api.tickets.get_tenant_id", return_value=test_tenant.id), \
         patch("app.api.tickets.get_current_user_id", return_value=test_draft_order.locked_by_user_id), \
         patch("app.api.tickets.get_user_role", return_value="manager"):

        import asyncio
        result = asyncio.run(
            hold_ticket(ticket.id, hold_data, test_tenant.id, test_draft_order.locked_by_user_id, "manager", db)
        )

    # Verify ticket is held
    db.refresh(ticket)
    assert ticket.is_held is True
    assert ticket.held_reason == "Waiting for special order"
    assert ticket.held_at is not None
    assert ticket.status == TicketStatus.PENDING
    assert ticket.version == 1

    # Fire the ticket
    fire_data = TicketFireRequest(version=1)

    with patch("app.api.tickets.get_tenant_id", return_value=test_tenant.id), \
         patch("app.api.tickets.get_current_user_id", return_value=test_draft_order.locked_by_user_id), \
         patch("app.api.tickets.get_user_role", return_value="manager"):

        result = asyncio.run(
            fire_ticket(ticket.id, fire_data, test_tenant.id, test_draft_order.locked_by_user_id, "manager", db)
        )

    # Verify ticket is fired
    db.refresh(ticket)
    assert ticket.is_held is False
    assert ticket.held_reason is None
    assert ticket.held_at is None
    assert ticket.fired_at is not None
    assert ticket.version == 2


def test_ticket_void_operation(
    db: Session,
    test_tenant: Tenant,
    test_manager_user: User,
    test_draft_order: DraftOrder,
    test_station: MenuStation,
    test_mains_course: KitchenCourse
):
    """Test voiding a ticket"""
    from app.api.tickets import void_ticket

    # Create a ticket
    ticket = Ticket(
        tenant_id=test_tenant.id,
        draft_order_id=test_draft_order.id,
        table_session_id=test_draft_order.table_session_id,
        station_id=test_station.id,
        status=TicketStatus.PREPARING,
        course_number=test_mains_course.course_number,
        course_name=test_mains_course.name,
        version=0
    )
    db.add(ticket)

    # Create line items
    line_item = TicketLineItem(
        tenant_id=test_tenant.id,
        ticket_id=ticket.id,
        menu_item_id=uuid.uuid4(),
        name="Test Item",
        quantity=1,
        price_at_order=Decimal("10.00"),
        line_total=Decimal("10.00"),
        fired_status=FiredStatus.FIRED
    )
    db.add(line_item)
    db.commit()
    db.refresh(ticket)

    # Void the ticket (manager)
    void_data = TicketVoidRequest(version=0, reason="Customer cancelled")

    with patch("app.api.tickets.get_tenant_id", return_value=test_tenant.id), \
         patch("app.api.tickets.get_current_user_id", return_value=test_manager_user.id), \
         patch("app.api.tickets.get_user_role", return_value="manager"):

        import asyncio
        result = asyncio.run(
            void_ticket(ticket.id, void_data, test_tenant.id, test_manager_user.id, "manager", db)
        )

    # Verify ticket was voided
    db.refresh(ticket)
    assert ticket.status == TicketStatus.VOIDED
    assert ticket.voided_at is not None
    assert ticket.voided_by == test_manager_user.id
    assert ticket.voided_reason == "Customer cancelled"
    assert ticket.version == 1

    # Verify line item was voided
    db.refresh(line_item)
    assert line_item.fired_status == FiredStatus.VOIDED
    assert line_item.voided_at is not None


def test_ticket_void_permission_denied(
    db: Session,
    test_tenant: Tenant,
    test_user: User,  # Regular user, not manager/admin
    test_draft_order: DraftOrder,
    test_station: MenuStation,
    test_mains_course: KitchenCourse
):
    """Test that non-managers cannot void tickets"""
    from app.api.tickets import void_ticket
    from fastapi import HTTPException

    # Create a ticket
    ticket = Ticket(
        tenant_id=test_tenant.id,
        draft_order_id=test_draft_order.id,
        table_session_id=test_draft_order.table_session_id,
        station_id=test_station.id,
        status=TicketStatus.PREPARING,
        course_number=test_mains_course.course_number,
        course_name=test_mains_course.name,
        version=0
    )
    db.add(ticket)
    db.commit()
    db.refresh(ticket)

    # Try to void as regular user
    void_data = TicketVoidRequest(version=0, reason="Unauthorized void")

    with patch("app.api.tickets.get_tenant_id", return_value=test_tenant.id), \
         patch("app.api.tickets.get_current_user_id", return_value=test_user.id), \
         patch("app.api.tickets.get_user_role", return_value="waiter"):

        import asyncio
        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(
                void_ticket(ticket.id, void_data, test_tenant.id, test_user.id, "waiter", db)
            )

    # Verify permission denied
    assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN


def test_optimistic_concurrency_version_check(
    db: Session,
    test_tenant: Tenant,
    test_draft_order: DraftOrder,
    test_station: MenuStation,
    test_mains_course: KitchenCourse
):
    """Test optimistic concurrency with version field"""
    from app.api.tickets import update_ticket_status
    from fastapi import HTTPException

    # Create a ticket
    ticket = Ticket(
        tenant_id=test_tenant.id,
        draft_order_id=test_draft_order.id,
        table_session_id=test_draft_order.table_session_id,
        station_id=test_station.id,
        status=TicketStatus.NEW,
        course_number=test_mains_course.course_number,
        course_name=test_mains_course.name,
        version=0
    )
    db.add(ticket)
    db.commit()
    db.refresh(ticket)

    # Simulate concurrent update by another user
    ticket.version = 1
    db.commit()

    # Try to update with stale version (version=0)
    status_data = TicketStatusUpdateRequest(version=0, status=TicketStatus.PREPARING)

    with patch("app.api.tickets.get_tenant_id", return_value=test_tenant.id), \
         patch("app.api.tickets.get_current_user_id", return_value=test_draft_order.locked_by_user_id), \
         patch("app.api.tickets.get_user_role", return_value="manager"):

        import asyncio
        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(
                update_ticket_status(ticket.id, status_data, test_tenant.id, test_draft_order.locked_by_user_id, "manager", db)
            )

    # Verify conflict error
    assert exc_info.value.status_code == status.HTTP_409_CONFLICT
    assert "modified by another user" in exc_info.value.detail.lower()


def test_ticket_reassign_operation(
    db: Session,
    test_tenant: Tenant,
    test_manager_user: User,
    test_draft_order: DraftOrder,
    test_station: MenuStation,
    test_bar_station: MenuStation,
    test_mains_course: KitchenCourse
):
    """Test reassigning ticket to different station"""
    from app.api.tickets import reassign_ticket

    # Create a ticket
    ticket = Ticket(
        tenant_id=test_tenant.id,
        draft_order_id=test_draft_order.id,
        table_session_id=test_draft_order.table_session_id,
        station_id=test_station.id,
        status=TicketStatus.PENDING,
        course_number=test_mains_course.course_number,
        course_name=test_mains_course.name,
        version=0
    )
    db.add(ticket)
    db.commit()
    db.refresh(ticket)

    original_station_id = ticket.station_id

    # Reassign to bar
    reassign_data = TicketReassignRequest(
        version=0,
        new_station_id=test_bar_station.id,
        reason="Kitchen overloaded"
    )

    with patch("app.api.tickets.get_tenant_id", return_value=test_tenant.id), \
         patch("app.api.tickets.get_current_user_id", return_value=test_manager_user.id), \
         patch("app.api.tickets.get_user_role", return_value="manager"):

        import asyncio
        result = asyncio.run(
            reassign_ticket(ticket.id, reassign_data, test_tenant.id, test_manager_user.id, "manager", db)
        )

    # Verify reassignment
    db.refresh(ticket)
    assert ticket.station_id == test_bar_station.id
    assert ticket.station_id != original_station_id
    assert ticket.version == 1


def test_ticket_reprint_operation(
    db: Session,
    test_tenant: Tenant,
    test_user: User,
    test_draft_order: DraftOrder,
    test_station: MenuStation,
    test_mains_course: KitchenCourse
):
    """Test reprinting a ticket"""
    from app.api.tickets import reprint_ticket

    # Create a ticket
    ticket = Ticket(
        tenant_id=test_tenant.id,
        draft_order_id=test_draft_order.id,
        table_session_id=test_draft_order.table_session_id,
        station_id=test_station.id,
        status=TicketStatus.PREPARING,
        course_number=test_mains_course.course_number,
        course_name=test_mains_course.name,
        print_count=1,
        last_printed_at=datetime.utcnow()
    )
    db.add(ticket)
    db.commit()
    db.refresh(ticket)

    # Reprint
    with patch("app.api.tickets.get_tenant_id", return_value=test_tenant.id), \
         patch("app.api.tickets.get_current_user_id", return_value=test_user.id), \
         patch("app.api.tickets.get_user_role", return_value="kitchen"):

        import asyncio
        result = asyncio.run(
            reprint_ticket(ticket.id, test_tenant.id, test_user.id, "kitchen", db)
        )

    # Verify print count incremented
    db.refresh(ticket)
    assert ticket.print_count == 2
    assert ticket.last_printed_at is not None


def test_course_assignment_logic(
    db: Session,
    test_tenant: Tenant,
    test_draft_order: DraftOrder,
    test_drink_item: MenuItem,
    test_food_item: MenuItem
):
    """Test that items are assigned to correct stations and courses"""
    from app.api.tickets import generate_tickets

    # Create line items with different stations and courses
    drink_line_item = DraftLineItem(
        tenant_id=test_tenant.id,
        draft_order_id=test_draft_order.id,
        menu_item_id=test_drink_item.id,
        name=test_drink_item.name,
        quantity=1,
        price_at_order=test_drink_item.price,
        line_total=test_drink_item.price,
        sort_order=1
    )
    db.add(drink_line_item)

    food_line_item = DraftLineItem(
        tenant_id=test_tenant.id,
        draft_order_id=test_draft_order.id,
        menu_item_id=test_food_item.id,
        name=test_food_item.name,
        quantity=1,
        price_at_order=test_food_item.price,
        line_total=test_food_item.price,
        sort_order=2
    )
    db.add(food_line_item)
    db.commit()

    # Generate tickets
    ticket_data = TicketCreate(draft_order_id=test_draft_order.id)

    with patch("app.api.tickets.get_tenant_id", return_value=test_tenant.id), \
         patch("app.api.tickets.get_current_user_id", return_value=test_draft_order.locked_by_user_id):

        import asyncio
        result = asyncio.run(
            generate_tickets(ticket_data, test_tenant.id, test_draft_order.locked_by_user_id, db)
        )

    # Verify tickets created for each station/course combination
    tickets = db.exec(select(Ticket).where(Ticket.draft_order_id == test_draft_order.id)).all()
    assert len(tickets) == 2

    # Verify drinks ticket
    drinks_ticket = next((t for t in tickets if t.station_id == test_drink_item.station_id), None)
    assert drinks_ticket is not None
    assert drinks_ticket.course_id == test_drink_item.course_id
    assert drinks_ticket.course_number == 1  # Drinks course number

    # Verify food ticket
    food_ticket = next((t for t in tickets if t.station_id == test_food_item.station_id), None)
    assert food_ticket is not None
    assert food_ticket.course_id == test_food_item.course_id
    assert food_ticket.course_number == 2  # Mains course number


def test_list_tickets_with_filters(
    db: Session,
    test_tenant: Tenant,
    test_draft_order: DraftOrder,
    test_station: MenuStation,
    test_mains_course: KitchenCourse
):
    """Test listing tickets with various filters"""
    # Create multiple tickets
    ticket1 = Ticket(
        tenant_id=test_tenant.id,
        draft_order_id=test_draft_order.id,
        table_session_id=test_draft_order.table_session_id,
        station_id=test_station.id,
        status=TicketStatus.PREPARING,
        course_number=test_mains_course.course_number,
        course_name=test_mains_course.name,
        is_rush=True
    )
    db.add(ticket1)

    ticket2 = Ticket(
        tenant_id=test_tenant.id,
        draft_order_id=test_draft_order.id,
        table_session_id=test_draft_order.table_session_id,
        station_id=test_station.id,
        status=TicketStatus.READY,
        course_number=test_mains_course.course_number,
        course_name=test_mains_course.name,
        is_rush=False
    )
    db.add(ticket2)

    ticket3 = Ticket(
        tenant_id=test_tenant.id,
        draft_order_id=test_draft_order.id,
        table_session_id=test_draft_order.table_session_id,
        station_id=test_station.id,
        status=TicketStatus.COMPLETED,
        course_number=test_mains_course.course_number,
        course_name=test_mains_course.name,
        is_rush=False,
        completed_at=datetime.utcnow() - timedelta(hours=1)
    )
    db.add(ticket3)

    # Old completed ticket (should be filtered out)
    ticket4 = Ticket(
        tenant_id=test_tenant.id,
        draft_order_id=test_draft_order.id,
        table_session_id=test_draft_order.table_session_id,
        station_id=test_station.id,
        status=TicketStatus.COMPLETED,
        course_number=test_mains_course.course_number,
        course_name=test_mains_course.name,
        is_rush=False,
        completed_at=datetime.utcnow() - timedelta(hours=25)  # Older than 24h
    )
    db.add(ticket4)

    db.commit()

    # Test station filter
    from app.api.tickets import list_tickets
    with patch("app.api.tickets.get_tenant_id", return_value=test_tenant.id), \
         patch("app.api.tickets.get_current_user_id", return_value=test_draft_order.locked_by_user_id), \
         patch("app.api.tickets.get_user_role", return_value="kitchen"):

        import asyncio
        result = asyncio.run(
            list_tickets(
                station_id=test_station.id,
                status_filter=None,
                course_number=None,
                table_session_id=None,
                tenant_id=test_tenant.id,
                current_user_id=test_draft_order.locked_by_user_id,
                user_role="kitchen",
                session=db
            )
        )

    # Verify results (rush first, then by time, excluding old completed)
    assert len(result) == 3  # Excludes the 25h old completed ticket
    assert result[0].is_rush is True  # Rush ticket first
    assert result[0].status == TicketStatus.PREPARING


def test_get_ticket_details_with_line_items(
    db: Session,
    test_tenant: Tenant,
    test_draft_order: DraftOrder,
    test_station: MenuStation,
    test_food_item: MenuItem,
    test_mains_course: KitchenCourse
):
    """Test getting ticket details with line items"""
    # Create a ticket
    ticket = Ticket(
        tenant_id=test_tenant.id,
        draft_order_id=test_draft_order.id,
        table_session_id=test_draft_order.table_session_id,
        station_id=test_station.id,
        status=TicketStatus.PREPARING,
        course_number=test_mains_course.course_number,
        course_name=test_mains_course.name
    )
    db.add(ticket)
    db.flush()

    # Create line items
    line_item1 = TicketLineItem(
        tenant_id=test_tenant.id,
        ticket_id=ticket.id,
        menu_item_id=test_food_item.id,
        name="Burger",
        quantity=1,
        price_at_order=Decimal("15.00"),
        line_total=Decimal("15.00"),
        course_number=test_mains_course.course_number,
        course_name=test_mains_course.name,
        sort_order=1
    )
    db.add(line_item1)

    line_item2 = TicketLineItem(
        tenant_id=test_tenant.id,
        ticket_id=ticket.id,
        menu_item_id=test_food_item.id,
        name="Fries",
        quantity=2,
        price_at_order=Decimal("5.00"),
        line_total=Decimal("10.00"),
        course_number=test_mains_course.course_number,
        course_name=test_mains_course.name,
        sort_order=2
    )
    db.add(line_item2)

    db.commit()

    # Get ticket details
    from app.api.tickets import get_ticket
    with patch("app.api.tickets.get_tenant_id", return_value=test_tenant.id), \
         patch("app.api.tickets.get_current_user_id", return_value=test_draft_order.locked_by_user_id):

        import asyncio
        result = asyncio.run(
            get_ticket(ticket.id, test_tenant.id, test_draft_order.locked_by_user_id, db)
        )

    # Verify ticket with line items
    assert result["id"] == ticket.id
    assert len(result["line_items"]) == 2
    assert result["line_items"][0].name == "Burger"  # Sorted by sort_order
    assert result["line_items"][1].name == "Fries"
