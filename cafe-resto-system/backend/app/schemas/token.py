"""
Pydantic schemas for authentication and tokens
"""

from pydantic import BaseModel, Field, EmailStr
from typing import Optional
from datetime import datetime
import uuid


class TokenPayload(BaseModel):
    """JWT token payload"""
    sub: str = Field(..., description="User ID")
    tenant_id: str = Field(..., description="Tenant ID")
    role: str = Field(..., description="User role")
    exp: datetime = Field(..., description="Expiration time")
    iat: datetime = Field(default_factory=datetime.utcnow, description="Issued at")


class TokenResponse(BaseModel):
    """Token response"""
    access_token: str
    token_type: str = "bearer"
    user_id: str
    role: str
