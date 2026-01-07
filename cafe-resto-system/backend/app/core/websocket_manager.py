"""
WebSocket connection manager for real-time updates

Manages WebSocket connections and broadcasts events to connected clients.
"""

from typing import Dict, Set, Optional
from fastapi import WebSocket, WebSocketDisconnect
from datetime import datetime
from json import dumps, loads
import structlog
import uuid

logger = structlog.get_logger(__name__)


class ConnectionManager:
    """Manages WebSocket connections"""

    def __init__(self):
        # Active connections by table session ID (for guests)
        self.table_connections: Dict[uuid.UUID, Set[WebSocket]] = {}

        # Active connections by user ID (for waiters/staff)
        self.user_connections: Dict[uuid.UUID, Set[WebSocket]] = {}

        # Active connections by station ID (for KDS screens)
        self.station_connections: Dict[uuid.UUID, Set[WebSocket]] = {}

        # WebSocket to identifier mappings (for cleanup)
        self.connection_to_table: Dict[WebSocket, uuid.UUID] = {}
        self.connection_to_user: Dict[WebSocket, uuid.UUID] = {}
        self.connection_to_station: Dict[WebSocket, uuid.UUID] = {}

    async def connect_table(self, websocket: WebSocket, table_session_id: uuid.UUID):
        """Connect a guest WebSocket for a table session"""
        await websocket.accept()

        if table_session_id not in self.table_connections:
            self.table_connections[table_session_id] = set()

        self.table_connections[table_session_id].add(websocket)
        self.connection_to_table[websocket] = table_session_id

        logger.info(f"Connected table session {table_session_id} WebSocket")
        return f"Connected to table session {table_session_id}"

    async def connect_user(self, websocket: WebSocket, user_id: uuid.UUID):
        """Connect a staff WebSocket for a user"""
        await websocket.accept()

        if user_id not in self.user_connections:
            self.user_connections[user_id] = set()

        self.user_connections[user_id].add(websocket)
        self.connection_to_user[websocket] = user_id

        logger.info(f"Connected user {user_id} WebSocket")
        return f"Connected as user {user_id}"

    async def connect_station(self, websocket: WebSocket, station_id: uuid.UUID):
        """Connect a KDS WebSocket for a station"""
        await websocket.accept()

        if station_id not in self.station_connections:
            self.station_connections[station_id] = set()

        self.station_connections[station_id].add(websocket)
        self.connection_to_station[websocket] = station_id

        logger.info(f"Connected station {station_id} WebSocket")
        return f"Connected to station {station_id}"

    def disconnect(self, websocket: WebSocket):
        """Disconnect a WebSocket connection"""
        # Check if it's a table connection
        if websocket in self.connection_to_table:
            table_session_id = self.connection_to_table[websocket]
            if table_session_id in self.table_connections:
                self.table_connections[table_session_id].discard(websocket)
                if not self.table_connections[table_session_id]:
                    del self.table_connections[table_session_id]
            del self.connection_to_table[websocket]
            logger.info(f"Disconnected table session {table_session_id} WebSocket")

        # Check if it's a user connection
        elif websocket in self.connection_to_user:
            user_id = self.connection_to_user[websocket]
            if user_id in self.user_connections:
                self.user_connections[user_id].discard(websocket)
                if not self.user_connections[user_id]:
                    del self.user_connections[user_id]
            del self.connection_to_user[websocket]
            logger.info(f"Disconnected user {user_id} WebSocket")

        # Check if it's a station connection
        elif websocket in self.connection_to_station:
            station_id = self.connection_to_station[websocket]
            if station_id in self.station_connections:
                self.station_connections[station_id].discard(websocket)
                if not self.station_connections[station_id]:
                    del self.station_connections[station_id]
            del self.connection_to_station[websocket]
            logger.info(f"Disconnected station {station_id} WebSocket")
        else:
            logger.warning(f"Attempted to disconnect unknown WebSocket")

    async def broadcast_to_table(self, table_session_id: uuid.UUID, message: dict):
        """Broadcast message to all connections for a table session"""
        if table_session_id not in self.table_connections:
            logger.debug(f"No connections for table session {table_session_id}")
            return

        connections = self.table_connections[table_session_id]
        message_json = dumps(message)

        disconnected = []
        for connection in connections:
            try:
                await connection.send_text(message_json)
            except Exception as e:
                logger.error(f"Error sending to connection: {e}")
                disconnected.append(connection)

        # Clean up dead connections
        for connection in disconnected:
            self.disconnect(connection)

        logger.debug(f"Broadcasted to {len(connections)} connections for table {table_session_id}")

    async def broadcast_to_user(self, user_id: uuid.UUID, message: dict):
        """Broadcast message to all connections for a user"""
        if user_id not in self.user_connections:
            logger.debug(f"No connections for user {user_id}")
            return

        connections = self.user_connections[user_id]
        message_json = dumps(message)

        disconnected = []
        for connection in connections:
            try:
                await connection.send_text(message_json)
            except Exception as e:
                logger.error(f"Error sending to connection: {e}")
                disconnected.append(connection)

        # Clean up dead connections
        for connection in disconnected:
            self.disconnect(connection)

        logger.debug(f"Broadcasted to {len(connections)} connections for user {user_id}")

    async def broadcast_to_station(self, station_id: uuid.UUID, message: dict):
        """Broadcast message to all connections for a station (KDS)"""
        if station_id not in self.station_connections:
            logger.debug(f"No connections for station {station_id}")
            return

        connections = self.station_connections[station_id]
        message_json = dumps(message)

        disconnected = []
        for connection in connections:
            try:
                await connection.send_text(message_json)
            except Exception as e:
                logger.error(f"Error sending to connection: {e}")
                disconnected.append(connection)

        # Clean up dead connections
        for connection in disconnected:
            self.disconnect(connection)

        logger.debug(f"Broadcasted to {len(connections)} connections for station {station_id}")

    async def send_draft_update(self, draft_id: uuid.UUID, status: str, table_session_id: uuid.UUID):
        """Send draft status update to table session"""
        async def _send():
            message = {
                "type": "draft_status_update",
                "draft_id": str(draft_id),
                "table_session_id": str(table_session_id),
                "status": status,
                "timestamp": datetime.utcnow().isoformat()
            }
            await self.broadcast_to_table(table_session_id, message)

        await _send()

    async def send_draft_locked(self, draft_id: uuid.UUID, locked_by: uuid.UUID, table_session_id: uuid.UUID):
        """Send draft locked notification to table session"""
        await self.send_draft_update(draft_id, "locked", table_session_id)

    async def send_draft_confirmed(self, draft_id: uuid.UUID, order_id: uuid.UUID, table_session_id: uuid.UUID):
        """Send draft confirmed notification to table session"""
        await self.send_draft_update(draft_id, "confirmed", table_session_id)

    async def send_draft_rejected(self, draft_id: uuid.UUID, reason: str, table_session_id: uuid.UUID):
        """Send draft rejected notification to table session"""
        await self.send_draft_update(draft_id, "rejected", table_session_id)

    async def send_ticket_created(
        self,
        ticket_id: uuid.UUID,
        station_id: uuid.UUID,
        table_session_id: uuid.UUID,
        course_number: int,
        course_name: str
    ):
        """Send ticket created event to station"""
        await self.broadcast_to_station(station_id, {
            "type": "ticket_created",
            "ticket_id": str(ticket_id),
            "table_session_id": str(table_session_id),
            "station_id": str(station_id),
            "course_number": course_number,
            "course_name": course_name,
            "timestamp": datetime.utcnow().isoformat()
        })

    async def send_ticket_updated(
        self,
        ticket_id: uuid.UUID,
        station_id: uuid.UUID,
        status: str,
        previous_status: Optional[str] = None
    ):
        """Send ticket updated event to station"""
        await self.broadcast_to_station(station_id, {
            "type": "ticket_updated",
            "ticket_id": str(ticket_id),
            "station_id": str(station_id),
            "status": status,
            "previous_status": previous_status,
            "timestamp": datetime.utcnow().isoformat()
        })

    async def send_ticket_bumped(self, ticket_id: uuid.UUID, station_id: uuid.UUID):
        """Send ticket bumped event to station"""
        await self.broadcast_to_station(station_id, {
            "type": "ticket_bumped",
            "ticket_id": str(ticket_id),
            "station_id": str(station_id),
            "timestamp": datetime.utcnow().isoformat()
        })

    async def send_ticket_held(self, ticket_id: uuid.UUID, station_id: uuid.UUID, held_by: uuid.UUID, reason: str):
        """Send ticket held event to station"""
        await self.broadcast_to_station(station_id, {
            "type": "ticket_held",
            "ticket_id": str(ticket_id),
            "station_id": str(station_id),
            "held_by": str(held_by),
            "reason": reason,
            "timestamp": datetime.utcnow().isoformat()
        })

    async def send_ticket_fired(self, ticket_id: uuid.UUID, station_id: uuid.UUID, fired_by: uuid.UUID):
        """Send ticket fired event to station"""
        await self.broadcast_to_station(station_id, {
            "type": "ticket_fired",
            "ticket_id": str(ticket_id),
            "station_id": str(station_id),
            "fired_by": str(fired_by),
            "timestamp": datetime.utcnow().isoformat()
        })

    async def send_ticket_voided(self, ticket_id: uuid.UUID, station_id: uuid.UUID, voided_by: uuid.UUID, reason: str):
        """Send ticket voided event to station"""
        await self.broadcast_to_station(station_id, {
            "type": "ticket_voided",
            "ticket_id": str(ticket_id),
            "station_id": str(station_id),
            "voided_by": str(voided_by),
            "reason": reason,
            "timestamp": datetime.utcnow().isoformat()
        })

    # Order event methods
    async def send_order_created(
        self,
        order_id: uuid.UUID,
        draft_order_id: uuid.UUID,
        table_session_id: uuid.UUID,
        total_amount: float
    ):
        """Send order created event to table session"""
        await self.broadcast_to_table(table_session_id, {
            "type": "order_created",
            "order_id": str(order_id),
            "draft_order_id": str(draft_order_id),
            "total_amount": total_amount,
            "timestamp": datetime.utcnow().isoformat()
        })

    async def send_order_updated(
        self,
        order_id: uuid.UUID,
        table_session_id: uuid.UUID,
        status: str,
        previous_status: Optional[str] = None
    ):
        """Send order updated event to table session"""
        await self.broadcast_to_table(table_session_id, {
            "type": "order_updated",
            "order_id": str(order_id),
            "status": status,
            "previous_status": previous_status,
            "timestamp": datetime.utcnow().isoformat()
        })

    async def send_order_completed(
        self,
        order_id: uuid.UUID,
        table_session_id: uuid.UUID,
        total_amount: float
    ):
        """Send order completed event to table session"""
        await self.broadcast_to_table(table_session_id, {
            "type": "order_completed",
            "order_id": str(order_id),
            "total_amount": total_amount,
            "timestamp": datetime.utcnow().isoformat()
        })

    async def send_order_cancelled(
        self,
        order_id: uuid.UUID,
        table_session_id: uuid.UUID,
        reason: str
    ):
        """Send order cancelled event to table session"""
        await self.broadcast_to_table(table_session_id, {
            "type": "order_cancelled",
            "order_id": str(order_id),
            "reason": reason,
            "timestamp": datetime.utcnow().isoformat()
        })

    # Payment event methods
    async def send_payment_created(
        self,
        payment_id: uuid.UUID,
        order_id: uuid.UUID,
        table_session_id: uuid.UUID,
        amount: float,
        method: str
    ):
        """Send payment created event to table session"""
        await self.broadcast_to_table(table_session_id, {
            "type": "payment_created",
            "payment_id": str(payment_id),
            "order_id": str(order_id),
            "amount": amount,
            "method": method,
            "timestamp": datetime.utcnow().isoformat()
        })

    async def send_payment_completed(
        self,
        payment_id: uuid.UUID,
        order_id: uuid.UUID,
        table_session_id: uuid.UUID,
        amount: float,
        method: str
    ):
        """Send payment completed event to table session"""
        await self.broadcast_to_table(table_session_id, {
            "type": "payment_completed",
            "payment_id": str(payment_id),
            "order_id": str(order_id),
            "amount": amount,
            "method": method,
            "timestamp": datetime.utcnow().isoformat()
        })

    async def send_payment_failed(
        self,
        payment_id: uuid.UUID,
        order_id: uuid.UUID,
        table_session_id: uuid.UUID,
        amount: float,
        method: str,
        reason: str
    ):
        """Send payment failed event to table session"""
        await self.broadcast_to_table(table_session_id, {
            "type": "payment_failed",
            "payment_id": str(payment_id),
            "order_id": str(order_id),
            "amount": amount,
            "method": method,
            "reason": reason,
            "timestamp": datetime.utcnow().isoformat()
        })

    async def send_refund_created(
        self,
        refund_id: uuid.UUID,
        payment_id: uuid.UUID,
        order_id: uuid.UUID,
        table_session_id: uuid.UUID,
        amount: float,
        reason: str
    ):
        """Send refund created event to table session"""
        await self.broadcast_to_table(table_session_id, {
            "type": "refund_created",
            "refund_id": str(refund_id),
            "payment_id": str(payment_id),
            "order_id": str(order_id),
            "amount": amount,
            "reason": reason,
            "timestamp": datetime.utcnow().isoformat()
        })

    # Shift event methods
    async def send_shift_opened(
        self,
        shift_id: uuid.UUID,
        server_id: uuid.UUID,
        location_id: uuid.UUID,
        opening_balance: float
    ):
        """Send shift opened event to server"""
        await self.broadcast_to_user(server_id, {
            "type": "shift_opened",
            "shift_id": str(shift_id),
            "location_id": str(location_id),
            "opening_balance": opening_balance,
            "timestamp": datetime.utcnow().isoformat()
        })

    async def send_shift_closed(
        self,
        shift_id: uuid.UUID,
        server_id: uuid.UUID,
        cash_sales: float,
        card_sales: float
    ):
        """Send shift closed event to server"""
        await self.broadcast_to_user(server_id, {
            "type": "shift_closed",
            "shift_id": str(shift_id),
            "cash_sales": cash_sales,
            "card_sales": card_sales,
            "timestamp": datetime.utcnow().isoformat()
        })

    async def send_shift_reconciled(
        self,
        shift_id: uuid.UUID,
        server_id: uuid.UUID,
        expected_cash: float,
        actual_cash: float,
        variance: float
    ):
        """Send shift reconciled event to server"""
        await self.broadcast_to_user(server_id, {
            "type": "shift_reconciled",
            "shift_id": str(shift_id),
            "expected_cash": expected_cash,
            "actual_cash": actual_cash,
            "variance": variance,
            "timestamp": datetime.utcnow().isoformat()
        })

    def get_connection_count(self) -> dict:
        """Get count of active connections"""
        return {
            "table_connections": sum(len(conns) for conns in self.table_connections.values()),
            "user_connections": sum(len(conns) for conns in self.user_connections.values()),
            "station_connections": sum(len(conns) for conns in self.station_connections.values()),
        }


# Global connection manager instance
manager = ConnectionManager()
