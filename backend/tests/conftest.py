import pytest
import pytest_asyncio
import httpx
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from main import app
from core.database import get_db
from core.config import settings
from sqlalchemy.pool import NullPool

# Create a dedicated test engine
test_engine = create_async_engine(settings.DATABASE_URL, poolclass=NullPool)

@pytest_asyncio.fixture()
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Creates an isolated database session for each test.
    Instead of committing to the DB, it creates a transaction and rolls it back
    after the test is finished. This leaves the database untouched.
    """
    async with test_engine.connect() as conn:
        # Start an outer transaction
        trans = await conn.begin()
        
        # Bind session to the connection with the active transaction
        session_maker = async_sessionmaker(
            bind=conn,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
            join_transaction_mode="create_savepoint"
        )
        
        async with session_maker() as session:
            yield session
            
        # Roll back everything that happened during the test
        await trans.rollback()

@pytest_asyncio.fixture()
async def client(db_session: AsyncSession) -> AsyncGenerator[httpx.AsyncClient, None]:
    """
    TestClient that uses the isolated db_session.
    """
    from httpx import ASGITransport
    
    async def override_get_db():
        yield db_session
        
    app.dependency_overrides[get_db] = override_get_db
    
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
        
    app.dependency_overrides.clear()
