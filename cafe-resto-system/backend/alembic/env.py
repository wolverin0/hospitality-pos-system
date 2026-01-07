"""Alembic environment configuration"""

from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
import asyncio
import sys
import os

# Add your model's MetaData object here
from app.core.database import async_engine
from app.models.tenant import Tenant

# this is the Alembic Config object
config = context.config

# Interpret the config file for Python logging
# fileConfig(config.config_file_name)

target_metadata = Tenant.metadata


def get_url():
    """Get database URL from config"""
    return config.get_main_option("sqlalchemy", "url")


def run_migrations_offline():
    """Run migrations in 'offline' mode"""
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations():
    """Run migrations in 'online' mode"""
    connectable = async_engine(url=get_url())

    async def run_migrations():
        async with connectable.connect() as connection:
            await connection.run_sync(do_run_migrations_sync)

    asyncio.run(run_migrations())


def do_run_migrations_sync():
    """Run migrations synchronously for initial setup"""
    # Create sync engine for Alembic
    from sqlalchemy import create_engine
    url = get_url().replace("postgresql+asyncpg://", "postgresql://")
    sync_engine = create_engine(url)

    with sync_engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if __name__ == "__main__":
    do_run_migrations_sync()
