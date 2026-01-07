"""
Hospitality OS - Main Application Entry Point
Multi-tenant restaurant POS system
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import structlog

from app.core.config import get_settings
from app.core.database import get_session
from app.api import (
    tenants, users, users_auth, locations, tables,
    table_sessions, drafts, menu_categories, menu_items,
    menu_stations, kitchen_courses, tickets, websockets,
    orders, payments, receipts, shifts
)

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
)

logger = structlog.get_logger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("Initializing Hospitality OS backend")
    # Tables are created by Alembic migrations, not auto-generated
    logger.info("Database managed by Alembic migrations")

    yield

    # Shutdown
    logger.info("Shutting down Hospitality OS backend")


# Create FastAPI application
app = FastAPI(
    title="Hospitality OS API",
    description="Multi-tenant restaurant POS system with draft-first QR ordering",
    version="1.0.0",
    lifespan=lifespan,
)

# Configure middleware stack
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Include routers
app.include_router(tenants.router, prefix="/api/v1/tenants", tags=["tenants"])
app.include_router(users_auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(users.router, prefix="/api/v1/users", tags=["users"])
app.include_router(locations.router, prefix="/api/v1/locations", tags=["locations"])
app.include_router(tables.router, prefix="/api/v1/tables", tags=["tables"])
app.include_router(table_sessions.router, prefix="/api/v1/table-sessions", tags=["table-sessions"])
app.include_router(drafts.router, prefix="/api/v1/drafts", tags=["drafts"])
app.include_router(menu_categories.router, prefix="/api/v1/menu-categories", tags=["menu-categories"])
app.include_router(menu_items.router, prefix="/api/v1/menu-items", tags=["menu-items"])
app.include_router(menu_stations.router, prefix="/api/v1/menu-stations", tags=["menu-stations"])
app.include_router(kitchen_courses.router, prefix="/api/v1/kitchen-courses", tags=["kitchen-courses"])
app.include_router(tickets.router, prefix="/api/v1/tickets", tags=["tickets"])
app.include_router(websockets.router, prefix="/api/v1/ws", tags=["websockets"])
app.include_router(orders.router, prefix="/api/v1/orders", tags=["orders"])
app.include_router(payments.router, prefix="/api/v1/payments", tags=["payments"])
app.include_router(receipts.router, prefix="/api/v1/receipts", tags=["receipts"])
app.include_router(shifts.router, prefix="/api/v1/shifts", tags=["shifts"])


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "hospitality-os-api"}


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Hospitality OS API",
        "version": "1.0.0",
        "docs": "/docs",
    }


if __name__ == "__main__":
    import uvicorn
    import asyncio
    asyncio.run(uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.ENVIRONMENT == "development",
        log_level="info",
    ))
