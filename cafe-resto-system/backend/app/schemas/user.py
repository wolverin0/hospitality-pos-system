"""
Pydantic schemas for users
"""

from pydantic import BaseModel, Field, EmailStr
from typing import Optional
from datetime import datetime
import uuid

from app.models.user import UserRole


class UserCreate(BaseModel):
    """User registration schema"""
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=100)
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    tenant_slug: str = Field(..., min_length=3, max_length=100)
    role: UserRole = Field(default=UserRole.WAITER)


class UserLogin(BaseModel):
    """User login schema"""
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=100)


class UserResponse(BaseModel):
    """User response model"""
    id: uuid.UUID
    email: str
    first_name: str
    last_name: str
    role: UserRole
    tenant_id: uuid.UUID
    is_active: bool
    email_verified: bool
    created_at: datetime
    last_login_at: Optional[datetime]
