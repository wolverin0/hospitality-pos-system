"""
Test configuration for pytest
"""

import pytest
import os
from sqlalchemy import create_engine
from sqlmodel import SQLModel, Session
from typing import Generator

# Test environment variables
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["REDIS_URL"] = "redis://localhost:6379"
os.environ["SECRET_KEY"] = "test-secret-key"
os.environ["JWT_SECRET_KEY"] = "test-jwt-secret"


# Create test engine using in-memory SQLite for unit tests
test_engine = create_engine(
    "sqlite:///:memory:",
    echo=False,
    future=True,
    connect_args={"check_same_thread": False},
)


@pytest.fixture(scope="function")
def db() -> Generator[Session, None, None]:
    """Create a clean database session for each test"""
    # Create all tables
    SQLModel.metadata.create_all(test_engine)

    # Create session
    with Session(test_engine) as session:
        yield session

    # Cleanup
    SQLModel.metadata.drop_all(test_engine)
