import os
import sys
from pathlib import Path
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import Base, get_db
from app.main import app
from app.models import User
from app.services.auth_service import hash_password


def _get_test_db_url() -> str:
    return os.getenv(
        "TEST_DATABASE_URL",
        "postgresql+asyncpg://fting@localhost:5432/hongshing_test",
    )


@pytest.fixture(autouse=True)
def _no_real_sms(monkeypatch):
    """Never hit AWS SNS during tests. The removed hardcoded-OTP demo path used to
    short-circuit SMS in send-otp; now send-otp always calls send_sms, so stub it.
    auth.py imports send_sms from this module at call time, so patching the module
    attribute is sufficient."""
    monkeypatch.setattr("app.services.sms_service.send_sms", lambda *a, **k: None)


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Each test gets its own engine, session, and transaction."""
    engine = create_async_engine(_get_test_db_url(), echo=False)

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    session = session_factory()

    try:
        yield session
    finally:
        await session.rollback()
        await session.close()
        # Drop all tables and dispose
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await engine.dispose()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """HTTP test client with DB dependency overridden to the test session."""

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def owner_user(db_session: AsyncSession) -> User:
    user = User(
        email="owner@hongshing.com",
        name="Owner",
        password_hash=hash_password("admin123"),
        role="owner",
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest_asyncio.fixture
async def manager_user(db_session: AsyncSession) -> User:
    user = User(
        email="manager@hongshing.com",
        name="Manager",
        password_hash=hash_password("manager123"),
        role="manager",
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest_asyncio.fixture
async def staff_user(db_session: AsyncSession) -> User:
    user = User(
        email="staff@hongshing.com",
        name="Staff",
        password_hash=hash_password("staff123"),
        role="staff",
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest_asyncio.fixture
async def customer_user(db_session: AsyncSession) -> User:
    user = User(phone="+16475551234", name="Test Customer", role="customer")
    db_session.add(user)
    await db_session.flush()
    return user
