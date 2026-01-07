"""
Authentication dependencies for FastAPI
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
import uuid
import structlog

from app.core.auth import create_access_token, verify_token
from app.core.config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()
security = HTTPBearer()


async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> uuid.UUID:
    """Get current user ID from JWT token"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    user_id = verify_token(credentials.credentials)
    if user_id is None:
        raise credentials_exception
    
    logger.debug(f"User authenticated: {user_id}")
    return user_id


async def get_tenant_id(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> uuid.UUID:
    """Get tenant ID from JWT token"""
    payload = verify_token(credentials.credentials)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )
    
    tenant_id = uuid.UUID(payload.get("tenant_id"))
    return tenant_id


async def get_user_role(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> str:
    """Get user role from JWT token"""
    payload = verify_token(credentials.credentials)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )
    
    role = payload.get("role")
    return role
