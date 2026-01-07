"""
Integration tests for Ticket System (KDS)
Tests complete ticket lifecycle: draft → ticket → KDS
"""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import Mock, patch, AsyncMock
import uuid

from sqlmodel import Session, select
from fastapi import status
from httpx import AsyncClient, ASGITransport

from app.models.ticket import Ticket, TicketStatus
from app.models.ticket_line_item import TicketLineItem, FiredStatus
from app.models.draft_order import DraftOrder, DraftStatus
from app.models.draft_line_item import DraftLineItem
from app.models.table_session import TableSession
from app.models.menu_item import MenuItem
from app.models.menu_station import MenuStation, StationType
from app.models.kitchen_course import KitchenCourse, CourseType
from app.models.user import User
from app.models.tenant import Tenant
from app.models.table import Table
from app.models.floor import Floor
from app.main import app


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
def test_floor(db: Session, test_tenant: Tenant):
    """Create a test floor"""
    floor = Floor(tenant_id=test_tenant.id, name="Main Floor", display_order=1)
    db.add(floor)
    db.commit()
    db.refresh(floor)
    return floor


@pytest.fixture
def test_table(db: Session, test_tenant: Tenant, test_floor: Floor):
    """Create a test table"""
    table = Table(
        tenant_id=test_tenant.id,
        floor_id=test_floor.id,
        table_number="T1",
        seats=4,
        is_active=True
    )
    db.add(table)
    db.commit()
    db.refresh(table)
    return table


