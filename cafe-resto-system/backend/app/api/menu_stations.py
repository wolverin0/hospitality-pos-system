"""
Menu stations API endpoints for KDS station management
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlmodel import Session, select, SQLModel
from typing import List, Optional
import structlog
import uuid

from app.core.database import get_session
from app.core.dependencies import get_tenant_id
from app.models.menu_station import MenuStation, StationType

logger = structlog.get_logger(__name__)
router = APIRouter()


class MenuStationResponse(SQLModel):
    """Schema for menu station response"""
    id: uuid.UUID
    tenant_id: uuid.UUID
    location_id: uuid.UUID
    name: str
    station_type: StationType
    display_order: int
    color: Optional[str] = None
    icon: Optional[str] = None
    is_active: bool = True
    is_visible_in_kds: bool = True
    requires_expo_approval: bool = False
    created_at: Optional[str] = None


@router.get("/", response_model=List[MenuStationResponse])
async def list_stations(
    location_id: Optional[uuid.UUID] = Query(None, description="Filter by location"),
    station_type: Optional[StationType] = Query(None, description="Filter by station type"),
    active_only: Optional[bool] = Query(True, description="Only return active stations"),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session: Session = Depends(get_session)
):
    """List menu stations for KDS filtering"""
    try:
        query = select(MenuStation).where(MenuStation.tenant_id == tenant_id)

        if location_id:
            query = query.where(MenuStation.location_id == location_id)

        if station_type:
            query = query.where(MenuStation.station_type == station_type)

        if active_only:
            query = query.where(MenuStation.is_active == True)

        # Sort by display_order
        query = query.order_by(MenuStation.display_order.asc(), MenuStation.name.asc())

        stations = session.exec(query).all()
        return stations

    except Exception as e:
        logger.error(f"Error listing stations: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list stations"
        )


@router.get("/{station_id}", response_model=MenuStationResponse)
async def get_station(
    station_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    session: Session = Depends(get_session)
):
    """Get station details"""
    try:
        station = session.exec(
            select(MenuStation).where(
                MenuStation.id == station_id,
                MenuStation.tenant_id == tenant_id
            )
        ).first()

        if not station:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Station not found"
            )

        return station

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting station: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get station"
        )
