"""
Database configuration and session management
"""

from sqlmodel import SQLModel
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
import structlog

from app.core.config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()

# Create async engine
async_engine = create_async_engine(
    settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"),
    echo=settings.DEBUG,
    future=True,
)

# Create async session factory
async_session_maker = async_sessionmaker(
    bind=async_engine,
    expire_on_commit=False,
)


async def init_db():
    """Initialize database tables"""
    async with async_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    logger.info("Database tables created")


async def get_session():
    """Dependency to get database session"""
    async with async_session_maker() as session:
        yield session
