"""
WebSocket endpoints for real-time updates
"""

from fastapi import APIRouter, WebSocket, Depends, WebSocketDisconnect, status
from sqlmodel import Session, select
from datetime import datetime
from typing import Optional
import structlog
import uuid

from app.core.database import get_session
from app.core.dependencies import get_tenant_id, get_current_user_id
from app.core.websocket_manager import manager
from app.models.menu_station import MenuStation
from app.models.draft_order import DraftOrder
from app.models.table import Table
from app.models.table_session import TableSession

logger = structlog.get_logger(__name__)
router = APIRouter()


@router.websocket("/table/{table_session_id}")
async def websocket_table_session(
    websocket: WebSocket,
    table_session_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    current_user_id: uuid.UUID = Depends(get_current_user_id)
):
    """WebSocket connection for guest at a table session"""
    try:
        # Verify table session exists and belongs to tenant
        session = next(get_session())
        table_session = session.exec(
            select(TableSession).where(
                TableSession.id == table_session_id,
                TableSession.tenant_id == tenant_id
            )
        ).first()

        if not table_session:
            logger.warning(f"Table session {table_session_id} not found for tenant {tenant_id}")
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        table = session.exec(
            select(Table).where(Table.id == table_session.table_id)
        ).first()

        if not table or table.tenant_id != tenant_id:
            logger.warning(f"Table {table_session.table_id} not found for tenant {tenant_id}")
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        # Connect to WebSocket
        message = await manager.connect_table(websocket, table_session_id)

        # Send connection confirmation
        await websocket.send_json({
            "type": "connection_confirmed",
            "table_session_id": str(table_session_id),
            "table_number": table.number if table else None,
            "message": message
        })

        # Listen for incoming messages (client pings, etc.)
        while True:
            try:
                data = await websocket.receive_json()
                logger.debug(f"Received message from table {table_session_id}: {data}")

                # Handle specific message types
                if data.get("type") == "ping":
                    await websocket.send_json({
                        "type": "pong",
                        "timestamp": datetime.utcnow().isoformat()
                    })

            except WebSocketDisconnect:
                manager.disconnect(websocket)
                logger.info(f"Table {table_session_id} disconnected")
                break

    except Exception as e:
        logger.error(f"Error in table WebSocket: {e}", exc_info=True)
        manager.disconnect(websocket)


@router.websocket("/user/{user_id}")
async def websocket_user(
    websocket: WebSocket,
    user_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_tenant_id)
):
    """WebSocket connection for staff user"""
    try:
        # Verify user exists and belongs to tenant
        session = next(get_session())
        from app.models.user import User
        user = session.exec(
            select(User).where(User.id == user_id, User.tenant_id == tenant_id)
        ).first()

        if not user:
            logger.warning(f"User {user_id} not found for tenant {tenant_id}")
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        # Connect to WebSocket
        message = await manager.connect_user(websocket, user_id)

        # Send connection confirmation
        await websocket.send_json({
            "type": "connection_confirmed",
            "user_id": str(user_id),
            "user_name": user.name,
            "message": message
        })

        # Send initial active drafts count
        active_drafts = session.exec(
            select(DraftOrder).where(
                DraftOrder.tenant_id == tenant_id,
                DraftOrder.status == "pending"
            )
        ).all()

        await websocket.send_json({
            "type": "initial_state",
            "active_drafts_count": len(active_drafts)
        })

        # Listen for incoming messages
        while True:
            try:
                data = await websocket.receive_json()
                logger.debug(f"Received message from user {user_id}: {data}")

                # Handle specific message types
                if data.get("type") == "ping":
                    await websocket.send_json({
                        "type": "pong",
                        "timestamp": datetime.utcnow().isoformat()
                    })

            except WebSocketDisconnect:
                manager.disconnect(websocket)
                logger.info(f"User {user_id} disconnected")
                break

    except Exception as e:
        logger.error(f"Error in user WebSocket: {e}", exc_info=True)
        manager.disconnect(websocket)


@router.websocket("/station/{station_id}")
async def websocket_station(
    websocket: WebSocket,
    station_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    current_user_id: uuid.UUID = Depends(get_current_user_id)
):
    """WebSocket connection for KDS station screen"""
    try:
        # Verify station exists and belongs to tenant
        session = next(get_session())
        station = session.exec(
            select(MenuStation).where(
                MenuStation.id == station_id,
                MenuStation.tenant_id == tenant_id
            )
        ).first()

        if not station:
            logger.warning(f"Station {station_id} not found for tenant {tenant_id}")
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        if not station.is_active:
            logger.warning(f"Station {station_id} is not active")
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        # Connect to WebSocket
        message = await manager.connect_station(websocket, station_id)

        # Send connection confirmation
        await websocket.send_json({
            "type": "connection_confirmed",
            "station_id": str(station_id),
            "station_name": station.name,
            "station_type": station.station_type,
            "message": message
        })

        # Listen for incoming messages
        while True:
            try:
                data = await websocket.receive_json()
                logger.debug(f"Received message from station {station_id}: {data}")

                # Handle specific message types
                if data.get("type") == "ping":
                    await websocket.send_json({
                        "type": "pong",
                        "timestamp": datetime.utcnow().isoformat()
                    })

            except WebSocketDisconnect:
                manager.disconnect(websocket)
                logger.info(f"Station {station_id} disconnected")
                break

    except Exception as e:
        logger.error(f"Error in station WebSocket: {e}", exc_info=True)
        manager.disconnect(websocket)


@router.get("/connections")
async def get_connections():
    """Get count of active WebSocket connections"""
    count = manager.get_connection_count()
    return {
        "table_connections": count.get("table_connections", 0),
        "user_connections": count.get("user_connections", 0),
        "station_connections": count.get("station_connections", 0),
        "total_connections": sum([
            count.get("table_connections", 0),
            count.get("user_connections", 0),
            count.get("station_connections", 0)
        ])
    }
