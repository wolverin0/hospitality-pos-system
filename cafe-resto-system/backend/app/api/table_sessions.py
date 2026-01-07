"""
Table sessions API endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlmodel import Session, select, SQLModel
from typing import List, Optional
from datetime import datetime
from decimal import Decimal
import structlog
import uuid

from app.core.database import get_session
from app.core.dependencies import get_tenant_id, get_current_user_id
from app.models.table_session import TableSession, TableSessionStatus
from app.models.table import Table

logger = structlog.get_logger(__name__)
router = APIRouter()


# Pydantic schemas
class TableSessionCreate(SQLModel):
    """Schema for creating a table session (guest scans QR)"""
    table_id: uuid.UUID
    guest_count: int = 1
    notes: Optional[str] = None


class TableSessionResponse(SQLModel):
    """Schema for table session response"""
    id: uuid.UUID
    table_id: uuid.UUID
    tenant_id: uuid.UUID
    location_id: uuid.UUID
    floor_id: Optional[uuid.UUID] = None
    status: str
    guest_count: int
    notes: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None


@router.post("/", response_model=TableSessionResponse)
async def create_table_session(
    session_data: TableSessionCreate,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    current_user_id: uuid.UUID = Depends(get_current_user_id),
    session: Session = Depends(get_session)
):
    """Create a new table session (guest scans QR code)"""
    try:
        # Get table and verify it belongs to tenant
        table = session.exec(
            select(Table).where(
                Table.id == session_data.table_id,
                Table.tenant_id == tenant_id
            )
        ).first()

        if not table:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Table not found"
            )

        # Check if table already has an active session
        active_session = session.exec(
            select(TableSession).where(
                TableSession.table_id == session_data.table_id,
                TableSession.status == TableSessionStatus.ACTIVE,
                TableSession.tenant_id == tenant_id
            )
        ).first()

        if active_session:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Table already has an active session"
            )

        # Create table session
        table_session = TableSession(
            tenant_id=tenant_id,
            location_id=table.location_id,
            table_id=session_data.table_id,
            floor_id=table.floor_id,
            status=TableSessionStatus.ACTIVE,
            guest_count=session_data.guest_count,
            notes=session_data.notes
        )
        session.add(table_session)
        session.commit()
        session.refresh(table_session)

        logger.info(f"Created table session {table_session.id} for table {session_data.table_id}")
        return table_session

    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"Error creating table session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create table session"
        )


@router.get("/", response_model=List[TableSessionResponse])
async def list_table_sessions(
    status_filter: Optional[str] = Query(None, description="Filter by status"),
    table_id: Optional[uuid.UUID] = Query(None, description="Filter by table"),
    location_id: Optional[uuid.UUID] = Query(None, description="Filter by location"),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    current_user_id: uuid.UUID = Depends(get_current_user_id),
    session: Session = Depends(get_session)
):
    """List table sessions"""
    try:
        query = select(TableSession).where(TableSession.tenant_id == tenant_id)

        # Apply filters
        if status_filter:
            query = query.where(TableSession.status == status_filter)

        if table_id:
            query = query.where(TableSession.table_id == table_id)

        if location_id:
            query = query.where(TableSession.location_id == location_id)

        # Sort by created_at (newest first)
        query = query.order_by(TableSession.created_at.desc())

        sessions = session.exec(query).all()
        return sessions

    except Exception as e:
        logger.error(f"Error listing table sessions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list table sessions"
        )


@router.get("/{session_id}", response_model=TableSessionResponse)
async def get_table_session(
    session_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    current_user_id: uuid.UUID = Depends(get_current_user_id),
    session: Session = Depends(get_session)
):
    """Get table session details"""
    try:
        session_obj = session.exec(
            select(TableSession).where(
                TableSession.id == session_id,
                TableSession.tenant_id == tenant_id
            )
        ).first()

        if not session_obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Table session not found"
            )

        return session_obj

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting table session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get table session"
        )


@router.patch("/{session_id}", response_model=TableSessionResponse)
async def update_table_session(
    session_id: uuid.UUID,
    status: Optional[str] = None,
    notes: Optional[str] = None,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    current_user_id: uuid.UUID = Depends(get_current_user_id),
    session: Session = Depends(get_session)
):
    """Update table session status or notes"""
    try:
        session_obj = session.exec(
            select(TableSession).where(
                TableSession.id == session_id,
                TableSession.tenant_id == tenant_id
            )
        ).first()

        if not session_obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Table session not found"
            )

        # Update fields if provided
        if status:
            session_obj.status = status
        if notes is not None:
            session_obj.notes = notes
        session_obj.updated_at = datetime.utcnow()

        session.commit()
        session.refresh(session_obj)

        logger.info(f"Updated table session {session_id}")
        return session_obj

    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"Error updating table session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update table session"
        )
