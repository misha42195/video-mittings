import os
from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from api.database import Base, get_db
from api.main import app

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/video_meetings",
)

test_engine = create_async_engine(TEST_DATABASE_URL, pool_pre_ping=True)
TestSessionFactory = async_sessionmaker(test_engine, expire_on_commit=False)


@pytest.fixture(scope="session", autouse=True)
async def _prepare_database() -> AsyncIterator[None]:
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await test_engine.dispose()


@pytest.fixture(autouse=True)
async def _clean_tables() -> AsyncIterator[None]:
    yield
    async with test_engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            await conn.execute(table.delete())


@pytest.fixture
async def db() -> AsyncIterator[AsyncSession]:
    async with TestSessionFactory() as session:
        yield session


@pytest.fixture
async def client(db: AsyncSession) -> AsyncIterator[AsyncClient]:
    async def override_get_db() -> AsyncIterator[AsyncSession]:
        yield db

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
