import asyncio
from typing import AsyncGenerator
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.main import app
from app.db import Base, get_db_session
from app.config import settings

# Force using SQLite in-memory database for local test runs
# This allows testing the API completely offline without Docker/Postgres running
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"
settings.DATABASE_URL = TEST_DATABASE_URL

# Create async engine for test SQLite DB
test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False}, # Required for SQLite async thread safety
)

# Async session factory for tests
TestSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False
)

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the session."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
    yield loop
    loop.close()

@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_test_db():
    """Build the database tables before running tests, and drop them after."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await test_engine.dispose()

@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide an async database session wrapped in an isolated transaction that rolls back after each test."""
    async with test_engine.connect() as connection:
        # Start transaction block
        transaction = await connection.begin()
        # Bind the session to the connection
        async_session = TestSessionLocal(bind=connection)
        
        try:
            yield async_session
        finally:
            # Roll back all operations
            await transaction.rollback()
            await async_session.close()

@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Provide an AsyncClient for testing API endpoints, overriding the DB dependency."""
    async def override_get_db_session():
        try:
            yield db_session
        finally:
            pass  # Handled by the fixture lifecycle

    app.dependency_overrides[get_db_session] = override_get_db_session
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as async_client:
        yield async_client
        
    app.dependency_overrides.clear()
