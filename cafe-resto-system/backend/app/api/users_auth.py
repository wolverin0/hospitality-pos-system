"""
User authentication API endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from datetime import datetime
from pydantic import EmailStr, BaseModel
import structlog
from passlib.context import CryptContext
import uuid

from app.core.database import get_session
from app.core.dependencies import get_current_user_id, get_tenant_id, get_user_role
from app.core.auth import create_access_token
from app.core.config import get_settings
from app.models.user import User, UserRole
from app.schemas.token import TokenPayload
from app.schemas.user import UserCreate, UserLogin, UserResponse

logger = structlog.get_logger(__name__)
router = APIRouter()
settings = get_settings()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class UserLoginSchema(BaseModel):
    """User login schema"""
    email: EmailStr
    password: str
    tenant_slug: str  # For multi-tenant login


@router.post("/register")
async def register_user(
    user_data: UserCreate,
    session: Session = Depends(get_session)
):
    """Register a new user"""
    # Check if user already exists in tenant
    existing_user = session.exec(
        select(User).where(User.email == user_data.email)
    ).first()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Hash password
    password_hash = pwd_context.hash(user_data.password)
    
    # Create user
    new_user = User(
        email=user_data.email,
        password_hash=password_hash,
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        role=user_data.role,
        tenant_id=uuid.UUID("00000000-0000-0000-000000000000"),  # TODO: Resolve from tenant_slug
        is_active=True,
        email_verified=False,
    )
    
    session.add(new_user)
    session.commit()
    session.refresh(new_user)
    
    logger.info(f"User registered: {new_user.id}")
    
    # Create access token
    access_token = create_access_token(
        user_id=new_user.id,
        tenant_id=new_user.tenant_id,
        role=new_user.role.value,
    )
    
    return UserResponse(
        id=new_user.id,
        email=new_user.email,
        first_name=new_user.first_name,
        last_name=new_user.last_name,
        role=new_user.role,
        tenant_id=new_user.tenant_id,
        is_active=new_user.is_active,
        email_verified=new_user.email_verified,
        created_at=new_user.created_at,
        last_login_at=new_user.last_login_at,
    )


@router.post("/login")
async def login_user(
    login_data: UserLogin,
    session: Session = Depends(get_session)
):
    """Login user"""
    # Find user by email
    user = session.exec(
        select(User).where(User.email == login_data.email)
    ).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    # Verify password
    if not pwd_context.verify(login_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )
    
    # Update last login
    user.last_login_at = datetime.utcnow()
    session.add(user)
    session.commit()
    
    logger.info(f"User logged in: {user.id}")
    
    # Create access token
    access_token = create_access_token(
        user_id=user.id,
        tenant_id=user.tenant_id,
        role=user.role.value,
    )
    
    return UserResponse(
        id=user.id,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        role=user.role,
        tenant_id=user.tenant_id,
        is_active=user.is_active,
        email_verified=user.email_verified,
        created_at=user.created_at,
        last_login_at=user.last_login_at,
    )


@router.get("/me")
async def get_current_user_info(
    user_id: uuid.UUID = Depends(get_current_user_id),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    role: str = Depends(get_user_role),
    session: Session = Depends(get_session)
):
    """Get current user info"""
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return UserResponse(
        id=user.id,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        role=user.role,
        tenant_id=user.tenant_id,
        is_active=user.is_active,
        email_verified=user.email_verified,
        created_at=user.created_at,
        last_login_at=user.last_login_at,
    )


@router.post("/login")
async def login_user(
    login_data: UserLoginSchema,
    session: Session = Depends(get_session)
):
    """Login user"""
    # Find user by email
    user = session.exec(
        select(User).where(User.email == login_data.email)
    ).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    # Verify password
    if not pwd_context.verify(login_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )
    
    # Update last login
    user.last_login_at = datetime.utcnow()
    session.add(user)
    session.commit()
    
    logger.info(f"User logged in: {user.id}")
    
    # Create access token
    access_token = create_access_token(
        user_id=user.id,
        tenant_id=user.tenant_id,
        role=user.role.value,
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_id": str(user.id),
        "role": user.role.value,
    }


@router.get("/me")
async def get_current_user_info(
    user_id: uuid.UUID = Depends(get_current_user_id),
    tenant_id: uuid.UUID = Depends(get_tenant_id),
    role: str = Depends(get_user_role),
    session: Session = Depends(get_session)
):
    """Get current user info"""
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return {
        "id": str(user.id),
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "role": role,
        "tenant_id": str(user.tenant_id),
        "is_active": user.is_active,
    }
