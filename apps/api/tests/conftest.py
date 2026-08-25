import os
import shutil
from collections.abc import AsyncIterator, Awaitable, Callable
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from api.config import get_settings
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
    # clean file storage (orphan files from meeting_files tests)
    storage_root = Path(get_settings().storage_root)
    if storage_root.exists():
        for child in storage_root.iterdir():
            if child.is_dir():
                shutil.rmtree(child)
            else:
                child.unlink(missing_ok=True)


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


async def _register_and_login(
    client: AsyncClient, email: str, password: str = "supersecret123"
) -> str:
    await client.post("/auth/register", json={"email": email, "password": password})
    login_response = await client.post(
        "/auth/login", data={"username": email, "password": password}
    )
    token: str = login_response.json()["access_token"]
    return token


@pytest.fixture
def register_user(client: AsyncClient) -> Callable[[str], Awaitable[dict[str, str]]]:
    """Registers+logs in a fresh user and returns Bearer auth headers for them."""

    async def _register(email: str) -> dict[str, str]:
        token = await _register_and_login(client, email)
        return {"Authorization": f"Bearer {token}"}

    return _register


@pytest.fixture
async def auth_headers(
    register_user: Callable[[str], Awaitable[dict[str, str]]],
) -> dict[str, str]:
    return await register_user("meetings-owner@example.com")
