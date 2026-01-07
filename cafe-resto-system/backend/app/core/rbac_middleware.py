"""
RBAC middleware to enforce permissions on protected endpoints
"""

from fastapi import Request
from typing import Callable
import structlog
from app.core.permissions import get_permissions_for_role

logger = structlog.get_logger(__name__)


class RBACMiddleware:
    """Middleware to inject user permissions into request state"""

    def __init__(self, app):
        self.app = app

    async def dispatch(self, request: Request, call_next: Callable):
        # Get user role (will be properly injected by auth middleware)
        # For now, just get from request state if available
        role = getattr(request.state, "user_role", None)

        if role:
            permissions = get_permissions_for_role(role)
            request.state.user_permissions = permissions
            logger.debug(f"Set permissions for role {role}: {len(permissions)}")
        else:
            request.state.user_permissions = []
            logger.debug("No user role found, permissions set to empty")

        response = await call_next(request)
        return response
