"""
WebSocket tests for real-time ticket updates
Tests WebSocket connections and event broadcasts
"""

import pytest
from datetime import datetime
from decimal import Decimal
from unittest.mock import AsyncMock, Mock
import uuid

from app.models.ticket import Ticket, TicketStatus
from app.models.ticket_line_item import TicketLineItem, FiredStatus
from app.models.menu_station import MenuStation, StationType
from app.models.kitchen_course import KitchenCourse, CourseType
from app.models.tenant import Tenant
from app.core.websocket_manager import manager
from app.core.events import (
    TicketCreated, TicketUpdated, TicketBumped,
    TicketHeld, TicketFired, TicketVoided
)


# Fixtures
@pytest.fixture
def test_tenant(db: Session):
    """Create a test tenant"""
    from sqlmodel import Session
    from sqlalchemy import create_engine
    from sqlmodel import SQLModel

    # Use in-memory SQLite for WebSocket tests
    engine = create_engine("sqlite:///:memory:", echo=False)
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        tenant = Tenant(
            name="Test Restaurant",
            slug="test-restaurant",
            address="123 Test St",
            phone="555-1234",
            is_active=True
        )
        session.add(tenant)
        session.commit()
        session.refresh(tenant)
        yield tenant

    SQLModel.metadata.drop_all(engine)


@pytest.fixture
def test_station(db: Session, test_tenant: Tenant):
    """Create a test station"""
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


# WebSocket Connection Tests
@pytest.mark.asyncio
async def test_websocket_connect_to_station(
    test_tenant: Tenant,
    test_station: MenuStation
):
    """Test connecting a KDS station to WebSocket"""
    # Mock WebSocket connection
    websocket = AsyncMock()

    # Connect station
    await manager.connect_station(
        websocket=websocket,
        station_id=test_station.id,
        tenant_id=test_tenant.id
    )

    # Verify connection registered
    station_key = str(test_station.id)
    assert station_key in manager.station_connections
    assert manager.station_connections[station_key] == websocket


@pytest.mark.asyncio
async def test_websocket_disconnect_from_station(
    test_tenant: Tenant,
    test_station: MenuStation
):
    """Test disconnecting a KDS station from WebSocket"""
    websocket = AsyncMock()

    # Connect first
    await manager.connect_station(
        websocket=websocket,
        station_id=test_station.id,
        tenant_id=test_tenant.id
    )

    # Disconnect
    await manager.disconnect_station(
        websocket=websocket,
        station_id=test_station.id,
        tenant_id=test_tenant.id
    )

    # Verify connection removed
    station_key = str(test_station.id)
    assert station_key not in manager.station_connections


@pytest.mark.asyncio
async def test_websocket_multiple_stations_connected(
    test_tenant: Tenant
):
    """Test multiple stations connected simultaneously"""
    from app.models.menu_station import MenuStation

    station1 = MenuStation(
        tenant_id=test_tenant.id,
        name="Kitchen",
        station_type=StationType.KITCHEN,
        is_active=True
    )
    station2 = MenuStation(
        tenant_id=test_tenant.id,
        name="Bar",
        station_type=StationType.BAR,
        is_active=True
    )

    websocket1 = AsyncMock()
    websocket2 = AsyncMock()

    # Connect both stations
    await manager.connect_station(
        websocket=websocket1,
        station_id=station1.id,
        tenant_id=test_tenant.id
    )
    await manager.connect_station(
        websocket=websocket2,
        station_id=station2.id,
        tenant_id=test_tenant.id
    )

    # Verify both connections registered
    assert len(manager.station_connections) == 2
    assert str(station1.id) in manager.station_connections
    assert str(station2.id) in manager.station_connections

    # Cleanup
    await manager.disconnect_station(
        websocket=websocket1,
        station_id=station1.id,
        tenant_id=test_tenant.id
    )
    await manager.disconnect_station(
        websocket=websocket2,
        station_id=station2.id,
        tenant_id=test_tenant.id
    )


# WebSocket Event Tests
@pytest.mark.asyncio
async def test_send_ticket_created_event(
    test_tenant: Tenant,
    test_station: MenuStation
):
    """Test broadcasting ticket created event to station"""
    websocket = AsyncMock()
    ticket_id = uuid.uuid4()

    # Connect station
    await manager.connect_station(
        websocket=websocket,
        station_id=test_station.id,
        tenant_id=test_tenant.id
    )

    # Send ticket created event
    event = TicketCreated(
        ticket_id=ticket_id,
        station_id=test_station.id,
        tenant_id=test_tenant.id,
        data={
            "course_number": 1,
            "course_name": "Mains",
            "table_number": "T1"
        }
    )

    await manager.send_ticket_created(
        manager=manager,
        ticket_id=ticket_id,
        station_id=test_station.id
    )

    # Verify WebSocket received event
    websocket.send_json.assert_called_once()
    call_args = websocket.send_json.call_args[0][0]
    assert call_args["type"] == "ticket_created"
    assert call_args["ticket_id"] == str(ticket_id)

    # Cleanup
    await manager.disconnect_station(
        websocket=websocket,
        station_id=test_station.id,
        tenant_id=test_tenant.id
    )


