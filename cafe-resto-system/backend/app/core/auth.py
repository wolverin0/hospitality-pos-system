"""
JWT Authentication utilities
"""

from datetime import datetime, timedelta
from jose import JWTError, jwt
from typing import Dict, Optional
import uuid
from app.core.config import get_settings

settings = get_settings()


def create_access_token(
    user_id: uuid.UUID,
    tenant_id: uuid.UUID,
    role: str,
    expires_delta: Optional[timedelta] = None
) -> str:
    """Create JWT access token with user claims"""
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode = {
        "sub": str(user_id),
        "tenant_id": str(tenant_id),
        "role": role,
        "exp": expire,
        "iat": datetime.utcnow(),
    }
    
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> Optional[Dict]:
    """Decode and validate JWT token"""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except JWTError:
        return None


def verify_token(token: str) -> Optional[uuid.UUID]:
    """Verify token and return user_id if valid"""
    payload = decode_access_token(token)
    if payload is None:
        return None
    
    user_id: uuid.UUID = uuid.UUID(payload.get("sub"))
    return user_id
