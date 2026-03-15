"""E2E test conftest — real FastAPI app with test database.

Uses httpx.AsyncClient with ASGITransport — no live server needed.
All middleware, auth, and error handlers run as they would in production.
"""

import os
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Override DATABASE_URL before importing the app
os.environ.setdefault(
    "DATABASE_URL",
    os.environ.get(
        "DATABASE_URL_TEST",
        "postgresql+asyncpg://postgres:postgres@localhost:5432/trading_platform_test",
    ),
)
# Ensure JWT secret is set for tests
os.environ.setdefault("AUTH_JWT_SECRET_KEY", "test-secret-key-for-e2e-tests")
os.environ.setdefault("ADMIN_SEED_PASSWORD", "changeme123456")

from app.common.base_model import Base
from app.main import app


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest_asyncio.fixture(scope="session")
async def setup_database():
    """Create all tables once per session, seed admin, drop after."""
    engine = create_async_engine(os.environ["DATABASE_URL"], echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Seed admin user for auth tests
    await _seed_admin(engine)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


async def _seed_admin(engine):
    """Create admin user if not exists."""
    from sqlalchemy import text

    import bcrypt

    password = "changeme123456"
    salt = bcrypt.gensalt(rounds=4)  # Fast for tests
    hashed = bcrypt.hashpw(password.encode(), salt).decode()

    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT COUNT(*) FROM users WHERE role = 'admin'"))
        count = result.scalar()
        if count and count > 0:
            return

        from datetime import datetime, timezone

        now = datetime.now(timezone.utc)
        user_id = uuid4()
        await conn.execute(
            text(
                "INSERT INTO users (id, email, username, password_hash, role, status, "
                "failed_login_count, created_at, updated_at) "
                "VALUES (:id, :email, :username, :password_hash, :role, :status, "
                ":failed_login_count, :created_at, :updated_at)"
            ),
            {
                "id": str(user_id),
                "email": "admin@ratatoskr.local",
                "username": "admin",
                "password_hash": hashed,
                "role": "admin",
                "status": "active",
                "failed_login_count": 0,
                "created_at": now,
                "updated_at": now,
            },
        )
        await conn.commit()


@pytest_asyncio.fixture
async def client(setup_database) -> AsyncClient:
    """Unauthenticated HTTP client hitting the real FastAPI app."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest_asyncio.fixture
async def auth_client(client) -> AsyncClient:
    """Authenticated HTTP client (logs in as admin, attaches JWT token)."""
    resp = await client.post("/api/v1/auth/login", json={
        "email": "admin@ratatoskr.local",
        "password": "changeme123456",
    })
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    token = resp.json()["data"]["accessToken"]
    client.headers["Authorization"] = f"Bearer {token}"
    yield client