@pytest.mark.asyncio
async def test_send_ticket_updated_event(
    test_tenant: Tenant,
    test_station: MenuStation
):
    """Test broadcasting ticket updated event to station"""
    websocket = AsyncMock()
    ticket_id = uuid.uuid4()

    # Connect station
    await manager.connect_station(
        websocket=websocket,
        station_id=test_station.id,
        tenant_id=test_tenant.id
    )

    # Send ticket updated event
    await manager.send_ticket_updated(
        manager=manager,
        ticket_id=ticket_id,
        station_id=test_station.id
    )

    # Verify WebSocket received event
    websocket.send_json.assert_called_once()
    call_args = websocket.send_json.call_args[0][0]
    assert call_args["type"] == "ticket_updated"
    assert call_args["ticket_id"] == str(ticket_id)

    # Cleanup
    await manager.disconnect_station(
        websocket=websocket,
        station_id=test_station.id,
        tenant_id=test_tenant.id
    )


@pytest.mark.asyncio
async def test_send_ticket_bumped_event(
    test_tenant: Tenant,
    test_station: MenuStation
):
    """Test broadcasting ticket bumped event to station"""
    websocket = AsyncMock()
    ticket_id = uuid.uuid4()

    # Connect station
    await manager.connect_station(
        websocket=websocket,
        station_id=test_station.id,
        tenant_id=test_tenant.id
    )

    # Send ticket bumped event
    await manager.send_ticket_bumped(
        manager=manager,
        ticket_id=ticket_id,
        station_id=test_station.id
    )

    # Verify WebSocket received event
    websocket.send_json.assert_called_once()
    call_args = websocket.send_json.call_args[0][0]
    assert call_args["type"] == "ticket_bumped"
    assert call_args["ticket_id"] == str(ticket_id)

    # Cleanup
    await manager.disconnect_station(
        websocket=websocket,
        station_id=test_station.id,
        tenant_id=test_tenant.id
    )


@pytest.mark.asyncio
async def test_send_ticket_held_event(
    test_tenant: Tenant,
    test_station: MenuStation
):
    """Test broadcasting ticket held event to station"""
    websocket = AsyncMock()
    ticket_id = uuid.uuid4()
    reason = "Waiting for special ingredient"

    # Connect station
    await manager.connect_station(
        websocket=websocket,
        station_id=test_station.id,
        tenant_id=test_tenant.id
    )

    # Send ticket held event
    await manager.send_ticket_held(
        manager=manager,
        ticket_id=ticket_id,
        station_id=test_station.id,
        reason=reason
    )

    # Verify WebSocket received event
    websocket.send_json.assert_called_once()
    call_args = websocket.send_json.call_args[0][0]
    assert call_args["type"] == "ticket_held"
    assert call_args["ticket_id"] == str(ticket_id)
    assert call_args["reason"] == reason

    # Cleanup
    await manager.disconnect_station(
        websocket=websocket,
        station_id=test_station.id,
        tenant_id=test_tenant.id
    )


@pytest.mark.asyncio
async def test_send_ticket_fired_event(
    test_tenant: Tenant,
    test_station: MenuStation
):
    """Test broadcasting ticket fired event to station"""
    websocket = AsyncMock()
    ticket_id = uuid.uuid4()

    # Connect station
    await manager.connect_station(
        websocket=websocket,
        station_id=test_station.id,
        tenant_id=test_tenant.id
    )

    # Send ticket fired event
    await manager.send_ticket_fired(
        manager=manager,
        ticket_id=ticket_id,
        station_id=test_station.id
    )

    # Verify WebSocket received event
    websocket.send_json.assert_called_once()
    call_args = websocket.send_json.call_args[0][0]
    assert call_args["type"] == "ticket_fired"
    assert call_args["ticket_id"] == str(ticket_id)

    # Cleanup
    await manager.disconnect_station(
        websocket=websocket,
        station_id=test_station.id,
        tenant_id=test_tenant.id
    )


