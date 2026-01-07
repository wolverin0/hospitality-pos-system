"""
Tenant API endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from typing import List
from datetime import datetime
import structlog
import uuid

from app.core.database import get_session
from app.models.tenant import Tenant

logger = structlog.get_logger(__name__)
router = APIRouter()


@router.post("/", response_model=Tenant, status_code=status.HTTP_201_CREATED)
async def create_tenant(
    tenant: Tenant,
    session: Session = Depends(get_session)
):
    """Create a new tenant"""
    try:
        session.add(tenant)
        session.commit()
        session.refresh(tenant)
        logger.info(f"Tenant created: {tenant.id}")
        return tenant
    except Exception as e:
        session.rollback()
        logger.error(f"Failed to create tenant: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to create tenant"
        )


@router.get("/{tenant_id}", response_model=Tenant)
async def get_tenant(
    tenant_id: uuid.UUID,
    session: Session = Depends(get_session)
):
    """Get tenant by ID"""
    tenant = session.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found"
        )
    return tenant


@router.get("/", response_model=List[Tenant])
async def list_tenants(
    skip: int = 0,
    limit: int = 100,
    session: Session = Depends(get_session)
):
    """List all tenants (admin only in production)"""
    tenants = session.exec(select(Tenant).offset(skip).limit(limit)).all()
    return tenants


@router.put("/{tenant_id}", response_model=Tenant)
async def update_tenant(
    tenant_id: uuid.UUID,
    tenant_update: Tenant,
    session: Session = Depends(get_session)
):
    """Update tenant"""
    db_tenant = session.get(Tenant, tenant_id)
    if not db_tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found"
        )
    
    tenant_data = tenant_update.model_dump(exclude_unset=True)
    for key, value in tenant_data.items():
        setattr(db_tenant, key, value)
    
    db_tenant.updated_at = datetime.utcnow()
    session.add(db_tenant)
    session.commit()
    session.refresh(db_tenant)
    logger.info(f"Tenant updated: {tenant_id}")
    return db_tenant
