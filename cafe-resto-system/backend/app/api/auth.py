"""
Auth API endpoints - Login and token management
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session
from datetime import datetime, timedelta
import structlog
from jose import JWTError, jwt

from app.core.database import get_session
from app.core.config import get_settings

logger = structlog.get_logger(__name__)
router = APIRouter()
settings = get_settings()


@router.post("/login")
async def login():
    """Login endpoint - TODO: implement with user model"""
    # Placeholder - will be implemented when User model is created
    return {"message": "Login endpoint - TODO"}


@router.post("/token")
async def create_access_token():
    """Create JWT access token - TODO: implement with user credentials"""
    # Placeholder - will be implemented when User model is created
    return {"message": "Token endpoint - TODO"}