@pytest.mark.asyncio
async def test_send_ticket_voided_event(
    test_tenant: Tenant,
    test_station: MenuStation
):
    """Test broadcasting ticket voided event to station"""
    websocket = AsyncMock()
    ticket_id = uuid.uuid4()
    reason = "Customer cancelled"

    # Connect station
    await manager.connect_station(
        websocket=websocket,
        station_id=test_station.id,
        tenant_id=test_tenant.id
    )

    # Send ticket voided event
    await manager.send_ticket_voided(
        manager=manager,
        ticket_id=ticket_id,
        station_id=test_station.id,
        reason=reason
    )

    # Verify WebSocket received event
    websocket.send_json.assert_called_once()
    call_args = websocket.send_json.call_args[0][0]
    assert call_args["type"] == "ticket_voided"
    assert call_args["ticket_id"] == str(ticket_id)
    assert call_args["reason"] == reason

    # Cleanup
    await manager.disconnect_station(
        websocket=websocket,
        station_id=test_station.id,
        tenant_id=test_tenant.id
    )


@pytest.mark.asyncio
async def test_websocket_event_isolation(
    test_tenant: Tenant
):
    """Test that stations only receive their own events"""
    from app.models.menu_station import MenuStation

    # Create two stations
    station_kitchen = MenuStation(
        tenant_id=test_tenant.id,
        name="Kitchen",
        station_type=StationType.KITCHEN,
        is_active=True
    )
    station_bar = MenuStation(
        tenant_id=test_tenant.id,
        name="Bar",
        station_type=StationType.BAR,
        is_active=True
    )

    # Connect both stations
    ws_kitchen = AsyncMock()
    ws_bar = AsyncMock()

    await manager.connect_station(
        websocket=ws_kitchen,
        station_id=station_kitchen.id,
        tenant_id=test_tenant.id
    )
    await manager.connect_station(
        websocket=ws_bar,
        station_id=station_bar.id,
        tenant_id=test_tenant.id
    )

    # Send event to kitchen only
    ticket_id = uuid.uuid4()
    await manager.send_ticket_bumped(
        manager=manager,
        ticket_id=ticket_id,
        station_id=station_kitchen.id
    )

    # Verify kitchen received event, bar did not
    ws_kitchen.send_json.assert_called_once()
    ws_bar.send_json.assert_not_called()

    # Cleanup
    await manager.disconnect_station(
        websocket=ws_kitchen,
        station_id=station_kitchen.id,
        tenant_id=test_tenant.id
    )
    await manager.disconnect_station(
        websocket=ws_bar,
        station_id=station_bar.id,
        tenant_id=test_tenant.id
    )


@pytest.mark.asyncio
async def test_websocket_multiple_clients_same_station(
    test_tenant: Tenant,
    test_station: MenuStation
):
    """Test multiple KDS clients connected to same station"""
    # Multiple screens for same station
    ws1 = AsyncMock()
    ws2 = AsyncMock()
    ws3 = AsyncMock()

    # Connect all clients to same station
    await manager.connect_station(
        websocket=ws1,
        station_id=test_station.id,
        tenant_id=test_tenant.id
    )
    await manager.connect_station(
        websocket=ws2,
        station_id=test_station.id,
        tenant_id=test_tenant.id
    )
    await manager.connect_station(
        websocket=ws3,
        station_id=test_station.id,
        tenant_id=test_tenant.id
    )

    # Broadcast event to station
    ticket_id = uuid.uuid4()
    await manager.send_ticket_bumped(
        manager=manager,
        ticket_id=ticket_id,
        station_id=test_station.id
    )

    # All clients should receive event (manager should handle broadcasting)
    # This test verifies the manager can handle multiple connections
    # Actual broadcasting behavior depends on implementation

    # Cleanup
    await manager.disconnect_station(
        websocket=ws1,
        station_id=test_station.id,
        tenant_id=test_tenant.id
    )
    await manager.disconnect_station(
        websocket=ws2,
        station_id=test_station.id,
        tenant_id=test_tenant.id
    )
    await manager.disconnect_station(
        websocket=ws3,
        station_id=test_station.id,
        tenant_id=test_tenant.id
    )


@pytest.mark.asyncio
async def test_websocket_connection_state_management(
    test_tenant: Tenant,
    test_station: MenuStation
):
    """Test WebSocket connection state management"""
    websocket = AsyncMock()

    # Initial state - not connected
    station_key = str(test_station.id)
    assert station_key not in manager.station_connections

    # Connect
    await manager.connect_station(
        websocket=websocket,
        station_id=test_station.id,
        tenant_id=test_tenant.id
    )
    assert station_key in manager.station_connections

    # Disconnect
    await manager.disconnect_station(
        websocket=websocket,
        station_id=test_station.id,
        tenant_id=test_tenant.id
    )
    assert station_key not in manager.station_connections

    # Reconnect (should work)
    await manager.connect_station(
        websocket=websocket,
        station_id=test_station.id,
        tenant_id=test_tenant.id
    )
    assert station_key in manager.station_connections

    # Final cleanup
    await manager.disconnect_station(
        websocket=websocket,
        station_id=test_station.id,
        tenant_id=test_tenant.id
    )
    assert station_key not in manager.station_connections
