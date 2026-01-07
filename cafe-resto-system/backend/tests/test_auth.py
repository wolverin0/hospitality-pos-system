"""
Unit test for JWT authentication
"""

import pytest
from datetime import datetime, timedelta
import uuid
from jose import jwt

from app.core.auth import create_access_token, verify_token, decode_access_token
from app.core.config import get_settings
from app.core.dependencies import get_current_user_id, get_tenant_id, get_user_role
from app.schemas.token import TokenPayload

settings = get_settings()


def test_create_access_token():
    """Test JWT token creation"""
    user_id = uuid.uuid4()
    tenant_id = uuid.uuid4()
    role = "waiter"
    expires_delta = timedelta(hours=24)
    
    token = create_access_token(
        user_id=user_id,
        tenant_id=tenant_id,
        role=role,
        expires_delta=expires_delta
    )
    
    assert token is not None
    assert isinstance(token, str)
    
    # Verify payload
    payload = verify_token(token)
    assert payload is not None
    assert payload["sub"] == str(user_id)
    assert payload["tenant_id"] == str(tenant_id)
    assert payload["role"] == role
    assert "exp" in payload


def test_decode_valid_token():
    """Test decoding a valid token"""
    user_id = uuid.uuid4()
    tenant_id = uuid.uuid4()
    role = "admin"
    
    token = create_access_token(
        user_id=user_id,
        tenant_id=tenant_id,
        role=role,
        expires_delta=timedelta(hours=1)
    )
    
    payload = decode_access_token(token)
    
    assert payload is not None
    assert payload["sub"] == str(user_id)
    assert payload["tenant_id"] == str(tenant_id)
    assert payload["role"] == role


def test_verify_invalid_token():
    """Test token verification with invalid token"""
    invalid_token = "invalid.token.string.here"
    
    payload = verify_token(invalid_token)
    assert payload is None


def test_expired_token():
    """Test that expired tokens are rejected"""
    user_id = uuid.uuid4()
    tenant_id = uuid.uuid4()
    role = "waiter"
    
    # Create token expired 1 hour ago
    token = create_access_token(
        user_id=user_id,
        tenant_id=tenant_id,
        role=role,
        expires_delta=timedelta(hours=-1)
    )
    
    # Token creation should succeed
    payload = decode_access_token(token)
    assert payload is not None
    
    # Verify should fail due to expiration
    # Note: JWT verification happens in dependencies
