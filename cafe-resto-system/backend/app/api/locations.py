"""
Locations API endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from typing import List, Optional
from datetime import datetime
import structlog
import uuid

from app.core.database import get_session
from app.core.dependencies import get_tenant_id, get_current_user_id
from app.models.location import Location
from app.models.table import Table
from app.models.floor import Floor

logger = structlog.get_logger(__name__)
router = APIRouter()


@router.post("/", response_model=Location)
async def create_location(
    location_data: dict,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    current_user_id: uuid.UUID = Depends(get_current_user_id),
    session: Session = Depends(get_session)
):
    """Create a new location"""
    new_location = Location(
        tenant_id=tenant_id,
        name=location_data.get("name"),
        address=location_data.get("address"),
        phone=location_data.get("phone"),
        email=location_data.get("email"),
        timezone=location_data.get("timezone"),
        currency=location_data.get("currency"),
        is_active=True,
    )
    
    session.add(new_location)
    session.commit()
    session.refresh(new_location)
    
    logger.info(f"Location created: {new_location.id}")
    return new_location


@router.get("/{location_id}", response_model=Location)
async def get_location(
    location_id: uuid.UUID,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    current_user_id: uuid.UUID = Depends(get_current_user_id),
    session: Session = Depends(get_session)
):
    """Get location by ID"""
    location = session.get(Location, location_id)
    if not location:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Location not found"
        )
    
    # Verify tenant access
    if location.tenant_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this location"
        )
    
    return location


@router.get("/", response_model=List[Location])
async def list_locations(
    skip: int = 0,
    limit: int = 100,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    current_user_id: uuid.UUID = Depends(get_current_user_id),
    session: Session = Depends(get_session)
):
    """List all locations for tenant"""
    locations = session.exec(
        select(Location)
        .where(Location.tenant_id == tenant_id)
        .offset(skip)
        .limit(limit)
    ).all()
    return locations


@router.put("/{location_id}", response_model=Location)
async def update_location(
    location_id: uuid.UUID,
    location_data: dict,
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    current_user_id: uuid.UUID = Depends(get_current_user_id),
    session: Session = Depends(get_session)
):
    """Update location"""
    location = session.get(Location, location_id)
    if not location:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Location not found"
        )
    
    # Verify tenant access
    if location.tenant_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this location"
        )
    
    for key, value in location_data.items():
        if hasattr(location, key):
            setattr(location, key, value)
    
    location.updated_at = datetime.utcnow()
    session.add(location)
    session.commit()
    session.refresh(location)
    
    logger.info(f"Location updated: {location_id}")
    return location
