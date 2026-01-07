"""
Tables API endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from typing import List, Optional
from datetime import datetime
import structlog
import uuid

from app.core.database import get_session
from app.core.dependencies import get_tenant_id, get_current_user_id
from app.models.table import Table
from app.models.floor import Floor

logger = structlog.get_logger(__name__)
router = APIRouter()


@router.post("/", response_model=Table)
async def create_table(
    table_data: dict,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    current_user_id: uuid.UUID = Depends(get_current_user_id),
    session: Session = Depends(get_session)
):
    """Create a new table"""
    # Get location_id from table_data
    location_id = table_data.get("location_id")
    if not location_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Location ID is required"
        )
    
    new_table = Table(
        tenant_id=tenant_id,
        location_id=uuid.UUID(location_id),
        floor_id=table_data.get("floor_id"),
        number=table_data.get("number"),
        seats=table_data.get("seats", 2),
        position_x=table_data.get("position_x"),
        position_y=table_data.get("position_y"),
        section_id=table_data.get("section_id"),
        is_active=True,
    )
    
    session.add(new_table)
    session.commit()
    session.refresh(new_table)
    
    logger.info(f"Table created: {new_table.id}")
    return new_table


@router.get("/{table_id}", response_model=Table)
async def get_table(
    table_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    current_user_id: uuid.UUID = Depends(get_current_user_id),
    session: Session = Depends(get_session)
):
    """Get table by ID"""
    table = session.get(Table, table_id)
    if not table:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Table not found"
        )
    
    # Verify tenant access
    if table.tenant_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this table"
        )
    
    return table


@router.get("/", response_model=List[Table])
async def list_tables(
    skip: int = 0,
    limit: int = 100,
    location_id: Optional[uuid.UUID] = None,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    current_user_id: uuid.UUID = Depends(get_current_user_id),
    session: Session = Depends(get_session)
):
    """List all tables for tenant or location"""
    query = select(Table).where(Table.tenant_id == tenant_id)
    
    if location_id:
        query = query.where(Table.location_id == location_id)
    
    tables = query.offset(skip).limit(limit).all()
    return tables


@router.put("/{table_id}", response_model=Table)
async def update_table(
    table_id: uuid.UUID,
    table_data: dict,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    current_user_id: uuid.UUID = Depends(get_current_user_id),
    session: Session = Depends(get_session)
):
    """Update table"""
    table = session.get(Table, table_id)
    if not table:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Table not found"
        )
    
    # Verify tenant access
    if table.tenant_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this table"
        )
    
    for key, value in table_data.items():
        if hasattr(table, key):
            setattr(table, key, value)
    
    table.updated_at = datetime.utcnow()
    session.add(table)
    session.commit()
    session.refresh(table)
    
    logger.info(f"Table updated: {table_id}")
    return table


@router.get("/{location_id}/tables", response_model=List[Table])
async def list_tables_by_location(
    location_id: uuid.UUID,
    skip: int = 0,
    limit: int = 100,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    current_user_id: uuid.UUID = Depends(get_current_user_id),
    session: Session = Depends(get_session)
):
    """List all tables for a location"""
    tables = session.exec(
        select(Table)
        .where(Table.tenant_id == tenant_id, Table.location_id == location_id)
        .offset(skip)
        .limit(limit)
    ).all()
    return tables


@router.get("/{location_id}/floors", response_model=List[Floor])
async def list_floors(
    location_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    current_user_id: uuid.UUID = Depends(get_current_user_id),
    session: Session = Depends(get_session)
):
    """List all floors for a location"""
    floors = session.exec(
        select(Floor).where(Floor.tenant_id == tenant_id, Floor.location_id == location_id)
    ).all()
    return floors