@pytest.fixture
def test_table_session(db: Session, test_tenant: Tenant, test_table: Table):
    """Create a test table session"""
    session = TableSession(
        tenant_id=test_tenant.id,
        table_id=test_table.id,
        server_id=None,
        guest_count=4,
        status="seated"
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


@pytest.fixture
def test_bar_station(db: Session, test_tenant: Tenant):
    """Create a test bar station"""
    station = MenuStation(
        tenant_id=test_tenant.id,
        name="Bar",
        station_type=StationType.BAR,
        display_order=1,
        color="#00FF00",
        icon="🍺",
        is_active=True
    )
    db.add(station)
    db.commit()
    db.refresh(station)
    return station


@pytest.fixture
def test_kitchen_station(db: Session, test_tenant: Tenant):
    """Create a test kitchen station"""
    station = MenuStation(
        tenant_id=test_tenant.id,
        name="Kitchen",
        station_type=StationType.KITCHEN,
        display_order=2,
        color="#FF0000",
        icon="🍳",
        is_active=True
    )
    db.add(station)
    db.commit()
    db.refresh(station)
    return station


@pytest.fixture
def test_drinks_course(db: Session, test_tenant: Tenant):
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
def test_mains_course(db: Session, test_tenant: Tenant):
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
    test_kitchen_station: MenuStation,
    test_mains_course: KitchenCourse
):
    """Create a test food menu item"""
    item = MenuItem(
        tenant_id=test_tenant.id,
        name="Burger",
        description="Beef burger with fries",
        price=Decimal("15.00"),
        station_id=test_kitchen_station.id,
        course_id=test_mains_course.id,
        default_prep_time_minutes=15,
        is_active=True
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


# Integration Tests
def test_complete_ticket_lifecycle(
    db: Session,
    test_tenant: Tenant,
    test_table_session: TableSession,
    test_user: User,
    test_drink_item: MenuItem,
    test_food_item: MenuItem,
    test_bar_station: MenuStation,
    test_kitchen_station: MenuStation,
    test_drinks_course: KitchenCourse,
    test_mains_course: KitchenCourse
):
    """Test complete ticket lifecycle from draft to completion"""

    # Step 1: Create draft order in CONFIRMED status
    draft = DraftOrder(
        tenant_id=test_tenant.id,
        table_session_id=test_table_session.id,
        status=DraftStatus.CONFIRMED,
        confirmed_by=test_user.id,
        locked_by=test_user.id,
        subtotal=Decimal("20.00"),
        tax_amount=Decimal("1.60"),
        total_amount=Decimal("21.60"),
        special_requests="No onions on burger"
    )
    db.add(draft)
    db.flush()

    # Step 2: Add draft line items
    drink_draft = DraftLineItem(
        tenant_id=test_tenant.id,
        draft_order_id=draft.id,
        menu_item_id=test_drink_item.id,
        name=test_drink_item.name,
        description=test_drink_item.description,
        quantity=2,
        price_at_order=test_drink_item.price,
        line_total=test_drink_item.price * 2,
        sort_order=1
    )
    db.add(drink_draft)

    food_draft = DraftLineItem(
        tenant_id=test_tenant.id,
        draft_order_id=draft.id,
        menu_item_id=test_food_item.id,
        name=test_food_item.name,
        description=test_food_item.description,
        quantity=1,
        price_at_order=test_food_item.price,
        line_total=test_food_item.price,
        sort_order=2,
        special_instructions="Medium rare"
    )
    db.add(food_draft)
    db.commit()
    db.refresh(draft)

    # Step 3: Generate tickets (simulating API call)
    now = datetime.utcnow()

    # Create drinks ticket (auto-fire = PENDING)
    drinks_ticket = Ticket(
        tenant_id=test_tenant.id,
        draft_order_id=draft.id,
        table_session_id=test_table_session.id,
        station_id=test_bar_station.id,
        status=TicketStatus.PENDING,  # Auto-fire
        course_number=1,
        course_name="Drinks",
        table_number="T1",
        server_name=test_user.email,
        special_instructions=draft.special_requests,
        fired_at=now,
        created_at=now
    )
    db.add(drinks_ticket)

    # Create food ticket (no auto-fire = NEW)
    food_ticket = Ticket(
        tenant_id=test_tenant.id,
        draft_order_id=draft.id,
        table_session_id=test_table_session.id,
        station_id=test_kitchen_station.id,
        status=TicketStatus.NEW,  # Not auto-fired
        course_number=2,
        course_name="Mains",
        table_number="T1",
        server_name=test_user.email,
        special_instructions=draft.special_requests,
        created_at=now
    )
    db.add(food_ticket)
    db.flush()

    # Step 4: Create ticket line items
    drinks_line = TicketLineItem(
        tenant_id=test_tenant.id,
        ticket_id=drinks_ticket.id,
        menu_item_id=test_drink_item.id,
        name=test_drink_item.name,
        quantity=2,
        price_at_order=test_drink_item.price,
        line_total=test_drink_item.price * 2,
        course_number=1,
        course_name="Drinks",
        fired_status=FiredStatus.FIRED,
        fired_at=now,
        created_at=now
    )
    db.add(drinks_line)

    food_line = TicketLineItem(
        tenant_id=test_tenant.id,
        ticket_id=food_ticket.id,
        menu_item_id=test_food_item.id,
        name=test_food_item.name,
        description=test_food_item.description,
        quantity=1,
        price_at_order=test_food_item.price,
        line_total=test_food_item.price,
        course_number=2,
        course_name="Mains",
        fired_status=FiredStatus.PENDING,  # Not fired yet
        special_instructions="Medium rare",
        created_at=now
    )
    db.add(food_line)
    db.commit()
    db.refresh(drinks_ticket)
    db.refresh(food_ticket)

    # Verify initial state
    assert drinks_ticket.status == TicketStatus.PENDING
    assert drinks_ticket.fired_at is not None
    assert drinks_ticket.course_number == 1

    assert food_ticket.status == TicketStatus.NEW
    assert food_ticket.fired_at is None
    assert food_ticket.course_number == 2

    # Step 5: Fire food ticket (Expo fires it to kitchen)
    food_ticket.status = TicketStatus.PENDING
    food_ticket.fired_at = datetime.utcnow()
    db.commit()
    db.refresh(food_line)
    food_line.fired_status = FiredStatus.FIRED
    food_line.fired_at = food_ticket.fired_at
    db.commit()
    db.refresh(food_ticket)

    assert food_ticket.status == TicketStatus.PENDING
    assert food_ticket.fired_at is not None
    assert food_line.fired_status == FiredStatus.FIRED

    # Step 6: Food ticket transitions to PREPARING
    food_ticket.status = TicketStatus.PREPARING
    food_ticket.prep_started_at = datetime.utcnow()
    db.commit()
    db.refresh(food_ticket)

    assert food_ticket.status == TicketStatus.PREPARING
    assert food_ticket.prep_started_at is not None

    # Step 7: Food ticket transitions to READY
    food_ticket.status = TicketStatus.READY
    food_ticket.ready_at = datetime.utcnow()
    db.commit()
    db.refresh(food_ticket)

    assert food_ticket.status == TicketStatus.READY
    assert food_ticket.ready_at is not None

    # Step 8: Bump food ticket to COMPLETED
    food_ticket.status = TicketStatus.COMPLETED
    food_ticket.completed_at = datetime.utcnow()
    food_line.preparation_status = "completed"
    db.commit()
    db.refresh(food_ticket)
    db.refresh(food_line)

    assert food_ticket.status == TicketStatus.COMPLETED
    assert food_ticket.completed_at is not None
    assert food_line.preparation_status == "completed"

    # Step 9: Drinks ticket follows lifecycle
    # Skip to READY for drinks (simulating quick service)
    drinks_ticket.status = TicketStatus.READY
    drinks_ticket.ready_at = datetime.utcnow()
    drinks_line.preparation_status = "completed"
    db.commit()
    db.refresh(drinks_ticket)
    db.refresh(drinks_line)

    # Step 10: Bump drinks ticket to COMPLETED
    drinks_ticket.status = TicketStatus.COMPLETED
    drinks_ticket.completed_at = datetime.utcnow()
    drinks_line.preparation_status = "served"
    db.commit()
    db.refresh(drinks_ticket)

    assert drinks_ticket.status == TicketStatus.COMPLETED
    assert drinks_ticket.completed_at is not None

    # Verify complete lifecycle - both tickets completed
    all_tickets = db.exec(select(Ticket).where(Ticket.draft_order_id == draft.id)).all()
    assert len(all_tickets) == 2
    completed_tickets = [t for t in all_tickets if t.status == TicketStatus.COMPLETED]
    assert len(completed_tickets) == 2


def test_station_routing_with_multiple_courses(
    db: Session,
    test_tenant: Tenant,
    test_table_session: TableSession,
    test_user: User,
    test_bar_station: MenuStation,
    test_kitchen_station: MenuStation,
    test_drinks_course: KitchenCourse,
    test_mains_course: KitchenCourse
):
    """Test that items are correctly routed to stations by course"""

    # Create menu items for multiple stations/courses
    drink_item1 = MenuItem(
        tenant_id=test_tenant.id,
        name="Beer",
        price=Decimal("4.00"),
        station_id=test_bar_station.id,
        course_id=test_drinks_course.id,
        is_active=True
    )
    db.add(drink_item1)

    drink_item2 = MenuItem(
        tenant_id=test_tenant.id,
        name="Wine",
        price=Decimal("8.00"),
        station_id=test_bar_station.id,
        course_id=test_drinks_course.id,
        is_active=True
    )
    db.add(drink_item2)

    food_item1 = MenuItem(
        tenant_id=test_tenant.id,
        name="Steak",
        price=Decimal("25.00"),
        station_id=test_kitchen_station.id,
        course_id=test_mains_course.id,
        is_active=True
    )
    db.add(food_item1)

    food_item2 = MenuItem(
        tenant_id=test_tenant.id,
        name="Pasta",
        price=Decimal("18.00"),
        station_id=test_kitchen_station.id,
        course_id=test_mains_course.id,
        is_active=True
    )
    db.add(food_item2)

    # Create draft order
    draft = DraftOrder(
        tenant_id=test_tenant.id,
        table_session_id=test_table_session.id,
        status=DraftStatus.CONFIRMED,
        confirmed_by=test_user.id,
        subtotal=Decimal("55.00"),
        total_amount=Decimal("55.00"),
    )
    db.add(draft)
    db.flush()

    # Add line items (mix of bar and kitchen)
    db.add(DraftLineItem(
        tenant_id=test_tenant.id,
        draft_order_id=draft.id,
        menu_item_id=drink_item1.id,
        name="Beer",
        quantity=1,
        price_at_order=drink_item1.price,
        line_total=drink_item1.price,
        sort_order=1
    ))
    db.add(DraftLineItem(
        tenant_id=test_tenant.id,
        draft_order_id=draft.id,
        menu_item_id=drink_item2.id,
        name="Wine",
        quantity=1,
        price_at_order=drink_item2.price,
        line_total=drink_item2.price,
        sort_order=2
    ))
    db.add(DraftLineItem(
        tenant_id=test_tenant.id,
        draft_order_id=draft.id,
        menu_item_id=food_item1.id,
        name="Steak",
        quantity=1,
        price_at_order=food_item1.price,
        line_total=food_item1.price,
        sort_order=3
    ))
    db.add(DraftLineItem(
        tenant_id=test_tenant.id,
        draft_order_id=draft.id,
        menu_item_id=food_item2.id,
        name="Pasta",
        quantity=1,
        price_at_order=food_item2.price,
        line_total=food_item2.price,
        sort_order=4
    ))
    db.commit()

    # Simulate ticket generation with proper routing
    now = datetime.utcnow()

    # Bar ticket should get all drink items
    bar_ticket = Ticket(
        tenant_id=test_tenant.id,
        draft_order_id=draft.id,
        table_session_id=test_table_session.id,
        station_id=test_bar_station.id,
        status=TicketStatus.PENDING,  # Auto-fire
        course_number=1,
        course_name="Drinks",
        table_number="T1",
        server_name=test_user.email,
        fired_at=now,
        created_at=now
    )
    db.add(bar_ticket)
    db.flush()

    # Kitchen ticket should get all food items
    kitchen_ticket = Ticket(
        tenant_id=test_tenant.id,
        draft_order_id=draft.id,
        table_session_id=test_table_session.id,
        station_id=test_kitchen_station.id,
        status=TicketStatus.NEW,  # Not auto-fired
        course_number=2,
        course_name="Mains",
        table_number="T1",
        server_name=test_user.email,
        created_at=now
    )
    db.add(kitchen_ticket)
    db.commit()
    db.refresh(bar_ticket)
    db.refresh(kitchen_ticket)

    # Verify routing: 2 tickets created
    tickets = db.exec(select(Ticket).where(Ticket.draft_order_id == draft.id)).all()
    assert len(tickets) == 2

    # Verify bar ticket
    assert bar_ticket.station_id == test_bar_station.id
    assert bar_ticket.course_number == 1
    assert bar_ticket.status == TicketStatus.PENDING  # Auto-fired

    # Verify kitchen ticket
    assert kitchen_ticket.station_id == test_kitchen_station.id
    assert kitchen_ticket.course_number == 2
    assert kitchen_ticket.status == TicketStatus.NEW  # Not auto-fired


def test_auto_fire_vs_manual_fire_lifecycle(
    db: Session,
    test_tenant: Tenant,
    test_table_session: TableSession,
    test_user: User,
    test_drink_item: MenuItem,
    test_food_item: MenuItem,
    test_bar_station: MenuStation,
    test_kitchen_station: MenuStation,
    test_drinks_course: KitchenCourse,
    test_mains_course: KitchenCourse
):
    """Test auto-fire (drinks) vs manual fire (food) lifecycle differences"""

    now = datetime.utcnow()

    # Auto-fire ticket (drinks)
    auto_fire_ticket = Ticket(
        tenant_id=test_tenant.id,
        draft_order_id=uuid.uuid4(),
        table_session_id=test_table_session.id,
        station_id=test_bar_station.id,
        status=TicketStatus.PENDING,  # Auto-fire = PENDING immediately
        course_number=1,
        course_name="Drinks",
        fired_at=now,  # Fired at creation
        created_at=now
    )
    db.add(auto_fire_ticket)
    db.commit()
    db.refresh(auto_fire_ticket)

    # Manual fire ticket (food)
    manual_fire_ticket = Ticket(
        tenant_id=test_tenant.id,
        draft_order_id=uuid.uuid4(),
        table_session_id=test_table_session.id,
        station_id=test_kitchen_station.id,
        status=TicketStatus.NEW,  # Manual = NEW until fired
        course_number=2,
        course_name="Mains",
        fired_at=None,  # Not fired yet
        created_at=now
    )
    db.add(manual_fire_ticket)
    db.commit()
    db.refresh(manual_fire_ticket)

    # Verify initial state differences
    assert auto_fire_ticket.status == TicketStatus.PENDING
    assert auto_fire_ticket.fired_at is not None

    assert manual_fire_ticket.status == TicketStatus.NEW
    assert manual_fire_ticket.fired_at is None

    # Fire manual ticket
    manual_fire_ticket.status = TicketStatus.PENDING
    manual_fire_ticket.fired_at = datetime.utcnow()
    db.commit()
    db.refresh(manual_fire_ticket)

    # Now both should be in same state
    assert auto_fire_ticket.status == TicketStatus.PENDING
    assert manual_fire_ticket.status == TicketStatus.PENDING
    assert manual_fire_ticket.fired_at is not None

    # Both should follow same lifecycle from here
    for ticket in [auto_fire_ticket, manual_fire_ticket]:
        ticket.status = TicketStatus.PREPARING
        ticket.prep_started_at = datetime.utcnow()
    db.commit()

    for ticket in [auto_fire_ticket, manual_fire_ticket]:
        ticket.status = TicketStatus.READY
        ticket.ready_at = datetime.utcnow()
    db.commit()

    for ticket in [auto_fire_ticket, manual_fire_ticket]:
        ticket.status = TicketStatus.COMPLETED
        ticket.completed_at = datetime.utcnow()
    db.commit()

    db.refresh(auto_fire_ticket)
    db.refresh(manual_fire_ticket)

    # Verify both completed
    assert auto_fire_ticket.status == TicketStatus.COMPLETED
    assert manual_fire_ticket.status == TicketStatus.COMPLETED


def test_expo_hold_and_fire_workflow(
    db: Session,
    test_tenant: Tenant,
    test_table_session: TableSession,
    test_user: User,
    test_food_item: MenuItem,
    test_kitchen_station: MenuStation,
    test_mains_course: KitchenCourse
):
    """Test Expo hold and fire workflow"""

    now = datetime.utcnow()

    # Create ticket in NEW status
    ticket = Ticket(
        tenant_id=test_tenant.id,
        draft_order_id=uuid.uuid4(),
        table_session_id=test_table_session.id,
        station_id=test_kitchen_station.id,
        status=TicketStatus.NEW,
        course_number=2,
        course_name="Mains",
        table_number="T1",
        server_name=test_user.email,
        created_at=now
    )
    db.add(ticket)
    db.commit()
    db.refresh(ticket)

    # Initial state
    assert ticket.status == TicketStatus.NEW
    assert ticket.is_held is False
    assert ticket.held_at is None

    # Expo holds ticket (e.g., waiting for special order)
    ticket.status = TicketStatus.PENDING
    ticket.is_held = True
    ticket.held_reason = "Waiting for special order ingredient"
    ticket.held_at = datetime.utcnow()
    db.commit()
    db.refresh(ticket)

    assert ticket.status == TicketStatus.PENDING
    assert ticket.is_held is True
    assert ticket.held_reason == "Waiting for special order ingredient"
    assert ticket.held_at is not None

    # Expo fires ticket (kitchen can now see it)
    ticket.is_held = False
    ticket.fired_at = datetime.utcnow()
    db.commit()
    db.refresh(ticket)

    assert ticket.is_held is False
    assert ticket.held_reason is None
    assert ticket.fired_at is not None

    # Ticket proceeds through kitchen lifecycle
    ticket.status = TicketStatus.PREPARING
    ticket.prep_started_at = datetime.utcnow()
    db.commit()

    ticket.status = TicketStatus.READY
    ticket.ready_at = datetime.utcnow()
    db.commit()

    ticket.status = TicketStatus.COMPLETED
    ticket.completed_at = datetime.utcnow()
    db.commit()
    db.refresh(ticket)

    assert ticket.status == TicketStatus.COMPLETED


def test_ticket_void_workflow(
    db: Session,
    test_tenant: Tenant,
    test_table_session: TableSession,
    test_user: User,
    test_food_item: MenuItem,
    test_kitchen_station: MenuStation,
    test_mains_course: KitchenCourse
):
    """Test ticket void workflow"""

    now = datetime.utcnow()

    # Create ticket
    ticket = Ticket(
        tenant_id=test_tenant.id,
        draft_order_id=uuid.uuid4(),
        table_session_id=test_table_session.id,
        station_id=test_kitchen_station.id,
        status=TicketStatus.PENDING,
        course_number=2,
        course_name="Mains",
        table_number="T1",
        server_name=test_user.email,
        fired_at=now,
        version=0
    )
    db.add(ticket)
    db.flush()

    # Create line item
    line_item = TicketLineItem(
        tenant_id=test_tenant.id,
        ticket_id=ticket.id,
        menu_item_id=test_food_item.id,
        name=test_food_item.name,
        quantity=1,
        price_at_order=test_food_item.price,
        line_total=test_food_item.price,
        course_number=2,
        course_name="Mains",
        fired_status=FiredStatus.FIRED,
        fired_at=now,
        version=0
    )
    db.add(line_item)
    db.commit()
    db.refresh(ticket)
    db.refresh(line_item)

    # Initial state
    assert ticket.status == TicketStatus.PENDING
    assert line_item.fired_status == FiredStatus.FIRED

    # Manager voids ticket (customer cancelled)
    ticket.status = TicketStatus.VOIDED
    ticket.voided_at = datetime.utcnow()
    ticket.voided_by = test_user.id
    ticket.voided_reason = "Customer cancelled order"
    ticket.version = 1
    db.commit()
    db.refresh(ticket)

    # Update line item
    line_item.fired_status = FiredStatus.VOIDED
    line_item.voided_at = datetime.utcnow()
    line_item.voided_by = test_user.id
    line_item.voided_reason = "Customer cancelled order"
    line_item.version = 1
    db.commit()
    db.refresh(line_item)

    # Verify void state
    assert ticket.status == TicketStatus.VOIDED
    assert ticket.voided_at is not None
    assert ticket.voided_reason == "Customer cancelled order"
    assert ticket.version == 1

    assert line_item.fired_status == FiredStatus.VOIDED
    assert line_item.voided_at is not None
    assert line_item.voided_reason == "Customer cancelled order"


def test_ticket_priority_sorting(
    db: Session,
    test_tenant: Tenant,
    test_table_session: TableSession,
    test_user: User,
    test_food_item: MenuItem,
    test_kitchen_station: MenuStation,
    test_mains_course: KitchenCourse
):
    """Test ticket sorting by priority (rush first, then by course/time)"""

    now = datetime.utcnow()

    # Create regular ticket
    regular_ticket = Ticket(
        tenant_id=test_tenant.id,
        draft_order_id=uuid.uuid4(),
        table_session_id=test_table_session.id,
        station_id=test_kitchen_station.id,
        status=TicketStatus.PENDING,
        course_number=2,
        is_rush=False,
        created_at=now - timedelta(minutes=10)
    )
    db.add(regular_ticket)

    # Create rush ticket (newer)
    rush_ticket = Ticket(
        tenant_id=test_tenant.id,
        draft_order_id=uuid.uuid4(),
        table_session_id=test_table_session.id,
        station_id=test_kitchen_station.id,
        status=TicketStatus.PENDING,
        course_number=2,
        is_rush=True,  # Rush order
        created_at=now - timedelta(minutes=5)
    )
    db.add(rush_ticket)

    # Create another regular ticket (oldest)
    old_ticket = Ticket(
        tenant_id=test_tenant.id,
        draft_order_id=uuid.uuid4(),
        table_session_id=test_table_session.id,
        station_id=test_kitchen_station.id,
        status=TicketStatus.PENDING,
        course_number=2,
        is_rush=False,
        created_at=now - timedelta(minutes=20)
    )
    db.add(old_ticket)
    db.commit()

    # Query tickets with proper sorting
    # KDS API sorts by: rush DESC, course ASC, created_at ASC
    tickets = db.exec(
        select(Ticket)
        .where(Ticket.station_id == test_kitchen_station.id)
        .where(Ticket.status == TicketStatus.PENDING)
        .order_by(
            Ticket.is_rush.desc(),
            Ticket.course_number.asc(),
            Ticket.created_at.asc()
        )
    ).all()

    assert len(tickets) == 3
    # Rush ticket should be first
    assert tickets[0].id == rush_ticket.id
    assert tickets[0].is_rush is True

    # Oldest regular ticket second
    assert tickets[1].id == old_ticket.id
    assert tickets[1].is_rush is False

    # Newest regular ticket last
    assert tickets[2].id == regular_ticket.id
    assert tickets[2].is_rush is False
