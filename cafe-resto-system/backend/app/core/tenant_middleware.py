"""
Tenant context middleware for multi-tenant isolation
"""

from fastapi import Request, HTTPException, status
from fastapi.middleware import Middleware
from typing import Callable
import uuid
import structlog

from app.core.config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()


class TenantContextMiddleware(Middleware):
    """Middleware to extract and set tenant context"""
    
    async def dispatch(self, request: Request, call_next: Callable):
        # Extract tenant from header (X-Tenant-ID)
        tenant_id = request.headers.get(settings.TENANT_HEADER)
        
        # Extract tenant from subdomain (if header not present)
        if not tenant_id:
            host = request.headers.get("host", "")
            # Extract subdomain from host: tenant.example.com
            parts = host.split(".")
            if len(parts) > 2:
                potential_slug = parts[0]
                # In production, query database to resolve slug to tenant_id
                # For now, store in request state
                tenant_id = potential_slug
        
        # Store tenant context in request state
        request.state.tenant_id = tenant_id
        request.state.tenant_id_uuid = uuid.UUID(tenant_id) if tenant_id else None if isinstance(tenant_id, str) else tenant_id
        
        # Log tenant context
        logger.debug(f"Tenant context: {tenant_id}")
        
        response = await call_next(request)
        return response
