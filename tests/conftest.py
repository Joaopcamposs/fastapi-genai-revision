import os
import shutil
from pathlib import Path

TEST_DB_PATH = Path(__file__).parent / "test.db"
TEST_CHAT_HISTORY_DIR = Path(__file__).parent / "chat-history"
TEST_DB_PATH.unlink(missing_ok=True)
shutil.rmtree(TEST_CHAT_HISTORY_DIR, ignore_errors=True)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{TEST_DB_PATH}"
os.environ["CHAT_HISTORY_DIR"] = str(TEST_CHAT_HISTORY_DIR)
os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("GOOGLE_API_KEY", "test-key")

import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from infra.database import (
    Base,
    create_db_and_tables,
    dispose_engine,
    engine,
)
from main import app


@pytest_asyncio.fixture(scope="session", autouse=True)
async def _setup_db():
    await create_db_and_tables()
    yield
    await dispose_engine()
    TEST_DB_PATH.unlink(missing_ok=True)
    shutil.rmtree(TEST_CHAT_HISTORY_DIR, ignore_errors=True)


@pytest_asyncio.fixture(autouse=True)
async def _clean_tables():
    yield
    async with engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            await conn.execute(table.delete())
    shutil.rmtree(TEST_CHAT_HISTORY_DIR, ignore_errors=True)
    TEST_CHAT_HISTORY_DIR.mkdir(exist_ok=True)


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def auth_headers(client: AsyncClient) -> dict:
    """Register and log in a user, returning ready-to-use auth headers."""
    await client.post(
        "/users/", json={"email": "user@example.com", "password": "secret123"}
    )
    response = await client.post(
        "/auth/token",
        data={"username": "user@example.com", "password": "secret123"},
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
