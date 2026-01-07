"""
RBAC (Role-Based Access Control) permission system
"""

from enum import Enum
from typing import List, Set
from fastapi import HTTPException, status


class Permission(str, Enum):
    """Permission definitions"""
    # Draft permissions
    DRAFT_VIEW = "draft:view"
    DRAFT_CONFIRM = "draft:confirm"
    DRAFT_REJECT = "draft:reject"
    DRAFT_REASSIGN_TABLE = "draft:reassign_table"
    
    # Order permissions
    ORDER_CREATE = "order:create"
    ORDER_FIRE_COURSE = "order:fire_course"
    ORDER_VOID_ITEM = "order:void_item"
    ORDER_DISCOUNT = "order:discount"
    
    # Payment permissions
    PAYMENT_RECORD_CASH = "payment:record_cash"
    PAYMENT_RECORD_EXTERNAL = "payment:record_external"
    PAYMENT_REFUND = "payment:refund"
    
    # Menu permissions
    MENU_EDIT = "menu:edit"
    PRICING_EDIT = "pricing:edit"
    
    # Table permissions
    TABLES_EDIT = "tables:edit"
    
    # Report permissions
    REPORTS_VIEW_SENSITIVE = "reports:view_sensitive"


# Role permission mapping
ROLE_PERMISSIONS = {
    "admin": {
        # Admins have all permissions
        Permission.DRAFT_VIEW,
        Permission.DRAFT_CONFIRM,
        Permission.DRAFT_REJECT,
        Permission.DRAFT_REASSIGN_TABLE,
        Permission.ORDER_CREATE,
        Permission.ORDER_FIRE_COURSE,
        Permission.ORDER_VOID_ITEM,
        Permission.ORDER_DISCOUNT,
        Permission.PAYMENT_RECORD_CASH,
        Permission.PAYMENT_RECORD_EXTERNAL,
        Permission.PAYMENT_REFUND,
        Permission.MENU_EDIT,
        Permission.PRICING_EDIT,
        Permission.TABLES_EDIT,
        Permission.REPORTS_VIEW_SENSITIVE,
    },
    "manager": {
        # Managers have most permissions except refund
        Permission.DRAFT_VIEW,
        Permission.DRAFT_CONFIRM,
        Permission.DRAFT_REJECT,
        Permission.DRAFT_REASSIGN_TABLE,
        Permission.ORDER_CREATE,
        Permission.ORDER_FIRE_COURSE,
        Permission.ORDER_VOID_ITEM,
        Permission.ORDER_DISCOUNT,
        Permission.PAYMENT_RECORD_CASH,
        Permission.PAYMENT_RECORD_EXTERNAL,
        Permission.MENU_EDIT,
        Permission.TABLES_EDIT,
        Permission.REPORTS_VIEW_SENSITIVE,
    },
    "waiter": {
        # Waiters can view drafts, confirm, but not reject
        Permission.DRAFT_VIEW,
        Permission.DRAFT_CONFIRM,
        Permission.ORDER_FIRE_COURSE,
        Permission.ORDER_VOID_ITEM,
        Permission.ORDER_DISCOUNT,
    },
    "cashier": {
        # Cashiers can record payments but limited order control
        Permission.ORDER_CREATE,
        Permission.PAYMENT_RECORD_CASH,
        Permission.PAYMENT_RECORD_EXTERNAL,
    },
    "kitchen": {
        # Kitchen staff can view orders, mark ready
        Permission.ORDER_CREATE,
    },
    "expo": {
        # Expo can view all tickets, fire courses, move items
        Permission.ORDER_CREATE,
        Permission.ORDER_FIRE_COURSE,
        Permission.DRAFT_REASSIGN_TABLE,
    },
}


def get_permissions_for_role(role: str) -> Set[Permission]:
    """Get permissions for a given role"""
    return ROLE_PERMISSIONS.get(role.lower(), set())


def has_permission(required_permission: Permission, user_permissions: Set[Permission]) -> bool:
    """Check if user has required permission"""
    return required_permission in user_permissions


def require_permission(required_permission: Permission):
    """Dependency factory to check permissions"""
    async def check_permission(user_permissions: Set[Permission]) -> bool:
        if not has_permission(required_permission, user_permissions):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission required: {required_permission}",
            )
        return True
    return check_permission
