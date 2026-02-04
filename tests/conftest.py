"""
Pytest configuration and fixtures for the test suite.

This module provides common fixtures for testing:
- Database session management with async SQLAlchemy
- Test client configuration
- Mock objects for external services
"""

# IMPORTANT: Set test environment variables FIRST, before any other imports
# This must happen at module load time before pytest_plugins are loaded
import os

# Bot token must be in valid format: {bot_id}:{alphanumeric_token}
# The token format is validated by aiogram, so we use a valid-looking format
os.environ.setdefault("BOT_TOKEN", "1234567890:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghi")
os.environ.setdefault("ADMIN_IDS", "[123456789]")
os.environ.setdefault("DB_HOST", "localhost")
os.environ.setdefault("DB_PORT", "5432")
os.environ.setdefault("DB_NAME", "test_db")
os.environ.setdefault("DB_USER", "test_user")
os.environ.setdefault("DB_PASSWORD", "test_password")
os.environ.setdefault("ACP_SERVER_URL", "http://localhost:8000")

# Now import everything else
import asyncio
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from sqlalchemy import Integer, String, BigInteger, TIMESTAMP, func
from sqlalchemy.ext.asyncio import (
    AsyncAttrs,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.pool import StaticPool
from datetime import datetime


# Test database URL - using SQLite for tests
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


class TestBase(AsyncAttrs, DeclarativeBase):
    """
    Test-specific base class for SQLAlchemy models.

    This mirrors the production Base class but is isolated for testing.
    """

    __abstract__ = True

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        server_default=func.now(),
        onupdate=func.now()
    )


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """
    Create an event loop for the entire test session.

    This fixture is required for pytest-asyncio to work properly
    with session-scoped async fixtures.
    """
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def async_engine():
    """
    Create an async engine for the test database.

    Uses SQLite in-memory database with StaticPool for testing.
    This ensures all connections share the same in-memory database.
    """
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )

    # Create all tables using TestBase
    async with engine.begin() as conn:
        await conn.run_sync(TestBase.metadata.create_all)

    yield engine

    # Drop all tables after tests
    async with engine.begin() as conn:
        await conn.run_sync(TestBase.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture(scope="session")
async def async_session_factory(async_engine) -> async_sessionmaker[AsyncSession]:
    """
    Create a session factory for the test database.
    """
    return async_sessionmaker(
        bind=async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )


@pytest_asyncio.fixture
async def db_session(
    async_session_factory: async_sessionmaker[AsyncSession],
) -> AsyncGenerator[AsyncSession, None]:
    """
    Create a database session for each test.

    Each test gets a fresh session that is rolled back after the test,
    ensuring test isolation.
    """
    async with async_session_factory() as session:
        yield session
        # Rollback any uncommitted changes
        await session.rollback()


@pytest.fixture
def mock_bot() -> MagicMock:
    """
    Create a mock bot instance for testing.

    This mock can be used to test handlers without actually
    sending messages to Telegram.
    """
    bot = MagicMock()
    bot.send_message = AsyncMock()
    bot.send_photo = AsyncMock()
    bot.send_document = AsyncMock()
    bot.edit_message_text = AsyncMock()
    bot.delete_message = AsyncMock()
    bot.answer_callback_query = AsyncMock()
    return bot


@pytest.fixture
def mock_message() -> MagicMock:
    """
    Create a mock Telegram message for testing handlers.
    """
    message = MagicMock()
    message.chat = MagicMock()
    message.chat.id = 123456789
    message.from_user = MagicMock()
    message.from_user.id = 123456789
    message.from_user.username = "test_user"
    message.from_user.first_name = "Test"
    message.from_user.last_name = "User"
    message.text = "test message"
    message.answer = AsyncMock()
    message.reply = AsyncMock()
    return message


@pytest.fixture
def mock_callback_query() -> MagicMock:
    """
    Create a mock callback query for testing inline keyboard handlers.
    """
    callback = MagicMock()
    callback.id = "test_callback_id"
    callback.data = "test_data"
    callback.message = MagicMock()
    callback.message.chat = MagicMock()
    callback.message.chat.id = 123456789
    callback.from_user = MagicMock()
    callback.from_user.id = 123456789
    callback.answer = AsyncMock()
    callback.message.edit_text = AsyncMock()
    return callback


@pytest.fixture
def sample_user_data() -> dict:
    """
    Provide sample user data for testing.
    """
    return {
        "telegram_id": 123456789,
        "username": "test_user",
        "first_name": "Test",
        "last_name": "User",
        "referral_id": None,
    }


@pytest.fixture
def mock_acp_context() -> MagicMock:
    """
    Create a mock ACP context for testing agent handlers.
    """
    context = MagicMock()
    context.run_id = "test-run-123"
    context.agent_name = "test_agent"
    context.metadata = {}
    return context


@pytest.fixture
def mock_acp_message() -> dict:
    """
    Create a sample ACP message structure for testing.
    """
    return {
        "role": "user",
        "parts": [
            {
                "type": "text",
                "content": "Hello, test message",
            }
        ],
    }


# Pytest configuration
def pytest_configure(config):
    """
    Configure pytest with custom markers.
    """
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "unit: marks tests as unit tests"
    )
