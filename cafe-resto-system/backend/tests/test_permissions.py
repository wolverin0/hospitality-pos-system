"""
Unit tests for RBAC permission system
"""

import pytest
from app.core.permissions import (
    Permission,
    get_permissions_for_role,
    has_permission,
    require_permission
)
from app.core.config import get_settings

settings = get_settings()


def test_get_permissions_for_role():
    """Test permission retrieval for all roles"""
    # Admin has all permissions
    admin_perms = get_permissions_for_role("admin")
    assert Permission.DRAFT_VIEW in admin_perms
    assert Permission.PAYMENT_REFUND in admin_perms
    
    # Manager has most permissions except refund
    manager_perms = get_permissions_for_role("manager")
    assert Permission.DRAFT_VIEW in manager_perms
    assert Permission.DRAFT_CONFIRM in manager_perms
    assert Permission.PAYMENT_REFUND not in manager_perms
    
    # Waiter has limited permissions
    waiter_perms = get_permissions_for_role("waiter")
    assert Permission.DRAFT_VIEW in waiter_perms
    assert Permission.DRAFT_CONFIRM in waiter_perms
    assert Permission.ORDER_VOID_ITEM in waiter_perms
    assert Permission.PAYMENT_RECORD_CASH not in waiter_perms


def test_has_permission():
    """Test permission checking logic"""
    # Create permission set for admin
    admin_perms = get_permissions_for_role("admin")
    
    # Admin should have all permissions
    assert has_permission(Permission.DRAFT_VIEW, admin_perms)
    assert has_permission(Permission.PAYMENT_REFUND, admin_perms)
    
    # Create permission set for waiter
    waiter_perms = get_permissions_for_role("waiter")
    
    # Waiter should not have manager permissions
    assert not has_permission(Permission.PAYMENT_REFUND, waiter_perms)


def test_require_permission_decorator():
    """Test permission requirement decorator"""
    # Test that require_permission creates a callable
    checker = require_permission(Permission.DRAFT_VIEW)
    assert callable(checker)
    
    # Test with different permissions
    admin_checker = require_permission(Permission.PAYMENT_REFUND)
    assert callable(admin_checker)
